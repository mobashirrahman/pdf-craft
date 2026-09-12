"""Repository-local CLI for repeatable pdf-craft conversions and smoke runs."""

import argparse
import gc
import importlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from pdf_craft import (
    ChapterXMLTransformer,
    ExtractionOptions,
    OCRMode,
    OCRTokensMetering,
    PDFCraft,
    PDFCraftExtraction,
    PDFOptions,
    SubmitKind,
    XMLTranslator,
)

from .runtime import (
    create_ocr_config_from_env,
    create_llm_from_env,
    load_project_env,
    ocr_mode_from_env,
    ocr_values_from_env,
    llm_values_from_env,
)
from .paths import DEFAULT_OUTPUT_ROOT, create_run_directory
from .smoke import SmokeRun, expand_matrix, run_smoke
from .smoke.assets import discover_assets


@dataclass(frozen=True)
class _ExtractionResult:
    craft: PDFCraft
    extraction: PDFCraftExtraction
    path: Path
    metering: OCRTokensMetering


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    result = args.handler(args)
    return result if isinstance(result, int) else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", title="commands")

    pdf = commands.add_parser("pdf", help="extract, convert, or translate a PDF")
    pdf_commands = pdf.add_subparsers(dest="pdf_command", required=True)
    extract = pdf_commands.add_parser("extract", help="PDF -> PDFCraftExtraction (.pcex)")
    _add_pdf_source(extract)
    _add_extraction_options(extract)
    extract.set_defaults(handler=_extract_pdf)

    convert = pdf_commands.add_parser("convert", help="PDF -> Markdown or EPUB")
    _add_pdf_source(convert)
    convert.add_argument("--format", choices=("markdown", "epub"), required=True)
    convert.add_argument("--output", type=Path, help="rendered file; defaults inside --work-dir")
    _add_extraction_options(convert)
    convert.set_defaults(handler=_convert_pdf)

    translate = pdf_commands.add_parser("translate", help="PDF -> translated Markdown, EPUB, or PDF")
    _add_pdf_source(translate)
    translate.add_argument("target_language")
    translate.add_argument("--format", choices=("markdown", "epub", "pdf"), default="pdf")
    translate.add_argument("--output", type=Path, help="translated file; defaults inside --work-dir")
    _add_translation_options(translate)
    _add_extraction_options(translate)
    translate.set_defaults(handler=_translate_pdf)

    proofread = pdf_commands.add_parser(
        "proofread", help="PDF -> proofread Markdown or EPUB"
    )
    _add_pdf_source(proofread)
    proofread.add_argument("--format", choices=("markdown", "epub"), required=True)
    proofread.add_argument("--output", type=Path, help="proofread file; defaults inside --work-dir")
    _add_proofreading_options(proofread)
    _add_extraction_options(proofread)
    proofread.set_defaults(handler=_proofread_pdf)

    package = commands.add_parser("package", help="operate on a PDFCraftExtraction (.pcex)")
    package_commands = package.add_subparsers(dest="package_command", required=True)
    package_translate = package_commands.add_parser(
        "translate", help="translate an existing PDFCraftExtraction"
    )
    package_translate.add_argument("package", type=Path)
    package_translate.add_argument("target_language")
    package_translate.add_argument("--output-package", type=Path)
    _add_work_dir(package_translate, "isolated run directory")
    _add_translation_options(package_translate)
    package_translate.set_defaults(handler=_translate_package)

    package_proofread = package_commands.add_parser(
        "proofread", help="proofread an existing PDFCraftExtraction"
    )
    package_proofread.add_argument("package", type=Path)
    package_proofread.add_argument("--format", choices=("markdown", "epub"), required=True)
    package_proofread.add_argument("--output", type=Path, help="proofread file; defaults inside --work-dir")
    package_proofread.add_argument("--output-package", type=Path)
    _add_work_dir(package_proofread, "isolated run directory")
    _add_proofreading_options(package_proofread)
    package_proofread.set_defaults(handler=_proofread_package)

    package_patch = package_commands.add_parser(
        "patch-pdf", help="patch an original PDF with a PDFCraftExtraction"
    )
    package_patch.add_argument("source", type=Path)
    package_patch.add_argument("package", type=Path)
    package_patch.add_argument("--output", type=Path, help="patched PDF; defaults inside --work-dir")
    _add_work_dir(package_patch, "isolated run directory")
    package_patch.set_defaults(handler=_patch_package_pdf)

    render = package_commands.add_parser("render", help="PDFCraftExtraction -> Markdown or EPUB")
    render.add_argument("package", type=Path)
    render.add_argument("--format", choices=("markdown", "epub"), required=True)
    render.add_argument("--output", type=Path, help="rendered file; defaults inside --work-dir")
    _add_work_dir(render, "isolated run directory")
    render.set_defaults(handler=_render_package)

    epub = commands.add_parser("epub", help="translate an existing EPUB")
    epub_commands = epub.add_subparsers(dest="epub_command", required=True)
    epub_translate = epub_commands.add_parser("translate", help="EPUB -> translated EPUB")
    epub_translate.add_argument("source", type=Path)
    epub_translate.add_argument("target_language")
    epub_translate.add_argument("--output", type=Path, help="translated file; defaults inside --work-dir")
    _add_work_dir(epub_translate, "isolated run directory")
    _add_translation_options(epub_translate)
    epub_translate.set_defaults(handler=_translate_epub)

    batch = commands.add_parser(
        "batch", help="recursively OCR and proofread a directory of PDFs"
    )
    batch.add_argument("source", type=Path, help="directory containing PDF books")
    batch.add_argument("--output-dir", type=Path, required=True)
    batch.add_argument("--format", choices=("markdown", "epub", "both"), default="both")
    batch.add_argument(
        "--stage", choices=("all", "extract", "proofread"), default="all",
        help="run OCR first, proofreading second, or both as separate GPU phases",
    )
    batch.add_argument("--limit", type=int, help="process only the first N books")
    batch.add_argument("--dry-run", action="store_true", help="list books without loading OCR or LLMs")
    batch.add_argument("--fail-fast", action="store_true")
    batch.add_argument("--ocr-mode", choices=_ocr_modes(), help="overrides PDF_CRAFT_OCR_MODE")
    _add_proofreading_options(batch)
    _add_extraction_options(batch)
    batch.set_defaults(handler=_batch_proofread)

    smoke = commands.add_parser("smoke", help="run parameterized smoke conversions and reports")
    smoke_commands = smoke.add_subparsers(dest="smoke_command", required=True)
    assets = smoke_commands.add_parser("assets", help="list discovered PDF and EPUB assets")
    assets.add_argument("--assets-root", type=Path, default=Path("tests/assets"))
    assets.set_defaults(handler=_list_assets)

    run = smoke_commands.add_parser("run", help="run one matrix route from command-line arguments")
    run.add_argument("--asset", required=True, help="path relative to --assets-root")
    run.add_argument(
        "--route",
        choices=(
            "package", "package-markdown", "package-epub", "markdown", "epub",
            "pdf-patch", "epub-check", "epub-translate",
        ),
        required=True,
    )
    run.add_argument("--assets-root", type=Path, default=Path("tests/assets"))
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT / "smoke")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--ocr-mode", choices=_ocr_modes())
    _add_smoke_options(run)
    run.set_defaults(handler=_run_smoke)

    matrix = smoke_commands.add_parser("matrix", help="run a JSON matrix config")
    matrix.add_argument("--config", type=Path, required=True)
    matrix.add_argument("--assets-root", type=Path, default=Path("tests/assets"))
    matrix.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT / "smoke")
    matrix.add_argument("--dry-run", action="store_true")
    matrix.set_defaults(handler=_run_matrix)
    return parser


def _add_pdf_source(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path)
    _add_work_dir(parser, "isolated run directory")
    parser.add_argument("--ocr-mode", choices=_ocr_modes(), help="overrides PDF_CRAFT_OCR_MODE")


def _add_work_dir(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument("--work-dir", type=Path, help=f"{help_text}; defaults under {DEFAULT_OUTPUT_ROOT}/manual")


def _add_extraction_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pages", help="comma-separated 1-based PDF page indexes")
    parser.add_argument("--ocr-size", choices=("tiny", "small", "base", "large", "gundam"))
    parser.set_defaults(default_ocr_size="gundam")
    parser.add_argument("--dpi", type=int)
    parser.add_argument("--max-page-image-file-size", type=int)
    parser.add_argument("--max-ocr-tokens", type=int)
    parser.add_argument("--max-ocr-output-tokens", type=int)
    parser.add_argument("--cover", action="store_true")
    parser.add_argument("--footnotes", action="store_true")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--toc-assumed", action="store_true")
    parser.add_argument("--toc-llm", metavar="PROFILE", help="optional LLM profile for TOC hierarchy analysis")


def _add_translation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--submit", choices=("replace", "append-block"), default="replace")
    parser.add_argument("--prompt")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-group-tokens", type=int, default=2600)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--translation-llm", default="translation", metavar="PROFILE")
    parser.add_argument("--fill-llm", default="fill", metavar="PROFILE")


def _add_proofreading_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--language", default="Bangla (Bengali)")
    parser.add_argument(
        "--prompt", help="optional collection-specific spelling or style rules"
    )
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-group-tokens", type=int, default=1800)
    parser.add_argument("--llm", default="proofread", metavar="PROFILE")
    parser.add_argument(
        "--fill-llm", metavar="PROFILE",
        help="optional separate XML reconstruction model; defaults to --llm",
    )


def _add_smoke_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pages", help="comma-separated 1-based PDF page indexes")
    parser.add_argument("--ocr-size", choices=("tiny", "small", "base", "large", "gundam"))
    parser.set_defaults(default_ocr_size="tiny")
    parser.add_argument("--dpi", type=int)
    parser.add_argument("--max-page-image-file-size", type=int)
    parser.add_argument("--max-ocr-tokens", type=int)
    parser.add_argument("--max-ocr-output-tokens", type=int)
    parser.add_argument("--cover", action="store_true")
    parser.add_argument("--footnotes", action="store_true")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--toc-assumed", action="store_true")
    parser.add_argument("--marker", help="deterministic package-transform marker for Markdown or EPUB routes")
    parser.add_argument("--submit", choices=("replace", "append-block"), default="replace")
    parser.add_argument("--patch-prefix", help="deterministic prefix used by the PDF patch smoke route")
    parser.add_argument("--target-language", default="zh")
    parser.add_argument("--prompt")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-group-tokens", type=int, default=2600)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--translation-llm-profile", metavar="PROFILE")
    parser.add_argument("--fill-llm-profile", metavar="PROFILE")


def _extract_pdf(args: argparse.Namespace) -> None:
    work_dir = _work_dir(args.source, args.work_dir, "extract")
    result = _extract(args, work_dir / "book.pcex")
    print(f"Extraction: {result.path}")
    _print_metering(result.metering)


def _convert_pdf(args: argparse.Namespace) -> None:
    work_dir = _work_dir(args.source, args.work_dir, "convert")
    result = _extract(args, work_dir / "book.pcex")
    output = args.output or work_dir / ("book.md" if args.format == "markdown" else "book.epub")
    output.parent.mkdir(parents=True, exist_ok=True)
    _render(result.craft, result.extraction, args.format, output)
    print(f"Extraction: {result.path}")
    print(f"Output: {output}")
    _print_metering(result.metering)


def _translate_pdf(args: argparse.Namespace) -> None:
    if args.format == "pdf" and args.submit != "replace":
        raise SystemExit("PDF output supports only --submit replace")
    work_dir = _work_dir(args.source, args.work_dir, "translate")
    result = _extract(args, work_dir / "book.pcex")
    result.craft.release_pdf_resources()
    _release_cuda_cache()
    transformer = _xml_transformer(args, work_dir)
    if args.format == "pdf":
        output = args.output or work_dir / f"{args.source.stem}-{args.target_language}.pdf"
        output.parent.mkdir(parents=True, exist_ok=True)
        result.craft.translate_pdf(args.source, result.extraction, output, transformer)
    else:
        mode = SubmitKind[args.submit.replace("-", "_").upper()]
        translated = result.craft.translate_extraction(
            result.extraction, work_dir / "translated.pcex", transformer, submit=mode,
        )
        output = args.output or work_dir / ("book.md" if args.format == "markdown" else "book.epub")
        output.parent.mkdir(parents=True, exist_ok=True)
        _render(result.craft, translated, args.format, output)
    print(f"Extraction: {result.path}")
    print(f"Output: {output}")
    _print_metering(result.metering)


def _proofread_pdf(args: argparse.Namespace) -> None:
    work_dir = _work_dir(args.source, args.work_dir, "proofread")
    result = _extract(args, work_dir / "book.pcex")
    result.craft.release_pdf_resources()
    _release_cuda_cache()
    proofread = result.craft.translate_extraction(
        result.extraction,
        work_dir / "proofread.pcex",
        _proofreading_transformer(args, work_dir),
    )
    output = args.output or work_dir / (
        "book.md" if args.format == "markdown" else "book.epub"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _render(result.craft, proofread, args.format, output)
    print(f"Extraction: {result.path}")
    print(f"Proofread extraction: {work_dir / 'proofread.pcex'}")
    print(f"Output: {output}")
    _print_metering(result.metering)


def _translate_package(args: argparse.Namespace) -> None:
    load_project_env(_project_root())
    work_dir = _work_dir(args.package, args.work_dir, "package-translate")
    extraction = PDFCraftExtraction.open(args.package)
    output_package = args.output_package or work_dir / "translated.pcex"
    transformer = _xml_transformer(args, work_dir)
    mode = SubmitKind[args.submit.replace("-", "_").upper()]
    PDFCraft().translate_extraction(
        extraction, output_package, transformer, submit=mode,
    )
    print(f"Extraction: {output_package}")


def _proofread_package(args: argparse.Namespace) -> None:
    load_project_env(_project_root())
    work_dir = _work_dir(args.package, args.work_dir, "package-proofread")
    extraction = PDFCraftExtraction.open(args.package)
    output_package = args.output_package or work_dir / "proofread.pcex"
    proofread = PDFCraft().translate_extraction(
        extraction, output_package, _proofreading_transformer(args, work_dir)
    )
    output = args.output or work_dir / (
        "book.md" if args.format == "markdown" else "book.epub"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _render(PDFCraft(), proofread, args.format, output)
    print(f"Proofread extraction: {output_package}")
    print(f"Output: {output}")


def _patch_package_pdf(args: argparse.Namespace) -> None:
    work_dir = _work_dir(args.source, args.work_dir, "package-patch")
    extraction = PDFCraftExtraction.open(args.package)
    output = args.output or work_dir / f"{args.source.stem}-patched.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    PDFCraft().patch_pdf_with_extraction(args.source, extraction, output)
    print(f"Output: {output}")


def _render_package(args: argparse.Namespace) -> None:
    work_dir = _work_dir(args.package, args.work_dir, "render")
    extraction = PDFCraftExtraction.open(args.package)
    output = args.output or work_dir / ("book.md" if args.format == "markdown" else "book.epub")
    output.parent.mkdir(parents=True, exist_ok=True)
    _render(PDFCraft(), extraction, args.format, output)
    print(f"Output: {output}")


def _translate_epub(args: argparse.Namespace) -> None:
    load_project_env(_project_root())
    work_dir = _work_dir(args.source, args.work_dir, "translate")
    output = args.output or work_dir / "book.epub"
    if output.exists():
        raise SystemExit(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    translation_llm = create_llm_from_env(args.translation_llm,
        cache_path=work_dir / "translation-cache", log_dir_path=work_dir / "translation-logs")
    fill_llm = translation_llm if args.fill_llm == args.translation_llm else create_llm_from_env(args.fill_llm,
        cache_path=work_dir / "fill-cache", log_dir_path=work_dir / "fill-logs")
    PDFCraft().translate_epub(
        args.source, output, target_language=args.target_language,
        submit=SubmitKind[args.submit.replace("-", "_").upper()],
        user_prompt=args.prompt, max_retries=args.max_retries,
        max_group_tokens=args.max_group_tokens, concurrency=args.concurrency,
        translation_llm=translation_llm, fill_llm=fill_llm,
    )
    print(f"Output: {output}")


def _batch_proofread(args: argparse.Namespace) -> int:
    if not args.source.is_dir():
        raise SystemExit(f"Batch source is not a directory: {args.source}")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be a positive integer")

    sources = sorted(
        path for path in args.source.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if args.limit is not None:
        sources = sources[:args.limit]
    if not sources:
        raise SystemExit(f"No PDF files found under: {args.source}")

    if args.dry_run:
        print(json.dumps({
            "status": "planned",
            "book_count": len(sources),
            "books": [str(path.relative_to(args.source)) for path in sources],
        }, ensure_ascii=False, indent=2))
        return 0

    load_project_env(_project_root())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "batch-report.json"
    report: dict[str, Any] = {
        "schema": 1,
        "source": str(args.source.resolve()),
        "output": str(args.output_dir.resolve()),
        "stage": args.stage,
        "book_count": len(sources),
        "books": [{"source": str(path.relative_to(args.source))} for path in sources],
    }
    entries = cast(list[dict[str, Any]], report["books"])
    stopped = False

    if args.stage in {"all", "extract"}:
        ocr_mode = cast(OCRMode | None, args.ocr_mode) or ocr_mode_from_env()
        ocr_size = _resolve_ocr_size(args.ocr_size, ocr_mode, args.default_ocr_size)
        _validate_ocr_size(ocr_mode, ocr_size)
        ocr_craft = PDFCraft(pdf=PDFOptions(ocr=create_ocr_config_from_env(ocr_mode)))
        for index, (source, entry) in enumerate(zip(sources, entries), 1):
            relative = source.relative_to(args.source)
            print(f"OCR [{index}/{len(sources)}] {relative}")
            try:
                extraction_path = _extract_batch_book(
                    args, source, relative, ocr_craft, ocr_mode, ocr_size
                )
                entry["extraction"] = str(extraction_path)
                entry["extraction_status"] = "completed"
            except Exception as error:  # isolate failures across a large collection
                _record_batch_failure(entry, "extraction", error)
                if args.fail_fast:
                    stopped = True
            _update_batch_report(report_path, report)
            if stopped:
                break
        del ocr_craft
        _release_cuda_cache()

    if args.stage in {"all", "proofread"} and not stopped:
        for index, (source, entry) in enumerate(zip(sources, entries), 1):
            relative = source.relative_to(args.source)
            if entry.get("error_phase") == "extraction":
                continue
            print(f"LLM [{index}/{len(sources)}] {relative}")
            try:
                result = _proofread_batch_book(args, relative)
                proofreading_status = result.pop("status")
                entry.update(result)
                entry["proofreading_status"] = proofreading_status
            except Exception as error:  # isolate failures across a large collection
                _record_batch_failure(entry, "proofreading", error)
                if args.fail_fast:
                    stopped = True
            _update_batch_report(report_path, report)
            if stopped:
                break

    failed = sum("error" in entry for entry in entries)
    for entry in entries:
        if "error" in entry:
            entry["status"] = "failed"
        elif args.stage == "extract" and entry.get("extraction_status") == "completed":
            entry["status"] = "completed"
        elif entry.get("proofreading_status") in {"completed", "skipped"}:
            entry["status"] = entry["proofreading_status"]
        else:
            entry["status"] = "not-run"
    report["failed"] = failed
    report["status"] = "failed" if failed or stopped else "completed"
    _write_batch_report(report_path, report)
    print(f"Batch report: {report_path}")
    return 1 if failed or stopped else 0


def _extract_batch_book(
    args: argparse.Namespace,
    source: Path,
    relative: Path,
    craft: PDFCraft,
    ocr_mode: OCRMode,
    ocr_size: str,
) -> Path:
    work_dir = args.output_dir / ".work" / relative.with_suffix("")
    extraction_path = work_dir / "book.pcex"
    if extraction_path.exists():
        PDFCraftExtraction.open(extraction_path).validate()
        print(f"RESUME extraction: {extraction_path}")
        return extraction_path
    work_dir.mkdir(parents=True, exist_ok=True)
    book_args = argparse.Namespace(**vars(args))
    book_args.source = source
    _extract_with_craft(book_args, extraction_path, craft, ocr_mode, ocr_size)
    return extraction_path


def _proofread_batch_book(
    args: argparse.Namespace, relative: Path
) -> dict[str, Any]:
    formats = ("markdown", "epub") if args.format == "both" else (args.format,)
    output_parent = args.output_dir / relative.parent
    outputs = {
        format_name: output_parent / (
            f"{relative.stem}.md" if format_name == "markdown" else f"{relative.stem}.epub"
        )
        for format_name in formats
    }
    if all(path.exists() for path in outputs.values()):
        print("SKIP: all requested outputs already exist")
        return {
            "source": str(relative),
            "status": "skipped",
            "outputs": {name: str(path) for name, path in outputs.items()},
        }

    work_dir = args.output_dir / ".work" / relative.with_suffix("")
    extraction_path = work_dir / "book.pcex"
    if not extraction_path.exists():
        raise FileNotFoundError(
            f"missing {extraction_path}; run batch with --stage extract first"
        )
    extraction = PDFCraftExtraction.open(extraction_path).validate()

    proofread_path = work_dir / "proofread.pcex"
    if proofread_path.exists():
        proofread = PDFCraftExtraction.open(proofread_path).validate()
        print(f"RESUME proofreading: {proofread_path}")
    else:
        proofread = PDFCraft().translate_extraction(
            extraction,
            proofread_path,
            _proofreading_transformer(args, work_dir),
        )

    for format_name, output in outputs.items():
        if output.exists():
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        _render(PDFCraft(), proofread, format_name, output)
        print(f"Output: {output}")
    return {
        "source": str(relative),
        "status": "completed",
        "extraction": str(extraction_path),
        "proofread_extraction": str(proofread_path),
        "outputs": {name: str(path) for name, path in outputs.items()},
    }


def _record_batch_failure(
    entry: dict[str, Any], phase: str, error: Exception
) -> None:
    entry["error_phase"] = phase
    entry["error"] = f"{type(error).__name__}: {error}"
    print(f"FAILED: {entry['error']}")


def _update_batch_report(path: Path, report: dict[str, Any]) -> None:
    entries = cast(list[dict[str, Any]], report["books"])
    report["completed_operations"] = sum(
        key in entry
        for entry in entries
        for key in ("extraction_status", "proofreading_status", "error")
    )
    report["failed"] = sum("error" in entry for entry in entries)
    _write_batch_report(path, report)


def _release_cuda_cache() -> None:
    """Release the in-process OCR model before Ollama takes over the GPU."""
    gc.collect()
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _write_batch_report(path: Path, report: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _list_assets(args: argparse.Namespace) -> None:
    print(json.dumps([
        asset.__dict__ | {"path": str(asset.path)} for asset in discover_assets(args.assets_root)
    ], ensure_ascii=False, indent=2))


def _run_smoke(args: argparse.Namespace) -> int:
    translation: dict[str, Any] = {}
    if args.marker:
        translation["package_marker"] = args.marker
        translation["package_submit"] = args.submit.replace("-", "_").upper()
    if args.patch_prefix:
        translation["patch_prefix"] = args.patch_prefix
    is_pdf_route = args.route in {
        "package", "package-markdown", "package-epub", "markdown", "epub", "pdf-patch",
    }
    if (is_pdf_route or args.route == "epub-translate") and not args.dry_run:
        load_project_env(_project_root())
    ocr_mode = cast(OCRMode | None, args.ocr_mode)
    if is_pdf_route:
        ocr_mode = ocr_mode or ocr_mode_from_env()
    ocr_size = _resolve_ocr_size(args.ocr_size, ocr_mode, args.default_ocr_size)
    _validate_ocr_size(cast(OCRMode | None, ocr_mode), ocr_size)
    if args.route == "epub-translate" or args.translation_llm_profile or args.fill_llm_profile:
        translation_profile = args.translation_llm_profile or "translation"
        fill_profile = args.fill_llm_profile or translation_profile
        translation.update({
            "translation_llm_profile": translation_profile,
            "fill_llm_profile": fill_profile,
            "target_language": args.target_language,
            "user_prompt": args.prompt,
            "max_retries": args.max_retries,
            "max_group_tokens": args.max_group_tokens,
            "concurrency": args.concurrency,
            "submit": args.submit.replace("-", "_").upper(),
        })
        if not args.dry_run:
            translation = _resolve_translation_profiles(translation, args.output_root) or {}
    run = SmokeRun(
        asset=args.asset, route=args.route, backend=ocr_mode,
        page_indexes=_page_indexes(args.pages), ocr_size=ocr_size, dpi=args.dpi,
        max_page_image_file_size=args.max_page_image_file_size,
        max_ocr_tokens=args.max_ocr_tokens, max_ocr_output_tokens=args.max_ocr_output_tokens,
        includes_cover=args.cover, includes_footnotes=args.footnotes,
        generate_plot=args.plot, toc_assumed=args.toc_assumed,
        ocr=ocr_values_from_env(ocr_mode) if ocr_mode and not args.dry_run else None,
        translation=translation or None,
    )
    run_path = run_smoke(run, assets_root=args.assets_root, output_root=args.output_root, dry_run=args.dry_run)
    print(run_path)
    return _smoke_exit_code(run_path)


def _run_matrix(args: argparse.Namespace) -> int:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    runs = expand_matrix(config, args.assets_root)
    env_error: str | None = None
    if any(_matrix_run_needs_env(run) for run in runs):
        try:
            load_project_env(_project_root())
        except SystemExit as error:
            env_error = str(error)
    exit_code = 0
    for run in runs:
        if env_error and _matrix_run_needs_env(run):
            run = replace(run, configuration_error=env_error)
        else:
            try:
                run = _resolve_matrix_runtime(run, args.output_root)
            except SystemExit as error:
                run = replace(run, configuration_error=str(error))
        run_path = run_smoke(run, assets_root=args.assets_root, output_root=args.output_root, dry_run=args.dry_run)
        print(run_path)
        exit_code = max(exit_code, _smoke_exit_code(run_path))
    return exit_code


def _smoke_exit_code(run_path: Path) -> int:
    """Return a non-zero code for failed or skipped required smoke runs."""
    try:
        status = json.loads((run_path / "checks.json").read_text(encoding="utf-8"))["status"]
    except (OSError, KeyError, json.JSONDecodeError):
        return 1
    return 0 if status in {"passed", "planned"} else 1


def _matrix_run_needs_env(run: SmokeRun) -> bool:
    if run.backend and run.ocr is None:
        return True
    translation = run.translation or {}
    return any(
        key in translation
        for key in ("llm_profile", "translation_llm_profile", "fill_llm_profile")
    )


def _resolve_matrix_runtime(run: SmokeRun, output_root: Path) -> SmokeRun:
    _validate_ocr_size(run.backend, run.ocr_size)
    ocr = run.ocr
    if run.backend and ocr is None:
        ocr = ocr_values_from_env(run.backend)
    translation = _resolve_translation_profiles(run.translation, output_root)
    return replace(run, ocr=ocr, translation=translation)


def _resolve_translation_profiles(translation: dict[str, Any] | None, output_root: Path) -> dict[str, Any] | None:
    if not translation:
        return translation
    resolved = dict(translation)
    profile = resolved.pop("llm_profile", None)
    translation_profile = resolved.pop("translation_llm_profile", profile)
    fill_profile = resolved.pop("fill_llm_profile", profile)
    if translation_profile and "llm" not in resolved:
        resolved["llm"] = llm_values_from_env(
            str(translation_profile),
            cache_path=output_root / "_c" / "t",
            log_dir_path=output_root / "_l" / "t",
        )
    if fill_profile and fill_profile != translation_profile and "fill_llm" not in resolved:
        resolved["fill_llm"] = llm_values_from_env(
            str(fill_profile),
            cache_path=output_root / "_c" / "f",
            log_dir_path=output_root / "_l" / "f",
        )
    return resolved


def _extract(args: argparse.Namespace, extraction_path: Path) -> _ExtractionResult:
    load_project_env(_project_root())
    ocr_mode = cast(OCRMode | None, args.ocr_mode) or ocr_mode_from_env()
    ocr_size = _resolve_ocr_size(args.ocr_size, ocr_mode, args.default_ocr_size)
    _validate_ocr_size(ocr_mode, ocr_size)
    craft = PDFCraft(pdf=PDFOptions(ocr=create_ocr_config_from_env(ocr_mode)))
    return _extract_with_craft(
        args, extraction_path, craft, ocr_mode, ocr_size
    )


def _extract_with_craft(
    args: argparse.Namespace,
    extraction_path: Path,
    craft: PDFCraft,
    ocr_mode: OCRMode,
    ocr_size: str,
) -> _ExtractionResult:
    _record_pdf_cache_owner(extraction_path.parent, args, ocr_mode, ocr_size)
    extraction, metering = craft.extract_pdf_with_metering(
        args.source, extraction_path, ExtractionOptions(
            page_indexes=_page_indexes(args.pages), ocr_size=cast(Any, ocr_size), dpi=args.dpi,
            max_page_image_file_size=args.max_page_image_file_size,
            max_ocr_tokens=args.max_ocr_tokens, max_ocr_output_tokens=args.max_ocr_output_tokens,
            includes_cover=args.cover, includes_footnotes=args.footnotes,
            generate_plot=args.plot, toc_assumed=args.toc_assumed,
            toc_llm=(create_llm_from_env(args.toc_llm, cache_path=extraction_path.parent / "toc-cache",
                log_dir_path=extraction_path.parent / "toc-logs") if args.toc_llm else None),
            on_ocr_event=_print_ocr_event,
        ),
        analysing_path=extraction_path.parent / "analysis",
    )
    return _ExtractionResult(craft, extraction, extraction_path, metering)


def _xml_transformer(args: argparse.Namespace, work_dir: Path) -> ChapterXMLTransformer:
    translation_llm = create_llm_from_env(args.translation_llm,
        cache_path=work_dir / "translation-cache", log_dir_path=work_dir / "translation-logs")
    fill_llm = translation_llm if args.fill_llm == args.translation_llm else create_llm_from_env(args.fill_llm,
        cache_path=work_dir / "fill-cache", log_dir_path=work_dir / "fill-logs")
    translator = XMLTranslator(
        translation_llm=translation_llm, fill_llm=fill_llm, target_language=args.target_language,
        user_prompt=args.prompt, ignore_translated_error=False, max_retries=args.max_retries,
        max_fill_displaying_errors=3, max_group_score=args.max_group_tokens,
        cache_seed_content=f"pdf-craft-tool:{args.target_language}",
    )
    return ChapterXMLTransformer(cast(Any, translator))


def _proofreading_transformer(
    args: argparse.Namespace, work_dir: Path
) -> ChapterXMLTransformer:
    proofreading_llm = create_llm_from_env(
        args.llm,
        cache_path=work_dir / "proofreading-cache",
        log_dir_path=work_dir / "proofreading-logs",
    )
    fill_profile = args.fill_llm or args.llm
    fill_llm = proofreading_llm if fill_profile == args.llm else create_llm_from_env(
        fill_profile,
        cache_path=work_dir / "fill-cache",
        log_dir_path=work_dir / "fill-logs",
    )
    proofreader = XMLTranslator(
        translation_llm=proofreading_llm,
        fill_llm=fill_llm,
        target_language=args.language,
        user_prompt=args.prompt,
        ignore_translated_error=False,
        max_retries=args.max_retries,
        max_fill_displaying_errors=3,
        max_group_score=args.max_group_tokens,
        cache_seed_content=f"pdf-craft-tool:proofread:{args.language}",
        prompt_template="proofread",
    )
    return ChapterXMLTransformer(cast(Any, proofreader))


def _render(craft: PDFCraft, extraction: PDFCraftExtraction,
            format_name: str, output: Path) -> None:
    if format_name == "markdown":
        craft.render_markdown(extraction, output, Path("assets"))
    else:
        craft.render_epub(extraction, output)


def _work_dir(source: Path, requested: Path | None, operation: str) -> Path:
    if requested is not None:
        path = requested
        if path.exists() and not path.is_dir():
            raise SystemExit(f"Work directory is not a directory: {path}")
        path.mkdir(parents=True, exist_ok=True)
        return path
    return create_run_directory(DEFAULT_OUTPUT_ROOT / "manual", f"{source.stem}-{operation}")


def _record_pdf_cache_owner(
    work_dir: Path,
    args: argparse.Namespace,
    ocr_mode: OCRMode,
    ocr_size: str,
) -> None:
    """Guard manual PDF work-dir reuse so OCR caches stay tied to one source/backend."""
    path = work_dir / ".pdf-craft-tool-run.json"
    source = args.source.resolve()
    stat = source.stat()
    current = {
        "schema": 1,
        "source": str(source),
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "ocr_mode": ocr_mode,
        "ocr_size": ocr_size,
        "dpi": args.dpi,
        "max_page_image_file_size": args.max_page_image_file_size,
        "includes_footnotes": args.footnotes,
        "max_ocr_tokens": args.max_ocr_tokens,
        "max_ocr_output_tokens": args.max_ocr_output_tokens,
    }
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        mismatched = [
            key
            for key, value in current.items()
            if key != "schema" and previous.get(key) != value
        ]
        if mismatched:
            raise SystemExit(
                "Work directory already contains OCR cache for different PDF/OCR "
                f"settings ({', '.join(mismatched)}): {work_dir}"
            )
        return
    if (work_dir / "analysis" / "ocr").exists():
        raise SystemExit(
            "Work directory contains legacy OCR cache without ownership metadata; "
            f"use a fresh directory or remove the stale cache: {work_dir}"
        )
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_ocr_size(value: str | None, ocr_mode: OCRMode | None, default: str) -> str:
    if value:
        return value
    if ocr_mode == "deepseek-ocr2-local":
        return "base"
    return default


def _validate_ocr_size(ocr_mode: OCRMode | None, ocr_size: str) -> None:
    if ocr_mode == "deepseek-ocr2-local" and ocr_size == "tiny":
        raise SystemExit(
            "deepseek-ocr2-local is not reliable with --ocr-size tiny; "
            "use --ocr-size base for the validated local OCR2 path."
        )


def _page_indexes(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    try:
        pages = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise SystemExit("--pages must be comma-separated positive integers") from error
    if not pages or any(page < 1 for page in pages):
        raise SystemExit("--pages uses 1-based positive page indexes")
    return pages


def _ocr_modes() -> tuple[str, ...]:
    return (
        "tesseract-ocr-local",
        "deepseek-ocr-local", "deepseek-ocr2-local", "unlimited-ocr-local",
        "deepseek-ocr-vendor", "deepseek-ocr2-vendor", "unlimited-ocr-vendor",
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _print_ocr_event(event) -> None:
    print(f"OCR {event.kind.name.lower()}: page {event.page_index}/{event.total_pages}")


def _print_metering(metering) -> None:
    print(f"OCR tokens: input={metering.input_tokens}, output={metering.output_tokens}")
