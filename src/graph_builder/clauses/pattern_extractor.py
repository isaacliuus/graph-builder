"""Pattern-based clause extractor using keyword matching."""

import re

from graph_builder.models import Document, Clause, ClauseType, ClauseLocation


# Keywords for clause type classification (case-insensitive)
CLAUSE_TYPE_KEYWORDS: dict[ClauseType, list[str]] = {
    ClauseType.DEFINITIONS: [
        "definition",
        "definitions",
        "defined terms",
        "interpretation",
        "定义",
        "释义",
        "定义条款",
        "术语",
        "解释",
    ],
    ClauseType.CONFIDENTIALITY: [
        "confidential",
        "confidentiality",
        "non-disclosure",
        "nda",
        "proprietary information",
        "trade secret",
        "保密",
        "保密协议",
        "不披露",
        "非公开",
        "专有信息",
        "商业秘密",
    ],
    ClauseType.TERMINATION: [
        "termination",
        "terminate",
        "expiration",
        "cancellation",
        "终止",
        "解除",
        "到期",
        "取消",
    ],
    ClauseType.INDEMNIFICATION: [
        "indemnif",
        "indemnity",
        "hold harmless",
        "赔偿",
        "补偿",
        "补偿条款",
        "使...免责",
    ],
    ClauseType.LIABILITY: [
        "liability",
        "limitation of liability",
        "damages",
        "consequential",
        "责任",
        "责任限制",
        "赔偿损失",
        "间接损失",
    ],
    ClauseType.GOVERNING_LAW: [
        "governing law",
        "applicable law",
        "choice of law",
        "jurisdiction",
        "适用法律",
        "管辖法律",
        "法律选择",
        "管辖权",
    ],
    ClauseType.DISPUTE_RESOLUTION: [
        "dispute",
        "arbitration",
        "mediation",
        "resolution",
        "争议",
        "仲裁",
        "调解",
        "争议解决",
    ],
    ClauseType.FORCE_MAJEURE: [
        "force majeure",
        "act of god",
        "unforeseen circumstances",
        "不可抗力",
        "天灾",
        "不可预见情况",
    ],
    ClauseType.PAYMENT: [
        "payment",
        "compensation",
        "fees",
        "invoic",
        "billing",
        "price",
        "付款",
        "报酬",
        "费用",
        "发票",
        "账单",
        "价格",
    ],
    ClauseType.INTELLECTUAL_PROPERTY: [
        "intellectual property",
        "ip rights",
        "patent",
        "copyright",
        "trademark",
        "license",
        "知识产权",
        "专利",
        "著作权",
        "版权",
        "商标",
        "许可",
    ],
    ClauseType.WARRANTIES: [
        "warrant",
        "warranty",
        "warranties",
        "as is",
        "保证",
        "担保",
        "如实",
    ],
    ClauseType.REPRESENTATIONS: [
        "representation",
        "represent",
        "covenants",
        "陈述",
        "声明",
        "承诺",
    ],
    ClauseType.NOTICES: [
        "notice",
        "notification",
        "communication",
        "通知",
        "通告",
        "沟通",
    ],
    ClauseType.TERM_AND_TERMINATION: [
        "term and termination",
        "duration",
        "effective date",
        "renewal",
        "期限与终止",
        "期间",
        "生效日期",
        "续期",
    ],
}


class PatternClauseExtractor:
    """Rule-based clause extractor using heading detection and keyword matching."""

    def __init__(self, min_clause_length: int = 50) -> None:
        """Initialize the extractor.

        Args:
            min_clause_length: Minimum character length for a valid clause.
        """
        self.min_clause_length = min_clause_length

    def extract(self, document: Document) -> list[Clause]:
        """Extract clauses from a document.

        Args:
            document: Document with paragraph metadata from DocxParser.

        Returns:
            List of extracted clauses.
        """
        paragraphs = document.metadata.get("paragraphs", [])

        if not paragraphs:
            # Fall back to simple paragraph splitting if no metadata
            return self._extract_from_plain_text(document)

        return self._extract_from_paragraphs(document, paragraphs)

    def _extract_from_paragraphs(
        self, document: Document, paragraphs: list[dict]
    ) -> list[Clause]:
        """Extract clauses using paragraph metadata."""
        clauses = []
        clause_boundaries = self._find_clause_boundaries(paragraphs)

        for start_idx, end_idx, section_info in clause_boundaries:
            clause_paragraphs = paragraphs[start_idx:end_idx]
            if not clause_paragraphs:
                continue

            content = "\n".join(p["text"] for p in clause_paragraphs)
            if len(content) < self.min_clause_length:
                continue

            first_para = clause_paragraphs[0]
            clause_type = self._classify_clause_type(
                section_info.get("title", ""), content
            )

            location = ClauseLocation(
                paragraph_index=first_para["index"],
                section_number=section_info.get("section_number"),
                section_title=section_info.get("title"),
                start_char=first_para["start_char"],
                end_char=clause_paragraphs[-1]["end_char"],
            )

            clause = Clause(
                content=content,
                type=clause_type,
                location=location,
                document_id=document.id,
                confidence=self._calculate_confidence(clause_type, content),
            )
            clauses.append(clause)

        return clauses

    def _find_clause_boundaries(
        self, paragraphs: list[dict]
    ) -> list[tuple[int, int, dict]]:
        """Find clause boundaries based on headings and section numbers.

        Returns:
            List of (start_idx, end_idx, section_info) tuples.
        """
        boundaries = []
        current_start = None
        current_section_info = {}

        for i, para in enumerate(paragraphs):
            is_section_start = para.get("is_heading") or para.get("section_number")

            if is_section_start:
                # Close previous section
                if current_start is not None:
                    boundaries.append((current_start, i, current_section_info))

                # Start new section
                current_start = i
                current_section_info = {
                    "section_number": para.get("section_number"),
                    "title": self._extract_section_title(para["text"]),
                }

        # Close final section
        if current_start is not None:
            boundaries.append((current_start, len(paragraphs), current_section_info))

        return boundaries

    def _extract_section_title(self, text: str) -> str:
        """Extract section title, removing section number prefix."""
        # Remove section number prefix (e.g., "1.2 Definitions" -> "Definitions")
        pattern = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")
        return pattern.sub("", text).strip()

    def _classify_clause_type(self, title: str, content: str) -> ClauseType:
        """Classify clause type based on title and content keywords."""
        combined_text = f"{title} {content}".lower()

        best_match = ClauseType.OTHER
        best_score = 0

        for clause_type, keywords in CLAUSE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            if score > best_score:
                best_score = score
                best_match = clause_type

        return best_match

    def _calculate_confidence(self, clause_type: ClauseType, content: str) -> float:
        """Calculate confidence score for the extraction."""
        if clause_type == ClauseType.OTHER:
            return 0.5

        # Check how many keywords match
        keywords = CLAUSE_TYPE_KEYWORDS.get(clause_type, [])
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw.lower() in content_lower)

        if matches >= 3:
            return 1.0
        elif matches >= 2:
            return 0.9
        elif matches >= 1:
            return 0.8
        return 0.6

    def _extract_from_plain_text(self, document: Document) -> list[Clause]:
        """Fallback extraction for documents without paragraph metadata."""
        clauses = []
        lines = document.content.split("\n")
        current_start = 0
        current_char = 0

        section_pattern = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+(.+)$")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            match = section_pattern.match(line)

            if match:
                # Found a section header, find content until next section
                section_number = match.group(1).rstrip(".")
                section_title = match.group(2)
                start_char = current_char

                content_lines = [line]
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if section_pattern.match(next_line):
                        break
                    if next_line:
                        content_lines.append(next_line)
                    j += 1

                content = "\n".join(content_lines)
                if len(content) >= self.min_clause_length:
                    clause_type = self._classify_clause_type(section_title, content)
                    end_char = start_char + len(content)

                    location = ClauseLocation(
                        paragraph_index=i,
                        section_number=section_number,
                        section_title=section_title,
                        start_char=start_char,
                        end_char=end_char,
                    )

                    clause = Clause(
                        content=content,
                        type=clause_type,
                        location=location,
                        document_id=document.id,
                        confidence=self._calculate_confidence(clause_type, content),
                    )
                    clauses.append(clause)

                i = j
            else:
                current_char += len(line) + 1
                i += 1

        return clauses
