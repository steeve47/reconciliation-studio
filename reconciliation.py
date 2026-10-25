"""Deterministic, explainable bank-to-ledger reconciliation rules."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

RULE_VERSION = "1.0.0"
REQUIRED_FIELDS = ("transaction_id", "date", "amount")
RESULT_COLUMNS = [
    "transaction_id",
    "bank_date",
    "bank_amount",
    "ledger_date",
    "ledger_amount",
    "difference",
    "status",
    "reason_code",
    "explanation",
    "human_review_required",
    "batch_id",
    "rule_version",
    "processed_at_utc",
]
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class DataValidationError(ValueError):
    """Raised when uploaded transaction data fails validation."""


def read_csv_bytes(content: bytes, source_name: str) -> pd.DataFrame:
    """Parse a UTF-8 CSV and reject malformed or ambiguous headers."""
    if not content:
        raise DataValidationError(f"{source_name}: the CSV file is empty.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataValidationError(
            f"{source_name}: the CSV must use UTF-8 text encoding."
        ) from exc

    try:
        header = next(csv.reader(io.StringIO(text), strict=True), None)
    except csv.Error as exc:
        raise DataValidationError(
            f"{source_name}: could not read the CSV header: {exc}"
        ) from exc

    if not header or not any(cell.strip() for cell in header):
        raise DataValidationError(f"{source_name}: the CSV has no header row.")

    normalized_header = [cell.strip() for cell in header]
    if any(not column for column in normalized_header):
        raise DataValidationError(
            f"{source_name}: column names must not be blank."
        )
    if len(set(normalized_header)) != len(normalized_header):
        raise DataValidationError(
            f"{source_name}: duplicate column names are not supported."
        )

    try:
        frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise DataValidationError(
            f"{source_name}: could not parse the CSV: {exc}"
        ) from exc

    frame.columns = normalized_header
    if frame.empty:
        raise DataValidationError(f"{source_name}: the CSV contains no transactions.")
    return frame


def _row_numbers(mask: pd.Series) -> str:
    return ", ".join(str(int(index) + 2) for index in mask[mask].index[:10])


def _amount_to_cents(value: Any, source_name: str, row_number: int) -> int:
    if pd.isna(value) or isinstance(value, bool):
        raise DataValidationError(
            f"{source_name}: missing or invalid amount at CSV row {row_number}."
        )

    raw = str(value).strip().replace(",", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise DataValidationError(
            f"{source_name}: invalid amount at CSV row {row_number}: {value!r}."
        ) from exc

    if not amount.is_finite():
        raise DataValidationError(
            f"{source_name}: invalid amount at CSV row {row_number}: {value!r}."
        )
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise DataValidationError(
            f"{source_name}: amount has more than two decimal places "
            f"at CSV row {row_number}: {value!r}."
        )
    return int(cents)


def normalize_transactions(
    frame: pd.DataFrame,
    column_mapping: dict[str, str | None],
    source_name: str,
) -> pd.DataFrame:
    """Map source-specific column names into the validated internal schema."""
    if not isinstance(frame, pd.DataFrame):
        raise DataValidationError(f"{source_name}: input must be a CSV table.")
    if frame.empty:
        raise DataValidationError(f"{source_name}: the CSV contains no transactions.")
    if frame.columns.duplicated().any():
        raise DataValidationError(
            f"{source_name}: duplicate column names are not supported."
        )

    missing_mappings = [
        field
        for field in REQUIRED_FIELDS
        if not column_mapping.get(field)
        or column_mapping[field] not in frame.columns
    ]
    if missing_mappings:
        raise DataValidationError(
            f"{source_name}: map a column for "
            f"{', '.join(missing_mappings)}."
        )

    required_columns = [column_mapping[field] for field in REQUIRED_FIELDS]
    if len(set(required_columns)) != len(required_columns):
        raise DataValidationError(
            f"{source_name}: reference, date and amount must use different columns."
        )

    ids = frame[column_mapping["transaction_id"]]
    missing_ids = ids.isna()
    if missing_ids.any():
        raise DataValidationError(
            f"{source_name}: blank transaction reference at CSV row(s) "
            f"{_row_numbers(missing_ids)}."
        )
    references = ids.astype("string").str.strip()
    blank_ids = references.eq("")
    if blank_ids.any():
        raise DataValidationError(
            f"{source_name}: blank transaction reference at CSV row(s) "
            f"{_row_numbers(blank_ids)}."
        )

    raw_dates = frame[column_mapping["date"]]
    missing_dates = raw_dates.isna() | raw_dates.astype("string").str.strip().eq("")
    if missing_dates.any():
        raise DataValidationError(
            f"{source_name}: missing date at CSV row(s) "
            f"{_row_numbers(missing_dates)}."
        )
    parsed_dates = pd.to_datetime(raw_dates, errors="coerce", format="mixed")
    invalid_dates = parsed_dates.isna()
    if invalid_dates.any():
        raise DataValidationError(
            f"{source_name}: invalid date at CSV row(s) "
            f"{_row_numbers(invalid_dates)}."
        )

    amount_column = column_mapping["amount"]
    cents = [
        _amount_to_cents(value, source_name, index + 2)
        for index, value in enumerate(frame[amount_column].tolist())
    ]
    description_column = column_mapping.get("description")
    if description_column and description_column in frame.columns:
        descriptions = (
            frame[description_column]
            .fillna("")
            .astype("string")
            .str.strip()
            .astype(str)
        )
    else:
        descriptions = pd.Series([""] * len(frame), index=frame.index, dtype="string")

    return pd.DataFrame(
        {
            "transaction_id": references.astype(str).to_numpy(),
            "date": parsed_dates.dt.strftime("%Y-%m-%d").to_numpy(),
            "amount_cents": cents,
            "description": descriptions.to_numpy(),
        }
    )


def _format_amount(cents: int | None) -> str:
    if cents is None:
        return ""
    amount = Decimal(int(cents)) / 100
    return f"{amount:.2f}"


def reconcile(
    bank: pd.DataFrame,
    ledger: pd.DataFrame,
    batch_id: str | None = None,
    processed_at_utc: str | None = None,
) -> pd.DataFrame:
    """Reconcile unique references and route duplicates or exceptions to review."""
    if bank.empty or ledger.empty:
        raise DataValidationError("Both sources must contain transactions.")

    batch_id = batch_id or str(uuid.uuid4())
    processed_at_utc = processed_at_utc or datetime.now(timezone.utc).isoformat()
    bank_counts = Counter(bank["transaction_id"])
    ledger_counts = Counter(ledger["transaction_id"])
    bank_by_id = {key: group for key, group in bank.groupby("transaction_id", sort=False)}
    ledger_by_id = {
        key: group for key, group in ledger.groupby("transaction_id", sort=False)
    }
    records = []

    for transaction_id in sorted(set(bank_counts) | set(ledger_counts)):
        bank_count = bank_counts.get(transaction_id, 0)
        ledger_count = ledger_counts.get(transaction_id, 0)
        bank_rows = bank_by_id.get(transaction_id)
        ledger_rows = ledger_by_id.get(transaction_id)
        bank_row = bank_rows.iloc[0] if bank_count == 1 else None
        ledger_row = ledger_rows.iloc[0] if ledger_count == 1 else None

        if bank_count > 1 or ledger_count > 1:
            status = "Duplicate review"
            reason_code = "DUPLICATE_REFERENCE"
            duplicate_sources = []
            if bank_count > 1:
                duplicate_sources.append("bank statement")
            if ledger_count > 1:
                duplicate_sources.append("ledger")
            explanation = (
                "Duplicate reference found in "
                + " and ".join(duplicate_sources)
                + "; ambiguous records were not matched."
            )
        elif bank_count == 0:
            status = "Missing in bank statement"
            reason_code = "MISSING_IN_BANK"
            explanation = "Reference exists in the ledger but not in the bank statement."
        elif ledger_count == 0:
            status = "Missing in ledger"
            reason_code = "MISSING_IN_LEDGER"
            explanation = "Reference exists in the bank statement but not in the ledger."
        elif bank_row["amount_cents"] != ledger_row["amount_cents"]:
            status = "Amount mismatch"
            reason_code = "AMOUNT_MISMATCH"
            explanation = (
                "Unique references have different amounts at two-decimal precision."
            )
        else:
            status = "Matched"
            reason_code = "MATCHED_EXACT"
            explanation = "Unique reference and amount match exactly."

        review_required = status != "Matched"
        records.append(
            {
                "transaction_id": transaction_id,
                "bank_date": bank_row["date"] if bank_row is not None else "",
                "bank_amount": _format_amount(
                    bank_row["amount_cents"] if bank_row is not None else None
                ),
                "ledger_date": ledger_row["date"] if ledger_row is not None else "",
                "ledger_amount": _format_amount(
                    ledger_row["amount_cents"] if ledger_row is not None else None
                ),
                "difference": (
                    _format_amount(
                        bank_row["amount_cents"] - ledger_row["amount_cents"]
                    )
                    if bank_row is not None and ledger_row is not None
                    else ""
                ),
                "status": status,
                "reason_code": reason_code,
                "explanation": explanation,
                "human_review_required": review_required,
                "batch_id": batch_id,
                "rule_version": RULE_VERSION,
                "processed_at_utc": processed_at_utc,
            }
        )

    return pd.DataFrame(records, columns=RESULT_COLUMNS)


def make_audit_manifest(
    bank_bytes: bytes,
    ledger_bytes: bytes,
    bank_row_count: int,
    ledger_row_count: int,
    results: pd.DataFrame,
    bank_mapping: dict[str, str | None] | None = None,
    ledger_mapping: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Build a minimal manifest without storing source values or filenames."""
    batch_id = str(results["batch_id"].iloc[0])
    return {
        "batch_id": batch_id,
        "processed_at_utc": str(results["processed_at_utc"].iloc[0]),
        "rule_version": RULE_VERSION,
        "matching_rule": "Unique exact transaction reference and amount to the cent",
        "column_mappings": {
            "bank_statement": bank_mapping or {},
            "ledger": ledger_mapping or {},
        },
        "sources": {
            "bank_statement": {
                "sha256": hashlib.sha256(bank_bytes).hexdigest(),
                "transaction_count": bank_row_count,
            },
            "ledger": {
                "sha256": hashlib.sha256(ledger_bytes).hexdigest(),
                "transaction_count": ledger_row_count,
            },
        },
        "result_count": len(results),
        "status_counts": {
            str(status): int(count)
            for status, count in results["status"].value_counts().items()
        },
        "human_review_required_count": int(
            results["human_review_required"].sum()
        ),
        "data_retention": "The prototype does not persist uploaded source files.",
    }


def to_safe_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize CSV while neutralizing spreadsheet formula-like text values."""
    safe_frame = frame.copy()
    for column in safe_frame.select_dtypes(include=["object", "string"]).columns:
        safe_frame[column] = safe_frame[column].map(
            lambda value: (
                "'" + value
                if isinstance(value, str)
                and value.lstrip().startswith(FORMULA_PREFIXES)
                else value
            )
        )
    return safe_frame.to_csv(index=False).encode("utf-8-sig")


def make_review_log(results: pd.DataFrame) -> pd.DataFrame:
    """Create a blank human-review worksheet for every flagged result."""
    exceptions = results.loc[results["human_review_required"]].copy()
    exceptions["review_status"] = "Pending"
    exceptions["reviewer"] = ""
    exceptions["reviewed_at_utc"] = ""
    exceptions["decision"] = ""
    exceptions["evidence_reference"] = ""
    exceptions["review_notes"] = ""
    return exceptions


def audit_json_bytes(manifest: dict[str, Any]) -> bytes:
    """Serialize an audit manifest as readable JSON."""
    return json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
