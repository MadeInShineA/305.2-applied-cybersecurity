from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage
from src.mail_client import Email
from src.config import Config
import re
from typing import Tuple


class EmailClassifier:
    """Classifies emails to detect job applications with CV attachments."""

    def __init__(self, config: Config):
        self.config = config

    def is_job_application(self, email: Email) -> Tuple[bool, int]:
        """Check if an email is a job application by validating CV structure in attachments."""
        print(email.subject)
        if email.has_pdf_attachment:
            for i, attachment in enumerate(email.attachments):
                if self.validate_cv_structure(attachment["data"]):
                    return True, i
            return False, -1
        else:
            return False, -1

    def validate_cv_structure(self, data: str) -> bool:
        """Validate CV structure by checking for presence of typical CV elements."""
        data = data.lower()
        data = data.lower()

        patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"(?:\+|00)?(?:[0-9] ?){9,14}",
            "dates": r"(?:\d{2}[./-]\d{2}[./-]\d{2,4})|(?:\d{2}[./-]\d{4})|(?:19|20)\d{2}",
        }

        cv_keywords = {
            "experience": [
                "experience",
                "expérience",
                "work",
                "travail",
                "parcours",
                "emplois",
            ],
            "education": [
                "education",
                "éducation",
                "formation",
                "cursus",
                "études",
                "diplôme",
            ],
            "skills": [
                "skills",
                "compétences",
                "outils",
                "capacités",
                "technologies",
                "interests",
            ],
            "languages": ["languages", "langues", "linguistique"],
        }

        results = {
            "emails": list(set(re.findall(patterns["email"], data))),
            "phones": list(set(re.findall(patterns["phone"], data))),
            "has_dates": len(re.findall(patterns["dates"], data)) >= 2,
            "matched_sections": [],
        }

        for section, keys in cv_keywords.items():
            if any(key in data for key in keys):
                results["matched_sections"].append(section)

        results["is_valid"] = (
            len(results["emails"]) > 0
            and len(results["phones"]) > 0
            and len(results["matched_sections"]) >= 2
            and results["has_dates"]
        )

        return results["is_valid"]
