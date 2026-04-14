from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage
from src.mail_client import Email
import config
import re
from typing import Tuple


class JobClassifier:
    def __init__(self, config: config.Config):
        self.llm = ChatOpenRouter(
            model='meta-llama/llama-3.2-3b-instruct:free',
            temperature=0,
        )
        self.config = config

    def is_job_application(self, email: Email) -> Tuple[bool, int]:
        print(email.subject)
        if email.has_pdf_attachment:
            for i, attachment in enumerate(email.attachments):
                if self.validate_cv_structure(attachment["data"]):
                    return True, i
            return False, -1
        else:
            return False, -1
    
    def validate_cv_structure(self, data: str) -> bool:
        """
        Analyses the Docling JSON to verify the presence of CV-specific attributes.
        Returns a dictionary with findings and a boolean 'is_valid'.
        """
        data = data.lower()

        patterns = {
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "phone": r'(?:\+|00)?(?:[0-9] ?){9,14}',
            "dates": r'(?:\d{2}[./-]\d{2}[./-]\d{2,4})|(?:\d{2}[./-]\d{4})|(?:19|20)\d{2}'
        }

        cv_keywords = {
            "experience": ["experience", "expérience", "work", "travail", "parcours", "emplois"],
            "education": ["education", "éducation", "formation", "cursus", "études", "diplôme"],
            "skills": ["skills", "compétences", "outils", "capacités", "technologies", "interests"],
            "languages": ["languages", "langues", "linguistique"]
        }

        results = {
            "emails": list(set(re.findall(patterns["email"], data))),
            "phones": list(set(re.findall(patterns["phone"], data))),
            "has_dates": len(re.findall(patterns["dates"], data)) >= 2,
            "matched_sections": []
        }


        for section, keys in cv_keywords.items():
            if any(key in data for key in keys):
                results["matched_sections"].append(section)

        results["is_valid"] = (
            len(results["emails"]) > 0 and 
            len(results["phones"]) > 0 and
            len(results["matched_sections"]) >= 2 and 
            results["has_dates"]
        )

        return results["is_valid"]

    def _classify_with_llm(self, email: Email) -> bool:
        prompt = f'''Analyze this email and determine if it is a job application.
Reply with only YES or NO.

Email Subject: {email.subject}
Email Body (first 2000 chars): {email.body[:2000]}'''

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip().upper()
            return content == 'YES'
        except Exception as e:
            print(f'LLM classification error: {e}')
            return False