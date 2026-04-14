from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage
from src.mail_client import Email
import config


class JobClassifier:
    def __init__(self, config: config.Config):
        self.llm = ChatOpenRouter(
            model='meta-llama/llama-3.2-3b-instruct:free',
            temperature=0,
        )
        self.config = config

    def is_job_application(self, email: Email) -> bool:
        if email.has_pdf_attachment:
            return True
        
        return self._classify_with_llm(email)

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