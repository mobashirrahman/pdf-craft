"""Audited reading-copy structure recovery, using extraction facts only."""

from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from ..common import save_xml, read_xml
from ..document import PDFCraftExtraction
from ..extractor.chapter import create_chapters_reader, ParagraphLayout
from ..extractor.chapter.chapter import Chapter, encode
from ..extractor.toc.types import Toc, TocInfo, encode as encode_toc, decode as decode_toc, iter_toc
from ..pdf import TITLE_TAGS

_FRONT = {"ভূমিকা", "উৎসর্গ", "নিবেদন", "মুখবন্ধ", "প্রাককথন", "preface", "dedication", "foreword", "introduction"}
_BACK = {"পরিশিষ্ট", "গ্রন্থপঞ্জি", "appendix", "bibliography", "acknowledgments"}
_NUMBER = r"(?:[০-৯0-9]+|[ivxlcdm]+|প্রথম|দ্বিতীয়|দ্বিতীয়|তৃতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম)"
_HEADING = re.compile(rf"^(?:(?:chapter|part|book|অধ্যায়|অধ্যায়|পরিচ্ছেদ|খণ্ড|খন্ড|পর্ব)\s+{_NUMBER}|{_NUMBER}\s+(?:অধ্যায়|অধ্যায়|পরিচ্ছেদ|খণ্ড|খন্ড|পর্ব))(?:\s*[:—–-]\s*.{{1,60}})?$", re.I)
_SCENE = re.compile(r"^(?:\*\s*){3,}$|^(?:✦\s*){1,3}$|^(?:⁂)$")


def plain(layout):
    if not isinstance(layout, ParagraphLayout) or not all(isinstance(part, str) for block in layout.blocks for part in block.content):
        return None
    return "".join(part for block in layout.blocks for part in block.content)


def section_kind(text):
    text = text.strip().casefold()
    if text in _FRONT:
        return "dedication" if text in {"উৎসর্গ", "dedication"} else "preface"
    if text in _BACK:
        return "appendix" if text in {"পরিশিষ্ট", "appendix"} else "bibliography"
    return None


def recover_structure(extraction, output: Path, audit_path: Path, overrides=()):
    """Create a new .pcex; source extraction and removed text remain recoverable.

    Overrides select an exact one-block paragraph by page/order, never replace text.
    Unknown or ambiguous selectors fail rather than silently applying elsewhere.
    """
    sizes = extraction.page_pixel_sizes()
    events = []
    with extraction._materialize() as paths, TemporaryDirectory(prefix="reading-structure-") as temporary:
        root = Path(temporary) / "extraction"
        shutil.copytree(paths.root, root)
        chapters = deepcopy(list(create_chapters_reader(paths.chapters)()))
        old_levels = {item.id: item.level for item in iter_toc(decode_toc(read_xml(paths.toc)).content)} if paths.toc.exists() else {}
        selected = {}
        for rule in overrides:
            if not isinstance(rule, dict) or set(rule) - {"page", "order", "kind", "level"}:
                raise ValueError("Structure override requires page, order, kind and optional level")
            if type(rule.get("page")) is not int or rule["page"] < 1 or type(rule.get("order")) is not int or rule["order"] < 0:
                raise ValueError("Structure selectors require positive page and nonnegative order")
            if rule.get("kind") not in {"heading", "verse", "letter", "quote", "scene-break", "keep", "remove"}:
                raise ValueError("Unknown structure override kind")
            if type(rule.get("level", 0)) is not int or not 0 <= rule.get("level", 0) <= 5:
                raise ValueError("Structure heading level must be 0–5")
            key = (rule["page"], rule["order"])
            if key in selected:
                raise ValueError("Duplicate structure selector")
            selected[key] = rule
        matches = defaultdict(int)
        for ch in chapters:
            for layout in ch.layouts:
                if isinstance(layout, ParagraphLayout) and len(layout.blocks) == 1:
                    block = layout.blocks[0]
                    matches[(block.page_index, block.order)] += 1
        if any(matches[key] != 1 for key in selected):
            raise ValueError("Structure selector must match exactly one single-block paragraph")
        # Repeated small text wholly outside the body, separated from body text.
        groups = defaultdict(list)
        page_blocks = defaultdict(list)
        for ch in chapters:
            for layout in ch.layouts:
                if isinstance(layout, ParagraphLayout):
                    for block in layout.blocks:
                        page_blocks[block.page_index].append(block)
        for ch in chapters:
            for layout in ch.layouts:
                if not isinstance(layout, ParagraphLayout) or layout.ref in TITLE_TAGS:
                    continue
                for block in layout.blocks:
                    if not all(isinstance(part, str) for part in block.content):
                        continue
                    text = "".join(block.content).strip()
                    width, height = sizes[block.page_index]
                    if not text or len(text) > 80 or "\n" in text or block.det[3] - block.det[1] > .035 * height:
                        continue
                    band = "top" if block.det[3] < .075 * height else "bottom" if block.det[1] > .925 * height else None
                    if not band:
                        continue
                    body = [other for other in page_blocks[block.page_index] if .1 * height <= other.det[1] and other.det[3] <= .9 * height]
                    if not body:
                        continue
                    signature = ("number", int(text) - block.page_index) if text.isdecimal() else ("text", " ".join(text.split()))
                    groups[(band, round(block.det[1] / height, 2), signature)].append(block)
        removed = set()
        for (band, _, signature), blocks in groups.items():
            pages = {block.page_index for block in blocks}
            # Allow alternating running titles; require majority within one parity.
            support = max((len({p for p in pages if p % 2 == parity}) / max(1, len([p for p in sizes if p % 2 == parity])) for parity in (0, 1)))
            if len(pages) < 3 or support < .6:
                continue
            for block in blocks:
                key = (block.page_index, block.order)
                if key in selected:
                    continue
                removed.add(key)
                events.append({"action": "remove", "reason": f"repeated {band} margin {signature[0]}",
                               "page": block.page_index, "order": block.order, "bbox": block.det,
                               "text": "".join(block.content), "support_pages": sorted(pages)})
        result = []
        part_active = False
        for original in chapters:
            current = Chapter(None, old_levels.get(original.id, max(0, original.level)), [])
            for layout in original.layouts:
                if isinstance(layout, ParagraphLayout):
                    layout.blocks = [b for b in layout.blocks if (b.page_index, b.order) not in removed]
                    if not layout.blocks:
                        continue
                    block = layout.blocks[0]
                    rule = selected.get((block.page_index, block.order)) if len(layout.blocks) == 1 else None
                    text = plain(layout)
                    if rule and rule["kind"] == "remove":
                        events.append({"action": "remove", "reason": "manual override", "xml": ET.tostring(encode(Chapter(None, 0, [layout])), encoding="unicode")})
                        continue
                    if rule and rule["kind"] not in {"keep", "heading"}:
                        layout.ref = rule["kind"]
                    is_heading = layout.ref in TITLE_TAGS
                    if rule and rule["kind"] == "heading":
                        is_heading = True
                    elif not rule and text and len(layout.blocks) == 1 and len(text.strip()) <= 90 and "\n" not in text.strip():
                        width, height = sizes[block.page_index]
                        centered = abs((block.det[0] + block.det[2]) / 2 - width / 2) < .12 * width
                        isolated = not any(other is not block and other.det[1] < block.det[3] + .012 * height and other.det[3] > block.det[1] - .012 * height for other in page_blocks[block.page_index])
                        is_heading |= centered and isolated and .08 * height < block.det[1] < .85 * height and (bool(_HEADING.fullmatch(text.strip())) or bool(section_kind(text)))
                        if _SCENE.fullmatch(text.strip()):
                            layout.ref = "scene-break"
                    if rule and rule["kind"] == "keep":
                        is_heading = layout.ref in TITLE_TAGS
                    if is_heading:
                        if current.layouts:
                            result.append(current)
                        level = old_levels.get(original.id, max(0, original.level)) if not current.layouts else max(0, layout.level)
                        if rule:
                            level = rule.get("level", level)
                        elif layout.ref not in TITLE_TAGS:
                            is_part = bool(re.search(r"\b(?:part|book)\b|খণ্ড|খন্ড|পর্ব", text or "", re.I))
                            level = 0 if is_part or section_kind(text or "") else int(part_active)
                            part_active = is_part or part_active
                        layout.ref, layout.level = "title", 0
                        current = Chapter(None, level, [])
                        events.append({"action": "heading", "page": block.page_index, "order": block.order,
                                       "text": text, "level": level, "section": section_kind(text or "")})
                    elif layout.ref in {"verse", "letter", "quote", "scene-break"}:
                        events.append({"action": "layout", "kind": layout.ref, "page": block.page_index, "order": block.order})
                    elif text and not rule:
                        lines = [line.strip() for line in text.splitlines() if line.strip()]
                        # Existing short, ragged lines are preserved, never synthesized.
                        if len(lines) >= 3 and max(map(len, lines)) <= 60 and min(map(len, lines)) >= 4 and max(map(len, lines)) >= 1.6 * min(map(len, lines)):
                            layout.ref = "verse"
                        if len(lines) >= 3 and re.match(r"^(?:Dear\b|প্রিয়\b|প্রিয়\b)", lines[0], re.I) and any(re.match(r"^(?:ইতি|বিনীত|Yours\b|Sincerely\b)", line, re.I) for line in lines[-3:]):
                            layout.ref = "letter"
                        if text.strip().startswith("“") and text.strip().endswith("”") and block.det[0] > .18 * sizes[block.page_index][0] and block.det[2] < .82 * sizes[block.page_index][0]:
                            layout.ref = "quote"
                        if layout.ref in {"verse", "letter", "quote"}:
                            events.append({"action": "layout", "kind": layout.ref, "page": block.page_index, "order": block.order,
                                           "reason": "existing line breaks or explicit quotation/salutation"})
                current.layouts.append(layout)
            if current.layouts:
                result.append(current)
        # Build a fresh chapter tree; source locations, assets and references survive.
        for path in (root / "chapters").glob("chapter_*.xml"):
            path.unlink()  # disposable copy only, never the input extraction
        toc, stack = [], []
        for index, ch in enumerate(result, 1):
            ch.id = index
            save_xml(encode(ch), root / "chapters" / f"chapter_{index}.xml")
            first = ch.layouts[0]
            block = first.blocks[0] if isinstance(first, ParagraphLayout) else first
            item = Toc(index, block.page_index, getattr(block, "order", 0), ch.level, [])
            while stack and stack[-1].level >= item.level:
                stack.pop()
            (stack[-1].children if stack else toc).append(item)
            stack.append(item)
        save_xml(encode_toc(TocInfo(toc, [])), root / "toc.xml")
        transformed = PDFCraftExtraction._from_workspace(root).export(output)
    audit_path.write_text(json.dumps({"protocol": "reading-structure-1", "events": events,
                                     "note": "Original extraction retained; flattened line breaks are not invented."}, ensure_ascii=False, indent=2), encoding="utf-8")
    return transformed
