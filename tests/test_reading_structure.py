import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from epub_generator import BookMeta

from pdf_craft import EpubRenderer, PublicationOptions
from pdf_craft.common import save_xml, read_xml
from pdf_craft.extractor.chapter import create_chapters_reader
from pdf_craft.extractor.chapter.chapter import Chapter, ParagraphLayout, BlockLayout, encode
from pdf_craft.extractor.toc.types import decode as decode_toc
from pdf_craft.renderer.epub.validation import validate_publication
from pdf_craft.transformer.reading_structure import recover_structure
from tests.extraction_helpers import make_extraction


def paragraph(text, page=1, order=0, box=(100, 200, 900, 250), ref="text"):
    return ParagraphLayout(ref, -1, [BlockLayout(page, order, box, [text])])


def fixture(tmp_path, layouts, pages=6):
    source = make_extraction(tmp_path / "source", with_toc=True,
                             page_pixel_sizes={i: (1000, 1000) for i in range(1, pages + 1)})
    save_xml(encode(Chapter(1, 0, layouts)), tmp_path / "source/chapters/chapter_1.xml")
    return source


def test_margin_consensus_keeps_body_repetitions_and_original(tmp_path):
    layouts = []
    for page in range(1, 7):
        layouts.extend([paragraph("Book title", page, 0, (400, 20, 600, 40)),
                        paragraph("Book title", page, 1),
                        paragraph(str(page + 10), page, 2, (450, 960, 550, 980))])
    source = fixture(tmp_path, layouts)
    before = (tmp_path / "source/chapters/chapter_1.xml").read_bytes()
    result = recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json")
    with result._materialize() as paths:
        ch = list(create_chapters_reader(paths.chapters)())[0]
        assert len(ch.layouts) == 6
        assert all(layout.blocks[0].order == 1 for layout in ch.layouts)
    assert len(json.loads((tmp_path / "audit.json").read_text())["events"]) == 12
    assert (tmp_path / "source/chapters/chapter_1.xml").read_bytes() == before


def test_clear_part_chapter_hierarchy_and_front_matter(tmp_path):
    source = fixture(tmp_path, [paragraph("ভূমিকা", 1, 0, (420, 120, 580, 150)), paragraph("Preface text", 1, 1),
                               paragraph("প্রথম খণ্ড", 2, 0, (400, 120, 600, 150)), paragraph("Part text", 2, 1),
                               paragraph("প্রথম অধ্যায়", 3, 0, (400, 120, 600, 150)), paragraph("Chapter text", 3, 1)])
    result = recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json")
    with result._materialize() as paths:
        toc = decode_toc(read_xml(paths.toc)).content
        assert len(toc) == 2
        assert len(toc[1].children) == 1
        assert [ch.layouts[0].ref for ch in create_chapters_reader(paths.chapters)()] == ["title"] * 3
    EpubRenderer().render(result, tmp_path / "book.epub", lan="bn", book_meta=BookMeta(title="Book"), publication=PublicationOptions())
    assert validate_publication(tmp_path / "book.epub")["status"] == "passed"
    with ZipFile(tmp_path / "book.epub") as archive:
        assert 'epub:type="preface"' in archive.read("OEBPS/Text/part1.xhtml").decode()


def test_manual_layouts_preserve_text_breaks_and_footnotes(tmp_path):
    from pdf_craft.extractor.chapter.chapter import Reference
    layouts = [paragraph("first line\nsecond line\nthird", order=0), paragraph("Dear friend\ntext\nYours", order=1), paragraph("quotation", order=2)]
    layouts[2].blocks[0].content.append(Reference(1, 8, "1", [paragraph("Note", order=8)]))
    source = fixture(tmp_path, layouts)
    rules = [{"page": 1, "order": index, "kind": kind} for index, kind in enumerate(("verse", "letter", "quote"))]
    result = recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json", rules)
    EpubRenderer().render(result, tmp_path / "book.epub", lan="bn")
    assert validate_publication(tmp_path / "book.epub")["status"] == "passed"
    with ZipFile(tmp_path / "book.epub") as archive:
        text = archive.read("OEBPS/Text/part1.xhtml").decode()
        assert "reading-verse" in text and "reading-letter" in text
        assert "<br" in text and "<blockquote" in text and "Note" in text


def test_manual_keep_overrides_repeated_margin_rule(tmp_path):
    layouts = [p for page in range(1, 7) for p in (paragraph("Header", page, 0, (400, 20, 600, 40)), paragraph("body", page, 1))]
    source = fixture(tmp_path, layouts)
    result = recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json", [{"page": 1, "order": 0, "kind": "keep"}])
    with result._materialize() as paths:
        assert len(list(create_chapters_reader(paths.chapters)())[0].layouts) == 7


def test_ambiguous_titles_and_two_page_repetitions_are_kept(tmp_path):
    layouts = [paragraph("Chapter 1", 1, 0), paragraph("Body", 1, 1, (100, 260, 900, 300)),
               paragraph("Header", 1, 2, (400, 20, 600, 40)), paragraph("Header", 2, 2, (400, 20, 600, 40))]
    source = fixture(tmp_path, layouts)
    result = recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json")
    with result._materialize() as paths:
        ch = list(create_chapters_reader(paths.chapters)())
        assert len(ch) == 1 and len(ch[0].layouts) == 4
        assert ch[0].layouts[0].ref == "text"


def test_unknown_override_selector_fails(tmp_path):
    source = fixture(tmp_path, [paragraph("Text")])
    with pytest.raises(ValueError, match="exactly one"):
        recover_structure(source, tmp_path / "reading.pcex", tmp_path / "audit.json", [{"page": 5, "order": 0, "kind": "remove"}])
