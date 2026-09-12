"""Markdown reading copy plus lossless, source-linked retrieval chunks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from tiktoken import get_encoding

from ...document import PDFCraftExtraction
from ...extractor.chapter import (
    AssetLayout, create_chapters_reader, references_to_map, search_references_in_chapter,
)
from ...markdown.render.layouts import render_layouts
from ...markdown.render.render import render_markdown_file, _render_footnotes_section
from ...metering import check_aborted


def render_markdown_bundle(extraction: PDFCraftExtraction, output: Path, *,
                           source_id: str, chunk_tokens: int = 800,
                           aborted=lambda: False) -> None:
    """Write book.md, chapters/, chunks.jsonl and source-map.json.

    Chunk offsets are Python Unicode codepoint offsets within a source-map
    segment, not tokenizer byte offsets. Concatenating chunks for a segment
    exactly reproduces its Markdown; Bengali combining marks are never split.
    Token counts use cl100k_base, not an assumed model-specific tokenizer.
    """
    if chunk_tokens < 16:
        raise ValueError("chunk_tokens must be at least 16")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    chapters_dir = output / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    assets_dir = output / "assets"
    assets_dir.mkdir(exist_ok=True)
    encoding = get_encoding("cl100k_base")
    sources = []
    with extraction._materialize() as paths, (output / "chunks.jsonl").open("w", encoding="utf-8") as chunk_file:
        render_markdown_file(paths.chapters, paths.assets, output / "book.md", assets_dir,
                             paths.cover if paths.cover.exists() else None, aborted)
        for number, chapter in enumerate(create_chapters_reader(paths.chapters)(), 1):
            check_aborted(aborted)
            chapter_id = f"chapter-{number:05d}"
            references = sorted(search_references_in_chapter(chapter), key=lambda ref: ref.id)
            ref_map = references_to_map(references)
            rendered = []
            for index, layout in enumerate(chapter.layouts):
                text = "".join(render_layouts([layout], paths.assets, assets_dir,
                                              Path("../assets"), chapter.level, ref_map))
                blocks = [layout] if isinstance(layout, AssetLayout) else layout.blocks
                locations = [{"page": block.page_index, "bbox": list(block.det),
                              "order": getattr(block, "order", None)} for block in blocks]
                rendered.append((f"{chapter_id}-s{index:05d}", text, locations))
            notes = "".join(_render_footnotes_section(references, paths.assets, assets_dir, Path("../assets")))
            if notes:
                rendered.append((f"{chapter_id}-notes", notes, [
                    {"page": ref.page_index, "order": ref.order, "bbox": None} for ref in references]))
            chapter_path = chapters_dir / f"{chapter_id}.md"
            chapter_path.write_text("\n\n".join(text for _, text, _ in rendered), encoding="utf-8")
            for segment_id, text, locations in rendered:
                sources.append({"id": segment_id, "chapter": chapter_id, "text": text, "locations": locations})
                for part, (start, end) in enumerate(split_chunks(text, chunk_tokens, encoding)):
                    content = text[start:end]
                    chunk = {"id": f"{source_id[:16]}-{segment_id}-{part:04d}",
                             "source_id": source_id, "chapter": chapter_id,
                             "markdown_file": str(chapter_path.relative_to(output)),
                             "segment_id": segment_id, "start": start, "end": end,
                             "pages": sorted({location["page"] for location in locations}),
                             "locations": locations, "text": content,
                             "token_count": len(encoding.encode(content, disallowed_special=())),
                             "tokenizer": "cl100k_base", "sha256": hashlib.sha256(content.encode()).hexdigest()}
                    chunk_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    (output / "source-map.json").write_text(json.dumps(
        {"source_id": source_id, "index_base": 1, "coordinate_space": "ocr_pixels",
         "dpi": extraction.render_dpi(), "segments": sources}, ensure_ascii=False, indent=2), encoding="utf-8")


def split_chunks(text: str, limit: int, encoding):
    """Prefer word boundaries; an indivisible oversized word is explicitly allowed."""
    start = 0
    end = 0
    for match in re.finditer(r"\S+\s*|\s+", text):
        next_end = match.end()
        if end > start and len(encoding.encode(text[start:next_end], disallowed_special=())) > limit:
            yield start, end
            start = end
        end = next_end
    if end > start:
        yield start, end
