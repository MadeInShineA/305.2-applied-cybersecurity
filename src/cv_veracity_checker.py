import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain.agents import create_agent
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_openrouter import ChatOpenRouter

# Resolve project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import Config


class CvVerifier:
    def __init__(self, config: Config):
        self.config = config

        self.llm = ChatOpenRouter(
            model="nvidia/nemotron-3-nano-30b-a3b", temperature=0, max_tokens=4096
        )

        self.search_tool = DuckDuckGoSearchResults()

        self.system_prompt = """
            You are an expert HR background verification assistant.
            Your task is to verify the authenticity of a CV provided as JSON.
            Extracted keys: 'personne', 'formation', 'experience_professionnelle', 'competences', 'langues', 'certifications', 'projets_notables', 'centres_interet'.

            VERIFICATION PROCESS:
            1. Identify key verifiable claims (companies, job titles, degrees, certifications, publications, major projects).
            2. Use the search tool to cross-reference these claims. Run targeted queries.
            3. Evaluate public evidence, consistency, and plausibility.
            4. Ignore personal/private details (phone, email, salary, home address).
            5. Score the CV from 0 to 100:
            - 0-20: Highly suspicious / likely fabricated
            - 21-40: Major inconsistencies / mostly unverifiable
            - 41-60: Moderate issues / mixed evidence
            - 61-80: Mostly accurate / minor gaps
            - 81-100: Highly credible / publicly verified

            OUTPUT RULES:
            - You MUST use the search tool to verify at least 2-3 major claims before scoring.
            - Think step-by-step in your internal reasoning.
            - In your FINAL response, output ONLY the numeric score.
            - Do NOT include explanations, markdown, or extra text in the FINAL response."""
        self.agent = create_agent(
            model=self.llm,
            tools=[self.search_tool],
            system_prompt=self.system_prompt,
        )

    def _save_debug_trace(
        self, response: dict, log_path: Path, final_score: Optional[int] = None
    ) -> None:
        """
        Writes the agent's execution trace as a structured JSON file.
        """
        trace_steps = []

        for msg in response.get("messages", []):
            msg_type = getattr(msg, "type", None)
            timestamp = datetime.now().isoformat()

            if msg_type == "human":
                continue  # Skip input echoing

            elif msg_type == "ai":
                # Capture reasoning
                content = getattr(msg, "content", "")
                if content and isinstance(content, str) and content.strip():
                    trace_steps.append(
                        {
                            "step_type": "reasoning",
                            "timestamp": timestamp,
                            "content": content.strip(),
                        }
                    )

                # Capture tool calls
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        trace_steps.append(
                            {
                                "step_type": "tool_call",
                                "timestamp": timestamp,
                                "tool_name": tc.get("name", "unknown"),
                                "args": tc.get("args", {}),
                            }
                        )

            elif msg_type == "tool":
                tool_name = getattr(msg, "name", "unknown")
                raw_content = str(msg.content)
                # Truncate long outputs to prevent massive JSON files
                truncated = (
                    raw_content[:500] + "... [truncated]"
                    if len(raw_content) > 500
                    else raw_content
                )
                trace_steps.append(
                    {
                        "step_type": "observation",
                        "timestamp": timestamp,
                        "tool_name": tool_name,
                        "content": truncated,
                    }
                )

        # Assemble structured payload
        log_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.llm.model_name
                if hasattr(self.llm, "model_name")
                else "unknown",
                "final_score": final_score,
            },
            "execution_trace": trace_steps,
        }

        # Write to JSON
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

    def verify_cv(
        self, cv_json: dict, debug: bool = False, log_path: Optional[Path] = None
    ) -> int:
        """
        Verifies the CV and returns an integer veracity score (0-100).

        Args:
            cv_json: The CV data as a dictionary.
            debug: If True, saves the execution trace to `log_path`.
            log_path: Path to save the debug log. Defaults to assets/cv_veracity_check_logs.json.

        Returns:
            An integer score between 0 and 100.
        """
        if log_path is None:
            log_path = project_root / "assets" / "cv_veracity_check_logs.json"

        try:
            response = self.agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Verify this CV and provide a score:\n{cv_json}",
                        }
                    ]
                }
            )

            # Parse score
            last_message = response["messages"][-1]
            raw_output = last_message.content.strip()
            numbers = re.findall(r"\b\d{1,3}\b", str(raw_output))

            if not numbers:
                raise RuntimeError(
                    "The agent didn't return a number for the cv veracity"
                )
            else:
                score = max(0, min(100, int(numbers[-1])))

            # Save trace if debug is enabled
            if debug:
                self._save_debug_trace(response, log_path, final_score=score)

            return score

        except Exception as e:
            raise RuntimeError(f"CV verification failed: {e}")


if __name__ == "__main__":
    try:
        from config import load_config
    except ModuleNotFoundError:
        from src.config import load_config

    config = load_config()
    cv_verifier = CvVerifier(config)

    cv_json_path = project_root / "assets" / "cv_2.json"
    if not cv_json_path.exists():
        raise FileNotFoundError(
            f"CV JSON not found at: {cv_json_path}. Please run extraction first."
        )

    with open(cv_json_path, "r", encoding="utf-8") as f:
        cv_json = json.load(f)

    debug_log_path = project_root / "assets" / "cv_2_veracity_check_logs.json"

    # Run verification with structured JSON logging
    score = cv_verifier.verify_cv(cv_json, debug=True, log_path=debug_log_path)

    print(f"Verification complete. Score: {score}/100")
    print(f"Execution trace saved to: {debug_log_path}")
