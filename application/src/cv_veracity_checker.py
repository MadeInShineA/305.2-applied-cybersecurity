"""
CV veracity checker module for the email agent application.

This module provides the CvVeracityChecker class which verifies the authenticity
of CV data by cross-referencing claims against web searches. It uses a LangChain
agent with DuckDuckGo search capabilities to validate information such as
companies, job titles, degrees, certifications, and other verifiable claims.

The verification process:
1. Identify key verifiable claims from the CV
2. Use web search to cross-reference these claims
3. Evaluate evidence for consistency and plausibility
4. Score the CV from 0-100 based on verification results
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from langchain.agents import create_agent
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from requests.exceptions import ConnectionError, Timeout, RequestException
from pydantic import PrivateAttr

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config import Config


class ResilientSearchTool(BaseTool):
    """
    A wrapper around DuckDuckGoSearchResults that ignores connection errors
    and returns empty results, allowing the agent to continue verification.
    Avoid linkedin and wikipedia because they have good antibot measures.
    """

    name: str = "resilient_search"
    description: str = (
        "Search the web. If the search fails, returns empty results and continues."
    )

    # Declare as a private Pydantic attribute to avoid validation errors
    _base_tool: DuckDuckGoSearchResults = PrivateAttr()

    def __init__(self, base_tool: DuckDuckGoSearchResults):
        super().__init__()
        self._base_tool = base_tool

    def _run(self, query: str) -> str:
        try:
            return self._base_tool.run(query)
        except (ConnectionError, Timeout, RequestException) as e:
            print(f"Search failed (ignored): {query} — {type(e).__name__}: {e}")
            return "[]"
        except Exception as e:
            print(f"Unexpected search error (ignored): {query} — {e}")
            return "[]"

    async def _arun(self, query: str) -> str:
        return self._run(query)


class CvVeracityChecker:
    """
    Verifies CV authenticity using web search and LLM analysis.

    This class provides functionality to verify claims made in a CV by
    cross-referencing them against publicly available information on the
    web. It uses a LangChain agent with DuckDuckGo search capabilities to:
    - Identify verifiable claims (companies, titles, degrees, certifications)
    - Search for evidence to support or refute these claims
    - Evaluate the overall credibility of the CV

    The verifier scores CVs on a 0-100 scale:
    - 0-20: Highly suspicious / likely fabricated
    - 21-40: Major inconsistencies / mostly unverifiable
    - 41-60: Moderate issues / mixed evidence
    - 61-80: Mostly accurate / minor gaps
    - 81-100: Highly credible / publicly verified

    Attributes:
        config: Configuration object containing LLM settings.
        llm: ChatOpenRouter instance for LLM-based reasoning.
        search_tool: DuckDuckGo search tool for web searches.
        system_prompt: The prompt defining the agent's verification instructions.
        agent: LangChain agent combining LLM and search capabilities.

    Example:
        >>> checker = CvVeracityChecker(config)
        >>> score = checker.verify_cv(cv_json, debug=True)
        >>> print(f"CV Verification Score: {score}/100")
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the CvVeracityChecker with configuration.

        Args:
            config: Config object containing OpenRouter API settings.
        """
        self.config = config

        # Initialize LLM with deterministic settings (temperature=0)
        self.llm = ChatOpenAI(
            model=self.config.infomaniak_model,
            temperature=0,
            openai_api_key=self.config.infomaniak_ai_api_key,
            openai_api_base=self.config.infomaniak_base_url,
        )

        # Initialize DuckDuckGo search tool for web verification
        search_tool = DuckDuckGoSearchResults()
        self.search_tool = ResilientSearchTool(search_tool)

        # Define system prompt for the verification agent
        self.system_prompt = """
            You are an expert HR background verification assistant.
            Your task is to verify the authenticity of a CV provided as JSON.

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

        # Create the LangChain agent with LLM and search tool
        self.agent = create_agent(
            model=self.llm,
            tools=[self.search_tool],
            system_prompt=self.system_prompt,
        )

    def _save_debug_trace(
        self, response: dict, log_path: Path, final_score: Optional[int] = None
    ) -> None:
        """
        Write the agent's execution trace as a structured JSON file.

        This internal method captures the agent's reasoning process and
        tool calls during CV verification, allowing for debugging and
        auditing of verification decisions.

        The trace includes:
        - Metadata (timestamp, model, final score)
        - Reasoning steps (LLM thoughts)
        - Tool calls (search queries made)
        - Observations (search results received)

        Args:
            response: The full agent response containing message history.
            log_path: Path to save the debug log JSON file.
            final_score: Optional final verification score to include in metadata.

        Note:
            - Long search results are truncated to 500 characters to prevent
              massive log files.
            - The log file is created with parent directories as needed.
        """
        # Initialize list to store trace steps
        trace_steps = []

        # Iterate through agent messages to extract trace information
        for msg in response.get("messages", []):
            msg_type = getattr(msg, "type", None)
            timestamp = datetime.now().isoformat()

            # Skip human messages (input echoing)
            if msg_type == "human":
                continue

            # Extract AI reasoning and tool calls
            elif msg_type == "ai":
                # Capture reasoning (LLM thoughts)
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

            # Extract tool observations (search results)
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

        # Assemble structured payload with metadata and trace
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

        # Write to JSON file (create parent directories if needed)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

    def verify_cv(
        self,
        cv_json: Dict[str, Any],
        debug: bool = False,
        log_path: Optional[Path] = None,
    ) -> int:
        """
        Verify the CV and return an integer veracity score (0-100).

        This method performs the main CV verification by invoking the
        LangChain agent with the CV JSON data. The agent searches for
        evidence to verify key claims and produces a credibility score.

        The score is extracted from the agent's final response using
        regex pattern matching to find the numeric score.

        Args:
            cv_json: The CV data as a dictionary (extracted from PDF).
            debug: If True, saves the execution trace to log_path.
            log_path: Path to save the debug log. Defaults to
                     assets/cv_veracity_check_logs.json if not specified.

        Returns:
            int: A score between 0 and 100 indicating CV veracity.
                 Higher scores indicate more credible/verifiable CVs.

        Raises:
            RuntimeError: If verification fails or no score is returned.

        Example:
            >>> checker = CvVeracityChecker(config)
            >>> score = checker.verify_cv(cv_json)
            >>> if score > 50:
            ...     print("CV verified - proceeding with application")
        """

        # Default log path if not specified and debug is enabled
        if debug and log_path is None:
            log_path = (
                Path(__file__).parent.parent / "assets" / "cv_veracity_check_logs.json"
            )

        try:
            # Invoke the agent with CV data for verification
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

            # Extract score from the last agent message
            last_message = response["messages"][-1]
            raw_output = last_message.content.strip()

            # Try to find a 1-3 digit number at the VERY END of the response
            match = re.search(r"(?<!\d)(\d{1,3})\s*$", raw_output)
            if match:
                score = int(match.group(1))
            else:
                # Fallback: extract the last standalone 1-3 digit number
                fallback_matches = re.findall(r"\b\d{1,3}\b", raw_output)
                if fallback_matches:
                    score = int(fallback_matches[-1])
                else:
                    raise RuntimeError(
                        f"Agent failed to return a numeric score. Raw output: {raw_output}"
                    )

            # Clamp to valid range
            score = max(0, min(100, score))

            # Save trace if debug is enabled
            if debug and log_path:
                self._save_debug_trace(response, log_path, final_score=score)

            return score

        except Exception as e:
            raise RuntimeError(f"CV verification failed: {e}")


# Main block for standalone testing
if __name__ == "__main__":
    try:
        from config import load_config
    except ModuleNotFoundError:
        from src.config import load_config

    # Load configuration
    config = load_config()
    cv_verifier = CvVeracityChecker(config)

    # Path to extracted CV JSON
    cv_json_path = Path(__file__).parent.parent / "assets" / "cv.json"
    if not cv_json_path.exists():
        raise FileNotFoundError(
            f"CV JSON not found at: {cv_json_path}. Please run extraction first."
        )

    # Load extracted CV data
    with open(cv_json_path, "r", encoding="utf-8") as f:
        cv_json = json.load(f)

    # Path for debug log output
    debug_log_path = (
        Path(__file__).parent.parent / "assets" / "cv_veracity_check_logs.json"
    )

    # Run verification with structured JSON logging
    score = cv_verifier.verify_cv(cv_json, debug=True, log_path=debug_log_path)

    print(f"Verification complete. Score: {score}/100")
    print(f"Execution trace saved to: {debug_log_path}")
