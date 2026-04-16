import json
from typing import Dict, Any, List, Tuple
from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage
from src.k_drive_tools import KDriveTools
from src.config import Config


class ApplicationMatcher:
    def __init__(self, config: Config, kdrive_tools: KDriveTools):
        self.config = config
        self.kdrive_tools = kdrive_tools
        self.llm = ChatOpenRouter(model="nvidia/nemotron-3-nano-30b-a3b", temperature=0)

    def get_job_offers(self) -> List[Dict[str, Any]]:
        directory_id = self.config.kdrive_job_offers_directory_id
        files = self.kdrive_tools.list_files(directory_id)

        job_offers = []
        for file in files:
            if file.get("type") == "file":
                file_id = file.get("id")
                content = self.kdrive_tools.extract_file_content(file_id)
                if content:
                    content_str = b"".join(content).decode("utf-8", errors="ignore")
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
    ) -> Tuple[int, Dict[str, Any], str]:
        job_offers = self.get_job_offers()

        if not job_offers:
            return 0, {}, "No job offers found"

        best_match_score = 0
        best_match_offer = None
        best_report = None

        for offer in job_offers:
            score, report = self._evaluate_match(cv_json, offer)
            if score > best_match_score:
                best_match_score = score
                best_match_offer = offer
                best_report = report

        return best_match_score, best_match_offer, best_report

    def _evaluate_match(
        self, cv_json: Dict[str, Any], offer: Dict[str, Any]
    ) -> Tuple[int, str]:
        cv_str = json.dumps(cv_json, indent=2)
        offer_content = offer.get("content", "")

        prompt = f"""You are a job matching expert. Evaluate how well a candidate's CV matches a job offer.

CV (JSON format):
{cv_str}

Job Offer:
{offer_content}

Provide your evaluation as a JSON object with the following structure:
{{
    "match_score": <integer 0-100>,
    "strengths": [<list of matching strengths>],
    "weaknesses": [<list of missing requirements or gaps>],
    "recommendation": "<brief recommendation>"
}}

Only respond with the JSON object, no other text."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end != 0:
                report_json = json.loads(response_text[json_start:json_end])
                return report_json.get("match_score", 0), report_json
            else:
                return 0, {"error": "Failed to parse LLM response"}
        except Exception as e:
            return 0, {"error": str(e)}
