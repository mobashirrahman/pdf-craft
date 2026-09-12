from dataclasses import dataclass, field
from math import isfinite
from os import PathLike
from pathlib import Path
from typing import Iterable, Literal, TypeAlias

from .to_path import to_path


@dataclass(frozen=True)
class DeepSeekOCRLocalConfig:
    models_cache_path: Path | None = None
    local_only: bool = False
    enable_devices_numbers: tuple[int, ...] | None = None

    def __init__(
        self,
        models_cache_path: PathLike | str | None = None,
        local_only: bool = False,
        enable_devices_numbers: Iterable[int] | None = None,
    ) -> None:
        object.__setattr__(
            self,
            "models_cache_path",
            to_path(models_cache_path) if models_cache_path is not None else None,
        )
        object.__setattr__(self, "local_only", local_only)
        object.__setattr__(
            self,
            "enable_devices_numbers",
            tuple(enable_devices_numbers) if enable_devices_numbers is not None else None,
        )


@dataclass(frozen=True)
class DeepSeekOCR2LocalConfig:
    models_cache_path: Path | None = None
    local_only: bool = False
    enable_devices_numbers: tuple[int, ...] | None = None

    def __init__(
        self,
        models_cache_path: PathLike | str | None = None,
        local_only: bool = False,
        enable_devices_numbers: Iterable[int] | None = None,
    ) -> None:
        object.__setattr__(
            self,
            "models_cache_path",
            to_path(models_cache_path) if models_cache_path is not None else None,
        )
        object.__setattr__(self, "local_only", local_only)
        object.__setattr__(
            self,
            "enable_devices_numbers",
            tuple(enable_devices_numbers) if enable_devices_numbers is not None else None,
        )


@dataclass(frozen=True)
class UnlimitedOCRLocalConfig:
    models_cache_path: Path | None = None
    local_only: bool = False
    enable_devices_numbers: tuple[int, ...] | None = None

    def __init__(
        self,
        models_cache_path: PathLike | str | None = None,
        local_only: bool = False,
        enable_devices_numbers: Iterable[int] | None = None,
    ) -> None:
        object.__setattr__(
            self,
            "models_cache_path",
            to_path(models_cache_path) if models_cache_path is not None else None,
        )
        object.__setattr__(self, "local_only", local_only)
        object.__setattr__(
            self,
            "enable_devices_numbers",
            tuple(enable_devices_numbers) if enable_devices_numbers is not None else None,
        )


@dataclass(frozen=True)
class DeepSeekOCRVendorConfig:
    base_url: str
    api_key: str = field(repr=False)
    model: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int = 8000
    timeout_seconds: int = 180


@dataclass(frozen=True)
class DeepSeekOCR2VendorConfig:
    base_url: str
    api_key: str = field(repr=False)
    model: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int = 8000
    timeout_seconds: int = 180


@dataclass(frozen=True)
class UnlimitedOCRVendorConfig:
    ak: str = field(repr=False)
    sk: str = field(repr=False)
    base_url: str = "https://aip.baidubce.com"
    poll_interval_seconds: float = 2.0
    timeout_seconds: int = 180


FallbackOCRConfig: TypeAlias = (
    DeepSeekOCRLocalConfig
    | DeepSeekOCR2LocalConfig
    | UnlimitedOCRLocalConfig
    | DeepSeekOCRVendorConfig
    | DeepSeekOCR2VendorConfig
    | UnlimitedOCRVendorConfig
)


@dataclass(frozen=True)
class TesseractOCRLocalConfig:
    """Local Tesseract OCR with conservative quality-gated retries.

    Tesseract itself and the requested language data are system dependencies.
    ``tessdata_path`` may point at a downloaded ``tessdata_best`` directory.
    """

    executable: str = "tesseract"
    tessdata_path: Path | None = None
    language: str = "ben"
    page_segmentation_modes: tuple[int, ...] = (3, 6)
    oem: int = 1
    timeout_seconds: int = 120
    minimum_confidence: float = 65.0
    minimum_bengali_ratio: float = 0.60
    minimum_ink_coverage: float = 0.45
    blank_page_ink_ratio: float = 0.002
    retry_with_autocontrast: bool = True
    load_sublanguages: bool = False
    fallback: FallbackOCRConfig | None = None
    easyocr_fallback: bool = False
    easyocr_model_path: Path | None = None

    def __init__(
        self,
        executable: PathLike | str = "tesseract",
        tessdata_path: PathLike | str | None = None,
        language: str = "ben",
        page_segmentation_modes: Iterable[int] = (3, 6),
        oem: int = 1,
        timeout_seconds: int = 120,
        minimum_confidence: float = 65.0,
        minimum_bengali_ratio: float = 0.60,
        minimum_ink_coverage: float = 0.45,
        blank_page_ink_ratio: float = 0.002,
        retry_with_autocontrast: bool = True,
        load_sublanguages: bool = False,
        fallback: FallbackOCRConfig | None = None,
        easyocr_fallback: bool = False,
        easyocr_model_path: PathLike | str | None = None,
    ) -> None:
        modes = tuple(page_segmentation_modes)
        if not modes or any(type(mode) is not int or mode < 3 or mode > 13 for mode in modes):
            raise ValueError("page_segmentation_modes must contain text recognition modes from 3 to 13")
        if type(oem) is not int or oem < 0 or oem > 3:
            raise ValueError("oem must be between 0 and 3")
        if not isfinite(timeout_seconds) or timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        if not isfinite(minimum_confidence) or minimum_confidence < 0 or minimum_confidence > 100:
            raise ValueError("minimum_confidence must be between 0 and 100")
        for name, value in (
            ("minimum_bengali_ratio", minimum_bengali_ratio),
            ("minimum_ink_coverage", minimum_ink_coverage),
            ("blank_page_ink_ratio", blank_page_ink_ratio),
        ):
            if not isfinite(value) or value < 0 or value > 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if not language.strip() or not str(executable).strip():
            raise ValueError("language and executable must be nonempty")

        object.__setattr__(self, "executable", str(executable))
        object.__setattr__(
            self,
            "tessdata_path",
            to_path(tessdata_path) if tessdata_path is not None else None,
        )
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "page_segmentation_modes", modes)
        object.__setattr__(self, "oem", oem)
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "minimum_confidence", minimum_confidence)
        object.__setattr__(self, "minimum_bengali_ratio", minimum_bengali_ratio)
        object.__setattr__(self, "minimum_ink_coverage", minimum_ink_coverage)
        object.__setattr__(self, "blank_page_ink_ratio", blank_page_ink_ratio)
        object.__setattr__(self, "retry_with_autocontrast", retry_with_autocontrast)
        object.__setattr__(self, "load_sublanguages", load_sublanguages)
        object.__setattr__(self, "fallback", fallback)
        object.__setattr__(self, "easyocr_fallback", easyocr_fallback)
        object.__setattr__(self, "easyocr_model_path", to_path(easyocr_model_path) if easyocr_model_path else None)


LocalOCRConfig: TypeAlias = (
    DeepSeekOCRLocalConfig
    | DeepSeekOCR2LocalConfig
    | UnlimitedOCRLocalConfig
    | TesseractOCRLocalConfig
)
VendorOCRConfig: TypeAlias = (
    DeepSeekOCRVendorConfig | DeepSeekOCR2VendorConfig | UnlimitedOCRVendorConfig
)
OCRConfig: TypeAlias = LocalOCRConfig | VendorOCRConfig
OCRMode: TypeAlias = Literal[
    "deepseek-ocr-local",
    "deepseek-ocr2-local",
    "unlimited-ocr-local",
    "tesseract-ocr-local",
    "deepseek-ocr-vendor",
    "deepseek-ocr2-vendor",
    "unlimited-ocr-vendor",
]


def ensure_ocr_config(
    ocr: OCRConfig | None,
    models_cache_path: PathLike | str | None,
    local_only: bool,
) -> OCRConfig:
    if ocr is not None:
        if models_cache_path is not None or local_only:
            raise ValueError(
                "ocr cannot be combined with models_cache_path or local_only."
            )
        return ocr
    return DeepSeekOCRLocalConfig(
        models_cache_path=models_cache_path,
        local_only=local_only,
    )
