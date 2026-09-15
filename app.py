from __future__ import annotations

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
    get_fixture_findings,
    get_source_text_for_row,
    generate_title_vii_blank_form,
    make_finding_id,
    parse_loaded_applicant_sample,
    parse_loaded_sample,
    prediction_status,
    record_edit_history,
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
        prepared_row["quote_validation_status"] = evaluate_quote_validation_status(quote_text, source_text)
        if not prepared_row.get("finding_id"):
            prepared_row["finding_id"] = make_finding_id(prepared_row.get("topic", ""), prepared_row.get("source_type", "Unknown"), prepared_row.get("source_location", ""), prepared_row.get("exact_quote", ""))
        prepared.append(prepared_row)
    return prepared


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
        "selected_finding_id",
        "title_vii_intake",
    ]:
        st.session_state.pop(key, None)


def add_manual_row() -> None:
    rows = st.session_state.get("review_rows", [])
    new_row = _empty_row()
    new_row["finding_id"] = make_finding_id("New finding", "Unknown", "", "")
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
        st.session_state["contract_text"] = extract_text_from_file(contract_file.name, contract_file.getvalue())
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
    edited_rows = st.data_editor(
        table_rows,
        num_rows="dynamic",
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
    for index, row in enumerate(edited_rows):
        if index < len(rows):
            rows[index]["topic"] = row.get("topic", "")
            rows[index]["field"] = row.get("topic", "")
            rows[index]["source_type"] = row.get("source_type", "Unknown")
            rows[index]["exact_quote"] = row.get("exact_quote", "")
            rows[index]["source_location"] = row.get("source_location", "")
            rows[index]["interpretation"] = row.get("interpretation", "")
            rows[index]["information_status"] = row.get("information_status", "Unknown")
            rows[index]["review_status"] = row.get("review_status", "Unreviewed")
            rows[index]["quote_validation_status"] = evaluate_quote_validation_status(
                rows[index].get("exact_quote", ""),
                get_source_text_for_row(
                    rows[index],
                    st.session_state.get("contract_text", ""),
                    st.session_state.get("worker_notes", ""),
                    st.session_state.get("applicant_notes", ""),
                ),
            )
    st.session_state["review_rows"] = rows
else:
    st.info("No findings yet. Add one to start a manual review.")

if st.button("Add review row"):
    add_manual_row()

if st.session_state.get("review_rows"):
    labels = [row.get("finding_id") or f"row-{idx}" for idx, row in enumerate(st.session_state["review_rows"])]
    selected_id = st.session_state.get("selected_finding_id")
    if selected_id not in labels:
        selected_id = labels[0]
    selected_index = labels.index(selected_id)
    selected_row = st.session_state["review_rows"][selected_index]
    st.session_state["selected_finding_id"] = selected_id

    with st.expander("Selected finding details", expanded=True):
        selected_row["topic"] = st.text_input("Topic", value=selected_row.get("topic", ""), key=f"detail_topic_{selected_id}")
        selected_row["field"] = selected_row["topic"]
        selected_row["source_type"] = st.selectbox("Source type", SOURCE_TYPES, index=SOURCE_TYPES.index(selected_row.get("source_type", "Unknown")) if selected_row.get("source_type", "Unknown") in SOURCE_TYPES else SOURCE_TYPES.index("Unknown"), key=f"detail_source_{selected_id}")
        selected_row["exact_quote"] = st.text_area("Exact quote", value=selected_row.get("exact_quote", ""), height=80, key=f"detail_quote_{selected_id}")
        selected_row["source_location"] = st.text_input("Source location", value=selected_row.get("source_location", ""), key=f"detail_location_{selected_id}")
        selected_row["interpretation"] = st.text_area("Interpretation", value=selected_row.get("interpretation", ""), height=110, key=f"detail_interpretation_{selected_id}")
        selected_row["information_status"] = st.selectbox("Information status", INFORMATION_STATUSES, index=INFORMATION_STATUSES.index(selected_row.get("information_status", "Unknown")) if selected_row.get("information_status", "Unknown") in INFORMATION_STATUSES else 1, key=f"detail_info_{selected_id}")
        selected_row["review_status"] = st.selectbox("Review status", REVIEW_STATUSES, index=REVIEW_STATUSES.index(selected_row.get("review_status", "Unreviewed")) if selected_row.get("review_status", "Unreviewed") in REVIEW_STATUSES else 0, key=f"detail_review_{selected_id}")
        selected_row["follow_up_question"] = st.text_area("Follow-up question", value=selected_row.get("follow_up_question", ""), height=70, key=f"detail_followup_{selected_id}")
        selected_row["evidence_to_request"] = st.text_area("Evidence to request", value=selected_row.get("evidence_to_request", ""), height=70, key=f"detail_evidence_{selected_id}")
        selected_row["reviewer_identifier"] = st.text_input("Reviewer identifier (optional)", value=selected_row.get("reviewer_identifier", ""), key=f"detail_reviewer_{selected_id}")
        source_text = get_source_text_for_row(
            selected_row,
            st.session_state.get("contract_text", ""),
            st.session_state.get("worker_notes", ""),
            st.session_state.get("applicant_notes", ""),
        )
        selected_row["quote_validation_status"] = evaluate_quote_validation_status(selected_row.get("exact_quote", ""), source_text)
        selected_row["finding_id"] = selected_row.get("finding_id") or make_finding_id(selected_row.get("topic", ""), selected_row.get("source_type", "Unknown"), selected_row.get("source_location", ""), selected_row.get("exact_quote", ""))
        previous = dict(st.session_state["review_rows"][selected_index])
        st.session_state["review_rows"][selected_index] = selected_row
        if previous != selected_row:
            selected_row["edit_history"] = record_edit_history(
                previous,
                selected_row,
                selected_row.get("reviewer_identifier") or None,
                event_type="human_edit",
                actor_type="human",
            )
            st.session_state["review_rows"][selected_index] = selected_row

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

st.subheader("Prediction")
st.info(prediction_status())

st.subheader("Export")
markdown = export_review_markdown(st.session_state.get("review_rows", []))
json_blob = export_review_json(
    st.session_state.get("review_rows", []),
    {
        "contract_text": st.session_state.get("contract_text", ""),
        "worker_notes": st.session_state.get("worker_notes", ""),
        "applicant_notes": st.session_state.get("applicant_notes", ""),
        "title_vii_intake": st.session_state.get("title_vii_intake", {}),
    },
)

st.download_button("Export review as Markdown", markdown, file_name="worker_intake_review.md", mime="text/markdown")
st.download_button("Export review as JSON", json_blob, file_name="worker_intake_review.json", mime="application/json")

st.caption("No shell, browser, filesystem or external tool access is granted to any extraction model. This prototype does not infer race, gender, immigration status or other sensitive traits from names or language.")
