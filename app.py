from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

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

ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "sample_data"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
STATUS_ORDER = [
    "Matched",
    "Amount mismatch",
    "Missing in bank statement",
    "Missing in ledger",
    "Duplicate review",
]

st.set_page_config(
    page_title="ClearLedger | Reconciliation Studio",
    page_icon="↔",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
      .block-container { max-width: 1440px; padding-top: 2rem; }
      .hero { padding: 1.7rem 1.9rem; border-radius: 18px;
        background: linear-gradient(125deg, #102b35 0%, #174b50 60%, #26756b 100%);
        color: #f4fbf8; margin-bottom: 1.1rem; }
      .hero h1 { color: #f4fbf8; margin: 0.25rem 0 0.45rem; letter-spacing: -0.04em; }
      .hero p { color: #d0e6df; max-width: 760px; margin-bottom: 0; }
      .eyebrow { color: #9de1c0; text-transform: uppercase; letter-spacing: .12em;
        font-size: .74rem; font-weight: 700; }
      .note { border-left: 3px solid #4a9b82; padding: .6rem .9rem;
        background: rgba(75, 155, 130, .08); border-radius: 0 8px 8px 0; }
      div[data-testid="stMetric"] { background: rgba(128, 160, 150, .08);
        padding: .85rem 1rem; border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def guess_column(columns: list[str], field: str) -> int:
    aliases = {
        "transaction_id": (
            "transaction_id",
            "transaction id",
            "reference",
            "transaction_reference",
            "transaction ref",
            "ref",
            "id",
        ),
        "date": ("date", "transaction_date", "transaction date", "posted_date"),
        "amount": ("amount", "transaction_amount", "transaction amount", "value"),
        "description": ("description", "details", "narration", "memo"),
    }
    normalized = {column: column.strip().lower() for column in columns}
    for alias in aliases[field]:
        for column, normalized_column in normalized.items():
            if normalized_column == alias:
                return columns.index(column)
    return 0


def read_source(content: bytes, source_name: str) -> pd.DataFrame:
    if len(content) > MAX_UPLOAD_BYTES:
        raise DataValidationError(
            f"{source_name}: file exceeds the 20 MB prototype upload limit."
        )
    return read_csv_bytes(content, source_name)


def source_mapping(
    frame: pd.DataFrame,
    source_name: str,
    key_prefix: str,
) -> dict[str, str | None]:
    columns = [str(column) for column in frame.columns]
    st.markdown(f"**{source_name} columns**")
    first, second = st.columns(2)
    mapping: dict[str, str | None] = {}
    for container, field, label in (
        (first, "transaction_id", "Transaction reference"),
        (second, "date", "Transaction date"),
        (first, "amount", "Amount"),
    ):
        index = guess_column(columns, field)
        mapping[field] = container.selectbox(
            label,
            options=columns,
            index=index,
            key=f"{key_prefix}_{field}",
        )
    mapping["description"] = st.selectbox(
        "Description (optional)",
        options=["— Not used —", *columns],
        index=(
            guess_column(columns, "description") + 1
            if any(
                column.strip().lower()
                in ("description", "details", "narration", "memo")
                for column in columns
            )
            else 0
        ),
        key=f"{key_prefix}_description",
    )
    if mapping["description"] == "— Not used —":
        mapping["description"] = None
    return mapping


def get_input_data() -> tuple[bytes, bytes] | None:
    mode = st.radio(
        "Choose your data source",
        ["Synthetic demo data", "Upload your CSVs"],
        horizontal=True,
        help="Use the included synthetic sample first, or upload a bank statement and ledger export.",
        key="data_source",
    )
    if mode == "Synthetic demo data":
        return (
            (SAMPLE_DIR / "bank_statement.csv").read_bytes(),
            (SAMPLE_DIR / "ledger.csv").read_bytes(),
        )

    bank_file, ledger_file = st.columns(2)
    with bank_file:
        bank_upload = st.file_uploader(
            "Bank statement CSV",
            type=["csv"],
            key="bank_upload",
            help="Maximum 20 MB. Your CSV is processed by this app instance and is not stored by this prototype.",
        )
    with ledger_file:
        ledger_upload = st.file_uploader(
            "Accounting ledger CSV",
            type=["csv"],
            key="ledger_upload",
            help="Maximum 20 MB. Your CSV is processed by this app instance and is not stored by this prototype.",
        )
    if bank_upload is None or ledger_upload is None:
        st.info("Upload both CSV files to continue. No file is needed to explore the synthetic demo.")
        return None
    return (
        bank_upload.getvalue(),
        ledger_upload.getvalue(),
    )


def show_downloads(results: pd.DataFrame, manifest: dict) -> None:
    review_log = make_review_log(results)
    one, two, three = st.columns(3)
    one.download_button(
        "Download reconciliation CSV",
        data=to_safe_csv_bytes(results),
        file_name="reconciliation_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
    two.download_button(
        "Download review worksheet",
        data=to_safe_csv_bytes(review_log),
        file_name="exception_review_log.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=review_log.empty,
    )
    three.download_button(
        "Download batch audit JSON",
        data=audit_json_bytes(manifest),
        file_name="reconciliation_audit.json",
        mime="application/json",
        use_container_width=True,
    )


def display_results(results: pd.DataFrame, manifest: dict) -> None:
    st.divider()
    st.subheader("Reconciliation results")
    st.caption(
        f"Batch `{manifest['batch_id']}` · rule version "
        f"`{manifest['rule_version']}` · processed "
        f"`{manifest['processed_at_utc']}`"
    )
    total = len(results)
    exceptions = int(results["human_review_required"].sum())
    matched = total - exceptions
    duplicates = int((results["status"] == "Duplicate review").sum())
    columns = st.columns(4)
    columns[0].metric("Transactions reviewed", f"{total:,}")
    columns[1].metric("Exact matches", f"{matched:,}")
    columns[2].metric("Needs human review", f"{exceptions:,}")
    columns[3].metric("Duplicate references", f"{duplicates:,}")

    left, right = st.columns([1, 1.2])
    counts = (
        results["status"]
        .value_counts()
        .reindex(STATUS_ORDER, fill_value=0)
        .rename_axis("Status")
        .reset_index(name="Transactions")
    )
    with left:
        st.markdown("**Outcome breakdown**")
        st.bar_chart(counts, x="Status", y="Transactions", horizontal=True)
    with right:
        st.markdown("**Review queue**")
        st.markdown(
            '<div class="note">Every non-match is routed to a human reviewer. '
            "The prototype does not approve, post, or pay transactions.</div>",
            unsafe_allow_html=True,
        )
        st.write(
            f"**{exceptions:,}** records need review. "
            "Use the downloaded worksheet to capture a reviewer, decision, "
            "supporting evidence, and notes."
        )

    selected_statuses = st.multiselect(
        "Filter by status",
        options=STATUS_ORDER,
        default=STATUS_ORDER,
        key=f"filter_{manifest['batch_id']}",
    )
    visible = results.loc[results["status"].isin(selected_statuses)]
    st.dataframe(visible, hide_index=True, use_container_width=True)
    show_downloads(results, manifest)

    with st.expander("Batch traceability"):
        st.json(manifest)


st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">Portfolio prototype · deterministic controls</div>
      <h1>ClearLedger Reconciliation Studio</h1>
      <p>Compare a bank statement with an accounting ledger, surface exceptions with
      traceable reasons, and prepare a practical human-review worksheet.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    "**Matching rule:** exact, unique transaction reference plus amount to the cent. "
    "Duplicate references and all exceptions require human review."
)
st.warning(
    "Use synthetic or explicitly authorized data only. This is a portfolio "
    "demonstration, not a banking system or production financial control."
)

with st.sidebar:
    st.title("About this prototype")
    st.write(
        "A business-analysis case study demonstrating a clear process, "
        "deterministic rules, input validation, traceable exceptions, and "
        "responsible human oversight."
    )
    st.markdown("**CSV requirements**")
    st.write("Each file needs a transaction reference, date, and amount column. "
             "You can map differently named columns after loading the files.")
    st.markdown("**Data handling**")
    st.write(
        "Files are held in the app session for processing and are not written "
        "to disk by the prototype. No external AI service is called. When "
        "hosted, the app's server still receives uploaded files; do not upload "
        "confidential information."
    )
    st.markdown("**What it does not do**")
    st.write(
        "It does not match on date or description, handle currencies or "
        "one-to-many settlements, post journal entries, or initiate payments."
    )
    st.caption("Rule version 1.0.0 · synthetic example included")

st.subheader("1. Choose your data")
input_data = get_input_data()
if input_data is not None:
    bank_bytes, ledger_bytes = input_data
    try:
        bank_frame = read_source(bank_bytes, "Bank statement")
        ledger_frame = read_source(ledger_bytes, "Accounting ledger")
    except DataValidationError as exc:
        st.error(str(exc))
        st.stop()

    if len(bank_frame) > 100_000 or len(ledger_frame) > 100_000:
        st.error("Each CSV is limited to 100,000 rows in this prototype.")
        st.stop()

    st.subheader("2. Confirm the columns")
    st.caption(
        f"Loaded {len(bank_frame):,} bank-statement rows and "
        f"{len(ledger_frame):,} ledger rows. Familiar column names are "
        "auto-detected; confirm both mappings before continuing."
    )
    bank_col, ledger_col = st.columns(2)
    with bank_col:
        bank_mapping = source_mapping(bank_frame, "Bank statement", "bank")
    with ledger_col:
        ledger_mapping = source_mapping(ledger_frame, "Accounting ledger", "ledger")

    st.subheader("3. Run the reconciliation")
    st.caption(
        "Only unique transaction references and amounts to the cent are "
        "matched. Every exception remains for human review."
    )
    run_column, _ = st.columns([1, 3])
    with run_column:
        run_clicked = st.button(
            "Run reconciliation",
            type="primary",
            use_container_width=True,
        )

    fingerprint = hashlib.sha256()
    for value in (
        bank_bytes,
        ledger_bytes,
        json.dumps(
            [bank_mapping, ledger_mapping],
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8"),
    ):
        fingerprint.update(len(value).to_bytes(8, "big"))
        fingerprint.update(value)
    input_fingerprint = fingerprint.hexdigest()

    if run_clicked:
        try:
            bank_data = normalize_transactions(
                bank_frame, bank_mapping, "Bank statement"
            )
            ledger_data = normalize_transactions(
                ledger_frame, ledger_mapping, "Accounting ledger"
            )
            results = reconcile(bank_data, ledger_data)
            manifest = make_audit_manifest(
                bank_bytes,
                ledger_bytes,
                len(bank_data),
                len(ledger_data),
                results,
                bank_mapping,
                ledger_mapping,
            )
            st.session_state["reconciliation_run"] = {
                "fingerprint": input_fingerprint,
                "results": results,
                "manifest": manifest,
            }
        except DataValidationError as exc:
            st.error(str(exc))

    saved_run = st.session_state.get("reconciliation_run")
    if saved_run and saved_run["fingerprint"] == input_fingerprint:
        display_results(saved_run["results"], saved_run["manifest"])
    elif not run_clicked:
        st.info("Confirm the column mappings, then select **Run reconciliation**.")
else:
    st.markdown("### Get started")
    st.write(
        "Choose **Synthetic demo data** above to explore the workflow, or "
        "upload both a bank statement and a ledger CSV."
    )
    with st.expander("Download synthetic example CSVs"):
        sample_bank, sample_ledger = st.columns(2)
        sample_bank.download_button(
            "Download sample bank statement",
            data=(SAMPLE_DIR / "bank_statement.csv").read_bytes(),
            file_name="sample_bank_statement.csv",
            mime="text/csv",
            use_container_width=True,
        )
        sample_ledger.download_button(
            "Download sample ledger",
            data=(SAMPLE_DIR / "ledger.csv").read_bytes(),
            file_name="sample_ledger.csv",
            mime="text/csv",
            use_container_width=True,
        )
