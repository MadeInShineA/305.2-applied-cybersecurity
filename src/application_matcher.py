import json
from typing import Dict, Any, List, Tuple
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from src.k_drive_tools import KDriveTools
from src.config import Config


class ApplicationMatcher:
    def __init__(self, config: Config, kdrive_tools: KDriveTools):
        self.config = config
        self.kdrive_tools = kdrive_tools
        # Using a temperature of 0 for deterministic evaluation
        self.llm = ChatOpenRouter(model=self.config.openrouter_model, temperature=0)
        self.output_parser = JsonOutputParser()

    def get_job_offers(self) -> List[Dict[str, Any]]:
        """Fetch and decode all job offer files from kDrive."""
        directory_id = self.config.kdrive_job_offers_directory_id
        files = self.kdrive_tools.list_files(directory_id)

        job_offers = []
        for file in files:
            if file.get("type") == "file":
                file_id = file.get("id")
                content_chunks = self.kdrive_tools.extract_file_content(file_id)
                if content_chunks:
                    # Decode bytes to string, ignoring potential corruption
                    content_str = b"".join(content_chunks).decode(
                        "utf-8", errors="ignore"
                    )
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
        Ensures that at least the first offer is returned if no scores are > 0.
        """
        job_offers = self.get_job_offers()

        if not job_offers:
            return 0, {}, {"recommendation": "No job offers found in the system."}

        # Initialize with the first offer to avoid returning None
        best_match_score = -1
        best_match_offer = job_offers[0]
        best_report = {
            "match_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendation": "Initial processing state.",
        }

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
        """Invoke the LLM to score the relevance between a CV and a job description."""
        cv_data_str = json.dumps(cv_json, indent=2)
        job_description = offer.get("content", "Empty job description")

        # Instruction with explicit JSON schema for the parser
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
            # Using SystemMessage for role definition and HumanMessage for the task
            messages = [
                SystemMessage(
                    content="You are a strict recruitment AI that outputs only JSON."
                ),
                HumanMessage(content=prompt_text),
            ]

            # Use the chain with the parser for automated cleaning of the LLM output
            chain = self.llm | self.output_parser
            report_json = chain.invoke(messages)

            # Ensure the score is an integer
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
