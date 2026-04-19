"""
Email answer generator module for the email agent application.

This module provides the EmailAnswerGenerator class which generates professional
email responses to job applicants based on the CV-to-job matching results.
It uses an LLM to draft personalized replies that acknowledge the application
and communicate the match evaluation.

The generation process:
1. Extract the candidate's name and original email content
2. Format the match report (strengths, weaknesses, recommendation)
3. Send to LLM with a prompt requesting professional email content
4. Parse the LLM response to extract subject and body
"""

import json
from dataclasses import dataclass
from typing import Dict, Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Handle imports for main block execution
if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config import Config
from src.mail_client import Email


@dataclass
class EmailAnswer:
    """
    Data class representing a generated email response.

    This class encapsulates the complete email response including the
    recipient address, subject line, and email body. It is returned by
    the EmailAnswerGenerator after creating a professional reply.

    Attributes:
        address: The recipient's email address (from the original application).
        subject: The subject line for the response email.
        body: The full email body content (may include HTML or plain text).
    """

    address: str
    subject: str
    body: str


class EmailAnswerGenerator:
    """
    Generates professional email responses to job applicants using LLM.

    This class provides functionality to automatically generate personalized
    email responses to job applicants. The responses are based on the
    evaluation results from the application matcher, including the match
    score, strengths, weaknesses, and recommendation.

    The generated email:
    - Acknowledges the candidate's application
    - References the match evaluation (strengths and gaps)
    - Communicates the recommendation or next steps
    - Maintains a professional, courteous tone
    - Replies in the same language as the original email

    Attributes:
        config: Configuration object containing LLM settings.
        llm: ChatOpenRouter instance for generating email content.

    Example:
        >>> generator = EmailAnswerGenerator(config)
        >>> answer = generator.generate_email_answer(email, "John Doe", match_report)
        >>> print(f"To: {answer.address}")
        >>> print(f"Subject: {answer.subject}")
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the EmailAnswerGenerator with configuration.

        Args:
            config: Config object containing OpenRouter API settings.
        """
        self.config = config
        self.llm = ChatOpenAI(
            model=self.config.infomaniak_model,
            temperature=0,
            openai_api_key=self.config.infomaniak_ai_api_key,
            openai_api_base=self.config.infomaniak_base_url,
        )

    def generate_email_answer(
        self, email: Email, candidat_name: str, match_report: Dict[str, Any]
    ) -> EmailAnswer:
        """
        Generate a professional reply subject and body using the match report.

        This method creates a personalized email response to a job applicant
        based on the CV-to-job matching results. It extracts the candidate's
        name, the original email content, and the match evaluation to craft
        a professional reply that acknowledges the application and provides
        feedback.

        The LLM is instructed to:
        - Reply in the same language as the original email
        - Use a professional, courteous tone
        - Include both subject and body in the response
        - Not include markdown formatting or extra text

        Args:
            email: The original Email object from the job application.
            candidat_name: The candidate's name extracted from the CV.
            match_report: Dictionary containing match evaluation:
                - match_score: Score from 0-100
                - strengths: List of candidate strengths
                - weaknesses: List of candidate gaps
                - recommendation: Overall recommendation

        Returns:
            EmailAnswer: An EmailAnswer object containing:
                - address: Recipient email address
                - subject: Professional subject line
                - body: Full email content

        Raises:
            RuntimeError: If email generation fails (LLM error, parsing error, etc.).

        Note:
            - The method attempts to extract the sender address from multiple
              possible fields (sender, from_address, email).
            - Temperature is set to 0.0 to maintain determinism
              professionalism.
            - The LLM returns JSON which is parsed to extract subject and body.
        """
        # Step 1: Extract address from the email object (try multiple fields)
        address = getattr(
            email, "sender", getattr(email, "from_address", getattr(email, "email", ""))
        )

        # Step 2: Extract original email content for context
        email_content = getattr(email, "body", getattr(email, "content", ""))

        # Step 3: Format match report for clean prompt injection
        match_report_str = json.dumps(match_report, indent=2, ensure_ascii=False)

        # Step 4: Create prompt template that strictly requests subject and body
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert recruitment assistant. Draft a professional email response to a spontaneous job applicant. "
                        "Use the provided original email, candidat name and match evaluation report to craft your reply. "
                        "Specify in the replay that this email was generated automatically by our AI agent"
                        "If the matching score is above 50, say that our HR department will contact them shortly"
                        "Be very profesional and respectful, don't discriminate in anyway"
                        "Return ONLY a valid JSON object with exactly these two keys: 'subject' and 'body'. "
                        "- 'subject': A clear, professional subject line regarding their application. "
                        "- 'body': The full email text. Acknowledge the application, professionally reference the match "
                        "evaluation (strengths and gaps), and clearly communicate the recommendation or next steps. "
                        "Maintain a courteous, professional tone. Reply in the same language as the original email. based on the body and the match report"
                        "For the signature ,use this information: "
                        "Tech corp AI agent"
                        "Do not include markdown formatting, code blocks, or any text outside the JSON."
                    ),
                ),
                (
                    "human",
                    (
                        "Original Email Content:\n{email_content}\n\n"
                        "Candidat Name: \n{candidat_name}\n\n"
                        "Match Evaluation Report:\n{match_report}\n\n"
                        "Generate the response subject and body as JSON:"
                    ),
                ),
            ]
        )

        # Step 5: Build the chain: prompt -> LLM -> JSON parser
        chain = prompt | self.llm | JsonOutputParser()

        try:
            # Invoke the chain with the prepared data
            result = chain.invoke(
                {
                    "email_content": email_content,
                    "candidat_name": candidat_name,
                    "match_report": match_report_str,
                }
            )

            # Step 6: Construct and return the EmailAnswer instance
            return EmailAnswer(
                address=address,
                subject=result.get("subject", "Re: Your Application"),
                body=result.get("body", ""),
            )

        except Exception as e:
            raise RuntimeError(
                f"CRITICAL: Failed to generate email reply through OpenRouter: {e}"
            )


# Main block for standalone testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.config import load_config

    config = load_config()
    generator = EmailAnswerGenerator(config)

    print("EmailAnswerGenerator initialized successfully")
    print(f"Using model: {config.openrouter_model}")
