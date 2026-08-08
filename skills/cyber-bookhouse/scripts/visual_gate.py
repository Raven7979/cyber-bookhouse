#!/usr/bin/env python3
"""Detect structural content and enforce a rendered, visually reviewed diagram."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


DIAGRAM_TYPES = {"architecture", "flow", "decision", "relationship", "causal", "timeline"}
RULES = (
    (
        "architecture",
        "architecture",
        re.compile(r"系统架构|技术架构|组织架构|数据流|调用关系|客户端.{0,12}服务端|模块.{0,12}组件|\b(?:system|technical|organizational)\s+architecture\b|\bdata\s+flow\b|\bclient.{0,12}server\b|\bcomponents?.{0,20}modules?\b", re.I),
    ),
    (
        "decision",
        "decision",
        re.compile(r"决策树|判断条件|适用.{0,10}不适用|如果.{0,24}(?:否则|那么)|分支路径|\bdecision\s+tree\b|\bif\b.{0,30}\b(?:then|else)\b|\bbranching\s+paths?\b", re.I),
    ),
    (
        "process",
        "flow",
        re.compile(r"(?:SOP|工作流|业务流程|操作流程|处理流程|闭环流程|至少三步|第一步.{0,80}第二步|\bworkflow\b|\bprocess\s+flow\b|\bstep\s+one\b.{0,80}\bstep\s+two\b)", re.I | re.S),
    ),
    (
        "layers",
        "relationship",
        re.compile(r"(?:[一二三四五六七八九十两0-9]+层(?:架构|结构|模型|进化|体系)?|分层模型|层级关系|核心观点.{0,20}影响.{0,20}(?:三个|3个|多项)|\b(?:two|three|four|five|\d+)[ -]layer(?:ed)?\b|\blayered\s+model\b)", re.I),
    ),
    (
        "causal",
        "causal",
        re.compile(r"因果链|因果关系|根因.{0,30}结果|导致.{0,30}(?:因此|从而)|驱动因素|\bcausal\s+(?:chain|relationship)\b|\broot\s+cause\b.{0,30}\bresult\b|\bdrivers?\b.{0,20}\boutcomes?\b", re.I),
    ),
    (
        "timeline",
        "timeline",
        re.compile(r"时间线|里程碑|演进阶段|发展阶段|开场.{0,80}转折.{0,80}结尾|\btimeline\b|\bmilestones?\b|\bevolution\s+stages?\b", re.I | re.S),
    ),
)


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(_strings(item))
        return output
    if isinstance(value, dict):
        output = []
        for item in value.values():
            output.extend(_strings(item))
        return output
    return []


def _read_source(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        return "\n".join(_strings(json.loads(raw)))
    except json.JSONDecodeError:
        return raw


def detect(paths: list[Path], force_type: str = "") -> dict[str, object]:
    text = "\n".join(_read_source(path) for path in paths)[:500_000]
    matches: list[dict[str, str]] = []
    categories: list[str] = []
    recommended = ""
    for category, diagram_type, pattern in RULES:
        for match in list(pattern.finditer(text))[:3]:
            if category not in categories:
                categories.append(category)
            if not recommended:
                recommended = diagram_type
            start = max(0, match.start() - 45)
            end = min(len(text), match.end() + 70)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            matches.append({"category": category, "term": match.group(0), "evidence": snippet})
    required = bool(force_type or matches)
    diagram_type = force_type or recommended or "none"
    return {
        "schema_version": 1,
        "required": required,
        "diagram_type": diagram_type,
        "trigger_categories": categories or (["user_requested"] if force_type else []),
        "matches": matches[:8],
        "source_files": [str(path) for path in paths],
        "status": "pending" if required else "not_required",
        "reason": "structural_trigger_detected" if required else "no_structural_trigger",
        "artifacts": {},
        "ready": not required,
    }


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _artifact_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    path = root / value
    return path if _inside(root, path) else None


def verify(report: object, artifact_root: Path | None = None) -> list[str]:
    if not isinstance(report, dict):
        return ["visual_report_not_object"]
    required = report.get("required") is True
    if not required:
        errors = []
        if report.get("status") != "not_required":
            errors.append("visual_status_not_required_invalid")
        if report.get("ready") is not True:
            errors.append("visual_not_required_not_ready")
        return errors
    errors: list[str] = []
    if report.get("diagram_type") not in DIAGRAM_TYPES:
        errors.append("visual_diagram_type_invalid")
    if report.get("status") != "complete" or report.get("ready") is not True:
        errors.append("visual_required_not_complete")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict):
        return [*errors, "visual_artifacts_missing"]
    for key in ("source", "preview", "check", "review"):
        if not artifacts.get(key):
            errors.append(f"visual_{key}_missing")
    if artifact_root is None:
        return errors
    root = artifact_root.resolve()
    resolved: dict[str, Path] = {}
    for key in ("source", "preview", "check", "review"):
        path = _artifact_path(root, artifacts.get(key))
        if path is None or not path.is_file() or path.stat().st_size == 0:
            errors.append(f"visual_{key}_invalid")
        else:
            resolved[key] = path
    source = resolved.get("source")
    if source is not None:
        content = source.read_text(encoding="utf-8", errors="replace")
        if source.suffix.lower() in {".mmd", ".md"} and not (
            re.search(r"(?m)^\s*(?:flowchart|graph)\s+(?:LR|RL|TB|TD|BT)\b", content)
            and re.search(r"-->|---|==>", content)
        ):
            errors.append("visual_mermaid_structure_invalid")
    preview = resolved.get("preview")
    if preview is not None:
        header = preview.read_bytes()[:16]
        if not (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")):
            errors.append("visual_preview_not_raster_image")
    check = resolved.get("check")
    if check is not None:
        try:
            payload = json.loads(check.read_text(encoding="utf-8"))
            summary = payload.get("data", {}).get("check", {}).get("summary", {})
            if payload.get("code") != 0 or any(
                int(summary.get(key, 0)) != 0
                for key in ("textOverflow", "nodeOverlap", "textOcclusion")
            ):
                errors.append("visual_geometry_check_failed")
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
            errors.append("visual_check_invalid_json")
    review = resolved.get("review")
    if review is not None:
        try:
            payload = json.loads(review.read_text(encoding="utf-8"))
            if not (
                payload.get("status") == "pass"
                and payload.get("text_readable") is True
                and payload.get("no_overlap") is True
                and payload.get("no_cropping") is True
                and payload.get("evidence_alignment") is True
                and payload.get("relationship_errors") == []
            ):
                errors.append("visual_review_failed")
        except (json.JSONDecodeError, AttributeError):
            errors.append("visual_review_invalid_json")
    return errors


def finalize(
    report_path: Path,
    artifact_root: Path,
    source: Path,
    preview: Path,
    check: Path,
    review: Path,
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("required") is not True:
        raise ValueError("visual report does not require a diagram")
    root = artifact_root.resolve()
    paths = {"source": source, "preview": preview, "check": check, "review": review}
    relative: dict[str, str] = {}
    for key, value in paths.items():
        resolved = value.resolve()
        if not _inside(root, resolved):
            raise ValueError(f"{key} must stay inside artifact root")
        relative[key] = resolved.relative_to(root).as_posix()
    report["artifacts"] = relative
    report["status"] = "complete"
    report["ready"] = True
    errors = verify(report, root)
    if errors:
        raise ValueError(", ".join(errors))
    _atomic_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--source", action="append", required=True, type=Path)
    detect_parser.add_argument("--force-type", choices=sorted(DIAGRAM_TYPES), default="")
    detect_parser.add_argument("--output", required=True, type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--report", required=True, type=Path)
    verify_parser.add_argument("--artifact-root", required=True, type=Path)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--report", required=True, type=Path)
    finalize_parser.add_argument("--artifact-root", required=True, type=Path)
    finalize_parser.add_argument("--source", required=True, type=Path)
    finalize_parser.add_argument("--preview", required=True, type=Path)
    finalize_parser.add_argument("--check", required=True, type=Path)
    finalize_parser.add_argument("--review", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "detect":
            report = detect(args.source, args.force_type)
            _atomic_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.command == "verify":
            report = json.loads(args.report.read_text(encoding="utf-8"))
            errors = verify(report, args.artifact_root)
            print(json.dumps({"ready": not errors, "errors": errors}, ensure_ascii=False, indent=2))
            return 0 if not errors else 2
        report = finalize(
            args.report,
            args.artifact_root,
            args.source,
            args.preview,
            args.check,
            args.review,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
