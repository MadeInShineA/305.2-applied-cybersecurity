"""
CV extractor module for the email agent application.

This module provides the CvExtractor class which converts PDF CV documents
into structured JSON data using a combination of Docling for PDF parsing
and a LLM for information extraction.

The module uses:
- Docling: For converting PDF documents to markdown format
- LangChain with OpenRouter: For LLM-powered extraction of structured data

The extraction process:
1. Convert PDF to markdown using Docling
2. Send markdown to LLM with a structured schema
3. Parse LLM response as JSON
"""

from io import BytesIO
from typing import Dict, Any

from docling.document_converter import DocumentConverter, DocumentStream
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config import Config


class CvExtractor:
    """
    Extract structured data from PDF CV documents using Docling and LLM.

    This class provides functionality to convert PDF CV documents into
    structured JSON data. It uses a two-stage process:
    1. Docling converts the PDF to markdown format
    2. An LLM extracts structured information following a predefined schema

    The extraction follows a strict JSON schema that includes:
    - Personal information (name, email, phone)
    - Education history
    - Work experience
    - Skills
    - Languages
    - Certifications
    - Notable projects
    - Interests

    Attributes:
        config: Configuration object containing LLM settings.
        converter: Docling DocumentConverter instance for PDF conversion.
        llm: ChatOpenRouter instance for LLM-based extraction.

    Example:
        >>> extractor = CvExtractor(config, DocumentConverter())
        >>> cv_bytes = pdf_path.read_bytes()
        >>> cv_json = extractor.extract_cv_to_json(cv_bytes)
        >>> print(cv_json['person']['name'])
    """

    def __init__(self, config: Config, converter: DocumentConverter) -> None:
        """
        Initialize the CvExtractor with configuration and converter.

        Args:
            config: Config object containing OpenRouter API settings.
            converter: Docling DocumentConverter instance for PDF processing.
        """
        self.config = config
        self.converter = converter
        self.llm = ChatOpenAI(
            model=self.config.infomaniak_model,
            temperature=0,
            openai_api_key=self.config.infomaniak_ai_api_key,
            openai_api_base=self.config.infomaniak_base_url,
        )

    def extract_cv_to_json(self, cv_pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract structured JSON data from a PDF CV document.

        This method processes a PDF CV by:
        1. Converting the PDF to markdown using Docling
        2. Sending the markdown to an LLM with an extraction prompt
        3. Parsing the LLM response as JSON

        The LLM is instructed to translate all values to English and use
        null for missing fields. Temperature is set to 0 for deterministic
        output.

        Args:
            cv_pdf_bytes: Raw PDF file bytes to extract data from.

        Returns:
            Dict[str, Any]: A dictionary containing the extracted CV data
                           following the predefined schema.

        Raises:
            RuntimeError: If LLM output is not valid JSON or extraction fails.

        Note:
            - The method uses a temperature of 0 for consistent results.
            - All extracted text is translated to English.
            - Missing fields are represented as null in the output.
        """
        # Stage 1: Convert PDF to markdown using Docling
        source = DocumentStream(name="cv.pdf", stream=BytesIO(cv_pdf_bytes))
        result = self.converter.convert(source)
        markdown_content = result.document.export_to_markdown()

        # Define the JSON schema for extraction
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

        # Create prompt template for LLM extraction
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

        # Build extraction chain: prompt -> LLM -> JSON parser
        chain = prompt | self.llm | JsonOutputParser()

        try:
            # Invoke the chain with markdown content
            json_output = chain.invoke({"cv_content": markdown_content})

            # Validate output is a dictionary
            if not isinstance(json_output, dict):
                raise ValueError(f"Expected dict, got {type(json_output)}")

            return json_output

        except Exception as e:
            raise RuntimeError(
                f"CRITICAL: LLM output is not a valid JSON structure: {e}"
            )


# Main block for standalone testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    from config import load_config
    from src.cv_extractor import CvExtractor

    # Load configuration
    config = load_config()
    cv_extractor = CvExtractor(config, DocumentConverter())

    # Path to test CV PDF
    cv_path = Path(__file__).parent.parent / "assets" / "cv.pdf"
    cv_bytes = cv_path.read_bytes()

    # Extract CV data
    cv_json = cv_extractor.extract_cv_to_json(cv_bytes)

    # Save extracted JSON to file
    output_json_path = Path(__file__).parent.parent / "assets" / "cv.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(cv_json, f, indent=4, ensure_ascii=False)
