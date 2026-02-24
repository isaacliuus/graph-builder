"""Unit tests for Textin clause chunker."""

import pytest
from uuid import uuid4

from graph_builder.clauses.textin_chunker import TextinClauseChunker
from graph_builder.models.document import Document


def _make_textin_document(
    markdown: str,
    toc: list[dict],
    paragraphs: list[dict] | None = None,
) -> Document:
    """Create a Document with Textin metadata for testing."""
    if paragraphs is None:
        paragraphs = []
    return Document(
        content=markdown,
        source="test.pdf",
        metadata={
            "parser": "textin",
            "textin_catalog": toc,
            "textin_detail": [],
            "paragraphs": paragraphs,
        },
    )


class TestBuildCatalogTree:
    """Tests for the build_catalog_tree static method."""

    def test_flat_toc_single_level(self):
        """Test tree building with all hierarchy=1 entries."""
        toc = [
            {"title": "Section A", "hierarchy": 1},
            {"title": "Section B", "hierarchy": 1},
            {"title": "Section C", "hierarchy": 1},
        ]
        tree = TextinClauseChunker.build_catalog_tree(toc)

        assert len(tree) == 3
        assert tree[0]["title"] == "Section A"
        assert tree[0]["children"] == []
        assert tree[1]["title"] == "Section B"
        assert tree[2]["title"] == "Section C"

    def test_nested_hierarchy(self):
        """Test tree building with nested hierarchy levels."""
        toc = [
            {"title": "1. Definitions", "hierarchy": 1},
            {"title": "1.1 Term A", "hierarchy": 2},
            {"title": "1.2 Term B", "hierarchy": 2},
            {"title": "2. Confidentiality", "hierarchy": 1},
        ]
        tree = TextinClauseChunker.build_catalog_tree(toc)

        assert len(tree) == 2
        assert tree[0]["title"] == "1. Definitions"
        assert len(tree[0]["children"]) == 2
        assert tree[0]["children"][0]["title"] == "1.1 Term A"
        assert tree[0]["children"][1]["title"] == "1.2 Term B"
        assert tree[1]["title"] == "2. Confidentiality"
        assert tree[1]["children"] == []

    def test_deeply_nested_hierarchy(self):
        """Test tree building with 3 levels of nesting."""
        toc = [
            {"title": "1. Section", "hierarchy": 1},
            {"title": "1.1 Subsection", "hierarchy": 2},
            {"title": "1.1.1 Sub-subsection", "hierarchy": 3},
            {"title": "2. Section", "hierarchy": 1},
        ]
        tree = TextinClauseChunker.build_catalog_tree(toc)

        assert len(tree) == 2
        assert len(tree[0]["children"]) == 1
        assert len(tree[0]["children"][0]["children"]) == 1
        assert tree[0]["children"][0]["children"][0]["title"] == "1.1.1 Sub-subsection"

    def test_empty_toc(self):
        """Test tree building with empty TOC."""
        tree = TextinClauseChunker.build_catalog_tree([])
        assert tree == []

    def test_sibling_hierarchy_pops_stack(self):
        """Test that same-level siblings pop the stack correctly."""
        toc = [
            {"title": "A", "hierarchy": 1},
            {"title": "A.1", "hierarchy": 2},
            {"title": "A.2", "hierarchy": 2},
            {"title": "A.2.1", "hierarchy": 3},
            {"title": "A.3", "hierarchy": 2},
        ]
        tree = TextinClauseChunker.build_catalog_tree(toc)

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 3
        assert len(tree[0]["children"][1]["children"]) == 1  # A.2 has A.2.1


class TestTextinClauseChunkerLevel1:
    """Tests for TextinClauseChunker with clause_level=1."""

    def test_basic_chunking_level1(self):
        """Test clause chunking at level 1."""
        markdown = (
            "# 1. Definitions\n\n"
            "The following terms shall have the meanings set forth below. "
            "This section defines key terminology.\n\n"
            "# 2. Confidentiality\n\n"
            "Each party shall maintain confidential all proprietary information "
            "received from the other party.\n"
        )
        toc = [
            {"title": "1. Definitions", "hierarchy": 1},
            {"title": "2. Confidentiality", "hierarchy": 1},
        ]
        paragraphs = [
            {"text": "1. Definitions", "start_char": 2, "end_char": 16},
            {"text": "The following terms shall have the meanings set forth below. This section defines key terminology.", "start_char": 18, "end_char": 116},
            {"text": "2. Confidentiality", "start_char": 121, "end_char": 139},
            {"text": "Each party shall maintain confidential all proprietary information received from the other party.", "start_char": 141, "end_char": 237},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10, clause_level=1)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 2
        assert "Definitions" in chunks[0].content
        assert "Confidentiality" in chunks[1].content

    def test_clause_type_classification_level1(self):
        """Test that clause types are classified from section titles."""
        markdown = (
            "# 1. Definitions\n\nTerms defined here.\n\n"
            "# 2. Confidentiality\n\nKeep secrets safe from disclosure.\n\n"
            "# 3. Payment Terms\n\nPayment is due on receipt of invoice.\n"
        )
        toc = [
            {"title": "1. Definitions", "hierarchy": 1},
            {"title": "2. Confidentiality", "hierarchy": 1},
            {"title": "3. Payment Terms", "hierarchy": 1},
        ]
        paragraphs = [
            {"text": "1. Definitions", "start_char": 2, "end_char": 16},
            {"text": "Terms defined here.", "start_char": 18, "end_char": 37},
            {"text": "2. Confidentiality", "start_char": 42, "end_char": 60},
            {"text": "Keep secrets safe from disclosure.", "start_char": 62, "end_char": 95},
            {"text": "3. Payment Terms", "start_char": 100, "end_char": 116},
            {"text": "Payment is due on receipt of invoice.", "start_char": 118, "end_char": 154},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10, clause_level=1)
        chunks = chunker.chunk([doc])

        assert chunks[0].metadata["clause_type"] == "DEFINITIONS"
        assert chunks[1].metadata["clause_type"] == "CONFIDENTIALITY"
        assert chunks[2].metadata["clause_type"] == "PAYMENT"


class TestTextinClauseChunkerLevel2:
    """Tests for TextinClauseChunker with clause_level=2 (default)."""

    def test_chunks_at_level2(self):
        """Test that level-2 entries become clause chunks."""
        markdown = (
            "# Contract Title\n\n"
            "Preamble text here.\n\n"
            "## Article 1 Definitions\n\n"
            "The following terms are defined for this agreement.\n\n"
            "## Article 2 Confidentiality\n\n"
            "Each party shall keep information confidential and not disclose.\n\n"
            "## Article 3 Payment\n\n"
            "Payment shall be made within 30 days of invoice receipt.\n"
        )
        toc = [
            {"title": "Contract Title", "hierarchy": 1},
            {"title": "Article 1 Definitions", "hierarchy": 2},
            {"title": "Article 2 Confidentiality", "hierarchy": 2},
            {"title": "Article 3 Payment", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Contract Title", "start_char": 2, "end_char": 16},
            {"text": "Preamble text here.", "start_char": 18, "end_char": 37},
            {"text": "Article 1 Definitions", "start_char": 42, "end_char": 63},
            {"text": "The following terms are defined for this agreement.", "start_char": 65, "end_char": 116},
            {"text": "Article 2 Confidentiality", "start_char": 121, "end_char": 146},
            {"text": "Each party shall keep information confidential and not disclose.", "start_char": 148, "end_char": 211},
            {"text": "Article 3 Payment", "start_char": 216, "end_char": 234},
            {"text": "Payment shall be made within 30 days of invoice receipt.", "start_char": 236, "end_char": 292},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)  # default clause_level=2
        chunks = chunker.chunk([doc])

        assert len(chunks) == 3
        assert "Definitions" in chunks[0].content
        assert "Confidentiality" in chunks[1].content
        assert "Payment" in chunks[2].content

        # Level-1 title should NOT be a chunk
        for chunk in chunks:
            assert chunk.metadata["catalog_node"]["hierarchy"] == 2

    def test_level2_clause_boundaries_stop_at_next_level2(self):
        """Test that each level-2 clause stops at the next level-2 entry."""
        markdown = (
            "# Title\n\n"
            "## Art 1\n\nContent for article one is here.\n\n"
            "## Art 2\n\nContent for article two is here.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "Art 1", "hierarchy": 2},
            {"title": "Art 2", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "Art 1", "start_char": 12, "end_char": 17},
            {"text": "Content for article one is here.", "start_char": 19, "end_char": 50},
            {"text": "Art 2", "start_char": 55, "end_char": 60},
            {"text": "Content for article two is here.", "start_char": 62, "end_char": 93},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 2
        # Art 1 content should NOT include Art 2 content
        assert "article two" not in chunks[0].content
        assert "article one" not in chunks[1].content

    def test_level2_with_level3_children(self):
        """Test that level-3 content is included in its parent level-2 chunk."""
        markdown = (
            "# Title\n\n"
            "## Art 1 Definitions\n\n"
            "### 1.1 Term A\n\nMeaning of Term A in this contract.\n\n"
            "### 1.2 Term B\n\nMeaning of Term B in this contract.\n\n"
            "## Art 2 Payment\n\n"
            "Payment terms are described in this section.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "Art 1 Definitions", "hierarchy": 2},
            {"title": "1.1 Term A", "hierarchy": 3},
            {"title": "1.2 Term B", "hierarchy": 3},
            {"title": "Art 2 Payment", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "Art 1 Definitions", "start_char": 12, "end_char": 29},
            {"text": "1.1 Term A", "start_char": 34, "end_char": 44},
            {"text": "Meaning of Term A in this contract.", "start_char": 46, "end_char": 81},
            {"text": "1.2 Term B", "start_char": 86, "end_char": 96},
            {"text": "Meaning of Term B in this contract.", "start_char": 98, "end_char": 133},
            {"text": "Art 2 Payment", "start_char": 138, "end_char": 151},
            {"text": "Payment terms are described in this section.", "start_char": 153, "end_char": 197},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 2  # only level-2 entries

        # Art 1 should include both sub-clauses
        assert "Term A" in chunks[0].content
        assert "Term B" in chunks[0].content

        # Art 2 should only have its own content
        assert "Payment" in chunks[1].content
        assert "Term A" not in chunks[1].content

    def test_fallback_to_level1_when_no_level2(self):
        """Test fallback to top-level nodes when no level-2 entries exist."""
        markdown = (
            "Section A\n\nContent for section A with enough text.\n\n"
            "Section B\n\nContent for section B with enough text.\n"
        )
        toc = [
            {"title": "Section A", "hierarchy": 1},
            {"title": "Section B", "hierarchy": 1},
        ]
        paragraphs = [
            {"text": "Section A", "start_char": 0, "end_char": 9},
            {"text": "Content for section A with enough text.", "start_char": 11, "end_char": 50},
            {"text": "Section B", "start_char": 52, "end_char": 61},
            {"text": "Content for section B with enough text.", "start_char": 63, "end_char": 102},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)  # default level=2
        chunks = chunker.chunk([doc])

        # Falls back to level-1 since no level-2 entries
        assert len(chunks) == 2
        assert "Section A" in chunks[0].content
        assert "Section B" in chunks[1].content

    def test_chinese_contract_structure(self):
        """Test chunking with Chinese contract structure (title=1, articles=2)."""
        markdown = (
            "# 设计服务合作协议\n\n"
            "甲方信息...\n\n"
            "## 第一条 合作内容\n\n"
            "甲方提供设计要求，乙方提供本协议约定的设计服务。\n\n"
            "## 第二条 保密条款\n\n"
            "双方应对保密信息采取严格保密措施，不得向第三方披露。\n\n"
            "## 第三条 违约责任\n\n"
            "乙方违反本协议约定的，应当承担违约金。\n"
        )
        toc = [
            {"title": "设计服务合作协议", "hierarchy": 1},
            {"title": "第一条 合作内容", "hierarchy": 2},
            {"title": "第二条 保密条款", "hierarchy": 2},
            {"title": "第三条 违约责任", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "设计服务合作协议", "start_char": 2, "end_char": 10},
            {"text": "甲方信息...", "start_char": 12, "end_char": 19},
            {"text": "第一条 合作内容", "start_char": 24, "end_char": 32},
            {"text": "甲方提供设计要求，乙方提供本协议约定的设计服务。", "start_char": 34, "end_char": 57},
            {"text": "第二条 保密条款", "start_char": 62, "end_char": 70},
            {"text": "双方应对保密信息采取严格保密措施，不得向第三方披露。", "start_char": 72, "end_char": 97},
            {"text": "第三条 违约责任", "start_char": 102, "end_char": 110},
            {"text": "乙方违反本协议约定的，应当承担违约金。", "start_char": 112, "end_char": 131},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 3
        assert "合作内容" in chunks[0].content
        assert "保密" in chunks[1].content
        assert "违约" in chunks[2].content
        assert chunks[1].metadata["clause_type"] == "CONFIDENTIALITY"


class TestTextinClauseChunkerGeneral:
    """General tests for TextinClauseChunker."""

    def test_min_clause_length_filtering(self):
        """Test that short clauses are filtered out."""
        markdown = (
            "# Title\n\n"
            "## Short\n\nHi.\n\n"
            "## Long Section\n\nThis section has enough content to pass the minimum length filter.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "Short", "hierarchy": 2},
            {"title": "Long Section", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "Short", "start_char": 12, "end_char": 17},
            {"text": "Hi.", "start_char": 19, "end_char": 22},
            {"text": "Long Section", "start_char": 27, "end_char": 39},
            {"text": "This section has enough content to pass the minimum length filter.", "start_char": 41, "end_char": 106},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=50)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        assert "Long Section" in chunks[0].content

    def test_chunk_metadata_fields(self):
        """Test that chunks have all required metadata fields."""
        markdown = "# Title\n\n## 1. Definitions\n\nThe following terms shall have the meanings set forth below in this agreement.\n"
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "1. Definitions", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "1. Definitions", "start_char": 12, "end_char": 26},
            {"text": "The following terms shall have the meanings set forth below in this agreement.", "start_char": 28, "end_char": 105},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        meta = chunks[0].metadata

        assert "clause_type" in meta
        assert "section_number" in meta
        assert "section_title" in meta
        assert "confidence" in meta
        assert "catalog_node" in meta

        assert meta["section_number"] == "1"
        assert meta["section_title"] == "Definitions"
        assert meta["confidence"] == 1.0
        assert meta["catalog_node"]["hierarchy"] == 2

    def test_catalog_node_children_in_metadata(self):
        """Test that catalog node children titles are in chunk metadata."""
        markdown = (
            "# Title\n\n"
            "## 1. Definitions\n\n"
            "### 1.1 Term A\n\nMeaning of Term A.\n\n"
            "### 1.2 Term B\n\nMeaning of Term B.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "1. Definitions", "hierarchy": 2},
            {"title": "1.1 Term A", "hierarchy": 3},
            {"title": "1.2 Term B", "hierarchy": 3},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "1. Definitions", "start_char": 12, "end_char": 26},
            {"text": "1.1 Term A", "start_char": 30, "end_char": 40},
            {"text": "Meaning of Term A.", "start_char": 42, "end_char": 60},
            {"text": "1.2 Term B", "start_char": 64, "end_char": 74},
            {"text": "Meaning of Term B.", "start_char": 76, "end_char": 94},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        children = chunks[0].metadata["catalog_node"]["children"]
        assert "1.1 Term A" in children
        assert "1.2 Term B" in children

    def test_empty_catalog_produces_no_chunks(self):
        """Test that empty catalog produces no chunks."""
        doc = _make_textin_document("Some content", [], [])
        chunker = TextinClauseChunker()
        chunks = chunker.chunk([doc])
        assert chunks == []

    def test_multiple_documents(self):
        """Test chunking across multiple documents."""
        markdown1 = "# T1\n\n## 1. Definitions\n\nTerms are defined in this section of the contract agreement.\n"
        markdown2 = "# T2\n\n## 1. Payment\n\nPayment shall be made according to the schedule and invoice terms.\n"

        toc1 = [
            {"title": "T1", "hierarchy": 1},
            {"title": "1. Definitions", "hierarchy": 2},
        ]
        toc2 = [
            {"title": "T2", "hierarchy": 1},
            {"title": "1. Payment", "hierarchy": 2},
        ]

        para1 = [
            {"text": "T1", "start_char": 2, "end_char": 4},
            {"text": "1. Definitions", "start_char": 9, "end_char": 23},
            {"text": "Terms are defined in this section of the contract agreement.", "start_char": 25, "end_char": 85},
        ]
        para2 = [
            {"text": "T2", "start_char": 2, "end_char": 4},
            {"text": "1. Payment", "start_char": 9, "end_char": 19},
            {"text": "Payment shall be made according to the schedule and invoice terms.", "start_char": 21, "end_char": 86},
        ]

        doc1 = _make_textin_document(markdown1, toc1, para1)
        doc2 = _make_textin_document(markdown2, toc2, para2)

        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc1, doc2])

        assert len(chunks) == 2
        assert chunks[0].document_id == doc1.id
        assert chunks[1].document_id == doc2.id

    def test_document_without_textin_metadata_skipped(self):
        """Test that non-textin documents are skipped gracefully."""
        doc = Document(content="Some content", source="test.txt")
        chunker = TextinClauseChunker()
        chunks = chunker.chunk([doc])
        assert chunks == []

    def test_custom_clause_level_3(self):
        """Test chunking at level 3."""
        markdown = (
            "# Title\n\n"
            "## Art 1\n\n"
            "### 1.1 Sub A\n\nSub-clause A content for testing.\n\n"
            "### 1.2 Sub B\n\nSub-clause B content for testing.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            {"title": "Art 1", "hierarchy": 2},
            {"title": "1.1 Sub A", "hierarchy": 3},
            {"title": "1.2 Sub B", "hierarchy": 3},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "Art 1", "start_char": 12, "end_char": 17},
            {"text": "1.1 Sub A", "start_char": 22, "end_char": 31},
            {"text": "Sub-clause A content for testing.", "start_char": 33, "end_char": 65},
            {"text": "1.2 Sub B", "start_char": 70, "end_char": 79},
            {"text": "Sub-clause B content for testing.", "start_char": 81, "end_char": 113},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10, clause_level=3)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 2
        assert "Sub A" in chunks[0].content
        assert "Sub B" in chunks[1].content
        for chunk in chunks:
            assert chunk.metadata["catalog_node"]["hierarchy"] == 3

    def test_fuzzy_title_match_extra_whitespace(self):
        """Test that titles with extra whitespace are matched fuzzily."""
        markdown = (
            "# Title\n\n"
            "## Article 1  Definitions\n\n"
            "Terms defined here for the agreement.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            # TOC title has different spacing than paragraph text
            {"title": "Article 1    Definitions", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            {"text": "Article 1  Definitions", "start_char": 12, "end_char": 34},
            {"text": "Terms defined here for the agreement.", "start_char": 36, "end_char": 72},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        assert "Definitions" in chunks[0].content

    def test_fuzzy_title_match_minor_differences(self):
        """Test fuzzy match handles minor text differences between TOC and paragraphs."""
        markdown = (
            "# Title\n\n"
            "## 第十一条 不可抗力\n\n"
            "Some force majeure content for the clause.\n"
        )
        toc = [
            {"title": "Title", "hierarchy": 1},
            # TOC has extra spaces
            {"title": "第十一条    不可抗力", "hierarchy": 2},
        ]
        paragraphs = [
            {"text": "Title", "start_char": 2, "end_char": 7},
            # Paragraph has single space
            {"text": "第十一条 不可抗力", "start_char": 12, "end_char": 21},
            {"text": "Some force majeure content for the clause.", "start_char": 23, "end_char": 65},
        ]

        doc = _make_textin_document(markdown, toc, paragraphs)
        chunker = TextinClauseChunker(min_clause_length=10)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        assert "不可抗力" in chunks[0].content
