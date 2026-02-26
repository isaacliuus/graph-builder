"""Clause chunker using Textin catalog tree for clause boundary detection."""

import re

from pydantic import BaseModel, Field

from graph_builder.clauses.pattern_extractor import CLAUSE_TYPE_KEYWORDS
from graph_builder.models.clause import Clause, ClauseLocation, ClauseType
from graph_builder.models.document import Document, Chunk


class ClauseClassification(BaseModel):
    """LLM classification result for a single clause."""

    title: str = Field(description="The clause title (must match the input title exactly)")
    type: ClauseType = Field(description="The classified clause type")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Classification confidence"
    )


class ClauseClassifications(BaseModel):
    """Batch classification results for multiple clauses."""

    clauses: list[ClauseClassification] = Field(
        default_factory=list, description="List of clause classifications"
    )


class TextinClauseChunker:
    """Chunker that uses Textin's catalog tree to split documents into clause chunks.

    Expects documents pre-parsed by TextinParser (with textin_catalog metadata).
    Uses the catalog's hierarchy levels to detect clause boundaries, which is
    more reliable than regex-based section detection.

    When an api_key is provided, uses LLM batch classification for clause types
    instead of keyword matching. This is more accurate for non-standard titles,
    especially in Chinese contracts.
    """

    def __init__(
        self,
        min_clause_length: int = 50,
        clause_level: int = 2,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        include_preamble: bool = True,
    ) -> None:
        """Initialize the chunker.

        Args:
            min_clause_length: Minimum characters for a valid clause chunk.
            clause_level: Hierarchy level that defines clause boundaries.
                Level 1 = top-level (e.g. document title, appendices).
                Level 2 = articles/clauses (e.g. 第一条, 第二条). Default.
                Level 3 = sub-clauses.
            api_key: OpenAI API key for LLM classification. If empty, falls
                back to keyword matching.
            model: LLM model for clause type classification.
            include_preamble: If True, extract preamble (text before first
                clause) and postamble (text after last clause) as additional
                chunks for entity extraction. These chunks omit clause_type
                metadata so they are skipped by clause-specific logic.
        """
        self.min_clause_length = min_clause_length
        self.clause_level = clause_level
        self.api_key = api_key
        self.model = model
        self.include_preamble = include_preamble
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
                    "LLM clause classification requires 'openai' and 'instructor' packages. "
                    "Install with: uv sync --extra llm"
                ) from e

            openai_client = OpenAI(api_key=self.api_key)
            self._client = instructor.from_openai(openai_client)
        return self._client

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks using Textin catalog tree.

        Entries at `clause_level` define clause boundaries. Each clause chunk
        spans from one entry to the next at the same or higher level.
        """
        chunks: list[Chunk] = []

        for document in documents:
            toc = document.metadata.get("textin_catalog", [])
            paragraphs = document.metadata.get("paragraphs", [])

            if not toc or not paragraphs:
                continue

            tree = self.build_catalog_tree(toc)
            clause_nodes = self._collect_clause_nodes(tree)
            doc_chunks = self._nodes_to_chunks(
                document, clause_nodes, toc, paragraphs
            )
            chunks.extend(doc_chunks)

        return chunks

    @staticmethod
    def build_catalog_tree(toc: list[dict]) -> list[dict]:
        """Build a nested tree from a flat TOC list using parent-stack algorithm.

        Args:
            toc: Flat list of TOC entries with 'hierarchy' levels.

        Returns:
            Nested tree where each node has a 'children' list.
        """
        result: list[dict] = []
        parent_stack: list[dict] = []

        for item in toc:
            node = {**item, "children": []}

            while parent_stack and parent_stack[-1]["hierarchy"] >= node["hierarchy"]:
                parent_stack.pop()

            if parent_stack:
                parent_stack[-1]["children"].append(node)
            else:
                result.append(node)

            parent_stack.append(node)

        return result

    def _collect_clause_nodes(self, tree: list[dict]) -> list[dict]:
        """Collect nodes at the configured clause_level from the tree.

        If no nodes exist at clause_level, falls back to top-level nodes.
        """
        nodes: list[dict] = []
        self._walk_tree(tree, nodes)

        if not nodes:
            # Fallback: use top-level nodes
            return tree

        return nodes

    def _walk_tree(self, nodes: list[dict], result: list[dict]) -> None:
        """Recursively collect nodes matching clause_level."""
        for node in nodes:
            if node.get("hierarchy") == self.clause_level:
                result.append(node)
            else:
                # Look deeper for matching nodes
                self._walk_tree(node.get("children", []), result)

    def _classify_clauses_llm(
        self, clause_items: list[tuple[str, str]]
    ) -> dict[str, tuple[ClauseType, float]]:
        """Batch-classify clause types using a single LLM call.

        Args:
            clause_items: List of (title, content_snippet) tuples.

        Returns:
            Dict mapping title → (ClauseType, confidence).
        """
        clause_list = "\n".join(
            f"- Title: {title}\n  Content: {snippet[:200]}"
            for title, snippet in clause_items
        )

        prompt = f"""Classify each of the following contract clause titles into one of these types:
DEFINITIONS, CONFIDENTIALITY, TERMINATION, INDEMNIFICATION, LIABILITY,
GOVERNING_LAW, DISPUTE_RESOLUTION, FORCE_MAJEURE, PAYMENT,
INTELLECTUAL_PROPERTY, WARRANTIES, REPRESENTATIONS, NOTICES,
TERM_AND_TERMINATION, OTHER

Chinese translations for reference:
定义=DEFINITIONS, 保密=CONFIDENTIALITY, 终止=TERMINATION, 赔偿=INDEMNIFICATION,
责任=LIABILITY, 适用法律=GOVERNING_LAW, 争议解决=DISPUTE_RESOLUTION,
不可抗力=FORCE_MAJEURE, 支付/付款=PAYMENT, 知识产权=INTELLECTUAL_PROPERTY,
保证=WARRANTIES, 陈述=REPRESENTATIONS, 通知=NOTICES, 期限=TERM_AND_TERMINATION

For each clause, return the title exactly as given, the classified type, and your confidence (0.0-1.0).

Clauses:
{clause_list}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=ClauseClassifications,
        )

        return {
            c.title: (c.type, c.confidence) for c in response.clauses
        }

    def _nodes_to_chunks(
        self,
        document: Document,
        clause_nodes: list[dict],
        toc: list[dict],
        paragraphs: list[dict],
    ) -> list[Chunk]:
        """Convert clause nodes into Chunk objects.

        Each clause spans from its title to the next clause's title
        (at the same or higher hierarchy level in the flat TOC).

        When api_key is set, batch-classifies all clauses via LLM in a single
        call. Otherwise falls back to keyword matching.
        """
        chunks: list[Chunk] = []
        content = document.content

        # Build ordered boundary list: positions of all TOC entries at
        # clause_level or above, so we know where each clause ends.
        boundary_titles = [
            entry["title"]
            for entry in toc
            if entry.get("hierarchy", 99) <= self.clause_level
        ]

        # First pass: extract all clause boundaries and content
        clause_data: list[tuple[dict, int, int, str]] = []  # (node, start, end, content)
        for node in clause_nodes:
            title = node.get("title", "")

            start_char = self._find_title_start(title, paragraphs, content)
            if start_char is None:
                continue

            # Find next boundary after this node
            end_char = len(content)
            found_self = False
            for bt in boundary_titles:
                if not found_self:
                    if bt == title:
                        found_self = True
                    continue
                next_start = self._find_title_start(bt, paragraphs, content)
                if next_start is not None and next_start > start_char:
                    end_char = next_start
                    break

            clause_content = content[start_char:end_char].strip()

            if len(clause_content) < self.min_clause_length:
                continue

            clause_data.append((node, start_char, end_char, clause_content))

        # Batch classify via LLM or fall back to keyword matching
        llm_results: dict[str, tuple[ClauseType, float]] = {}
        if self.api_key and clause_data:
            clause_items = [
                (node.get("title", ""), clause_content)
                for node, _, _, clause_content in clause_data
            ]
            llm_results = self._classify_clauses_llm(clause_items)

        # Extract preamble and postamble
        preamble_chunk = None
        postamble_chunk = None
        if self.include_preamble and clause_data:
            first_clause_start = min(start for _, start, _, _ in clause_data)
            preamble_text = content[:first_clause_start].strip()
            if len(preamble_text) >= self.min_clause_length:
                preamble_chunk = Chunk(
                    content=preamble_text,
                    document_id=document.id,
                    start_index=0,
                    end_index=first_clause_start,
                    metadata={
                        "chunk_type": "PREAMBLE",
                        "section_title": "Preamble",
                        "section_number": None,
                        "confidence": 1.0,
                    },
                )

            last_clause_end = max(end for _, _, end, _ in clause_data)
            postamble_text = content[last_clause_end:].strip()
            if len(postamble_text) >= self.min_clause_length:
                postamble_chunk = Chunk(
                    content=postamble_text,
                    document_id=document.id,
                    start_index=last_clause_end,
                    end_index=len(content),
                    metadata={
                        "chunk_type": "POSTAMBLE",
                        "section_title": "Postamble",
                        "section_number": None,
                        "confidence": 1.0,
                    },
                )

        for node, start_char, end_char, clause_content in clause_data:
            title = node.get("title", "")

            if title in llm_results:
                clause_type, confidence = llm_results[title]
            else:
                clause_type = self._classify_clause_type(title, clause_content)
                confidence = 1.0

            section_match = re.match(r"^(\d+(?:\.\d+)*\.?)\s+", title)
            section_number = (
                section_match.group(1).rstrip(".") if section_match else None
            )

            section_title = title
            if section_match:
                section_title = title[section_match.end():].strip()

            children_titles = [
                child.get("title", "") for child in node.get("children", [])
            ]

            chunks.append(
                Chunk(
                    content=clause_content,
                    document_id=document.id,
                    start_index=start_char,
                    end_index=end_char,
                    metadata={
                        "clause_type": clause_type.value,
                        "section_number": section_number,
                        "section_title": section_title,
                        "confidence": confidence,
                        "catalog_node": {
                            "title": title,
                            "hierarchy": node.get("hierarchy", 1),
                            "children": children_titles,
                        },
                    },
                )
            )

        if preamble_chunk:
            chunks.insert(0, preamble_chunk)
        if postamble_chunk:
            chunks.append(postamble_chunk)

        return chunks

    def _find_title_start(
        self, title: str, paragraphs: list[dict], content: str
    ) -> int | None:
        """Find the start character offset for a catalog title.

        Tries exact match first, then fuzzy match against paragraph text,
        then falls back to searching in the content directly.
        """
        if not title:
            return None

        # 1. Exact substring match against paragraphs
        for para in paragraphs:
            if title in para.get("text", ""):
                return para["start_char"]

        # 2. Fuzzy match against paragraphs (handles whitespace/formatting diffs)
        from difflib import SequenceMatcher

        title_normalized = self._normalize(title)
        best_ratio = 0.0
        best_para = None

        for para in paragraphs:
            para_text = para.get("text", "")
            if not para_text:
                continue
            para_normalized = self._normalize(para_text)

            # Compare against full paragraph text (for short headings)
            ratio = SequenceMatcher(
                None, title_normalized, para_normalized
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_para = para

            # Also check if title is a fuzzy substring of longer paragraphs
            if len(para_normalized) > len(title_normalized):
                # Sliding window check on the paragraph prefix
                prefix = para_normalized[: len(title_normalized) + 10]
                ratio = SequenceMatcher(None, title_normalized, prefix).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_para = para

        if best_para is not None and best_ratio >= 0.7:
            return best_para["start_char"]

        # 3. Fallback: exact search in content
        pos = content.find(title)
        return pos if pos >= 0 else None

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for fuzzy comparison (collapse whitespace, lowercase)."""
        return " ".join(text.lower().split())

    @staticmethod
    def _classify_clause_type(title: str, content: str) -> ClauseType:
        """Classify clause type using keyword matching.

        Reuses CLAUSE_TYPE_KEYWORDS from PatternClauseExtractor for consistency.
        """
        combined_text = f"{title} {content}".lower()

        best_type = ClauseType.OTHER
        best_score = 0

        for clause_type, keywords in CLAUSE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            if score > best_score:
                best_score = score
                best_type = clause_type

        return best_type


class TextinClauseExtractor:
    """Adapter that wraps TextinClauseChunker to implement ClauseExtractor protocol.

    Converts Chunk objects (from TextinClauseChunker) into Clause objects,
    enabling use with ClauseEvaluator and other components that expect
    the ClauseExtractor interface.
    """

    def __init__(
        self,
        min_clause_length: int = 50,
        clause_level: int = 2,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        include_preamble: bool = True,
    ) -> None:
        self._chunker = TextinClauseChunker(
            min_clause_length=min_clause_length,
            clause_level=clause_level,
            api_key=api_key,
            model=model,
            include_preamble=include_preamble,
        )

    def extract(self, document: Document) -> list[Clause]:
        """Extract clauses from a Textin-parsed document.

        Args:
            document: Document parsed by TextinParser (with textin_catalog metadata).

        Returns:
            List of Clause objects with location information.
        """
        chunks = self._chunker.chunk([document])
        paragraphs = document.metadata.get("paragraphs", [])

        clauses: list[Clause] = []
        for chunk in chunks:
            paragraph_index = self._find_paragraph_index(
                chunk.start_index, paragraphs
            )
            clause = Clause(
                content=chunk.content,
                type=ClauseType(chunk.metadata["clause_type"]),
                location=ClauseLocation(
                    paragraph_index=paragraph_index,
                    section_number=chunk.metadata.get("section_number"),
                    section_title=chunk.metadata.get("section_title"),
                    start_char=chunk.start_index,
                    end_char=chunk.end_index,
                ),
                document_id=chunk.document_id,
                confidence=chunk.metadata.get("confidence", 1.0),
                metadata=chunk.metadata,
            )
            clauses.append(clause)

        return clauses

    @staticmethod
    def _find_paragraph_index(start_char: int, paragraphs: list[dict]) -> int:
        """Find the paragraph index that contains the given character offset."""
        for i, para in enumerate(paragraphs):
            para_start = para.get("start_char", 0)
            para_end = para.get("end_char", 0)
            if para_start <= start_char < para_end:
                return i
            # Also handle case where start_char matches exactly
            if para_start == start_char:
                return i
        return 0
