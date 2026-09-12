"""Tesseract adapter that emits pdf-craft's stable page representation."""

from __future__ import annotations

import csv
import io
import os
import subprocess
import tempfile
import unicodedata
import time
from math import isfinite
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import ImageDraw, ImageOps, ImageStat
from PIL.Image import Image

from ..metering import AbortedCheck, check_aborted
from ..ocr_config import TesseractOCRLocalConfig
from .types import Page, PageLayout


class TesseractQualityError(RuntimeError):
    """Raised when every Tesseract attempt fails the configured quality gate."""


@dataclass(frozen=True)
class _Word:
    block: int
    paragraph: int
    line: int
    left: int
    top: int
    width: int
    height: int
    confidence: float
    text: str

    @property
    def det(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.left + self.width, self.top + self.height


@dataclass(frozen=True)
class _Candidate:
    words: tuple[_Word, ...]
    layouts: tuple[PageLayout, ...]
    confidence: float
    bengali_ratio: float
    ink_coverage: float
    page_ink_ratio: float
    passed: bool
    reason: str
    psm: int = 3
    variant: str = "original"
    elapsed_seconds: float = 0.0

    @property
    def score(self) -> float:
        return self.confidence + 10 * self.bengali_ratio + 10 * self.ink_coverage


class TesseractPageExtractor:
    """Run Tesseract once, retry weak pages, and retain the best safe result."""

    def __init__(self, config: TesseractOCRLocalConfig) -> None:
        self._config = config
        self._validated = False
        self._easyocr = None

    def download_ocr_model(self, revision: str | None) -> None:
        if revision is not None:
            raise ValueError("Tesseract language data does not use model revisions")
        self.load_ocr_model()

    def load_ocr_model(self) -> None:
        if self._validated:
            return
        version = self._run_command([self._config.executable, "--version"])
        if "tesseract" not in version.stdout.lower():
            raise RuntimeError("Configured executable is not Tesseract")
        languages = self._run_command([self._config.executable, "--list-langs"])
        available = {line.strip() for line in languages.stdout.splitlines()}
        if not set(self._config.language.split("+")).issubset(available):
            location = (
                f" in {self._config.tessdata_path}"
                if self._config.tessdata_path is not None
                else ""
            )
            raise RuntimeError(
                f"Tesseract language '{self._config.language}' is not installed{location}"
            )
        self._validated = True

    def recognize(
        self,
        image: Image,
        page_index: int,
        includes_raw_image: bool,
        plot_path: Path | None,
        aborted: AbortedCheck,
    ) -> Page:
        self.load_ocr_model()
        check_aborted(aborted)

        with tempfile.TemporaryDirectory(prefix="pdf-craft-tesseract-") as directory:
            root = Path(directory)
            original_path = root / "page.png"
            image.save(original_path, format="PNG")

            modes = self._config.page_segmentation_modes
            first = self._recognize_candidate(image, original_path, modes[0])
            candidates = [first]
            if not first.passed:
                for mode in modes[1:]:
                    check_aborted(aborted)
                    candidates.append(self._recognize_candidate(image, original_path, mode))

                if self._config.retry_with_autocontrast:
                    contrasted = ImageOps.autocontrast(ImageOps.grayscale(image))
                    contrasted_path = root / "page-autocontrast.png"
                    contrasted.save(contrasted_path, format="PNG")
                    for mode in modes:
                        check_aborted(aborted)
                        candidates.append(
                            self._recognize_candidate(contrasted, contrasted_path, mode)
                        )

        check_aborted(aborted)
        candidate = max(candidates, key=lambda item: (item.passed, item.score))
        alternatives = []
        if not candidate.passed and self._config.easyocr_fallback:
            try:
                alternatives = self._easyocr_alternatives(image)
            except (ImportError, RuntimeError, OSError) as error:
                alternatives = [{"error": str(error)}]
        if not candidate.passed and not candidate.words and self._config.fallback is not None:
            raise TesseractQualityError(
                f"Tesseract page {page_index} failed quality checks: {candidate.reason} "
                f"(confidence={candidate.confidence:.1f}, "
                f"bengali_ratio={candidate.bengali_ratio:.3f}, "
                f"ink_coverage={candidate.ink_coverage:.3f})"
            )

        layouts = [
            PageLayout(
                ref=layout.ref,
                det=layout.det,
                text=layout.text,
                order=order,
                hash=None,
            )
            for order, layout in enumerate(candidate.layouts)
        ]
        if plot_path is not None:
            self._save_plot(image, layouts, plot_path / f"page_{page_index}_stage_1.png")
        return Page(
            index=page_index,
            image=image if includes_raw_image else None,
            body_layouts=layouts,
            footnotes_layouts=[],
            input_tokens=0,
            output_tokens=0,
            diagnostics={
                "engine": "tesseract", "needs_review": not candidate.passed,
                "reason": candidate.reason,
                "attempts": [
                    {"psm": item.psm, "variant": item.variant, "elapsed_seconds": item.elapsed_seconds,
                     "confidence": item.confidence, "ink_coverage": item.ink_coverage,
                     "bengali_ratio": item.bengali_ratio, "passed": item.passed,
                     "text": " ".join(layout.text for layout in item.layouts)}
                    for item in candidates
                ],
                "words": [asdict(word) for word in candidate.words],
                "flagged_orders": [
                    index for index, layout in enumerate(layouts)
                    if not candidate.passed or any(
                        word.confidence < self._config.minimum_confidence
                        and layout.det[0] <= word.left < layout.det[2]
                        and layout.det[1] <= word.top < layout.det[3]
                        for word in candidate.words
                    )
                ],
                "alternatives": alternatives,
            },
        )

    def _easyocr_alternatives(self, image: Image) -> list[dict]:
        """Retain a second reading for review; confidence scales are incomparable."""
        import easyocr
        import numpy as np

        if self._easyocr is None:
            self._easyocr = easyocr.Reader(
                ["bn", "en"], gpu=False, verbose=False,
                model_storage_directory=str(self._config.easyocr_model_path)
                if self._config.easyocr_model_path else None,
            )
        return [{"text": text, "confidence": float(confidence),
                 "bbox": [[int(x), int(y)] for x, y in box]}
                for box, text, confidence in self._easyocr.readtext(np.asarray(image))]

    def _recognize_candidate(
        self, image: Image, image_path: Path, page_segmentation_mode: int
    ) -> _Candidate:
        started = time.monotonic()
        command = [
            self._config.executable,
            str(image_path),
            "stdout",
            "-l",
            self._config.language,
            "--oem",
            str(self._config.oem),
            "--psm",
            str(page_segmentation_mode),
            "-c",
            "tessedit_create_tsv=1",
        ]
        if not self._config.load_sublanguages:
            command.extend(["-c", "tessedit_load_sublangs="])
        result = self._run_command(command)
        words = self._parse_tsv(result.stdout)
        layouts = self._layouts_from_words(words, image.size)
        confidence = self._mean_confidence(words)
        bengali_ratio = self._bengali_ratio(words)
        ink_coverage, page_ink_ratio = self._ink_metrics(image, words)
        passed, reason = self._quality_result(
            words, confidence, bengali_ratio, ink_coverage, page_ink_ratio
        )
        return _Candidate(
            words=tuple(words),
            layouts=tuple(layouts),
            confidence=confidence,
            bengali_ratio=bengali_ratio,
            ink_coverage=ink_coverage,
            page_ink_ratio=page_ink_ratio,
            passed=passed,
            reason=reason,
            psm=page_segmentation_mode,
            variant="autocontrast" if "autocontrast" in image_path.stem else "original",
            elapsed_seconds=round(time.monotonic() - started, 4),
        )

    def _run_command(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if self._config.tessdata_path is not None:
            environment["TESSDATA_PREFIX"] = str(self._config.tessdata_path)
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._config.timeout_seconds,
                env=environment,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Tesseract executable was not found: {self._config.executable}"
            ) from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"Tesseract exceeded the {self._config.timeout_seconds}s timeout"
            ) from error
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "unknown error").strip()
            raise RuntimeError(f"Tesseract failed: {detail}") from error

    @staticmethod
    def _parse_tsv(content: str) -> list[_Word]:
        words: list[_Word] = []
        if not content.startswith("level\tpage_num\t"):
            raise RuntimeError("Tesseract returned malformed TSV output")
        for row in csv.DictReader(io.StringIO(content), delimiter="\t"):
            text = (row.get("text") or "").strip()
            if row.get("level") != "5" or not text:
                continue
            try:
                words.append(
                    _Word(
                        block=int(row["block_num"]),
                        paragraph=int(row["par_num"]),
                        line=int(row["line_num"]),
                        left=int(row["left"]),
                        top=int(row["top"]),
                        width=int(row["width"]),
                        height=int(row["height"]),
                        confidence=float(row["conf"]),
                        text=text,
                    )
                )
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError("Tesseract returned malformed TSV output") from error
            word = words[-1]
            if min(word.left, word.top) < 0 or min(word.width, word.height) <= 0 or not isfinite(word.confidence):
                raise RuntimeError("Tesseract returned invalid word geometry or confidence")
        return words

    @classmethod
    def _layouts_from_words(
        cls, words: list[_Word], image_size: tuple[int, int]
    ) -> list[PageLayout]:
        paragraphs: OrderedDict[tuple[int, int], list[_Word]] = OrderedDict()
        for word in words:
            paragraphs.setdefault((word.block, word.paragraph), []).append(word)

        layouts: list[PageLayout] = []
        paragraph_words = list(paragraphs.values())
        title_index = cls._title_index(paragraph_words, image_size)
        for index, group in enumerate(paragraph_words):
            lines: OrderedDict[int, list[str]] = OrderedDict()
            for word in group:
                lines.setdefault(word.line, []).append(word.text)
            text = " ".join(" ".join(line) for line in lines.values())
            text = cls._normalize_text(text)
            left = min(word.left for word in group)
            top = min(word.top for word in group)
            right = max(word.left + word.width for word in group)
            bottom = max(word.top + word.height for word in group)
            layouts.append(
                PageLayout(
                    ref="sub_title" if index == title_index else "text",
                    det=(left, top, right, bottom),
                    text=text,
                    order=index,
                    hash=None,
                )
            )
        return layouts

    @staticmethod
    def _normalize_text(text: str) -> str:
        for punctuation in "।,;:!?":
            text = text.replace(f" {punctuation}", punctuation)
        return " ".join(text.split())

    @staticmethod
    def _title_index(
        paragraphs: list[list[_Word]], image_size: tuple[int, int]
    ) -> int | None:
        if len(paragraphs) < 2:
            return None
        group = paragraphs[0]
        next_group = paragraphs[1]
        width, height = image_size
        left = min(word.left for word in group)
        top = min(word.top for word in group)
        right = max(word.left + word.width for word in group)
        bottom = max(word.top + word.height for word in group)
        next_top = min(word.top for word in next_group)
        median_height = sorted(word.height for word in group)[len(group) // 2]
        centered = abs(((left + right) / 2) - width / 2) <= width * 0.15
        return 0 if (
            top <= height * 0.20
            and len(group) <= 14
            and right - left <= width * 0.80
            and centered
            and next_top - bottom >= median_height * 1.25
        ) else None

    @staticmethod
    def _mean_confidence(words: list[_Word]) -> float:
        weights = [max(1, len(word.text)) for word in words]
        total = sum(weights)
        if total == 0:
            return 100.0
        return sum(
            max(0.0, word.confidence) * weight
            for word, weight in zip(words, weights)
        ) / total

    @staticmethod
    def _bengali_ratio(words: list[_Word]) -> float:
        characters = "".join(word.text for word in words)
        letters = [
            char for char in characters
            if unicodedata.category(char)[0] in {"L", "M"}
        ]
        if not letters:
            return 1.0
        return sum("\u0980" <= char <= "\u09ff" for char in letters) / len(letters)

    @staticmethod
    def _ink_metrics(image: Image, words: list[_Word]) -> tuple[float, float]:
        grayscale = ImageOps.grayscale(image)
        ink = grayscale.point(lambda value: 255 if value < 200 else 0)
        total_ink = ImageStat.Stat(ink).sum[0] / 255
        page_ink_ratio = total_ink / (image.width * image.height)
        if total_ink == 0:
            return 1.0, 0.0
        # An image mask keeps this dependency-free while avoiding per-pixel
        # Python loops.
        mask = grayscale.point(lambda _: 0)
        drawing = ImageDraw.Draw(mask)
        for word in words:
            drawing.rectangle(word.det, fill=255)
        covered_ink = ImageStat.Stat(ink, mask=mask).sum[0] / 255
        return covered_ink / total_ink, page_ink_ratio

    def _quality_result(
        self,
        words: list[_Word],
        confidence: float,
        bengali_ratio: float,
        ink_coverage: float,
        page_ink_ratio: float,
    ) -> tuple[bool, str]:
        if not words:
            if page_ink_ratio <= self._config.blank_page_ink_ratio:
                return True, "blank page"
            return False, "no text detected on a non-blank page"
        failures: list[str] = []
        if confidence < self._config.minimum_confidence:
            failures.append("low confidence")
        letter_count = sum(
            unicodedata.category(char)[0] in {"L", "M"}
            for word in words for char in word.text
        )
        if "ben" in self._config.language.split("+") and letter_count >= 20 and bengali_ratio < self._config.minimum_bengali_ratio:
            failures.append("low Bengali character ratio")
        if ink_coverage < self._config.minimum_ink_coverage:
            failures.append("low page ink coverage")
        return not failures, ", ".join(failures) or "passed"

    @staticmethod
    def _save_plot(image: Image, layouts: list[PageLayout], path: Path) -> None:
        plotted = image.copy().convert("RGB")
        drawing = ImageDraw.Draw(plotted)
        for layout in layouts:
            color = "#d97706" if layout.ref == "sub_title" else "#059669"
            drawing.rectangle(layout.det, outline=color, width=3)
        path.parent.mkdir(parents=True, exist_ok=True)
        plotted.save(path, format="PNG")
