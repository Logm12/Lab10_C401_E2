"""
Cleaning rules - raw export -> cleaned rows + quarantine.

Sprint 2 adds measurable rules and returns metric impact so the report can
show before/after evidence instead of only describing the logic.
"""

from __future__ import annotations

import csv
import hashlib
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"\b0\d{2}[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CURRENCY_VND = re.compile(r"\b(\d{3,})\s*vnd\b", re.IGNORECASE)

EXPORT_DT_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def _bump(metrics: Dict[str, int], key: str, inc: int = 1) -> None:
    metrics[key] = metrics.get(key, 0) + inc


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    digest = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{digest}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    match = _DMY_SLASH.match(s)
    if match:
        dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ""
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), ""
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ""
    except ValueError:
        pass
    for fmt in EXPORT_DT_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), ""
        except ValueError:
            continue
    return "", "invalid_exported_at"


def _normalize_contact_tokens(text: str) -> Tuple[str, bool]:
    changed = False

    def lower_email(match: re.Match[str]) -> str:
        nonlocal changed
        token = match.group(0)
        lowered = token.lower()
        changed = changed or lowered != token
        return lowered

    def compact_phone(match: re.Match[str]) -> str:
        nonlocal changed
        token = match.group(0)
        compact = re.sub(r"\D", "", token)
        changed = changed or compact != token
        return compact

    updated = _EMAIL.sub(lower_email, text)
    updated = _PHONE.sub(compact_phone, updated)
    return updated, changed


def _normalize_currency_vnd(text: str) -> Tuple[str, bool]:
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        token = match.group(0)
        amount = int(match.group(1))
        normalized = f"{amount:,} VND"
        changed = changed or normalized != token
        return normalized

    updated = _CURRENCY_VND.sub(repl, text)
    return updated, changed


def _normalize_chunk_text(text: str, doc_id: str, metrics: Dict[str, int]) -> str:
    updated = text

    html_unescaped = html.unescape(updated)
    if html_unescaped != updated:
        _bump(metrics, "rule_html_unescape")
        updated = html_unescaped

    compacted = " ".join(updated.split())
    if compacted != updated:
        _bump(metrics, "rule_compact_whitespace")
        updated = compacted

    updated_contacts, contact_changed = _normalize_contact_tokens(updated)
    if contact_changed:
        _bump(metrics, "rule_normalize_contact_tokens")
        updated = updated_contacts

    updated_currency, currency_changed = _normalize_currency_vnd(updated)
    if currency_changed:
        _bump(metrics, "rule_normalize_currency_vnd")
        updated = updated_currency

    if doc_id == "hr_leave_policy" and "10 ngày phép năm" in updated:
        updated = updated.replace("10 ngày phép năm", "12 ngày phép năm")
        updated += " [cleaned: hr_leave_policy_2026]"
        _bump(metrics, "rule_fix_hr_leave_version")

    return updated


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    metrics: Dict[str, int] = {}
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_raw = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            _bump(metrics, "rule_quarantine_unknown_doc_id")
            quarantine.append({**raw, "reason": "unknown_doc_id", "source_stage": "clean"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            _bump(metrics, "rule_quarantine_missing_effective_date")
            quarantine.append({**raw, "reason": "missing_effective_date", "source_stage": "clean"})
            continue
        if eff_err == "invalid_effective_date_format":
            _bump(metrics, "rule_quarantine_invalid_effective_date")
            quarantine.append(
                {
                    **raw,
                    "reason": "invalid_effective_date_format",
                    "effective_date_raw": eff_raw,
                    "source_stage": "clean",
                }
            )
            continue
        if eff_norm != eff_raw:
            _bump(metrics, "rule_normalize_effective_date")

        exported_norm, exported_err = _normalize_exported_at(exported_raw)
        if exported_err:
            _bump(metrics, "rule_quarantine_invalid_exported_at")
            quarantine.append({**raw, "reason": exported_err, "source_stage": "clean"})
            continue
        if exported_norm != exported_raw:
            _bump(metrics, "rule_normalize_exported_at")

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            _bump(metrics, "rule_quarantine_stale_hr_effective_date")
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                    "source_stage": "clean",
                }
            )
            continue

        if not text:
            _bump(metrics, "rule_quarantine_missing_chunk_text")
            quarantine.append({**raw, "reason": "missing_chunk_text", "source_stage": "clean"})
            continue

        fixed_text = _normalize_chunk_text(text, doc_id, metrics)

        key = _norm_text(fixed_text)
        if key in seen_text:
            _bump(metrics, "rule_dedupe_chunk_text")
            quarantine.append({**raw, "reason": "duplicate_chunk_text", "source_stage": "clean"})
            continue
        seen_text.add(key)

        if apply_refund_window_fix and doc_id == "policy_refund_v4" and "14 ngày làm việc" in fixed_text:
            fixed_text = fixed_text.replace("14 ngày làm việc", "7 ngày làm việc")
            fixed_text += " [cleaned: stale_refund_window]"
            _bump(metrics, "rule_fix_refund_window")

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_norm,
            }
        )

    return cleaned, quarantine, metrics


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    if not rows:
        path.write_text(",".join(fieldnames) + "\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason,source_stage\n", encoding="utf-8")
        return

    keys: List[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                keys.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
