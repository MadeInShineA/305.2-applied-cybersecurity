"""
Application matcher module for the email agent application.

This module provides the ApplicationMatcher class which compares candidate CVs
against available job offers to find the best match. It uses an LLM to evaluate
the relevance between CV data and job descriptions (extracted from PDFs), producing
a match score along with strengths, weaknesses, and recommendations.

The matching process:
1. Compare each CV against each job offer using LLM
2. Return the best matching job offer with evaluation details
"""

import json
from typing import Dict, List, Any, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.k_drive_tools import KDriveTools
from src.config import Config


class MatchReportSchema(BaseModel):
    """Pydantic model for job match evaluation report."""

    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Match score between 0 and 100 indicating how well the CV fits the job offer.",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="List of candidate's strengths relative to the job requirements.",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="List of candidate's weaknesses or gaps relative to the job requirements.",
    )
    recommendation: str = Field(
        ..., description="Final recommendation or conclusion regarding the application."
    )


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
        self.llm = ChatOpenAI(
            model=self.config.infomaniak_model,
            temperature=0,
            openai_api_key=self.config.infomaniak_ai_api_key,
            openai_api_base=self.config.infomaniak_base_url,
        )
        self.llm = self.llm.with_structured_output(MatchReportSchema)

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
        job_offers = self.kdrive_tools.get_job_offers()

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
            "Extract the match score, strengths, weaknesses, and recommendation based on the provided schema."
        )

        try:
            messages = [
                SystemMessage(
                    content="You are a strict data processor evaluating candidate profiles against job descriptions. "
                    "Output ONLY data conforming to the schema."
                ),
                HumanMessage(content=prompt_text),
            ]

            # Invoke structured LLM; returns a validated MatchReportSchema Pydantic object
            report_pydantic = self.llm.invoke(messages)

            # Convert Pydantic object to dictionary
            report_json = report_pydantic.model_dump()
            score = report_json["match_score"]

            return score, report_json

        except Exception as e:
            raise RuntimeError(f"Evaluation validation failed: {e}")
