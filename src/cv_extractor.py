from src.config import Config
from io import BytesIO
from docling.document_converter import DocumentConverter, DocumentStream
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openrouter import ChatOpenRouter


class CvExtractor:
    def __init__(self, config: Config):
        self.config = config

        self.llm = ChatOpenRouter(model="nvidia/nemotron-3-nano-30b-a3b", temperature=0)

    def extract_cv_to_json(self, cv_pdf_bytes: bytes) -> dict:
        """
        Extract CV data to JSON using Docling and ChatOpenRouter.
        Uses a LangChain pipeline to ensure structured output.
        """
        converter = DocumentConverter()
        source = DocumentStream(name="cv.pdf", stream=BytesIO(cv_pdf_bytes))
        result = converter.convert(source)
        markdown_content = result.document.export_to_markdown()

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert recruitment assistant. Analyze the provided CV (English or French) "
                        "and extract information into a strict JSON format. "
                        "Use these French keys: 'personne', 'formation', 'experience_professionnelle', "
                        "'competences', 'langues', 'certifications', 'projets_notables', 'centres_interet'. "
                        "If information is missing, use null. Translate English values to French. "
                        "Return only the JSON object."
                    ),
                ),
                ("human", "{cv_content}"),
            ]
        )

        chain = prompt | self.llm | JsonOutputParser()

        try:
            json_output = chain.invoke({"cv_content": markdown_content})
            return json_output
        except Exception as e:
            raise RuntimeError(
                f"CRITICAL: Failed to process CV through OpenRouter: {e}"
            )
