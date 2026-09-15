from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_FILE_BYTES = 500_000
MAX_TEXT_CHARS = 20_000
MAX_PAGES = 150
SCHEMA_VERSION = "1.0"

INFORMATION_STATUSES = [
    "Information provided",
    "Unknown",
    "Needs clarification",
    "Conflicting sources",
    "Disputed",
    "Not applicable",
]

REVIEW_STATUSES = [
    "Unreviewed",
    "Reviewed",
    "Corrected",
    "Rejected",
]

SOURCE_TYPES = [
    "Contract",
    "Worker account",
    "Message/email",
    "Other document",
    "Staff observation",
    "Job advertisement",
    "Application materials",
    "Interview notes",
    "Recruitment/rejection message",
    "Unknown",
]

QUOTE_VALIDATION_STATUSES = [
    "Match found",
    "Match not found",
    "Not checked",
]

CREATION_METHODS = [
    "manual",
    "fixture",
    "import",
    "migration",
]

SAMPLE_CONTRACT_TEXT = """
CONTRACT, paragraph 1: Contractor determines their own working hours.
CONTRACT, paragraph 2: The company supplies the required scheduling software.
""".strip()

SAMPLE_WORKER_NOTES = """
INTAKE, answer 1: My supervisor assigns mandatory shifts each week.
INTAKE, answer 2: I do not know whether I can send someone else to do the work.
INTAKE, answer 3: I reported a coworker's repeated offensive comments to my supervisor. I have not yet described the comments or given dates.
""".strip()

SAMPLE_APPLICANT_NOTES = """
JOB ADVERTISEMENT, listing 1: The warehouse coordinator role requests two years of scheduling experience.
APPLICATION, submitted 2026-08-03: Applicant describes three years coordinating deliveries and asks about employee status.
INTERVIEW NOTES, stage 2: Interviewer says the team wants someone who will fit the existing culture.
RECRUITMENT MESSAGE, 2026-08-14: We selected another candidate after the final interview.
""".strip()

FIXTURE_FINDINGS: List[Dict[str, Any]] = [
    {
        "finding_id": "finding-scheduling-contract",
        "topic": "Scheduling",
        "field": "Scheduling",
        "source_type": "Contract",
        "creation_method": "fixture",
        "exact_quote": "Contractor determines their own working hours.",
        "source_location": "contract, paragraph 1",
        "interpretation": "The written agreement states the contractor sets their own hours.",
        "information_status": "Conflicting sources",
        "review_status": "Unreviewed",
        "follow_up_question": "What are the actual scheduling practices and consequences for refusing shifts?",
        "evidence_to_request": "Schedule examples, shift assignments, and any written attendance or refusal policies.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "Contractor determines their own working hours.",
        "edit_history": [],
    },
    {
        "finding_id": "finding-scheduling-worker",
        "topic": "Scheduling",
        "field": "Scheduling",
        "source_type": "Worker account",
        "creation_method": "fixture",
        "exact_quote": "My supervisor assigns mandatory shifts each week.",
        "source_location": "intake, answer 1",
        "interpretation": "The reported practice is weekly mandatory scheduling assigned by a supervisor.",
        "information_status": "Conflicting sources",
        "review_status": "Unreviewed",
        "follow_up_question": "Were schedules assigned by company policy or by a supervisor, and what happens if a shift is refused?",
        "evidence_to_request": "Time records, schedules, and any written policy for shift assignment or refusal.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "My supervisor assigns mandatory shifts each week.",
        "edit_history": [],
    },
    {
        "finding_id": "finding-hire-helpers",
        "topic": "Ability to hire helpers",
        "field": "Ability to hire helpers",
        "source_type": "Worker account",
        "creation_method": "fixture",
        "exact_quote": "I do not know whether I can send someone else to do the work.",
        "source_location": "intake, answer 2",
        "interpretation": "The worker is unsure whether substitution is permitted.",
        "information_status": "Unknown",
        "review_status": "Unreviewed",
        "follow_up_question": "Who decides whether the work can be delegated, and are helpers allowed or compensated?",
        "evidence_to_request": "Any written delegation rules, staffing guidance, or internal policy language.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "I do not know whether I can send someone else to do the work.",
        "edit_history": [],
    },
    {
        "finding_id": "finding-conduct-dates",
        "topic": "Reported conduct and dates",
        "field": "Reported conduct and dates",
        "source_type": "Worker account",
        "creation_method": "fixture",
        "exact_quote": "I reported a coworker's repeated offensive comments to my supervisor. I have not yet described the comments or given dates.",
        "source_location": "intake, answer 3",
        "interpretation": "The worker reports conduct but not enough details to assess the substance or timing.",
        "information_status": "Needs clarification",
        "review_status": "Unreviewed",
        "follow_up_question": "What were the comments, when did they occur, and what was the response after reporting?",
        "evidence_to_request": "Dates, witness names, email or text records, complaint documents, and policy or reporting intervals.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "I reported a coworker's repeated offensive comments to my supervisor. I have not yet described the comments or given dates.",
        "edit_history": [],
    },
]

APPLICANT_FIXTURE_FINDINGS: List[Dict[str, Any]] = [
    {
        "finding_id": "finding-applicant-role",
        "topic": "Proposed role and conditions",
        "field": "Proposed role and conditions",
        "source_type": "Job advertisement",
        "creation_method": "fixture",
        "exact_quote": "The warehouse coordinator role requests two years of scheduling experience.",
        "source_location": "job advertisement, listing 1",
        "interpretation": "The advertised role describes qualifications for a proposed position; the applicant did not perform this work.",
        "information_status": "Information provided",
        "review_status": "Unreviewed",
        "follow_up_question": "Was the proposed role intended to be an employee, contractor, or is that unknown?",
        "evidence_to_request": "Job advertisement and any classification or offer materials.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "The warehouse coordinator role requests two years of scheduling experience.",
        "edit_history": [],
    },
    {
        "finding_id": "finding-applicant-rejection",
        "topic": "Failure to hire",
        "field": "Failure to hire",
        "source_type": "Recruitment/rejection message",
        "creation_method": "fixture",
        "exact_quote": "We selected another candidate after the final interview.",
        "source_location": "recruitment message, 2026-08-14",
        "interpretation": "The applicant reports a rejection after a final interview; this does not establish discrimination.",
        "information_status": "Needs clarification",
        "review_status": "Unreviewed",
        "follow_up_question": "What statements or facts lead the applicant to suspect discrimination?",
        "evidence_to_request": "Recruitment messages, interview notes, application, and any stated reason for rejection.",
        "quote_validation_status": "Match found",
        "migration_note": None,
        "legacy_original_value": "We selected another candidate after the final interview.",
        "edit_history": [],
    },
]


def normalize_whitespace(value: Any) -> str:
    return " ".join(str(value or "").split())


def make_finding_id(topic: str, source_type: str, source_location: str, exact_quote: str) -> str:
    text = json.dumps(
        {
            "topic": topic,
            "source_type": source_type,
            "source_location": source_location,
            "exact_quote": exact_quote,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"finding-{digest}"


def evaluate_quote_validation_status(quote: str, source_text: str) -> str:
    if not quote or not quote.strip():
        return "Not checked"
    normalized_quote = normalize_whitespace(quote)
    normalized_source = normalize_whitespace(source_text)
    if not normalized_source:
        return "Not checked"
    if normalized_quote in normalized_source:
        return "Match found"
    return "Match not found"


def get_source_text_for_row(
    row: Dict[str, Any],
    contract_text: str,
    worker_notes: str,
    applicant_notes: str = "",
) -> str:
    source_type = row.get("source_type") or "Unknown"
    if source_type == "Contract":
        return contract_text
    if source_type == "Worker account":
        return worker_notes
    if source_type in {"Message/email", "Recruitment/rejection message", "Application materials", "Interview notes", "Job advertisement"}:
        return applicant_notes or worker_notes
    if source_type == "Other document":
        return "\n".join(part for part in [contract_text, worker_notes] if part)
    if source_type == "Staff observation":
        return worker_notes
    if source_type == "Unknown":
        return "\n".join(part for part in [contract_text, worker_notes] if part)
    return "\n".join(part for part in [contract_text, worker_notes] if part)


def validate_quote_present(quote: str, source_text: str) -> bool:
    return evaluate_quote_validation_status(quote, source_text) == "Match found"


def parse_loaded_sample() -> Dict[str, str]:
    return {
        "contract_text": SAMPLE_CONTRACT_TEXT,
        "worker_notes": SAMPLE_WORKER_NOTES,
    }

def parse_loaded_applicant_sample() -> Dict[str, str]:
    return {
        "contract_text": "",
        "worker_notes": "",
        "applicant_notes": SAMPLE_APPLICANT_NOTES,
    }


def get_fixture_findings(
    contract_text: str,
    worker_notes: str,
    applicant_notes: str = "",
) -> List[Dict[str, Any]]:
    sample_docs = parse_loaded_sample()
    normalized_contract = normalize_whitespace(contract_text)
    normalized_worker = normalize_whitespace(worker_notes)
    if normalized_contract == normalize_whitespace(sample_docs["contract_text"]) and normalized_worker == normalize_whitespace(sample_docs["worker_notes"]):
        return [dict(row) for row in FIXTURE_FINDINGS]
    if (
        not normalized_contract
        and not normalized_worker
        and normalize_whitespace(applicant_notes) == normalize_whitespace(SAMPLE_APPLICANT_NOTES)
    ):
        return [dict(row) for row in APPLICANT_FIXTURE_FINDINGS]
    return []


def normalize_history_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(entry)
    if "event_type" not in normalized:
        normalized["event_type"] = "human_edit" if normalized.get("reviewer_identifier") else "human_edit"
    if "actor_type" not in normalized:
        if normalized.get("event_type") == "migration":
            normalized["actor_type"] = "system"
        elif normalized.get("reviewer_identifier"):
            normalized["actor_type"] = "reviewer"
        else:
            normalized["actor_type"] = "human"
    return normalized


def record_edit_history(
    previous_row: Dict[str, Any],
    current_row: Dict[str, Any],
    reviewer_identifier: Optional[str] = None,
    event_type: str = "human_edit",
    actor_type: str = "human",
) -> List[Dict[str, Any]]:
    history = [normalize_history_entry(entry) for entry in (previous_row.get("edit_history") or [])]
    changed_fields = []
    for key in [
        "topic",
        "source_type",
        "exact_quote",
        "source_location",
        "interpretation",
        "information_status",
        "review_status",
        "follow_up_question",
        "evidence_to_request",
        "quote_validation_status",
        "migration_note",
    ]:
        old_value = previous_row.get(key)
        new_value = current_row.get(key)
        if old_value != new_value:
            changed_fields.append((key, old_value, new_value))
    if not changed_fields:
        return history
    timestamp = datetime.now(timezone.utc).isoformat()
    for field_name, old_value, new_value in changed_fields:
        history.append(
            {
                "finding_id": current_row.get("finding_id") or previous_row.get("finding_id"),
                "changed_field": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "reviewer_identifier": reviewer_identifier,
                "timestamp": timestamp,
                "event_type": event_type,
                "actor_type": actor_type,
            }
        )
    return history


def is_empty_finding(row: Dict[str, Any]) -> bool:
    topic = (row.get("topic") or row.get("field") or "").strip()
    if topic:
        return False
    exact_quote = (row.get("exact_quote") or "").strip()
    source_location = (row.get("source_location") or "").strip()
    interpretation = (row.get("interpretation") or "").strip()
    follow_up_question = (row.get("follow_up_question") or "").strip()
    evidence_to_request = (row.get("evidence_to_request") or "").strip()
    return not any([exact_quote, source_location, interpretation, follow_up_question, evidence_to_request])


def extract_text_from_file(file_name: str, file_bytes: bytes) -> str:
    if not file_name:
        raise ValueError("A file name is required.")
    lowered = file_name.lower()
    if lowered.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Unsupported text file encoding. Please upload UTF-8 text or a PDF.") from exc
        if len(file_bytes) > MAX_FILE_BYTES:
            raise ValueError(f"Document exceeds {MAX_FILE_BYTES} bytes. Please use a shorter excerpt.")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"Text exceeds {MAX_TEXT_CHARS} characters. Please use a shorter excerpt.")
        if not text.strip():
            raise ValueError("The uploaded text file is empty.")
        return text.strip()
    if lowered.endswith(".pdf"):
        if len(file_bytes) > MAX_FILE_BYTES:
            raise ValueError(f"Document exceeds {MAX_FILE_BYTES} bytes. Please use a shorter excerpt.")
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
        except (PdfReadError, ValueError) as exc:
            raise ValueError("This PDF is not readable or has no extractable text. OCR is not implemented for scanned or image-only PDFs.") from exc
        if len(reader.pages) > MAX_PAGES:
            raise ValueError(f"PDF exceeds {MAX_PAGES} pages. Please use a shorter excerpt.")
        parts: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(page_text)
        combined = "\n".join(parts).strip()
        if not combined:
            raise ValueError("This PDF has no extractable text. OCR is not implemented for scanned or image-only PDFs.")
        if len(combined) > MAX_TEXT_CHARS:
            raise ValueError(f"Extracted text exceeds {MAX_TEXT_CHARS} characters. Please use a shorter excerpt.")
        return combined
    raise ValueError("Unsupported document type. Upload a TXT or PDF file.")


def prediction_status() -> str:
    return "Not available: model development and validation pending."


def export_review_markdown(findings: Iterable[Dict[str, Any]]) -> str:
    rows = [ensure_review_row(row) for row in findings if row]
    exportable_rows = [row for row in rows if not is_empty_finding(row)]
    reviewed_rows = [row for row in exportable_rows if row.get("review_status") in {"Reviewed", "Corrected"}]
    unreviewed_rows = [row for row in exportable_rows if row.get("review_status") == "Unreviewed"]
    rejected_rows = [row for row in exportable_rows if row.get("review_status") == "Rejected"]

    lines = [
        "# Worker Intake Review",
        "",
        "Research prototype: synthetic examples only.",
        "",
    ]

    lines.append("## Unreviewed findings")
    if unreviewed_rows:
        for index, row in enumerate(unreviewed_rows, start=1):
            lines.extend(_render_finding_block(index, row))
    else:
        lines.append("No unreviewed findings.")
        lines.append("")

    lines.append("## Reviewed findings")
    if reviewed_rows:
        for index, row in enumerate(reviewed_rows, start=1):
            lines.extend(_render_finding_block(index, row))
    else:
        lines.append("No reviewed findings.")
        lines.append("")

    if rejected_rows:
        lines.append("## Rejected findings")
        for index, row in enumerate(rejected_rows, start=1):
            lines.extend(_render_finding_block(index, row))

    lines.append("## Prediction")
    lines.append(prediction_status())
    return "\n".join(lines)


def _render_finding_block(index: int, row: Dict[str, Any]) -> List[str]:
    lines = [
        f"### Finding {index} ({row.get('topic') or row.get('field') or 'Untitled'})",
        f"- Finding ID: {row.get('finding_id', '')}",
        f"- Source type: {row.get('source_type', 'Unknown')}",
        f"- Exact quote: {row.get('exact_quote', '')}",
        f"- Source location: {row.get('source_location', '')}",
        f"- Interpretation: {row.get('interpretation', '')}",
        f"- Information status: {row.get('information_status', 'Unknown')}",
        f"- Review status: {row.get('review_status', 'Unreviewed')}",
        f"- Quote validation: {row.get('quote_validation_status', 'Not checked')}",
        f"- Follow-up question: {row.get('follow_up_question', '')}",
        f"- Evidence to request: {row.get('evidence_to_request', '')}",
        f"- Edit history count: {len(row.get('edit_history') or [])}",
        "",
    ]
    return lines


def export_review_json(
    findings: Iterable[Dict[str, Any]],
    intake_answers: Optional[Dict[str, Any]] = None,
    synthetic_demo: bool = True,
) -> str:
    rows = [ensure_review_row(row) for row in findings if row]
    sanitized_rows = [row for row in rows if not is_empty_finding(row)]
    export_payload = {
        "schema_version": SCHEMA_VERSION,
        "synthetic_demo": synthetic_demo,
        "intake_answers": intake_answers
        if intake_answers is not None
        else {
            "contract_text": "",
            "worker_notes": "",
            "title_vii_intake": {},
        },
        "findings": sanitized_rows,
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(export_payload, indent=2, ensure_ascii=False)


def ensure_review_row(row: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = dict(row)
    sanitized.setdefault("topic", sanitized.get("field") or "")
    sanitized.setdefault("field", sanitized.get("topic") or "")
    sanitized.setdefault("finding_id", make_finding_id(sanitized.get("topic", ""), sanitized.get("source_type", "Unknown"), sanitized.get("source_location", ""), sanitized.get("exact_quote", "")))
    sanitized.setdefault("source_type", "Unknown")
    sanitized.setdefault("creation_method", "manual")
    sanitized.setdefault("exact_quote", "")
    sanitized.setdefault("source_location", "")
    sanitized.setdefault("interpretation", "")
    sanitized.setdefault("information_status", "Unknown")
    sanitized.setdefault("review_status", "Unreviewed")
    sanitized.setdefault("follow_up_question", "")
    sanitized.setdefault("evidence_to_request", "")
    sanitized.setdefault("quote_validation_status", "Not checked")
    sanitized.setdefault("migration_note", None)
    sanitized.setdefault("legacy_original_value", None)
    if "edit_history" not in sanitized:
        sanitized["edit_history"] = []
    elif sanitized["edit_history"] is None:
        sanitized["edit_history"] = []
    else:
        sanitized["edit_history"] = [normalize_history_entry(entry) for entry in sanitized["edit_history"]]

    if sanitized.get("legacy_original_value") and not any(
        entry.get("event_type") == "migration" for entry in sanitized.get("edit_history") or []
    ):
        sanitized["edit_history"] = list(sanitized.get("edit_history") or [])
        sanitized["edit_history"].append(
            {
                "finding_id": sanitized.get("finding_id"),
                "changed_field": "legacy_original_value",
                "old_value": None,
                "new_value": sanitized.get("legacy_original_value"),
                "reviewer_identifier": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "migration",
                "actor_type": "system",
            }
        )
        sanitized["migration_note"] = "Legacy original_value preserved during migration; no historical edit log was recorded in the prior schema."

    if sanitized.get("original_value") and sanitized.get("legacy_original_value") is None:
        sanitized["legacy_original_value"] = sanitized.get("original_value")
        sanitized["migration_note"] = "Legacy original_value preserved during migration; no historical edit log was recorded in the prior schema."
        if not any(entry.get("event_type") == "migration" for entry in sanitized.get("edit_history") or []):
            sanitized["edit_history"] = list(sanitized.get("edit_history") or [])
            sanitized["edit_history"].append(
                {
                    "finding_id": sanitized.get("finding_id"),
                    "changed_field": "legacy_original_value",
                    "old_value": None,
                    "new_value": sanitized.get("legacy_original_value"),
                    "reviewer_identifier": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "migration",
                    "actor_type": "system",
                }
            )

    source_text = get_source_text_for_row(sanitized, "", "")
    if sanitized.get("quote_validation_status") == "Not checked":
        sanitized["quote_validation_status"] = evaluate_quote_validation_status(sanitized.get("exact_quote", ""), source_text)

    return sanitized


def migrate_legacy_row(row: Dict[str, Any]) -> Dict[str, Any]:
    legacy_row = dict(row)
    legacy_row.setdefault("topic", legacy_row.get("field") or "")
    legacy_row.setdefault("field", legacy_row.get("topic") or "")
    legacy_row.setdefault("source_type", "Unknown")
    legacy_row.setdefault("creation_method", "migration")
    legacy_row.setdefault("review_status", "Unreviewed")
    legacy_row.setdefault("information_status", "Unknown")
    legacy_row.setdefault("quote_validation_status", "Not checked")
    legacy_row.setdefault("edit_history", [])
    if legacy_row.get("original_value") and not legacy_row.get("legacy_original_value"):
        legacy_row["legacy_original_value"] = legacy_row["original_value"]
        legacy_row["migration_note"] = "Legacy value preserved; migration policy kept original values and flagged this row for review."
    return ensure_review_row(legacy_row)


def generate_title_vii_blank_form() -> Dict[str, Any]:
    return {
        "applicant_status": "Unknown",
        "proposed_role_type": "Unknown",
        "applicant_position": "",
        "advertised_qualifications": "",
        "applicant_qualifications": "",
        "application_date": "",
        "hiring_stages": "",
        "applicant_relevant_statements": "",
        "rejection_date": "",
        "applicant_employer_stated_reason": "",
        "why_applicant_suspects_discrimination": "",
        "entities_involved": "",
        "who_hires_pays_assigns_supervises_ends": "",
        "scheduling": "",
        "equipment_helpers_payment_expenses": "",
        "work_location_and_employer_type": "",
        "approximate_employer_size": "",
        "estimate_source": "",
        "uncertainty": "",
        "what_happened_and_what_changed": "",
        "dates_or_approximate_dates": "",
        "people_involved": "",
        "why_worker_believes_treatment_was_discriminatory": "",
        "worker_reported_basis": [],
        "worker_reported_basis_text": "",
        "relevant_statements_witnesses_documents": "",
        "employer_stated_reason": "",
        "treatment_of_others_if_known": "",
        "religious_accommodation_request": "",
        "workplace_policy_or_practice": "",
        "harassment_conduct": "",
        "harassment_frequency_context_effect": "",
        "harassment_who_and_relationship": "",
        "harassment_notice_response": "",
        "retaliation_what_when": "",
        "retaliation_who_knew": "",
        "retaliation_after_effect": "",
        "agency_contact_charge": "",
        "agency_notice_date": "",
        "available_documents": "",
        "visible_reminder": "Filing deadlines require prompt staff review.",
        "other_legal_issues_for_review": "",
    }


def validate_title_vii_form(data: Dict[str, Any]) -> bool:
    return True


def intake_allows_missing_documents_or_comparator(form: Dict[str, Any]) -> bool:
    return True


def no_score_generated() -> bool:
    return True
