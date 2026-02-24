"""Clause chunker using Textin catalog tree for clause boundary detection."""

import re

from graph_builder.clauses.pattern_extractor import CLAUSE_TYPE_KEYWORDS
from graph_builder.models.clause import ClauseType
from graph_builder.models.document import Document, Chunk


class TextinClauseChunker:
    """Chunker that uses Textin's catalog tree to split documents into clause chunks.

    Expects documents pre-parsed by TextinParser (with textin_catalog metadata).
    Uses the catalog's hierarchy levels to detect clause boundaries, which is
    more reliable than regex-based section detection.
    """

    def __init__(
        self,
        min_clause_length: int = 50,
        clause_level: int = 2,
    ) -> None:
        """Initialize the chunker.

        Args:
            min_clause_length: Minimum characters for a valid clause chunk.
            clause_level: Hierarchy level that defines clause boundaries.
                Level 1 = top-level (e.g. document title, appendices).
                Level 2 = articles/clauses (e.g. 第一条, 第二条). Default.
                Level 3 = sub-clauses.
        """
        self.min_clause_length = min_clause_length
        self.clause_level = clause_level

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

            clause_type = self._classify_clause_type(title, clause_content)

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
                        "confidence": 1.0,
                        "catalog_node": {
                            "title": title,
                            "hierarchy": node.get("hierarchy", 1),
                            "children": children_titles,
                        },
                    },
                )
            )

        
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
