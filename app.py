from __future__ import annotations

import copy
import streamlit as st

from worker_intake_ai.logic import (
    INFORMATION_STATUSES,
    REVIEW_STATUSES,
    SOURCE_TYPES,
    ensure_review_row,
    evaluate_quote_validation_status,
    export_review_json,
    export_review_markdown,
    extract_text_from_file,
    extract_document_pages,
    get_fixture_findings,
    get_source_text_for_row,
    generate_title_vii_blank_form,
    make_finding_id,
    make_unique_finding_id,
    make_source_id,
    parse_loaded_applicant_sample,
    parse_loaded_sample,
    prediction_status,
    record_edit_history,
    update_finding,
    validate_source,
)
from worker_intake_ai.research import (
    COURT_LEVELS,
    DOCUMENT_TYPES,
    ISSUE_OPTIONS,
    REVIEWER_STATUSES,
    SEARCH_SCOPES,
    TREATMENT_STATES,
    VERIFICATION_STATES,
    UnavailableLiveSearchProvider,
    make_authority_record,
    make_research_plan,
)


def _empty_row() -> dict:
    return {
        "finding_id": "",
        "topic": "",
        "field": "",
        "source_type": "Unknown",
        "creation_method": "manual",
        "exact_quote": "",
        "source_location": "",
        "interpretation": "",
        "information_status": "Unknown",
        "review_status": "Unreviewed",
        "follow_up_question": "",
        "evidence_to_request": "",
        "quote_validation_status": "Not checked",
        "migration_note": None,
        "legacy_original_value": None,
        "edit_history": [],
    }


def _ensure_rows(rows):
    prepared = []
    for row in rows:
        prepared_row = ensure_review_row(row)
        quote_text = prepared_row.get("exact_quote", "")
        source_text = get_source_text_for_row(
            prepared_row,
            st.session_state.get("contract_text", ""),
            st.session_state.get("worker_notes", ""),
            st.session_state.get("applicant_notes", ""),
        )
        prepared_row.update(
            validate_source(
                prepared_row,
                source_text,
                st.session_state.get("contract_pages", [])
                if prepared_row.get("source_type") == "Contract"
                else [],
            )
        )
        prepared_row["source_id"] = prepared_row.get("source_id") or make_source_id(
            prepared_row.get("source_type", "Unknown"), prepared_row.get("source_name", "")
        )
        prepared.append(prepared_row)
    return prepared


def _sync_detail_widget_state(row):
    finding_id = row.get("finding_id")
    if not finding_id:
        return
    values = {
        f"detail_topic_{finding_id}": row.get("topic", ""),
        f"detail_source_{finding_id}": row.get("source_type", "Unknown"),
        f"detail_quote_{finding_id}": row.get("exact_quote", ""),
        f"detail_location_{finding_id}": row.get("source_location", ""),
        f"detail_interpretation_{finding_id}": row.get("interpretation", ""),
        f"detail_info_{finding_id}": row.get("information_status", "Unknown"),
        f"detail_review_{finding_id}": row.get("review_status", "Unreviewed"),
        f"detail_followup_{finding_id}": row.get("follow_up_question", ""),
        f"detail_evidence_{finding_id}": row.get("evidence_to_request", ""),
        f"detail_reviewer_{finding_id}": row.get("reviewer_identifier", ""),
    }
    for key, value in values.items():
        st.session_state[key] = value


def load_example_into_session() -> None:
    sample = parse_loaded_sample()
    st.session_state["contract_text"] = sample["contract_text"]
    st.session_state["worker_notes"] = sample["worker_notes"]
    st.session_state["applicant_notes"] = ""
    st.session_state["title_vii_intake"] = generate_title_vii_blank_form()
    st.session_state["review_rows"] = _ensure_rows(get_fixture_findings(sample["contract_text"], sample["worker_notes"]))
    if st.session_state["review_rows"]:
        st.session_state["selected_finding_id"] = st.session_state["review_rows"][0]["finding_id"]

def load_applicant_example_into_session() -> None:
    sample = parse_loaded_applicant_sample()
    st.session_state["contract_text"] = sample["contract_text"]
    st.session_state["worker_notes"] = sample["worker_notes"]
    st.session_state["applicant_notes"] = sample["applicant_notes"]
    st.session_state["title_vii_intake"] = generate_title_vii_blank_form()
    st.session_state["title_vii_intake"].update(
        {
            "applicant_status": "Applicant",
            "proposed_role_type": "Employee",
            "applicant_position": "Warehouse coordinator",
            "advertised_qualifications": "Two years of scheduling experience.",
            "applicant_qualifications": "Three years coordinating deliveries.",
            "application_date": "2026-08-03",
            "hiring_stages": "Application, phone screen, final interview.",
            "applicant_relevant_statements": "The team wants someone who will fit the existing culture.",
            "rejection_date": "Approximately 2026-08-14",
            "applicant_employer_stated_reason": "Another candidate was selected.",
            "why_applicant_suspects_discrimination": "Applicant wants staff to review whether the stated reason and interview statements relate to the reported basis.",
        }
    )
    st.session_state["review_rows"] = _ensure_rows(
        get_fixture_findings(sample["contract_text"], sample["worker_notes"], sample["applicant_notes"])
    )
    if st.session_state["review_rows"]:
        st.session_state["selected_finding_id"] = st.session_state["review_rows"][0]["finding_id"]


def reset_session() -> None:
    for key in [
        "contract_text",
        "worker_notes",
        "applicant_notes",
        "review_rows",
        "contract_file",
        "contract_pages",
        "selected_finding_id",
        "title_vii_intake",
        "research",
        "authority_saved_once",
    ]:
        st.session_state.pop(key, None)


def add_manual_row() -> None:
    rows = st.session_state.get("review_rows", [])
    new_row = _empty_row()
    new_row["finding_id"] = make_unique_finding_id()
    rows.append(new_row)
    st.session_state["review_rows"] = _ensure_rows(rows)
    st.session_state["selected_finding_id"] = new_row["finding_id"]


st.set_page_config(page_title="Worker Intake AI", layout="wide")

if "contract_text" not in st.session_state:
    st.session_state["contract_text"] = ""
if "worker_notes" not in st.session_state:
    st.session_state["worker_notes"] = ""
if "applicant_notes" not in st.session_state:
    st.session_state["applicant_notes"] = ""
if "review_rows" not in st.session_state:
    st.session_state["review_rows"] = []
if "title_vii_intake" not in st.session_state:
    st.session_state["title_vii_intake"] = generate_title_vii_blank_form()
if "selected_finding_id" not in st.session_state and st.session_state.get("review_rows"):
    st.session_state["selected_finding_id"] = st.session_state["review_rows"][0]["finding_id"]
if "research" not in st.session_state:
    st.session_state["research"] = {
        "plan": make_research_plan("Other"),
        "authorities": [],
        "argument_examples": [],
    }

st.title("Research prototype: synthetic examples only.")
st.caption("This is a local legal-aid intake review prototype. No real client data or external services are used.")

with st.sidebar:
    st.subheader("Session controls")
    st.button("Load included fictional example", on_click=load_example_into_session)
    st.button("Load fictional applicant example", on_click=load_applicant_example_into_session)
    st.button("Clear session", on_click=reset_session)
    st.markdown("- No uploads to external services.")
    st.markdown("- Session memory only; not a production privacy guarantee.")
    st.markdown("- Future extraction remains separate from historical prediction.")

st.write("The fixture provider is active only for the exact included synthetic sample. For arbitrary inputs, use manual review only and do not treat fixture findings as analysis of a new document.")

contract_file = st.file_uploader(
    "Upload contract (TXT or PDF)",
    type=["txt", "pdf"],
    help="Limits: 500000 bytes, 150 pages, 20000 extracted characters. OCR is not implemented.",
)

if contract_file is not None:
    try:
        contract_pages = extract_document_pages(contract_file.name, contract_file.getvalue())
        st.session_state["contract_pages"] = contract_pages
        st.session_state["contract_text"] = "\n".join(contract_pages)
    except ValueError as exc:
        st.error(str(exc))

st.subheader("Contract and worker account")
col1, col2 = st.columns(2)
with col1:
    st.text_area(
        "Contract text",
        key="contract_text",
        height=240,
        help="Preserve page or paragraph references and do not silently omit text.",
    )
with col2:
    st.text_area(
        "Worker account / intake notes",
        key="worker_notes",
        height=240,
        help="Separate the interview account from the contract wording.",
    )
st.text_area(
    "Applicant materials / recruitment notes",
    key="applicant_notes",
    height=160,
    help="Use this for job advertisements, applications, interview notes, or recruitment/rejection messages. It is especially relevant when the person never performed the proposed work.",
)

st.subheader("Review table")
rows = _ensure_rows(st.session_state.get("review_rows", []))
st.session_state["review_rows"] = rows

if rows:
    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "finding_id": row.get("finding_id", ""),
                "topic": row.get("topic") or row.get("field") or "",
                "source_type": row.get("source_type", "Unknown"),
                "exact_quote": row.get("exact_quote", ""),
                "source_location": row.get("source_location", ""),
                "interpretation": row.get("interpretation", ""),
                "information_status": row.get("information_status", "Unknown"),
                "review_status": row.get("review_status", "Unreviewed"),
            }
        )
    original_by_id = {row["finding_id"]: copy.deepcopy(row) for row in rows}
    table_changed_ids = set()
    edited_rows = st.data_editor(
        table_rows,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        key="main_review_table",
        column_config={
            "topic": st.column_config.TextColumn("Topic", required=False),
            "source_type": st.column_config.SelectboxColumn("Source type", options=SOURCE_TYPES, required=False),
            "exact_quote": st.column_config.TextColumn("Exact quote"),
            "source_location": st.column_config.TextColumn("Source location"),
            "interpretation": st.column_config.TextColumn("Interpretation"),
            "information_status": st.column_config.SelectboxColumn("Information status", options=INFORMATION_STATUSES, required=False),
            "review_status": st.column_config.SelectboxColumn("Review status", options=REVIEW_STATUSES, required=False),
        },
        disabled=["finding_id"],
    )
    for edited in edited_rows:
        finding_id = edited.get("finding_id")
        if finding_id not in original_by_id:
            continue
        changes = {key: edited.get(key, original_by_id[finding_id].get(key, "")) for key in (
            "topic", "source_type", "exact_quote", "source_location", "interpretation",
            "information_status", "review_status",
        )}
        changes["field"] = changes["topic"]
        if changes != {key: original_by_id[finding_id].get(key, "") for key in changes}:
            st.session_state["review_rows"] = update_finding(
                st.session_state["review_rows"], finding_id, changes,
                st.session_state.get("reviewer_identifier") or None,
            )
            table_changed_ids.add(finding_id)
            rows = _ensure_rows(st.session_state["review_rows"])
    st.session_state["review_rows"] = rows
    for row in rows:
        if row.get("finding_id") in table_changed_ids:
            _sync_detail_widget_state(row)
else:
    st.info("No findings yet. Add one to start a manual review.")

if st.button("Add review row"):
    add_manual_row()

if st.session_state.get("review_rows"):
    labels = [row.get("finding_id") for row in st.session_state["review_rows"]]
    display_labels = [
        f"{row.get('topic') or row.get('field') or 'Untitled'} — {row.get('source_type', 'Unknown')}"
        for row in st.session_state["review_rows"]
    ]
    current_id = st.session_state.get("selected_finding_id")
    current_index = labels.index(current_id) if current_id in labels else 0
    selected_id = st.selectbox(
        "Select finding (topic / source)",
        labels,
        index=current_index,
        key="finding_selector",
        format_func=lambda finding_id: display_labels[labels.index(finding_id)],
    )
    selected_index = labels.index(selected_id)
    selected_row = copy.deepcopy(st.session_state["review_rows"][selected_index])
    st.session_state["selected_finding_id"] = selected_id

    with st.expander("Selected finding details", expanded=True):
        topic = st.text_input("Topic", value=selected_row.get("topic", ""), key=f"detail_topic_{selected_id}")
        source_type = st.selectbox("Source type", SOURCE_TYPES, index=SOURCE_TYPES.index(selected_row.get("source_type", "Unknown")) if selected_row.get("source_type", "Unknown") in SOURCE_TYPES else SOURCE_TYPES.index("Unknown"), key=f"detail_source_{selected_id}")
        exact_quote = st.text_area("Exact quote", value=selected_row.get("exact_quote", ""), height=80, key=f"detail_quote_{selected_id}")
        source_location = st.text_input("Source location", value=selected_row.get("source_location", ""), key=f"detail_location_{selected_id}")
        interpretation = st.text_area("Interpretation", value=selected_row.get("interpretation", ""), height=110, key=f"detail_interpretation_{selected_id}")
        information_status = st.selectbox("Information status", INFORMATION_STATUSES, index=INFORMATION_STATUSES.index(selected_row.get("information_status", "Unknown")) if selected_row.get("information_status", "Unknown") in INFORMATION_STATUSES else 1, key=f"detail_info_{selected_id}")
        review_status = st.selectbox("Review status", REVIEW_STATUSES, index=REVIEW_STATUSES.index(selected_row.get("review_status", "Unreviewed")) if selected_row.get("review_status", "Unreviewed") in REVIEW_STATUSES else 0, key=f"detail_review_{selected_id}")
        follow_up_question = st.text_area("Follow-up question", value=selected_row.get("follow_up_question", ""), height=70, key=f"detail_followup_{selected_id}")
        evidence_to_request = st.text_area("Evidence to request", value=selected_row.get("evidence_to_request", ""), height=70, key=f"detail_evidence_{selected_id}")
        reviewer_identifier = st.text_input("Reviewer identifier (optional)", value=selected_row.get("reviewer_identifier", ""), key=f"detail_reviewer_{selected_id}")
        source_text = get_source_text_for_row(
            selected_row,
            st.session_state.get("contract_text", ""),
            st.session_state.get("worker_notes", ""),
            st.session_state.get("applicant_notes", ""),
        )
        changes = {
            "topic": topic, "field": topic, "source_type": source_type,
            "exact_quote": exact_quote, "source_location": source_location,
            "interpretation": interpretation, "information_status": information_status,
            "review_status": review_status, "follow_up_question": follow_up_question,
            "evidence_to_request": evidence_to_request,
            "reviewer_identifier": reviewer_identifier,
        }
        if any(selected_row.get(key) != value for key, value in changes.items()):
            st.session_state["review_rows"] = update_finding(
                st.session_state["review_rows"], selected_id, changes,
                reviewer_identifier or None,
            )

with st.expander("Completed Title VII intake answers", expanded=False):
    relationship_options = ["Applicant", "Current worker", "Former worker", "Unknown"]
    current_relationship = st.session_state["title_vii_intake"].get("applicant_status", "Unknown")
    st.session_state["title_vii_intake"]["applicant_status"] = st.selectbox(
        "Relationship to the employer",
        relationship_options,
        index=relationship_options.index(current_relationship) if current_relationship in relationship_options else 3,
        key="title_vii_relationship",
        help="Optional intake classification. Unknown is allowed and does not block continuation.",
    )
    if st.session_state["title_vii_intake"]["applicant_status"] == "Applicant":
        st.caption("Applicant path: proposed conditions describe the role the person sought; they are not actual work experience.")
        proposed_role_options = ["Employee", "Contractor", "Unknown"]
        proposed_role = st.session_state["title_vii_intake"].get("proposed_role_type", "Unknown")
        st.session_state["title_vii_intake"]["proposed_role_type"] = st.selectbox(
            "Proposed role type",
            proposed_role_options,
            index=proposed_role_options.index(proposed_role) if proposed_role in proposed_role_options else 2,
            key="title_vii_proposed_role_type",
        )
        applicant_fields = [
            ("applicant_position", "Position sought"),
            ("advertised_qualifications", "Advertised qualifications"),
            ("applicant_qualifications", "Applicant's qualifications"),
            ("application_date", "Application date or approximate date"),
            ("hiring_stages", "Hiring stages"),
            ("applicant_relevant_statements", "Relevant recruitment or interview statements"),
            ("rejection_date", "Rejection date or approximate date"),
            ("applicant_employer_stated_reason", "Employer's stated reason"),
            ("why_applicant_suspects_discrimination", "Why the applicant suspects discrimination"),
        ]
        for field_name, label in applicant_fields:
            st.session_state["title_vii_intake"][field_name] = st.text_area(
                label,
                value=st.session_state["title_vii_intake"].get(field_name, ""),
                key=f"title_vii_{field_name}",
            )
    st.session_state["title_vii_intake"]["work_relationship"] = st.text_area(
        "Work relationship and coverage",
        value=st.session_state["title_vii_intake"].get("work_relationship", ""),
        key="title_vii_work_relationship",
    )
    st.session_state["title_vii_intake"]["alleged_discrimination"] = st.text_area(
        "Alleged discrimination",
        value=st.session_state["title_vii_intake"].get("alleged_discrimination", ""),
        key="title_vii_alleged_discrimination",
    )
    st.session_state["title_vii_intake"]["agency_contact"] = st.text_area(
        "Agency contact or charge details",
        value=st.session_state["title_vii_intake"].get("agency_contact", ""),
        key="title_vii_agency_contact",
    )
    intake = st.session_state["title_vii_intake"]
    for field_name, label in [
        ("entities_involved", "Entities involved (including staffing agency)"),
        ("who_hires_pays_assigns_supervises_ends", "Who hires, pays, assigns, supervises, or can end the relationship"),
        ("scheduling", "Scheduling and work conditions"),
        ("equipment_helpers_payment_expenses", "Equipment, helpers, payment, and expenses"),
        ("work_location_and_employer_type", "Work location and employer type"),
        ("approximate_employer_size", "Approximate employer size"),
        ("estimate_source", "Source of employer-size estimate and uncertainty"),
        ("what_happened_and_what_changed", "What happened and what changed"),
        ("dates_or_approximate_dates", "Dates or approximate dates"),
        ("people_involved", "People involved and roles"),
        ("why_worker_believes_treatment_was_discriminatory", "Why the worker believes treatment was discriminatory"),
        ("relevant_statements_witnesses_documents", "Relevant statements, witnesses, and documents"),
        ("employer_stated_reason", "Employer's stated reason"),
        ("treatment_of_others_if_known", "Treatment of others, if known"),
        ("religious_accommodation_request", "Religious accommodation request and response"),
        ("workplace_policy_or_practice", "Workplace policy or practice"),
        ("harassment_conduct", "Harassment: specific conduct"),
        ("harassment_frequency_context_effect", "Harassment: frequency, context, and effect on work"),
        ("harassment_who_and_relationship", "Harassment: who engaged in it and relationship"),
        ("harassment_notice_response", "Harassment: notice, date, and response"),
        ("retaliation_protected_activity", "Retaliation: protected activity or report"),
        ("retaliation_what_when", "Retaliation: what happened and when"),
        ("retaliation_who_knew", "Retaliation: who knew"),
        ("retaliation_after_effect", "Retaliation: what happened afterward"),
        ("agency_contact_charge", "Agency contact or charge details"),
        ("agency_notice_date", "Agency notice and date received"),
        ("available_documents", "Available documents"),
    ]:
        intake[field_name] = st.text_area(
            label, value=intake.get(field_name, ""), key=f"title_vii_{field_name}"
        )
    basis_options = ["Race", "Color", "Religion", "Sex", "National origin", "Unsure", "Not provided"]
    intake["reported_basis"] = st.multiselect(
        "Worker-reported possible basis (select all that apply)",
        basis_options,
        default=intake.get("reported_basis", intake.get("worker_reported_basis", [])),
        key="title_vii_reported_basis",
    )
    intake["worker_reported_basis"] = intake["reported_basis"]
    intake["reported_basis_text"] = st.text_area(
        "Reported basis — optional explanation",
        value=intake.get("reported_basis_text", ""),
        key="title_vii_reported_basis_text",
    )
    intake["agency_contact_type"] = st.text_input(
        "Agency contact type", value=intake.get("agency_contact_type", ""), key="title_vii_agency_contact_type"
    )
    intake["agency_contact_date"] = st.text_input(
        "Agency contact date", value=intake.get("agency_contact_date", ""), key="title_vii_agency_contact_date"
    )
    intake["charge_number"] = st.text_input(
        "Charge number (if provided)", value=intake.get("charge_number", ""), key="title_vii_charge_number"
    )

st.caption("Missing is not 'no.' Retain source provenance and record corrections in the finding history.")

st.subheader("Extraction provider")
exp_provider = get_fixture_findings(
    st.session_state["contract_text"],
    st.session_state["worker_notes"],
    st.session_state["applicant_notes"],
)
if exp_provider:
    st.success("Fixture provider: exact sample match found. Review the supplied findings and correct any issues before export.")
else:
    st.info("Automated extraction is not connected for arbitrary inputs. Use the manual review table and preserve source provenance.")

st.subheader("Title VII intake prompts")
with st.expander("Working relationship and coverage", expanded=False):
    st.markdown(
        "- Applicant, current worker, former worker, or unknown\n"
        "- Entities involved, including staffing agency or intermediary\n"
        "- Who hires, pays, assigns work, supervises, and can end the relationship\n"
        "- Scheduling, equipment, helpers, payment, expenses, duration, outside work, and relevant contract terms\n"
        "- Work location and employer type\n"
        "- Approximate employer size, source of estimate, and uncertainty"
        "\n- For applicants: record proposed conditions separately from actual work experience; missing contract, comparator, work history, or documents do not block intake"
    )

with st.expander("Alleged discrimination", expanded=False):
    st.markdown(
        "- What happened and what changed in the worker's employment\n"
        "- Dates or approximate dates; preserve date uncertainty\n"
        "- People involved and their roles\n"
        "- Why the worker believes the treatment was discriminatory\n"
        "- Worker-reported possible basis: race, color, religion, sex, national origin, unsure, or not provided; allow multiple selections and optional explanatory text\n"
        "- Relevant statements, witnesses, documents, employer's stated reason, and treatment of others if known\n"
        "- Possible religious accommodation request and response, if relevant\n"
        "- Workplace policy or practice the worker identifies, if relevant"
        "\n- For applicants: position, advertised and applicant qualifications, application and rejection dates, hiring stages, relevant statements, employer's stated reason, and why discrimination is suspected"
        "\n- Applicant evidence sources may include job advertisements, applications, interview notes, and recruitment or rejection messages"
    )

with st.expander("Harassment follow-up, when relevant", expanded=False):
    st.markdown(
        "- Specific conduct, frequency, context, and effect on work\n"
        "- Who engaged in it and their relationship to the organization\n"
        "- Whether anyone was notified, when, and how the organization responded"
    )

with st.expander("Retaliation follow-up, when relevant", expanded=False):
    st.markdown(
        "- What the worker reported, opposed, or participated in, and when\n"
        "- Who knew about it\n"
        "- What happened afterward and when"
    )

with st.expander("Procedural information", expanded=False):
    st.markdown(
        "- Any EEOC or state agency contact or charge and its date\n"
        "- Any agency notice, date received, and available document\n"
        "- Filing deadlines require prompt staff review\n"
        "- No automatic deadline calculation or matter late determination"
    )

st.subheader("Authorities and arguments")
st.caption("Manual records only. Live legal search is unavailable; verify links and current law independently.")
research = st.session_state["research"]
plan = research["plan"]
plan["issue"] = st.selectbox("Research issue", ISSUE_OPTIONS, index=ISSUE_OPTIONS.index(plan.get("issue", "Other")), key="research_issue")
finding_options = ["No linked finding"] + [
    f"{row.get('topic') or row.get('field') or 'Untitled'} — {row.get('source_type', 'Unknown')} ({row['finding_id']})"
    for row in st.session_state.get("review_rows", [])
]
plan["linked_finding_id"] = st.selectbox("Link an existing intake finding (optional)", finding_options, key="research_finding")
plan["target_jurisdiction"] = st.text_input("Target jurisdiction/circuit", value=plan.get("target_jurisdiction", ""), key="research_jurisdiction")
plan["search_scope"] = st.selectbox("Jurisdictions searched", SEARCH_SCOPES, index=SEARCH_SCOPES.index(plan.get("search_scope", SEARCH_SCOPES[0])), key="research_scope")
plan["court_level"] = st.selectbox("Court level", COURT_LEVELS, index=COURT_LEVELS.index(plan.get("court_level", "Any")), key="research_court_level")
plan["decision_date_from"] = st.text_input("Decision date from (optional)", value=plan.get("decision_date_from", ""), key="research_date_from")
plan["decision_date_to"] = st.text_input("Decision date to (optional)", value=plan.get("decision_date_to", ""), key="research_date_to")
plan["fact_keywords"] = st.text_input("Optional fact keywords", value=plan.get("fact_keywords", ""), key="research_fact_keywords")
plan["query"] = st.text_input("Research issue / statute query", value=plan.get("query", ""), key="research_query")
try:
    UnavailableLiveSearchProvider().search(plan["query"], plan["search_scope"])
except RuntimeError as exc:
    st.info(str(exc))
with st.expander("Add manual authority", expanded=False):
    authority_title = st.text_input("Authority title or label", key="authority_title")
    authority_citation = st.text_input("Citation", key="authority_citation")
    authority_court = st.text_input("Court", key="authority_court")
    authority_date = st.text_input("Decision date", key="authority_date")
    authority_url = st.text_input("Link", key="authority_url")
    authority_type = st.selectbox("Document type", DOCUMENT_TYPES, key="authority_type")
    authority_passage = st.text_area("Relevant passage", key="authority_passage")
    authority_pinpoint = st.text_input("Pinpoint location", key="authority_pinpoint")
    authority_issue = st.text_input("Issue addressed", key="authority_issue")
    authority_posture = st.text_input("Procedural posture", key="authority_posture")
    authority_disposition = st.text_input("Disposition", key="authority_disposition")
    authority_relevance = st.text_area("Possible relevance", key="authority_relevance")
    authority_differences = st.text_area("Important factual/procedural differences", key="authority_differences")
    link_labels = ["None"] + [row["finding_id"] for row in st.session_state.get("review_rows", [])]
    authority_link = st.multiselect("Linked intake finding IDs", link_labels, key="authority_finding_ids")
    authority_review = st.selectbox("Reviewer status", REVIEWER_STATUSES, key="authority_review_status")
    authority_reviewer_notes = st.text_area("Reviewer notes", key="authority_reviewer_notes")
    authority_proposition = st.text_area("Proposition", key="authority_proposition")
    authority_holding = st.text_area("Holding (keep separate from party arguments)", key="authority_holding")
    authority_arguments = st.text_area("Party arguments (not holdings)", key="authority_arguments")
    fictional = st.checkbox("Fictional example (label required)", key="authority_fictional")
    citation_state = st.selectbox("Citation verification", VERIFICATION_STATES, key="authority_citation_state")
    source_verified = st.selectbox("Source identity verified", VERIFICATION_STATES, key="authority_source_verified")
    passage_checked = st.selectbox("Passage checked against source", VERIFICATION_STATES, key="authority_passage_checked")
    treatment_state = st.selectbox("Subsequent treatment", TREATMENT_STATES, key="authority_treatment")
    treatment_source = st.text_input("Treatment-check source", key="authority_treatment_source")
    treatment_date = st.text_input("Treatment-check date", key="authority_treatment_date")
    treatment_reviewer = st.text_input("Treatment-check reviewer", key="authority_treatment_reviewer")
    treatment_notes = st.text_area("Treatment-check notes", key="authority_treatment_notes")
    current_state = st.selectbox("Legacy current-law verification", VERIFICATION_STATES, key="authority_current_state")
    submitted = st.checkbox("Save authority record", key="authority_save")
    if submitted and not st.session_state.get("authority_saved_once"):
        try:
            research["authorities"].append(make_authority_record(
                title=authority_title, citation=authority_citation, url=authority_url,
                court=authority_court, decision_date=authority_date, document_type=authority_type,
                relevant_passage=authority_passage, pinpoint_location=authority_pinpoint,
                issue_addressed=authority_issue, procedural_posture=authority_posture,
                disposition=authority_disposition, possible_relevance=authority_relevance,
                factual_differences=authority_differences,
                linked_finding_ids=authority_link if "None" not in authority_link else [],
                reviewer_status=authority_review, reviewer_notes=authority_reviewer_notes,
                source_identity_verified=source_verified, passage_checked=passage_checked,
                subsequent_treatment=treatment_state, treatment_check_source=treatment_source,
                treatment_check_date=treatment_date, treatment_check_reviewer=treatment_reviewer,
                treatment_check_notes=treatment_notes,
                proposition=authority_proposition, holding=authority_holding,
                party_arguments=authority_arguments, is_fictional=fictional,
                citation_verification=citation_state, current_law_verification=current_state,
            ))
            st.session_state["authority_saved_once"] = True
            st.success("Manual authority saved.")
        except ValueError as exc:
            st.error(str(exc))
if research["authorities"]:
    st.dataframe([
        {
            "title": authority.get("title") or authority.get("citation"),
            "link": authority.get("url", ""),
            "citation verification": authority.get("citation_verification"),
            "current-law verification": authority.get("current_law_verification"),
        }
        for authority in research["authorities"]
    ], use_container_width=True, hide_index=True)
with st.expander("Add argument example", expanded=False):
    argument_text = st.text_area("Brief argument excerpt", key="research_argument_text")
    argument_maker = st.text_input("Who made the argument?", key="research_argument_maker")
    argument_authority = st.text_input("Linked authority or docket", key="research_argument_authority")
    argument_addressed = st.selectbox("Whether the court addressed it", ("Unknown", "Addressed", "Not addressed"), key="research_argument_addressed")
    if st.button("Save argument example", key="save_argument_example"):
        research["argument_examples"].append(
            {
                "label": "Manual argument example",
                "text": argument_text,
                "made_by": argument_maker,
                "linked_authority_or_docket": argument_authority,
                "court_addressed": argument_addressed,
                "fictional": False,
            }
        )
        st.success("Argument example saved as a research material, not a holding or recommendation.")

st.subheader("Prediction")
st.info(prediction_status())

st.subheader("Export")
markdown = export_review_markdown(st.session_state.get("review_rows", []), st.session_state.get("research"))
json_blob = export_review_json(
    st.session_state.get("review_rows", []),
    {
        "contract_text": st.session_state.get("contract_text", ""),
        "worker_notes": st.session_state.get("worker_notes", ""),
        "applicant_notes": st.session_state.get("applicant_notes", ""),
        "title_vii_intake": st.session_state.get("title_vii_intake", {}),
    },
    research=st.session_state.get("research"),
)

st.download_button("Export review as Markdown", markdown, file_name="worker_intake_review.md", mime="text/markdown")
st.download_button("Export review as JSON", json_blob, file_name="worker_intake_review.json", mime="application/json")

st.caption("No shell, browser, filesystem or external tool access is granted to any extraction model. This prototype does not infer race, gender, immigration status or other sensitive traits from names or language.")
