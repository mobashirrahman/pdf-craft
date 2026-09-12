"""Repair language metadata emitted by epub-generator 0.1.x without patching it."""

from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from html import escape
import posixpath

from epub_generator import BookMeta
from .options import PublicationOptions


_READING_CSS = """
/* pdf-craft: reflowable, reader-theme-friendly typography */
html, body { background: transparent !important; color: inherit !important; }
body { font-family: serif; line-height: 1.65; padding: 0; margin: 0 5%; }
p { text-align: start; orphans: 2; widows: 2; }
h1, h2, h3, h4, h5, h6 { break-after: avoid; line-height: 1.3; }
img, svg { max-width: 100%; height: auto; }
table { max-width: 100%; overflow-wrap: anywhere; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
.reading-verse, .reading-poetry, .reading-letter { display: block; white-space: pre-wrap; }
.reading-verse, .reading-poetry { margin-inline-start: 1em; }
.reading-scene-break { display: block; text-align: center; margin-block: 1.5em; }
blockquote { margin-inline: 1.5em; }
"""


def finalize_publication(path: Path, language: str,
                         options: PublicationOptions | None = None,
                         book_meta: BookMeta | None = None) -> None:
    # Replace metadata only, never occurrences of language codes in book text.
    # Preserve namespace prefixes (notably epub:type), ZIP ordering and compression.
    with NamedTemporaryFile(dir=path.parent, suffix=".epub", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with ZipFile(path) as source, ZipFile(temporary, "w") as target:
            replacements = _enrich(source, language, options, book_meta) if options else {}
            for entry in source.infolist():
                content = replacements.pop(entry.filename, None)
                if content is None:
                    content = source.read(entry)
                if entry.filename.endswith((".opf", ".xhtml", ".ncx")):
                    text = content.decode("utf-8")
                    text = re.sub(r'\bxml:lang="[^"]*"', f'xml:lang="{language}"', text, count=1)
                    text = re.sub(r'(?<![\w:])lang="[^"]*"', f'lang="{language}"', text, count=1)
                    if entry.filename.endswith(".opf"):
                        text = re.sub(r"(<dc:language>)[^<]*(</dc:language>)", rf"\g<1>{language}\g<2>", text)
                    if language == "bn" and entry.filename.endswith("nav.xhtml"):
                        for tag, original, translated in (("title", "Table of Contents", "সূচিপত্র"),
                                                          ("h1", "Table of Contents", "সূচিপত্র"),
                                                          ("h2", "Landmarks", "বইয়ের অংশ")):
                            text = text.replace(f"<{tag}>{original}</{tag}>", f"<{tag}>{translated}</{tag}>")
                    content = text.encode("utf-8")
                elif entry.filename.endswith(".css"):
                    content += _READING_CSS.encode("utf-8")
                target.writestr(entry, content)
            for name, content in replacements.items():
                target.writestr(name, content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


_OPF = "http://www.idpf.org/2007/opf"
_DC = "http://purl.org/dc/elements/1.1/"
_XHTML = "http://www.w3.org/1999/xhtml"
_EPUB = "http://www.idpf.org/2007/ops"
ET.register_namespace("dc", _DC)
ET.register_namespace("opf", _OPF)
ET.register_namespace("epub", _EPUB)
ET.register_namespace("", _XHTML)


def _xml(node):
    return ET.tostring(node, encoding="utf-8", xml_declaration=True)


def _enrich(archive, language, options, book_meta):
    """Enrich our generator output without modifying its dependency or book text."""
    container = ET.fromstring(archive.read("META-INF/container.xml"))
    opf_path = container.find(".//{*}rootfile").get("full-path")
    root = ET.fromstring(archive.read(opf_path))
    metadata = root.find(f"{{{_OPF}}}metadata")
    manifest = root.find(f"{{{_OPF}}}manifest")
    spine = root.find(f"{{{_OPF}}}spine")
    replacements = {}
    if options.identifier:
        uid = root.get("unique-identifier")
        metadata.find(f"{{{_DC}}}identifier[@id='{uid}']").text = options.identifier
    if book_meta and book_meta.isbn:
        # Keep the scanned edition's ISBN even when the digital copy has its own UID.
        ET.SubElement(metadata, f"{{{_DC}}}source").text = f"ISBN {book_meta.isbn}"
    for person in metadata.findall(f"{{{_DC}}}creator"):
        role = metadata.find(f"{{{_OPF}}}meta[@refines='#{person.get('id')}'][@property='role']")
        if role is not None and role.text in {"edt", "trl"}:
            person.tag = f"{{{_DC}}}contributor"
    for subject in options.subjects:
        ET.SubElement(metadata, f"{{{_DC}}}subject").text = subject
    for tag, value in (("rights", options.rights), ("source", options.source_identifier)):
        if value:
            ET.SubElement(metadata, f"{{{_DC}}}{tag}").text = value
    # Retain original-edition details as source description, never dc:date (digital date).
    source_details = [value for value in (options.source_date, options.edition) if value]
    if source_details:
        ET.SubElement(metadata, f"{{{_OPF}}}meta", {"property": "dcterms:bibliographicCitation"}).text = "; ".join(source_details)
    ET.SubElement(metadata, f"{{{_OPF}}}meta", {"property": "dcterms:provenance"}).text = "Digitized with pdf-craft; OCR text may contain errors."
    items = {item.get("id"): item for item in manifest}
    nav_item = next(item for item in manifest if "nav" in item.get("properties", "").split())
    base = posixpath.dirname(opf_path)
    nav_path = posixpath.normpath(posixpath.join(base, nav_item.get("href")))
    nav = ET.fromstring(archive.read(nav_path))
    nav_base = posixpath.dirname(nav_path)
    def relative(href):
        return posixpath.relpath(posixpath.join(base, href), nav_base)
    landmarks = nav.find(f".//{{{_XHTML}}}nav[@{{{_EPUB}}}type='landmarks']")
    if landmarks is None:
        landmarks = ET.SubElement(nav.find(f"{{{_XHTML}}}body"), f"{{{_XHTML}}}nav",
                                  {f"{{{_EPUB}}}type": "landmarks", "hidden": "hidden"})
    for child in list(landmarks):
        landmarks.remove(child)
    ET.SubElement(landmarks, f"{{{_XHTML}}}h2").text = "বইয়ের অংশ" if language == "bn" else "Landmarks"
    links = ET.SubElement(landmarks, f"{{{_XHTML}}}ol")
    landmark_kinds = set()
    def landmark(kind, href, label):
        if kind in landmark_kinds:
            return
        landmark_kinds.add(kind)
        row = ET.SubElement(links, f"{{{_XHTML}}}li")
        ET.SubElement(row, f"{{{_XHTML}}}a", {f"{{{_EPUB}}}type": kind, "href": relative(href)}).text = label
    # Existing cover page and image are generated upstream, including cover-image metadata.
    cover_refs = []
    front_refs = []
    for ref in spine:
        item = items[ref.get("idref")]
        content = archive.read(posixpath.normpath(posixpath.join(base, item.get("href"))))
        if b'epub:type="cover"' in content or "cover" in item.get("href").lower():
            cover_refs.append(ref)
            landmark("cover", item.get("href"), "প্রচ্ছদ" if language == "bn" else "Cover")
        else:
            from ...transformer.reading_structure import section_kind
            document = ET.fromstring(content)
            heading = next((node for node in document.iter() if node.tag in {f"{{{_XHTML}}}h1", f"{{{_XHTML}}}h2"}), None)
            kind = section_kind("".join(heading.itertext())) if heading is not None else None
            if kind:
                document.find(f"{{{_XHTML}}}body").set(f"{{{_EPUB}}}type", kind)
                replacements[posixpath.normpath(posixpath.join(base, item.get("href")))] = _xml(document)
                landmark(kind, item.get("href"), "".join(heading.itertext()))
                front_refs.append(ref)
    body_ref = next((ref for ref in spine if ref not in cover_refs and ref not in front_refs), None)
    if options.title_page:
        title = (book_meta.title if book_meta else None) or metadata.findtext(f"{{{_DC}}}title") or "Untitled"
        lines = []
        for label, values in (("", book_meta.authors if book_meta else []),
                              ("সম্পাদক" if language == "bn" else "Editor", book_meta.editors if book_meta else []),
                              ("অনুবাদক" if language == "bn" else "Translator", book_meta.translators if book_meta else [])):
            for value in values:
                lines.append(f"<p>{escape(label + ': ' if label else '')}{escape(value)}</p>")
        for value in ((book_meta.publisher if book_meta else None), options.source_date, options.edition):
            if value:
                lines.append(f"<p>{escape(value)}</p>")
        title_href = "pdf-craft-title.xhtml"
        css = next((item.get("href") for item in manifest if item.get("media-type") == "text/css"), None)
        style = f'<link rel="stylesheet" href="{escape(css, quote=True)}"/>' if css else ""
        document = (f'<html xmlns="{_XHTML}" xmlns:epub="{_EPUB}" xml:lang="{language}" lang="{language}">'
                    f'<head><title>{escape(title)}</title>{style}</head><body><section epub:type="titlepage">'
                    f'<h1>{escape(title)}</h1>{"".join(lines)}</section></body></html>')
        replacements[posixpath.join(base, title_href)] = document.encode("utf-8")
        ET.SubElement(manifest, f"{{{_OPF}}}item", {"id": "pdf-craft-title", "href": title_href,
                                                       "media-type": "application/xhtml+xml"})
        spine.insert(len(cover_refs), ET.Element(f"{{{_OPF}}}itemref", {"idref": "pdf-craft-title"}))
        landmark("titlepage", title_href, "নামপত্র" if language == "bn" else "Title page")
    landmark("toc", nav_item.get("href"), "সূচিপত্র" if language == "bn" else "Contents")
    if not any(ref.get("idref") == nav_item.get("id") for ref in spine):
        spine.insert(len(cover_refs) + int(options.title_page),
                     ET.Element(f"{{{_OPF}}}itemref", {"idref": nav_item.get("id"), "linear": "no"}))
    if body_ref is not None:
        landmark("bodymatter", items[body_ref.get("idref")].get("href"), "মূল পাঠ" if language == "bn" else "Start of content")
    for item in manifest:
        if item.get("media-type") != "application/xhtml+xml" or not item.get("href"):
            continue
        name = posixpath.normpath(posixpath.join(base, item.get("href")))
        try:
            content = replacements.get(name, archive.read(name))
        except KeyError:
            continue
        if b"<math" in content or b":math" in content or b"http://www.w3.org/1998/Math/MathML" in content:
            properties = item.get("properties", "").split()
            if "mathml" not in properties:
                item.set("properties", " ".join(properties + ["mathml"]).strip())
    replacements[nav_path] = _xml(nav)
    replacements[opf_path] = _xml(root)
    return replacements
