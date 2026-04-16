from io import BytesIO

from docling.document_converter import DocumentConverter, DocumentStream
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


class CvExtractor:
    def __init__(self, config: Config):
        self.config = config

        self.llm = ChatOpenRouter(
            model="nvidia/nemotron-3-nano-30b-a3b", temperature=0, max_tokens=4096
        )

    def extract_cv_to_json(self, cv_pdf_bytes: bytes) -> dict:
        """
        Extract CV data to JSON using Docling and ChatOpenRouter.
        Uses a LangChain pipeline to ensure structured output.
        """
        converter = DocumentConverter()
        source = DocumentStream(name="cv.pdf", stream=BytesIO(cv_pdf_bytes))
        result = converter.convert(source)
        markdown_content = result.document.export_to_markdown()

        # TODO: Use english instead of french?
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


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    from config import load_config
    from src.cv_extractor import CvExtractor

    config = load_config()
    cv_extractor = CvExtractor(config)

    cv_path = Path(__file__).parent.parent / "assets" / "cv.pdf"
    cv_bytes = cv_path.read_bytes()

    cv_json = cv_extractor.extract_cv_to_json(cv_bytes)

    output_json_path = Path(__file__).parent.parent / "assets" / "cv.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(cv_json, f, indent=4, ensure_ascii=False)
