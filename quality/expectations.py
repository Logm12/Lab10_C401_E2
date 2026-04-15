"""
Simple expectation suite for the ETL pipeline.

Sprint 2 adds row-level validation quarantine so invalid cleaned rows can be
stored separately while the pipeline still exits successfully in the normal flow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def _norm_text(value: str) -> str:
    return " ".join((value or "").strip().split()).lower()


def _is_iso_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", (value or "").strip()))


def _is_iso_datetime_utc(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", (value or "").strip()))


def quarantine_invalid_rows(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []
    metrics: Dict[str, int] = {}
    seen_pairs: set[Tuple[str, str]] = set()

    for row in cleaned_rows:
        reason = ""
        pair = ((row.get("doc_id") or "").strip(), _norm_text(row.get("chunk_text") or ""))

        if len((row.get("chunk_text") or "").strip()) < 8:
            reason = "validation_chunk_too_short"
        elif not _is_iso_date(row.get("effective_date") or ""):
            reason = "validation_invalid_effective_date"
        elif not _is_iso_datetime_utc(row.get("exported_at") or ""):
            reason = "validation_invalid_exported_at"
        elif row.get("doc_id") == "policy_refund_v4" and "14 ngày làm việc" in (row.get("chunk_text") or ""):
            reason = "validation_stale_refund_window"
        elif row.get("doc_id") == "hr_leave_policy" and "10 ngày phép năm" in (row.get("chunk_text") or ""):
            reason = "validation_stale_hr_leave_version"
        elif pair in seen_pairs:
            reason = "validation_duplicate_doc_chunk"

        if reason:
            metrics[reason] = metrics.get(reason, 0) + 1
            invalid_rows.append({**row, "reason": reason, "source_stage": "validate"})
            continue

        seen_pairs.add(pair)
        valid_rows.append(row)

    return valid_rows, invalid_rows, metrics


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    results: List[ExpectationResult] = []

    ok = len(cleaned_rows) >= 1
    results.append(ExpectationResult("min_one_row", ok, "halt", f"cleaned_rows={len(cleaned_rows)}"))

    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            len(bad_doc) == 0,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4" and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            len(bad_refund) == 0,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "").strip()) < 8]
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            len(short) == 0,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    iso_bad = [r for r in cleaned_rows if not _is_iso_date(r.get("effective_date") or "")]
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            len(iso_bad) == 0,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    bad_hr = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy" and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            len(bad_hr) == 0,
            "halt",
            f"violations={len(bad_hr)}",
        )
    )

    bad_exported = [r for r in cleaned_rows if not _is_iso_datetime_utc(r.get("exported_at") or "")]
    results.append(
        ExpectationResult(
            "exported_at_iso_utc",
            len(bad_exported) == 0,
            "halt",
            f"invalid_exported_at={len(bad_exported)}",
        )
    )

    seen_pairs: set[Tuple[str, str]] = set()
    dup_pairs = 0
    for row in cleaned_rows:
        pair = ((row.get("doc_id") or "").strip(), _norm_text(row.get("chunk_text") or ""))
        if pair in seen_pairs:
            dup_pairs += 1
        else:
            seen_pairs.add(pair)
    results.append(
        ExpectationResult(
            "unique_doc_id_chunk_text",
            dup_pairs == 0,
            "halt",
            f"duplicate_pairs={dup_pairs}",
        )
    )

    halt = any(not result.passed and result.severity == "halt" for result in results)
    return results, halt
