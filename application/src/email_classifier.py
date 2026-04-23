"""
Email classifier module for the email agent application.

This module provides the EmailClassifier class which analyzes incoming emails
to determine if they are job applications with CV attachments. It uses pattern
matching to validate the structure of PDF content and detect typical CV elements
such as contact information, education, work experience, and skills.
"""

import re
from typing import Tuple

from src.mail_client import Email
from src.config import Config


class EmailClassifier:
    """
    Classifies emails to detect job applications with CV attachments.

    This class provides methods to analyze email content and attachments
    to determine whether an email represents a job application. It performs
    structural validation on PDF attachments to verify they contain typical
    CV elements like contact information, education history, work experience,
    and skills.

    The classifier uses a keyword-based approach combined with regex pattern
    matching to validate CV structure. It checks for:
    - Absence of forbidden strings (e.g., '{', '}')
    - Email addresses (contact information)
    - Phone numbers
    - Date references (employment/education periods)
    - Keywords indicating work experience, education, and skills sections

    Attributes:
        config: Configuration object (currently unused but reserved for future extensions).
        FORBIDDEN_STRINGS: Tuple of strings that automatically invalidate a CV if present.

    Example:
        >>> classifier = EmailClassifier(config)
        >>> is_job, index = classifier.is_job_application(email)
        >>> if is_job:
        ...     print(f"Job application detected! CV in attachment {index}")
    """

    # Strings/patterns that automatically disqualify a document as a CV
    FORBIDDEN_STRINGS: Tuple[str, ...] = ("{", "}", "[", "]", "\\", "json", "system prompt")

    def __init__(self, config: Config) -> None:
        """
        Initialize the EmailClassifier with configuration.

        Args:
            config: Configuration object (reserved for future use).
        """
        self.config = config

    def is_job_application(self, email: Email) -> Tuple[bool, int]:
        """
        Check if an email is a job application by validating CV structure in attachments.

        This method first checks if the email has any PDF attachments. If so,
        it iterates through each attachment and validates its structure to
        determine if it appears to be a CV/resume document.

        Args:
            email: The Email object to classify, containing attachments and metadata.

        Returns:
            Tuple[bool, int]: A tuple containing:
                - First element: True if the email is a job application, False otherwise.
                - Second element: Index of the CV attachment if found, -1 otherwise.

        Note:
            - Only PDF attachments are considered as potential CVs.
            - The first attachment that passes validation is returned.
            - The email subject is printed for debugging purposes.
        """
        if email.has_pdf_attachment:
            for i, attachment in enumerate(email.attachments):
                if self.validate_cv_structure(attachment["data"]):
                    return True, i
            return False, -1
        else:
            return False, -1

    def validate_cv_structure(self, data: str) -> bool:
        """
        Validate CV structure by checking for presence of typical CV elements.

        This method performs structural validation on extracted PDF text to
        determine if it represents a valid CV/resume. It uses a combination
        of regex patterns and keyword matching to identify key CV components.

        Validation criteria (all must be met):
        1. No forbidden strings present (e.g., '{', '}')
        2. At least one email address
        3. At least one phone number
        4. At least two date references (indicating work/education periods)
        5. At least two CV section keywords from: experience, education, skills, languages

        Args:
            data: The extracted text content from a PDF attachment.

        Returns:
            bool: True if the content appears to be a valid CV, False otherwise.

        Note:
            - The validation is case-insensitive (text is converted to lowercase).
            - Regex patterns match both Swiss and international phone/date formats.
            - The method supports both English and French CV keywords.
            - Fails fast if any string in FORBIDDEN_STRINGS is detected.
        """

        # Convert to lowercase for case-insensitive matching
        data= data.lower()

        # Fail-fast check: reject if any forbidden string is present
        if any(forbidden in data for forbidden in self.FORBIDDEN_STRINGS):
            return False


        # Define regex patterns for key CV elements
        patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"(?:\+|00)?(?:[0-9] ?){9,14}",
            "dates": r"(?:\d{2}[./-]\d{2}[./-]\d{2,4})|(?:\d{2}[./-]\d{4})|(?:19|20)\d{2}",
        }

        # Define keywords for CV sections (supporting English and French)
        cv_keywords = {
            "experience": [
                "experience",
                "expérience",
                "work",
                "travaille",
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

        # Extract matching elements using regex patterns
        results = {
            "emails": list(set(re.findall(patterns["email"], data_lower))),
            "phones": list(set(re.findall(patterns["phone"], data_lower))),
            "has_dates": len(re.findall(patterns["dates"], data_lower)) >= 2,
            "matched_sections": [],
        }

        # Check for CV section keywords
        for section, keys in cv_keywords.items():
            if any(key in data_lower for key in keys):
                results["matched_sections"].append(section)

        # Determine if the content is a valid CV based on all criteria
        results["is_valid"] = (
            len(results["emails"]) > 0
            and len(results["phones"]) > 0
            and len(results["matched_sections"]) >= 2
            and results["has_dates"]
        )

        return results["is_valid"]
