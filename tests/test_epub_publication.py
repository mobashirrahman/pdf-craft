from zipfile import ZipFile
from xml.etree import ElementTree as ET

from epub_generator import BookMeta
from PIL import Image

from pdf_craft import PublicationOptions, EpubRenderer
from pdf_craft.common import save_xml
from pdf_craft.extractor.chapter.chapter import Chapter, ParagraphLayout, BlockLayout, encode
from pdf_craft.renderer.epub.validation import validate_publication
from tests.extraction_helpers import make_extraction


def chapter(text="মেয়েঢিই ঘরে গেল।"):
    return Chapter(1, 0, [ParagraphLayout("text", -1, [BlockLayout(1, 0, (5, 5, 90, 90), [text])])])


def test_enriched_metadata_cover_title_and_links(tmp_path):
    extraction = make_extraction(tmp_path / "source", with_toc=True)
    save_xml(encode(chapter()), tmp_path / "source/chapters/chapter_1.xml")
    cover = tmp_path / "override.jpg"
    Image.new("RGB", (100, 150), "navy").save(cover)
    output = tmp_path / "book.epub"
    EpubRenderer().render(extraction, output, lan="bn",
                          book_meta=BookMeta(title="বই & <শিরোনাম>", authors=["লেখক"],
                                             editors=["সম্পাদক"], translators=["অনুবাদক"], publisher="প্রকাশক", isbn="9780000000002"),
                          publication=PublicationOptions(cover_path=cover, source_date="১৯২০",
                                                         edition="প্রথম", subjects=["উপন্যাস"],
                                                         identifier="urn:test:book", rights="Unknown"))
    assert validate_publication(output)["status"] == "passed"
    with ZipFile(output) as archive:
        opf = ET.fromstring(archive.read("OEBPS/content.opf"))
        assert opf.findtext(".//{*}identifier") == "urn:test:book"
        assert opf.findtext(".//{*}subject") == "উপন্যাস"
        assert len(opf.findall(".//{*}creator")) == 1
        assert len(opf.findall(".//{*}contributor")) == 2
        assert any(node.text == "ISBN 9780000000002" for node in opf.findall(".//{*}source"))
        assert opf.find(".//{*}date") is None
        assert opf.find(".//{*}item[@properties='cover-image']") is not None
        assert archive.read("OEBPS/assets/cover.png").startswith(b"\x89PNG")
        title = ET.fromstring(archive.read("OEBPS/pdf-craft-title.xhtml"))
        assert title.findtext(".//{*}h1") == "বই & <শিরোনাম>"
        nav = ET.fromstring(archive.read("OEBPS/nav.xhtml"))
        types = {node.get("{http://www.idpf.org/2007/ops}type") for node in nav.iter()}
        assert {"cover", "titlepage", "toc", "bodymatter"} <= types
        assert [node.get("idref") for node in opf.find("{*}spine")][:2] == ["x_cover.xhtml", "pdf-craft-title"]
        assert opf.find(".//{*}itemref[@idref='nav']") is not None
        assert "মেয়েঢিই ঘরে গেল।" in archive.read("OEBPS/Text/part1.xhtml").decode()
