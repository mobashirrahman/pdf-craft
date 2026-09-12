# OCR Backend Guide

Choose one OCR configuration for each PDF extraction. Local backends run models on a CUDA-capable NVIDIA GPU (or, for Tesseract, a CPU); vendor backends send pages to a remote service. Use local OCR for local or offline processing after models are cached. Use vendor OCR when you do not have CUDA or prefer managed compute.

DeepSeek OCR and DeepSeek OCR 2 are from [DeepSeek](https://github.com/deepseek-ai/DeepSeek-OCR); [Unlimited OCR](https://github.com/baidu/Unlimited-OCR) is from Baidu; Tesseract is the [Tesseract OCR engine](https://github.com/tesseract-ocr/tesseract), run as a system dependency rather than a downloaded model.

| Configuration | Model | Runtime |
| --- | --- | --- |
| `DeepSeekOCRLocalConfig` | DeepSeek OCR | Local GPU |
| `DeepSeekOCR2LocalConfig` | DeepSeek OCR 2 | Local GPU |
| `UnlimitedOCRLocalConfig` | Unlimited OCR | Local GPU |
| `TesseractOCRLocalConfig` | Tesseract | Local CPU |
| `DeepSeekOCRVendorConfig` | DeepSeek OCR | OpenAI-compatible remote service |
| `DeepSeekOCR2VendorConfig` | DeepSeek OCR 2 | OpenAI-compatible remote service |
| `UnlimitedOCRVendorConfig` | Unlimited OCR | Baidu remote service |

Pass a configuration through `PDFOptions(ocr=...)`; the library does not load `.env` files.

## Local backends

All three local configurations accept `models_cache_path`, `local_only`, and `enable_devices_numbers`.

```python
from pdf_craft import DeepSeekOCRLocalConfig, PDFCraft, PDFOptions

craft = PDFCraft(pdf=PDFOptions(ocr=DeepSeekOCRLocalConfig(
    models_cache_path="models-cache",
    enable_devices_numbers=[0],
)))
```

`local_only=True` prevents a missing model from downloading. Use it only after the model is present in the selected cache. Device numbers are interpreted by the upstream OCR runtime and normally correspond to CUDA devices visible to the process.

`ocr_size` belongs to `ExtractionOptions`, not the OCR configuration. Unlimited OCR local supports `base` and `gundam`. DeepSeek OCR 2 local is validated with `base`; explicit `tiny` is rejected before extraction.

## Tesseract (CPU, no GPU required)

`TesseractOCRLocalConfig` drives a system-installed `tesseract` binary with
conservative quality gating rather than a downloaded model:

```python
from pdf_craft import TesseractOCRLocalConfig, PDFCraft, PDFOptions

craft = PDFCraft(pdf=PDFOptions(ocr=TesseractOCRLocalConfig(
    tessdata_path="/path/to/tessdata_best",
    language="ben",
)))
```

`executable` (default `"tesseract"`) and the requested `language` traineddata are
system dependencies you install yourself; `tessdata_path` points at a downloaded
`tessdata_best` directory when the system's own tessdata is not the version you
want. `page_segmentation_modes` (default `(3, 6)`) and `oem` (default `1`) are
retried in order. A page's OCR is accepted only when it clears all three quality
gates: `minimum_confidence` (Tesseract's own reported confidence, default `65.0`),
`minimum_bengali_ratio` (share of recognized characters in the Bengali block,
default `0.60` — adjust or ignore for other scripts), and `minimum_ink_coverage`
(share of the page that is dark ink versus background, default `0.45`, which
catches a segmentation mode returning almost nothing). A page that fails every
attempted mode is reported empty rather than returning a low-confidence guess.

## Vendor backends

DeepSeek vendor configurations take `base_url`, `api_key`, and `model`; they also accept `temperature`, `top_p`, `max_tokens` (default `8000`), and `timeout_seconds` (default `180`).

```python
from pdf_craft import DeepSeekOCRVendorConfig, PDFCraft, PDFOptions

craft = PDFCraft(pdf=PDFOptions(ocr=DeepSeekOCRVendorConfig(
    base_url="https://example.com/v1",
    api_key="your-api-key",
    model="deepseek-ocr",
)))
```

`UnlimitedOCRVendorConfig` takes Baidu `ak` and `sk`; its `base_url` defaults to `https://aip.baidubce.com`. It also accepts `poll_interval_seconds` and `timeout_seconds`.

```python
from pdf_craft import UnlimitedOCRVendorConfig

ocr = UnlimitedOCRVendorConfig(ak="your-access-key", sk="your-secret-key")
```

## Convenience defaults

When `PDFOptions` has no explicit `ocr`, `models_cache_path` and `local_only` configure the default local DeepSeek OCR setup. Do not combine either convenience field with an explicit `ocr` configuration; that is rejected because the ownership of those settings would be ambiguous.

OCR recognizes pages only. Text translation uses a separate LLM configuration; see the PDF and EPUB guides.
