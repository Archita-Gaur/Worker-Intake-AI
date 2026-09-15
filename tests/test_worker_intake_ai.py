import json

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
    intake_allows_missing_documents_or_comparator,
    migrate_legacy_row,
    no_score_generated,
    prediction_status,
    record_edit_history,
    validate_quote_present,
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
