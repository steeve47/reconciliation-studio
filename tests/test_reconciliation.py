import json
from pathlib import Path

import pandas as pd
import pytest

from reconciliation import (
    DataValidationError,
    audit_json_bytes,
    make_audit_manifest,
    make_review_log,
    normalize_transactions,
    read_csv_bytes,
    reconcile,
    to_safe_csv_bytes,
)

ROOT = Path(__file__).parents[1]
REQUIRED_MAPPING = {
    "transaction_id": "transaction_id",
    "date": "date",
    "amount": "amount",
    "description": "description",
}


def load_sample(filename, source):
    content = (ROOT / "sample_data" / filename).read_bytes()
    frame = read_csv_bytes(content, source)
    return content, normalize_transactions(frame, REQUIRED_MAPPING, source)


@pytest.fixture
def sample_run():
    bank_bytes, bank = load_sample("bank_statement.csv", "Bank statement")
    ledger_bytes, ledger = load_sample("ledger.csv", "Ledger")
    results = reconcile(
        bank,
        ledger,
        batch_id="test-batch",
        processed_at_utc="2026-10-25T00:00:00+00:00",
    )
    manifest = make_audit_manifest(
        bank_bytes, ledger_bytes, len(bank), len(ledger), results
    )
    return bank_bytes, ledger_bytes, bank, ledger, results, manifest


def test_synthetic_sample_has_expected_status_counts(sample_run):
    results = sample_run[4]
    assert results["status"].value_counts().to_dict() == {
        "Matched": 3,
        "Missing in bank statement": 2,
        "Amount mismatch": 1,
        "Missing in ledger": 1,
        "Duplicate review": 1,
    }


def test_unique_exact_match_has_no_review(sample_run):
    result = sample_run[4].set_index("transaction_id").loc["T001"]
    assert result["status"] == "Matched"
    assert result["reason_code"] == "MATCHED_EXACT"
    assert not result["human_review_required"]
    assert result["difference"] == "0.00"


def test_duplicate_reference_is_not_silently_matched(sample_run):
    result = sample_run[4].set_index("transaction_id").loc["T006"]
    assert result["status"] == "Duplicate review"
    assert result["reason_code"] == "DUPLICATE_REFERENCE"
    assert result["bank_amount"] == ""
    assert result["human_review_required"]
    assert "bank statement" in result["explanation"]


def test_amount_difference_is_reported_exactly(sample_run):
    result = sample_run[4].set_index("transaction_id").loc["T003"]
    assert result["status"] == "Amount mismatch"
    assert result["difference"] == "-50.00"
    assert result["human_review_required"]


def test_missing_source_reasons_are_directional(sample_run):
    results = sample_run[4].set_index("transaction_id")
    assert results.loc["T004", "reason_code"] == "MISSING_IN_LEDGER"
    assert results.loc["T005", "reason_code"] == "MISSING_IN_BANK"


def test_amounts_are_compared_to_cents():
    bank = pd.DataFrame(
        {"transaction_id": ["A"], "date": ["2026-10-01"], "amount": ["1.10"]}
    )
    ledger = pd.DataFrame(
        {"transaction_id": ["A"], "date": ["2026-10-01"], "amount": ["1.1"]}
    )
    mapping = {"transaction_id": "transaction_id", "date": "date", "amount": "amount"}
    result = reconcile(
        normalize_transactions(bank, mapping, "Bank"),
        normalize_transactions(ledger, mapping, "Ledger"),
    )
    assert result.loc[0, "status"] == "Matched"


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pd.DataFrame({"transaction_id": ["A"], "amount": [1]}), "map a column"),
        (
            pd.DataFrame(
                {
                    "transaction_id": ["A"],
                    "date": ["2026-10-01"],
                    "amount": ["1.001"],
                }
            ),
            "more than two decimal places",
        ),
        (
            pd.DataFrame(
                {
                    "transaction_id": ["A"],
                    "date": ["not-a-date"],
                    "amount": [1],
                }
            ),
            "invalid date",
        ),
        (
            pd.DataFrame(
                {
                    "transaction_id": ["  "],
                    "date": ["2026-10-01"],
                    "amount": [1],
                }
            ),
            "blank transaction reference",
        ),
    ],
)
def test_invalid_transaction_data_is_rejected(frame, message):
    mapping = {
        "transaction_id": "transaction_id",
        "date": "date",
        "amount": "amount",
    }
    with pytest.raises(DataValidationError, match=message):
        normalize_transactions(frame, mapping, "Test source")


def test_missing_amount_is_rejected():
    frame = pd.DataFrame(
        {"transaction_id": ["A"], "date": ["2026-10-01"], "amount": [None]}
    )
    with pytest.raises(DataValidationError, match="missing or invalid amount"):
        normalize_transactions(
            frame,
            {"transaction_id": "transaction_id", "date": "date", "amount": "amount"},
            "Test source",
        )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (b"\xff\xfe", "UTF-8"),
        (b"transaction_id, transaction_id,date,amount\nA,A,2026-10-01,1\n", "duplicate"),
        (b"transaction_id,,date,amount\nA,,2026-10-01,1\n", "blank"),
        (b"transaction_id,date,amount\n", "no transactions"),
    ],
)
def test_invalid_csv_is_rejected(content, message):
    with pytest.raises(DataValidationError, match=message):
        read_csv_bytes(content, "Test CSV")


def test_review_worksheet_only_contains_exceptions(sample_run):
    review_log = make_review_log(sample_run[4])
    assert len(review_log) == 5
    assert set(review_log["review_status"]) == {"Pending"}
    assert set(review_log["reviewer"]) == {""}


def test_audit_manifest_contains_hashes_and_counts(sample_run):
    bank_bytes, ledger_bytes, bank, ledger, results, manifest = sample_run
    assert manifest["sources"]["bank_statement"]["sha256"]
    assert manifest["sources"]["ledger"]["sha256"]
    assert manifest["result_count"] == 8
    assert manifest["human_review_required_count"] == 5
    assert "T001" not in json.dumps(manifest)
    assert audit_json_bytes(manifest).startswith(b"{")


def test_csv_exports_escape_spreadsheet_formulas():
    frame = pd.DataFrame({"transaction_id": ["=1+1"], "amount": ["-4.25"]})
    exported = to_safe_csv_bytes(frame).decode("utf-8-sig")
    assert "'=1+1" in exported
    assert "-4.25" in exported


def test_reconcile_requires_both_sources():
    with pytest.raises(DataValidationError, match="Both sources"):
        reconcile(
            pd.DataFrame(columns=["transaction_id"]),
            pd.DataFrame(columns=["transaction_id"]),
        )
