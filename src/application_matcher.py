"""
Application matcher module for the email agent application.

This module provides the ApplicationMatcher class which compares candidate CVs
against available job offers to find the best match. It uses an LLM to evaluate
the relevance between CV data and job descriptions (extracted from PDFs), producing
a match score along with strengths, weaknesses, and recommendations.

The matching process:
1. Fetch all job offer PDFs from kDrive
2. Extract text from each PDF using pdfplumber
3. Compare each CV against each job offer using LLM
4. Return the best matching job offer with evaluation details
"""

import io
import json
import re
from typing import Dict, Any, List, Tuple

import pdfplumber
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from src.k_drive_tools import KDriveTools
from src.config import Config


class ApplicationMatcher:
    """
    Matches candidate CVs against available job offers using LLM evaluation.

    This class provides functionality to compare a candidate's CV (in JSON format)
    against all available job offers stored in kDrive as PDF files. It uses an LLM
    to perform detailed evaluation of the match, providing:
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
        Fetch and extract text from all job offer PDFs from kDrive.

        This method retrieves all PDF files from the configured job offers
        directory in kDrive. It extracts the text content from each PDF using
        pdfplumber and returns a list of job offer objects containing the name,
        ID, and extracted text content.

        The method:
        - Filters for PDF files only (ignores directories and non-PDF files)
        - Extracts text from all pages, concatenating with double newlines
        - Only includes offers where text was successfully extracted
        - Handles extraction errors gracefully, printing warnings and skipping failed files

        Returns:
            List[Dict[str, Any]]: A list of job offer dictionaries, each containing:
                - name: The filename of the job offer PDF
                - id: The kDrive file ID
                - content: The extracted text content from the PDF

        Note:
            - Only PDF files are processed (filtered by .pdf extension)
            - Empty PDFs or those that fail extraction are skipped
            - Text is extracted page-by-page and concatenated
        """
        # Get the kDrive directory ID for job offers from configuration
        directory_id = self.config.kdrive_job_offers_directory_id
        # List all files in the job offers directory
        files = self.kdrive_tools.list_files(directory_id)

        # Process each file to extract job offer content
        job_offers = []
        for file in files:
            # Filter for PDF files to avoid unnecessary processing
            if file.get("type") == "file" and file.get("name", "").lower().endswith(
                ".pdf"
            ):
                file_id = file.get("id")
                # Extract file content from kDrive
                content_chunks = self.kdrive_tools.extract_file_content(file_id)
                if content_chunks:
                    # Combine byte chunks into a single PDF
                    pdf_bytes = b"".join(content_chunks)
                    try:
                        # Open PDF and extract text from all pages
                        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                            # Extract and concatenate text from all non-empty pages
                            extracted_text = "\n\n".join(
                                page.extract_text()
                                for page in pdf.pages
                                if page.extract_text()
                            )

                        # Only add offers with meaningful extracted text
                        if extracted_text.strip():
                            job_offers.append(
                                {
                                    "name": file.get("name"),
                                    "id": file_id,
                                    "content": extracted_text,
                                }
                            )
                    except Exception as e:
                        # In production, replace with proper logging: logger.warning(...)
                        print(
                            f"Warning: Failed to extract text from PDF {file.get('name')}: {e}"
                        )
                        continue
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
        # Fetch all available job offers from kDrive (as PDF text)
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

        This internal method sends the CV and job description (extracted from PDF)
        to the LLM with a detailed prompt requesting evaluation in a specific JSON
        format. The LLM analyzes the match and provides a score along with strengths,
        weaknesses, and a recommendation.

        The method uses regex parsing instead of JsonOutputParser to handle cases
        where the LLM might include reasoning text before the JSON output.

        Args:
            cv_json: The candidate's CV data as a dictionary.
            offer: The job offer dictionary containing name, id, and extracted content.

        Returns:
            Tuple[int, Dict[str, Any]]: A tuple containing:
                - score: Integer match score (0-100)
                - report: Dictionary with evaluation details

        Note:
            - The LLM is instructed to return only valid JSON without explanations
            - Regex extraction is used to handle potential reasoning text in output
            - If parsing fails, a RuntimeError is raised
        """
        # Prepare CV and job description for the prompt
        cv_data_str = json.dumps(cv_json, indent=2)
        # Get extracted text from the job offer PDF
        job_description = offer.get("content", "Empty job description")

        # Strict prompt to prevent chain of thought reasoning in output
        prompt_text = (
            "Evaluate candidate CV against job offer.\n\n"
            f"CANDIDATE CV:\n{cv_data_str}\n\n"
            f"JOB OFFER:\n{job_description}\n\n"
            "Return ONLY a valid JSON object. No explanation. No markdown formatting. No reasoning. Use exactly this structure:\n"
            "{\n"
            '  "match_score": 0,\n'
            '  "strengths": [""],\n'
            '  "weaknesses": [""],\n'
            '  "recommendation": ""\n'
            "}"
        )

        try:
            # Prepare messages: SystemMessage for role, HumanMessage for task
            messages = [
                SystemMessage(
                    content="You are a strict data processor. Output ONLY raw JSON."
                ),
                HumanMessage(content=prompt_text),
            ]

            # Invoke LLM without the strict output parser to handle raw text
            response = self.llm.invoke(messages)
            raw_output = response.content

            # Extract JSON payload using regex to bypass any leaked reasoning
            json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)

            if not json_match:
                raise ValueError(f"No JSON object found in LLM output: {raw_output}")

            # Parse the extracted JSON string
            report_json = json.loads(json_match.group(0))

            # Extract and ensure the score is an integer
            score = int(report_json.get("match_score", 0))
            return score, report_json

        except Exception as e:
            raise RuntimeError(f"Evaluation failed: {e}")
