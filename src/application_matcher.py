"""
Application matcher module for the email agent application.

This module provides the ApplicationMatcher class which compares candidate CVs
against available job offers to find the best match. It uses an LLM to evaluate
the relevance between CV data and job descriptions, producing a match score
along with strengths, weaknesses, and recommendations.

The matching process:
1. Fetch all job offers from kDrive
2. Compare each CV against each job offer using LLM
3. Return the best matching job offer with evaluation details
"""

import json
from typing import Dict, Any, List, Tuple, Optional

from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from src.k_drive_tools import KDriveTools
from src.config import Config


class ApplicationMatcher:
    """
    Matches candidate CVs against available job offers using LLM evaluation.

    This class provides functionality to compare a candidate's CV (in JSON format)
    against all available job offers stored in kDrive. It uses an LLM to perform
    detailed evaluation of the match, providing:
    - A match score (0-100)
    - Candidate strengths relative to the job
    - Candidate weaknesses or gaps
    - A recommendation for the application

    The class fetches job offers from kDrive on each comparison to ensure
    up-to-date listings. It uses temperature=0 for deterministic evaluation.

    Attributes:
        config: Configuration object containing LLM settings.
        kdrive_tools: KDriveTools instance for accessing job offers.
        llm: ChatOpenRouter instance for LLM-based evaluation.
        output_parser: JsonOutputParser for parsing LLM JSON responses.

    Example:
        >>> matcher = ApplicationMatcher(config, kdrive_tools)
        >>> score, offer, report = matcher.compare_with_offers(cv_json)
        >>> print(f"Best match: {offer['name']} ({score}/100)")
    """

    def __init__(self, config: Config, kdrive_tools: KDriveTools) -> None:
        """
        Initialize the ApplicationMatcher with configuration and kDrive tools.

        Args:
            config: Config object containing OpenRouter API settings.
            kdrive_tools: KDriveTools instance for accessing job offers.
        """
        self.config = config
        self.kdrive_tools = kdrive_tools
        # Using a temperature of 0 for deterministic evaluation
        self.llm = ChatOpenRouter(model=self.config.openrouter_model, temperature=0)
        self.output_parser = JsonOutputParser()

    def get_job_offers(self) -> List[Dict[str, Any]]:
        """
        Fetch and decode all job offer files from kDrive.

        This method retrieves all files from the configured job offers
        directory in kDrive. It reads each file's content and returns
        a list of job offer objects containing the name, ID, and content.

        Returns:
            List[Dict[str, Any]]: A list of job offer dictionaries, each containing:
                - name: The filename of the job offer
                - id: The kDrive file ID
                - content: The text content of the job offer

        Note:
            - Only files (not directories) are included in the results.
            - File content is decoded as UTF-8, with errors ignored for
              corrupted files.
            - Empty files or files that fail to load are skipped.
        """
        # Get the kDrive directory ID for job offers from configuration
        directory_id = self.config.kdrive_job_offers_directory_id
        # List all files in the job offers directory
        files = self.kdrive_tools.list_files(directory_id)

        # Process each file to extract job offer content
        job_offers = []
        for file in files:
            # Only process actual files (not subdirectories)
            if file.get("type") == "file":
                file_id = file.get("id")
                # Extract file content from kDrive
                content_chunks = self.kdrive_tools.extract_file_content(file_id)
                if content_chunks:
                    # Decode bytes to string, ignoring potential encoding errors
                    content_str = b"".join(content_chunks).decode(
                        "utf-8", errors="ignore"
                    )
                    # Add the job offer to our list
                    job_offers.append(
                        {
                            "name": file.get("name"),
                            "id": file_id,
                            "content": content_str,
                        }
                    )
        return job_offers

    def compare_with_offers(
        self, cv_json: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
        """
        Compare a CV against all available job offers and return the best match.

        This method iterates through all job offers from kDrive and evaluates
        how well the candidate's CV matches each position. It uses an LLM to
        perform detailed evaluation including scoring, strength/weakness
        identification, and recommendation generation.

        The method ensures that at least the first job offer is always returned,
        even if no offers score above 0.

        Args:
            cv_json: The candidate's CV data as a dictionary (from cv_extractor).

        Returns:
            Tuple[int, Dict[str, Any], Dict[str, Any]]: A tuple containing:
                - match_score: Integer score (0-100) of the best match
                - best_match_offer: Dictionary with job offer details (name, id, content)
                - best_report: Dictionary with evaluation (score, strengths, weaknesses, recommendation)

        Note:
            - If no job offers are found, returns a score of 0 with an empty offer
              and a "No job offers found" recommendation.
            - The comparison is case-sensitive for content matching but the LLM
              handles semantic evaluation.
        """
        # Fetch all available job offers from kDrive
        job_offers = self.get_job_offers()

        # Handle case with no job offers
        if not job_offers:
            return 0, {}, {"recommendation": "No job offers found in the system."}

        # Initialize with the first offer to ensure we always return something
        best_match_score = -1
        best_match_offer = job_offers[0]
        best_report = {
            "match_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendation": "Initial processing state.",
        }

        # Evaluate the CV against each job offer
        for offer in job_offers:
            score, report = self._evaluate_match(cv_json, offer)

            # If the current match is better than the previous best, update
            if score > best_match_score:
                best_match_score = score
                best_match_offer = offer
                best_report = report

        return best_match_score, best_match_offer, best_report

    def _evaluate_match(
        self, cv_json: Dict[str, Any], offer: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Invoke the LLM to score the relevance between a CV and a job description.

        This internal method sends the CV and job description to the LLM
        with a detailed prompt requesting evaluation in a specific JSON format.
        The LLM analyzes the match and provides a score along with strengths,
        weaknesses, and a recommendation.

        Args:
            cv_json: The candidate's CV data as a dictionary.
            offer: The job offer dictionary containing name, id, and content.

        Returns:
            Tuple[int, Dict[str, Any]]: A tuple containing:
                - score: Integer match score (0-100)
                - report: Dictionary with evaluation details

        Note:
            - The LLM is instructed to return only valid JSON.
            - If parsing fails or the LLM returns invalid JSON, a fallback
              error report is returned with score 0.
            - The output parser ensures clean JSON output from the LLM.
        """
        # Prepare CV and job description for the prompt
        cv_data_str = json.dumps(cv_json, indent=2)
        job_description = offer.get("content", "Empty job description")

        # Construct the evaluation prompt with explicit JSON schema
        prompt_text = (
            "You are a job matching expert. Evaluate the candidate's CV against the job offer.\n\n"
            f"CANDIDATE CV (JSON):\n{cv_data_str}\n\n"
            f"JOB OFFER:\n{job_description}\n\n"
            "Provide your evaluation as a strict JSON object with this exact structure:\n"
            "{\n"
            '  "match_score": <integer 0-100>,\n'
            '  "strengths": [<list of strings>],\n'
            '  "weaknesses": [<list of strings>],\n'
            '  "recommendation": "<string>"\n'
            "}\n"
            "Return only the JSON object."
        )

        try:
            # Prepare messages: SystemMessage for role, HumanMessage for task
            messages = [
                SystemMessage(
                    content="You are a strict recruitment AI that outputs only JSON."
                ),
                HumanMessage(content=prompt_text),
            ]

            # Build the chain: LLM -> output parser for automated JSON cleaning
            chain = self.llm | self.output_parser
            report_json = chain.invoke(messages)

            # Extract and ensure the score is an integer
            score = int(report_json.get("match_score", 0))
            return score, report_json

        except Exception as e:
            # Fallback in case of LLM failure or parsing error
            error_report = {
                "match_score": 0,
                "strengths": [],
                "weaknesses": [f"Processing error: {str(e)}"],
                "recommendation": "Error during LLM evaluation.",
            }
            return 0, error_report
