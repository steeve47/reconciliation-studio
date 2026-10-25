from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parents[1]


def test_demo_app_renders_and_runs_reconciliation():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not app.exception
    assert any(element.value == "1. Choose your data" for element in app.subheader)

    app.button[0].click().run(timeout=30)

    assert not app.exception
    assert any(element.value == "2. Confirm the columns" for element in app.subheader)
    assert any(
        element.value == "3. Run the reconciliation" for element in app.subheader
    )
    assert any(
        element.label == "Run reconciliation"
        for element in app.button
    )
    assert any(
        element.value == "Reconciliation results"
        for element in app.subheader
    )
    assert len(app.get("download_button")) >= 3


def test_upload_flow_prompts_for_both_csvs_and_offers_synthetic_examples():
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)

    app.radio[0].set_value("Upload your CSVs").run(timeout=30)

    assert not app.exception
    assert len(app.get("file_uploader")) == 2
    assert len(app.get("download_button")) == 2


def test_business_case_page_renders():
    app = AppTest.from_file(str(ROOT / "pages" / "2_Business_Case.py")).run(
        timeout=30
    )
    assert not app.exception
    assert any(element.value == "Benefits model" for element in app.title)
