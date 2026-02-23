"""Parser for documents using Textin xParse API."""

import re
from pathlib import Path

from graph_builder.models import Document


class TextinParser:
    """Parser using Textin's xParse API for document parsing.

    Textin xParse provides high-quality document parsing with built-in
    heading detection via outline_level and catalog/TOC extraction.
    Supports PDF, DOCX, DOC, PPTX, XLSX, HTML, and TXT files.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".html", ".txt"}
    SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")

    API_URL = "https://api.textin.com/ai/service/v1/pdf_to_markdown"

    def __init__(self, app_id: str = "", secret_code: str = "") -> None:
        """Initialize the parser.

        Args:
            app_id: Textin app ID. Falls back to Settings().textin_app_id.
            secret_code: Textin secret code. Falls back to Settings().textin_secret_code.
        """
        if app_id and secret_code:
            self._app_id = app_id
            self._secret_code = secret_code
        else:
            from graph_builder.config.settings import get_settings

            settings = get_settings()
            self._app_id = app_id or settings.textin_app_id
            self._secret_code = secret_code or settings.textin_secret_code

    def supports(self, file_path: Path) -> bool:
        """Check if this parser supports the given file type."""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> Document:
        """Parse a document using Textin xParse API.

        Args:
            file_path: Path to the document file.

        Returns:
            Document with content, paragraph metadata, and catalog data.

        Raises:
            ValueError: If file type is not supported.
            FileNotFoundError: If file does not exist.
            RuntimeError: If the API request fails.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports(file_path):
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        result = self._call_api(file_path)

        markdown = result.get("markdown", "")
        detail = result.get("detail", [])
        catalog = result.get("catalog", {})
        toc = catalog.get("toc", [])

        paragraphs_data = self._detail_to_paragraphs(detail, markdown)

        return Document(
            content=markdown,
            source=str(file_path),
            metadata={
                "file_type": file_path.suffix.lower().lstrip("."),
                "file_name": file_path.name,
                "parser": "textin",
                "paragraphs": paragraphs_data,
                "paragraph_count": len(paragraphs_data),
                "textin_catalog": toc,
                "textin_detail": detail,
            },
        )

    def _call_api(self, file_path: Path) -> dict:
        """Call the Textin xParse API.

        Args:
            file_path: Path to the file to parse.

        Returns:
            The 'result' dict from the API response.

        Raises:
            RuntimeError: If the API request fails.
        """
        import httpx

        if not self._app_id or not self._secret_code:
            raise RuntimeError(
                "Textin credentials required. Set GRAPH_BUILDER_TEXTIN_APP_ID "
                "and GRAPH_BUILDER_TEXTIN_SECRET_CODE environment variables."
            )

        headers = {
            "x-ti-app-id": self._app_id,
            "x-ti-secret-code": self._secret_code,
            "Content-Type": "application/octet-stream",
        }

        params = {
            "catalog_details": "1",
            "apply_document_tree": "1",
            "table_flavor": "html",
        }

        with open(file_path, "rb") as f:
            data = f.read()

        response = httpx.post(
            self.API_URL,
            headers=headers,
            params=params,
            content=data,
            timeout=120.0,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Textin API request failed with status {response.status_code}: "
                f"{response.text}"
            )

        body = response.json()
        code = body.get("code", -1)
        if code != 200:
            raise RuntimeError(
                f"Textin API returned error code {code}: {body.get('message', '')}"
            )

        return body.get("result", {})

    def _detail_to_paragraphs(
        self, detail: list[dict], markdown: str
    ) -> list[dict]:
        """Convert Textin detail array to standard paragraph metadata format.

        Args:
            detail: The detail array from the Textin API response.
            markdown: The full markdown content for character offset computation.

        Returns:
            List of paragraph metadata dicts in the standard format.
        """
        paragraphs: list[dict] = []
        current_char_offset = 0

        for item in detail:
            text = item.get("text", "").strip()
            if not text:
                continue

            outline_level = item.get("outline_level", -1)
            is_heading = outline_level >= 0

            # Determine style based on outline_level
            if is_heading:
                # outline_level 0 = Heading 1, 1 = Heading 2, etc.
                heading_level = outline_level + 1
                if heading_level <= 2:
                    style = f"Heading {heading_level}"
                else:
                    style = "Heading"
            else:
                style = "Normal"

            # Extract section number
            section_match = self.SECTION_NUMBER_PATTERN.match(text)
            section_number = (
                section_match.group(1).rstrip(".") if section_match else None
            )

            # Compute character offsets from markdown content
            text_pos = markdown.find(text, current_char_offset)
            if text_pos >= 0:
                start_char = text_pos
                end_char = text_pos + len(text)
                current_char_offset = end_char
            else:
                start_char = current_char_offset
                end_char = current_char_offset + len(text)
                current_char_offset = end_char

            paragraphs.append(
                {
                    "index": len(paragraphs),
                    "text": text,
                    "style": style,
                    "is_heading": is_heading,
                    "section_number": section_number,
                    "start_char": start_char,
                    "end_char": end_char,
                }
            )

        return paragraphs
