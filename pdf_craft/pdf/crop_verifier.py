"""Corroborate proposed glyph corrections with fresh, tightly cropped OCR."""

import hashlib
from pathlib import Path
import unicodedata

from PIL import ImageOps

from .handler import DefaultPDFHandler
from .tesseract import TesseractPageExtractor


class TesseractCropVerifier:
    def __init__(self, source: Path, config, diagnostics: dict[int, dict], evidence_path: Path, dpi: int = 300):
        self.source, self.diagnostics, self.dpi = source, diagnostics, dpi
        self.adapter = TesseractPageExtractor(config)
        self.evidence_path = evidence_path
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        self.document = None
        self._page = None
        self._image = None

    def close(self):
        if self.document is not None:
            self.document.close()
            self.document = None
        if self._image is not None:
            self._image.close()
            self._image = None

    def __call__(self, block, edit: dict) -> dict:
        words = self.diagnostics.get(block.page_index, {}).get("words", [])
        matches = [word for word in words if _word(word["text"]) == _word(edit["before"])
                   and block.det[0] <= word["left"] < block.det[2]
                   and block.det[1] <= word["top"] < block.det[3]]
        if len(matches) != 1:
            return {"supported": False, "reason": "no unique source word box"}
        word = matches[0]
        det = (word["left"], word["top"], word["left"] + word["width"], word["top"] + word["height"])
        if self.document is None:
            self.document = DefaultPDFHandler().open(self.source)
        if self._page != block.page_index:
            if self._image is not None:
                self._image.close()
            self._image = self.document.render_page(block.page_index, self.dpi)
            self._page = block.page_index
        crop = ImageOps.expand(self._image.crop(det), border=12, fill="white")
        crop = crop.resize((crop.width * 2, crop.height * 2))
        name = f"p{block.page_index}-b{block.order}-{hashlib.sha256(edit['before'].encode()).hexdigest()[:12]}.png"
        path = self.evidence_path / name
        crop.save(path)
        readings = []
        # Two segmentation assumptions must independently reproduce the proposed
        # word. These are correlated Tesseract readings, not proof of correctness.
        for mode in (8, 13):
            candidate = self.adapter._recognize_candidate(crop, path, mode)
            text = " ".join(word.text for word in candidate.words)
            readings.append({"psm": mode, "text": text, "confidence": candidate.confidence})
        return {"supported": all(_word(item["text"]) == _word(edit["after"]) and item["confidence"] >= 80 for item in readings),
                "crop": str(path), "bbox": det, "readings": readings}


def _word(text: str) -> str:
    return unicodedata.normalize("NFC", text.strip(" \t\r\n।॥,;:!?\"'—–-()[]"))
