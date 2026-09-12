# pylint: disable=protected-access

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, cast
from ...document import PDFCraftExtraction
from .render import render_epub_file
from .options import PublicationOptions
from epub_generator import BookMeta, LaTeXRender, TableRender

class EpubRenderer:
    """Render a PDFCraftExtraction to EPUB."""
    def render(self, extraction: PDFCraftExtraction, output_path: Path, *,
               book_meta: BookMeta | None = None,
               publication: PublicationOptions | None = None,
               lan: str | None = None, table_render=TableRender.HTML,
               latex_render=LaTeXRender.MATHML, inline_latex: bool = True,
               aborted=lambda: False) -> None:
        extraction.validate(require_toc=True)
        language = lan or extraction.language() or "zh"
        book_meta = book_meta or extraction.book_meta()
        if language not in {"zh", "en", "bn"}:
            raise ValueError(f"unsupported EPUB language: {language}")
        generator_language = cast(Literal["zh", "en"], "en" if language == "bn" else language)
        with extraction._materialize() as paths, TemporaryDirectory(prefix="pdf-craft-cover-") as temporary:
            cover = paths.cover if paths.cover.exists() else None
            if publication and publication.cover_path:
                from PIL import Image, ImageOps
                cover = Path(temporary) / "cover.png"
                with Image.open(publication.cover_path) as image:
                    ImageOps.exif_transpose(image).convert("RGB").save(cover)
            render_epub_file(paths.chapters, paths.toc, paths.assets,
                             output_path, cover,
                             book_meta, generator_language, table_render,
                             latex_render, inline_latex, aborted)
        from .publication import finalize_publication
        finalize_publication(output_path, language, publication, book_meta)
