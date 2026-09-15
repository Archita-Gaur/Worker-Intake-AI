import json

import pytest


try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover - depends on the installed Streamlit version
    AppTest = None


pytestmark = pytest.mark.skipif(AppTest is None, reason="Streamlit AppTest is unavailable")


def test_app_loads_examples_and_manual_rows_have_unique_ids():
    app = AppTest.from_file("app.py").run(timeout=30)
    assert not app.exception

    app.button[3].click().run(timeout=30)  # fictional applicant example
    assert not app.exception
    assert app.session_state["title_vii_intake"]["applicant_status"] == "Applicant"
    assert app.session_state["review_rows"][0]["finding_id"] != app.session_state["review_rows"][1]["finding_id"]

    app.button[0].click().run(timeout=30)
    app.button[0].click().run(timeout=30)
    ids = [row["finding_id"] for row in app.session_state["review_rows"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 4


def test_app_clear_removes_example_answers_and_findings():
    app = AppTest.from_file("app.py").run(timeout=30)
    app.button[3].click().run(timeout=30)
    assert app.session_state["applicant_notes"]

    app.button[4].click().run(timeout=30)  # clear session
    assert not app.session_state["review_rows"]
    assert not app.session_state["applicant_notes"]
    assert app.session_state["title_vii_intake"]["applicant_status"] == "Unknown"


def test_detail_interpretation_edit_records_human_history_and_intake_exports():
    app = AppTest.from_file("app.py").run(timeout=30)
    app.button[2].click().run(timeout=30)
    interpretation = next(item for item in app.text_area if item.label == "Interpretation")
    interpretation.set_value("Updated through the detail editor").run(timeout=30)

    row = app.session_state["review_rows"][0]
    event = next(item for item in row["edit_history"] if item["changed_field"] == "interpretation")
    assert event["old_value"]
    assert event["new_value"] == "Updated through the detail editor"
    assert event["actor_type"] == "human"

    harassment = next(item for item in app.text_area if item.label == "Harassment: specific conduct")
    harassment.set_value("Synthetic reported conduct").run(timeout=30)
    assert app.session_state["title_vii_intake"]["harassment_conduct"] == "Synthetic reported conduct"
    from worker_intake_ai.logic import export_review_json

    payload = json.loads(
        export_review_json(
            app.session_state["review_rows"],
            {
                "title_vii_intake": dict(app.session_state["title_vii_intake"]),
            },
        )
    )
    assert payload["intake_answers"]["title_vii_intake"]["harassment_conduct"] == "Synthetic reported conduct"
