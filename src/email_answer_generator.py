import json
from dataclasses import dataclass
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openrouter import ChatOpenRouter

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
    address: str
    subject: str
    body: str


class EmailAnswerGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.llm = ChatOpenRouter(
            model=self.config.openrouter_model, temperature=0.3, max_tokens=4096
        )

    def generate_email_answer(
        self, email: Email, candidat_name: str, match_report: dict
    ) -> EmailAnswer:
        """
        Generates a professional reply subject and body using the match report.
        The recipient address is taken directly from the email argument.
        """
        # 1. Extract address directly from the email object
        address = getattr(
            email, "sender", getattr(email, "from_address", getattr(email, "email", ""))
        )

        # 2. Extract original email content
        email_content = getattr(email, "body", getattr(email, "content", ""))

        # Format match report for clean prompt injection
        match_report_str = json.dumps(match_report, indent=2, ensure_ascii=False)

        # 3. Prompt strictly requests only 'subject' and 'body'
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert recruitment assistant. Draft a professional email response to a job applicant. "
                        "Use the provided original email, candidat name and match evaluation report to craft your reply. "
                        "Return ONLY a valid JSON object with exactly these two keys: 'subject' and 'body'. "
                        "- 'subject': A clear, professional subject line regarding their application. "
                        "- 'body': The full email text. Acknowledge the application, professionally reference the match "
                        "evaluation (strengths and gaps), and clearly communicate the recommendation or next steps. "
                        "Maintain a courteous, professional tone. Reply in the same language as the original email. based on the body and the match report"
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

        # 4. Build chain with JSON parser
        chain = prompt | self.llm | JsonOutputParser()

        try:
            result = chain.invoke(
                {
                    "email_content": email_content,
                    "candidat_name": candidat_name,
                    "match_report": match_report_str,
                }
            )

            # 5. Construct and return the EmailAnswer instance
            return EmailAnswer(
                address=address,
                subject=result.get("subject", "Re: Your Application"),
                body=result.get("body", ""),
            )

        except Exception as e:
            raise RuntimeError(
                f"CRITICAL: Failed to generate email reply through OpenRouter: {e}"
            )
