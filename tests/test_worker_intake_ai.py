import json
import uuid

import pytest

from worker_intake_ai.logic import (
    INFORMATION_STATUSES,
    REVIEW_STATUSES,
    SOURCE_TYPES,
    ensure_review_row,
    evaluate_quote_validation_status,
    export_review_json,
    export_review_markdown,
    extract_text_from_file,
    get_fixture_findings,
    parse_loaded_applicant_sample,
    generate_title_vii_blank_form,
    intake_allows_missing_documents_or_comparator,
    migrate_legacy_row,
    make_unique_finding_id,
    no_score_generated,
    prediction_status,
    record_edit_history,
    validate_quote_present,
    update_finding,
    validate_source,
)
from worker_intake_ai.research import (
    UnavailableLiveSearchProvider,
    export_research_json,
    export_research_markdown,
    make_authority_record,
    normalize_research,
)


def test_unknown_survives_editing_and_export():
    row = {
        "finding_id": "finding-1",
        "topic": "Ability to hire helpers",
        "source_type": "Worker account",
        "exact_quote": "I do not know whether I can send someone else to do the work.",
        "source_location": "intake, answer 2",
        "information_status": "Unknown",
        "review_status": "Unreviewed",
        "follow_up_question": "Who decides whether the work can be delegated?",
    }
    clean = ensure_review_row(row)
    assert clean["information_status"] == "Unknown"
    assert "Unknown" in export_review_markdown([clean])


def test_conflicting_sources_remains_distinct_from_contested_facts():
    row = {"topic": "Scheduling", "information_status": "Conflicting sources", "review_status": "Unreviewed"}
    clean = ensure_review_row(row)
    assert clean["information_status"] == "Conflicting sources"
    assert clean["information_status"] != "Disputed"
    assert "Conflicting sources" in export_review_json([clean])


def test_review_status_does_not_overwrite_information_status():
    row = {"information_status": "Needs clarification", "review_status": "Reviewed"}
    clean = ensure_review_row(row)
    assert clean["information_status"] == "Needs clarification"
    assert clean["review_status"] == "Reviewed"


def test_human_edit_history_and_migration_events_are_distinct():
    previous = {
        "finding_id": "finding-edit",
        "topic": "Scheduling",
        "source_type": "Worker account",
        "exact_quote": "Old quote",
        "source_location": "intake, answer 1",
        "interpretation": "Old interpretation",
        "review_status": "Unreviewed",
        "edit_history": [],
    }
    current = {
        "finding_id": "finding-edit",
        "topic": "Scheduling",
        "source_type": "Worker account",
        "exact_quote": "Old quote",
        "source_location": "intake, answer 1",
        "interpretation": "Updated interpretation",
        "review_status": "Reviewed",
        "edit_history": [],
    }
    history = record_edit_history(previous, current, reviewer_identifier="staff-1")
    interpretation_event = next(entry for entry in history if entry["changed_field"] == "interpretation")
    assert interpretation_event["event_type"] == "human_edit"
    assert interpretation_event["actor_type"] == "human"
    assert interpretation_event["old_value"] == "Old interpretation"
    assert interpretation_event["new_value"] == "Updated interpretation"
    assert any(entry["changed_field"] == "review_status" for entry in history)

    migrated = ensure_review_row({"finding_id": "finding-migration", "field": "Scheduling", "original_value": "Legacy quote"})
    assert any(entry.get("event_type") == "migration" for entry in migrated["edit_history"])
    assert all(entry.get("actor_type") != "human" for entry in migrated["edit_history"] if entry.get("event_type") == "migration")


def test_quote_checks_update_after_quote_source_edits():
    row = {
        "finding_id": "finding-2",
        "topic": "Scheduling",
        "source_type": "Contract",
        "exact_quote": "Contractor determines their own working hours.",
        "source_location": "contract, paragraph 1",
    }
    clean = ensure_review_row(row)
    contract_text = "CONTRACT, paragraph 1: Contractor determines their own working hours."
    assert evaluate_quote_validation_status(clean["exact_quote"], contract_text) == "Match found"
    clean["exact_quote"] = "Different wording"
    assert evaluate_quote_validation_status(clean["exact_quote"], contract_text) == "Match not found"
    assert validate_quote_present(clean["exact_quote"], contract_text) is False


def test_correction_history_records_actual_changed_fields():
    previous = {
        "finding_id": "finding-3",
        "topic": "Scheduling",
        "source_type": "Worker account",
        "exact_quote": "Old quote",
        "source_location": "intake, answer 1",
        "interpretation": "Old interpretation",
        "information_status": "Unknown",
        "review_status": "Unreviewed",
        "edit_history": [],
    }
    current = {
        "finding_id": "finding-3",
        "topic": "Scheduling",
        "source_type": "Worker account",
        "exact_quote": "Updated quote",
        "source_location": "intake, answer 1",
        "interpretation": "Updated interpretation",
        "information_status": "Unknown",
        "review_status": "Reviewed",
        "edit_history": [],
    }
    history = record_edit_history(previous, current, "reviewer-1")
    assert any(entry["changed_field"] == "exact_quote" for entry in history)
    assert any(entry["changed_field"] == "review_status" for entry in history)
    assert history[0]["reviewer_identifier"] == "reviewer-1"


def test_empty_rows_are_excluded_without_dropping_partially_completed_rows():
    empty = {"topic": "", "exact_quote": "", "source_location": ""}
    partial = {"topic": "Scheduling", "exact_quote": "", "source_location": "intake, answer 1"}
    rows = [empty, partial]
    exported = export_review_json(rows)
    assert "Scheduling" in exported
    assert "topic" in exported


def test_rejected_and_unreviewed_findings_are_handled_as_specified():
    rejected = {"topic": "Rejected topic", "source_type": "Unknown", "review_status": "Rejected", "exact_quote": "Obs"}
    unreviewed = {"topic": "Unreviewed topic", "source_type": "Contract", "review_status": "Unreviewed", "exact_quote": "Clause"}
    markdown = export_review_markdown([rejected, unreviewed])
    assert "Rejected findings" in markdown
    assert "Unreviewed findings" in markdown
    assert "Unreviewed topic" in markdown
    assert "Rejected topic" in markdown


def test_legacy_exports_migrate_without_silent_data_loss():
    legacy = {
        "field": "Scheduling",
        "source_type": "Contract",
        "original_value": "Legacy original quote",
        "review_status": "Unreviewed",
        "information_status": "Disputed",
    }
    migrated = migrate_legacy_row(legacy)
    assert migrated["legacy_original_value"] == "Legacy original quote"
    assert isinstance(migrated["edit_history"], list)
    assert migrated["migration_note"] is not None


def test_missing_documents_or_comparator_do_not_block_intake():
    form = {"work_location_and_employer_type": "", "approximate_employer_size": "", "treatment_of_others_if_known": ""}
    assert intake_allows_missing_documents_or_comparator(form) is True


def test_no_score_or_deadline_generated():
    assert prediction_status() == "Not available: model development and validation pending."
    assert no_score_generated() is True
    payload = export_review_json([{"topic": "Scheduling", "review_status": "Unreviewed"}])
    assert "score" not in payload.lower()
    assert "deadline" not in payload.lower()


def test_complete_exportincludes_schema_version_and_title_vii_answers():
    row = {"topic": "Scheduling", "source_type": "Contract", "review_status": "Reviewed", "exact_quote": "Clause"}
    payload = json.loads(
        export_review_json(
            [row],
            {
                "contract_text": "sample contract text",
                "worker_notes": "sample worker notes",
                "title_vii_intake": {
                    "work_relationship": "Current worker",
                    "alleged_discrimination": "Late shift assignment",
                    "agency_contact": "EEOC intake in progress",
                },
            },
        )
    )
    assert payload["schema_version"] == "1.0"
    assert payload["synthetic_demo"] is True
    assert payload["intake_answers"]["title_vii_intake"]["work_relationship"] == "Current worker"
    assert payload["findings"][0]["review_status"] == "Reviewed"
    assert "export_timestamp" in payload


def test_sample_fixture_rows_are_present_and_statuses_are_correct():
    rows = get_fixture_findings(
        "CONTRACT, paragraph 1: Contractor determines their own working hours.\nCONTRACT, paragraph 2: The company supplies the required scheduling software.",
        "INTAKE, answer 1: My supervisor assigns mandatory shifts each week.\nINTAKE, answer 2: I do not know whether I can send someone else to do the work.\nINTAKE, answer 3: I reported a coworker's repeated offensive comments to my supervisor. I have not yet described the comments or given dates."
    )
    assert len(rows) == 4
    assert rows[0]["information_status"] == "Conflicting sources"
    assert rows[2]["information_status"] == "Unknown"
    assert rows[3]["information_status"] == "Needs clarification"
    assert all(row["review_status"] == "Unreviewed" for row in rows)


def test_applicant_fixture_and_proposed_conditions_are_distinct():
    sample = parse_loaded_applicant_sample()
    rows = get_fixture_findings(
        sample["contract_text"],
        sample["worker_notes"],
        sample["applicant_notes"],
    )
    assert len(rows) == 2
    assert rows[0]["source_type"] == "Job advertisement"
    assert "did not perform" in rows[0]["interpretation"]
    assert rows[1]["source_type"] == "Recruitment/rejection message"
    assert all(row["review_status"] == "Unreviewed" for row in rows)


def test_applicant_answers_survive_complete_export_without_legal_conclusion():
    intake = generate_title_vii_blank_form()
    intake.update(
        {
            "applicant_status": "Applicant",
            "proposed_role_type": "Unknown",
            "applicant_position": "Warehouse coordinator",
            "application_date": "Approximately August 3, 2026",
            "rejection_date": "Unknown",
            "applicant_qualifications": "Three years coordinating deliveries.",
        }
    )
    payload = json.loads(export_review_json([], {"title_vii_intake": intake}))
    exported = payload["intake_answers"]["title_vii_intake"]
    assert exported["applicant_status"] == "Applicant"
    assert exported["proposed_role_type"] == "Unknown"
    assert exported["application_date"] == "Approximately August 3, 2026"
    assert exported["rejection_date"] == "Unknown"
    assert "score" not in json.dumps(payload).lower()
    assert "calculate" not in json.dumps(payload).lower()


def test_unsupported_document_type_and_pdf_behavior():
    try:
        extract_text_from_file("bad.txt", b"\xff\xff")
    except ValueError:
        pass
    else:
        assert False, "Expected a ValueError for unsupported text"

    try:
        extract_text_from_file("bad.pdf", b"%PDF-1.4\ntrailer\n<<>>\n%%EOF")
    except ValueError:
        pass
    else:
        assert False, "Expected a ValueError for unreadable PDF"

    assert "Unknown" in SOURCE_TYPES
    assert "Reviewed" in REVIEW_STATUSES
    assert "Information provided" in INFORMATION_STATUSES
    assert "Job advertisement" in SOURCE_TYPES
    assert "Interview notes" in SOURCE_TYPES


def test_finding_ids_are_uuid_and_atomic_updates_preserve_identity_and_history():
    row = ensure_review_row({"topic": "Scheduling", "source_type": "Worker account"})
    uuid.UUID(row["finding_id"])
    original_history = row["edit_history"]
    updated = update_finding([row], row["finding_id"], {"interpretation": "Staff review"}, "staff-7")
    assert updated[0]["finding_id"] == row["finding_id"]
    assert row["interpretation"] == ""
    assert row["edit_history"] is original_history
    events = [e for e in updated[0]["edit_history"] if e["changed_field"] == "interpretation"]
    assert len(events) == 1
    assert events[0]["old_value"] == ""
    assert events[0]["new_value"] == "Staff review"


def test_manual_finding_ids_are_unique():
    assert make_unique_finding_id() != make_unique_finding_id()


def test_source_validation_separates_document_and_location():
    row = {
        "exact_quote": "A quoted sentence.",
        "source_location": "page 2",
        "source_type": "Contract",
    }
    result = validate_source(row, "intro\nA quoted sentence.", ["intro", "A quoted sentence."])
    assert result["document_validation_status"] == "Match found"
    assert result["location_validation_status"] == "Match found"
    wrong = validate_source(row, "intro\nA quoted sentence.", ["intro", "different text"])
    assert wrong["document_validation_status"] == "Match found"
    assert wrong["location_validation_status"] == "Match not found"


def test_legacy_invalid_status_and_source_remain_visible():
    migrated = ensure_review_row(
        {"topic": "Legacy", "source_type": "old-source", "information_status": "old-status"}
    )
    assert migrated["source_type"] == "Unknown"
    assert migrated["legacy_original_source_type"] == "old-source"
    assert migrated["legacy_original_information_status"] == "old-status"
    assert migrated["migration_note"]


def test_research_links_and_party_arguments_are_distinct_from_holdings():
    authority = make_authority_record(
        title="Fictional example authority",
        url="https://example.test/authority",
        holding="The fictional court held only the stated rule.",
        party_arguments="The fictional party argued for a broader rule.",
        is_fictional=True,
    )
    assert authority["url"].startswith("https://")
    assert authority["holding"] != authority["party_arguments"]
    markdown = export_research_markdown({"authorities": [authority]})
    assert "Party arguments (not holdings)" in markdown
    assert "[Fictional]" in markdown


def test_research_verification_states_are_independent_and_unchecked_is_not_current_law():
    authority = make_authority_record(citation_verification="Identity verified")
    data = normalize_research({"authorities": [authority]})
    saved = data["authorities"][0]
    assert saved["citation_verification"] == "Identity verified"
    assert saved["current_law_verification"] == "Unchecked"
    assert "Current law verified" not in export_research_markdown(data)


def test_research_export_persists_records_and_live_search_is_unavailable():
    authority = make_authority_record(citation="Fictional citation", is_fictional=True)
    research = {
        "plan": {"issue": "Failure to hire", "search_scope": "Federal", "query": "fictional"},
        "authorities": [authority],
        "argument_examples": [{"text": "A fictional argument.", "label": "Fictional example"}],
    }
    payload = json.loads(export_research_json(research))
    assert payload["authorities"][0]["citation"] == "Fictional citation"
    assert payload["argument_examples"][0]["fictional"] is True
    with pytest.raises(RuntimeError, match="unavailable"):
        UnavailableLiveSearchProvider().search("anything")
