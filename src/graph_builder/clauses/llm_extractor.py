"""LLM-based clause extraction using instructor."""

from pydantic import BaseModel, Field

from graph_builder.models import Document, Clause, ClauseType, ClauseLocation


class ExtractedClause(BaseModel):
    """Schema for LLM-extracted clause."""

    type: ClauseType = Field(description="The type of clause")
    section_title: str | None = Field(
        default=None, description="The title or heading of the clause section"
    )
    section_number: str | None = Field(
        default=None, description="The section number (e.g., '3.1', '4.2.1')"
    )
    content: str = Field(description="The full text content of the clause")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score"
    )


class ExtractedClauses(BaseModel):
    """Container for extracted clauses."""

    clauses: list[ExtractedClause] = Field(
        default_factory=list, description="List of extracted clauses"
    )


class LLMClauseExtractor:
    """Clause extractor using LLM with instructor."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the LLM clause extractor.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the instructor client."""
        if self._client is None:
            try:
                import instructor
                from openai import OpenAI
            except ImportError as e:
                raise ImportError(
                    "LLM clause extraction requires 'openai' and 'instructor' packages. "
                    "Install with: uv sync --extra llm"
                ) from e

            openai_client = OpenAI(api_key=self.api_key)
            self._client = instructor.from_openai(openai_client)
        return self._client

    def extract(self, document: Document) -> list[Clause]:
        """Extract clauses from a document using LLM.

        Args:
            document: Document to extract clauses from.

        Returns:
            List of extracted clauses.
        """
        prompt = f"""Extract all legal clauses from the following contract document.

For each clause, identify:
- type: Choose from the following clause types (with Chinese translations):
    - DEFINITIONS（定义条款）
    - CONFIDENTIALITY（保密条款）
    - TERMINATION（终止条款）
    - INDEMNIFICATION（赔偿条款）
    - LIABILITY（责任条款）
    - GOVERNING_LAW（适用法律条款）
    - DISPUTE_RESOLUTION（争议解决条款）
    - FORCE_MAJEURE（不可抗力条款）
    - PAYMENT（支付条款）
    - INTELLECTUAL_PROPERTY（知识产权条款）
    - WARRANTIES（保证条款）
    - REPRESENTATIONS（陈述条款）
    - NOTICES（通知条款）
    - TERM_AND_TERMINATION（期限与终止条款）
    - OTHER（其他）
- title: The heading or title of the clause (e.g., "Confidential Information", "知识产权")
- section_number: The section number if present (e.g., "2", "3.1", "4.2.1")
- content: The complete text of the clause including the title
- confidence: Your confidence in the classification (0.0 to 1.0)

Contract Text:
{document.content}

Extract all major clauses with their types and content. Be thorough and capture all important
contractual clauses."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=ExtractedClauses,
        )

        clauses = []
        paragraphs = document.metadata.get("paragraphs", [])

        for extracted in response.clauses:
            # Find location in document
            location = self._find_clause_location(
                extracted.content, extracted.section_title, paragraphs
            )

            clause = Clause(
                content=extracted.content,
                type=extracted.type,
                location=location,
                document_id=document.id,
                confidence=extracted.confidence,
                metadata={"extraction_method": "llm", "model": self.model},
            )
            clauses.append(clause)

        return clauses

    def _find_clause_location(
        self, content: str, section_title: str | None, paragraphs: list[dict]
    ) -> ClauseLocation:
        """Find the location of a clause in the document.

        Args:
            content: The clause content
            section_title: The section title
            paragraphs: List of paragraph metadata from DocxParser

        Returns:
            ClauseLocation with position information
        """
        # Try to find the clause by matching section title
        if section_title and paragraphs:
            for para in paragraphs:
                if section_title in para.get("text", ""):
                    return ClauseLocation(
                        paragraph_index=para["index"],
                        section_number=para.get("section_number"),
                        section_title=section_title,
                        start_char=para.get("start_char", 0),
                        end_char=para.get("end_char", len(content)),
                    )

        # Try to find by content match
        if paragraphs:
            # Look for first few words of content
            content_start = content[:50].strip()
            for para in paragraphs:
                if content_start in para.get("text", ""):
                    return ClauseLocation(
                        paragraph_index=para["index"],
                        section_number=para.get("section_number"),
                        section_title=section_title,
                        start_char=para.get("start_char", 0),
                        end_char=para.get("end_char", len(content)),
                    )

        # Fallback to default location
        return ClauseLocation(
            paragraph_index=0,
            section_number=None,
            section_title=section_title,
            start_char=0,
            end_char=len(content),
        )
