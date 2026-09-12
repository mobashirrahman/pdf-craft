"""Publication-only settings; changing these never changes extracted text."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PublicationOptions:
    """Optional enrichment of an EPUB; bibliographic people live in BookMeta.

    ``source_date`` describes the scanned edition, not this digital publication.
    A cover override is a local raster image. No images or fonts are downloaded.
    """

    source_date: str | None = None
    edition: str | None = None
    subjects: list[str] = field(default_factory=list)
    rights: str | None = None
    source_identifier: str | None = None
    identifier: str | None = None
    cover_path: Path | None = None
    title_page: bool = True
