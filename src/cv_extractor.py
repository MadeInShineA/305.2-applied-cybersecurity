from io import BytesIO

from docling.document_converter import DocumentConverter, DocumentStream
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openrouter import ChatOpenRouter
import json

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config import Config


class CvExtractor:
    def __init__(self, config: Config, converter: DocumentConverter):
        self.config = config
        self.converter = converter
        self.llm = ChatOpenRouter(
            model=self.config.openrouter_model, temperature=0, max_tokens=4096
        )

    def extract_cv_to_json(self, cv_pdf_bytes: bytes) -> dict:
        source = DocumentStream(name="cv.pdf", stream=BytesIO(cv_pdf_bytes))
        result = self.converter.convert(source)
        markdown_content = result.document.export_to_markdown()

        json_schema = {
            "person": {
                "name": "Full Name",
                "email": "email@example.com",
                "phone": "phone number",
            },
            "education": [],
            "work_experience": [],
            "skills": [],
            "languages": [],
            "certifications": [],
            "notable_projects": [],
            "interests": [],
        }

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert recruitment assistant. Analyze the provided CV "
                        "and extract information into this STRICT JSON format: \n"
                        f"{json.dumps(json_schema).replace('{', '{{').replace('}', '}}')} \n"
                        "Return ONLY the JSON object. Translate all values to English. "
                        "If a field is missing, use null."
                    ),
                ),
                (
                    "human",
                    "{cv_content}",
                ),
            ]
        )

        chain = prompt | self.llm | JsonOutputParser()

        try:
            json_output = chain.invoke({"cv_content": markdown_content})

            if not isinstance(json_output, dict):
                raise ValueError(f"Expected dict, got {type(json_output)}")

            return json_output

        except Exception as e:
            raise RuntimeError(
                f"CRITICAL: LLM output is not a valid JSON structure: {e}"
            )


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    from config import load_config
    from src.cv_extractor import CvExtractor

    config = load_config()
    cv_extractor = CvExtractor(config, DocumentConverter())

    cv_path = Path(__file__).parent.parent / "assets" / "cv.pdf"
    cv_bytes = cv_path.read_bytes()

    cv_json = cv_extractor.extract_cv_to_json(cv_bytes)

    output_json_path = Path(__file__).parent.parent / "assets" / "cv.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(cv_json, f, indent=4, ensure_ascii=False)
