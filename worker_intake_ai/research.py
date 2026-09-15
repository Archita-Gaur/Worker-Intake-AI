"""Manual legal-research records with an intentionally unavailable live provider.

This module stores research as staff-reviewed data. It does not invent authorities,
quotes, holdings, or recommendations.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlparse

ISSUE_OPTIONS = (
    "Employee status",
    "Coverage / relationship",
    "Discrimination merits",
    "Harassment",
    "Retaliation",
    "Failure to hire",
    "Other",
)
SEARCH_SCOPES = ("Target jurisdiction", "Target plus persuasive elsewhere", "All available")
COURT_LEVELS = ("Any", "Trial", "Appellate", "Highest court", "Administrative")
TREATMENT_STATES = (
    "Not checked",
    "Checked with limitations",
    "Adverse treatment identified",
)
REVIEWER_STATUSES = ("Unreviewed", "Reviewed", "Rejected")
DOCUMENT_TYPES = ("Judicial opinion", "Party brief", "Statute", "Guidance")
VERIFICATION_STATES = ("Not checked", "Unchecked", "Identity verified", "Current law verified", "Rejected")


class LiveSearchProvider(Protocol):
    """Small future-provider seam; implementations return provider records only."""

    def search(self, query: str, scope: str = "Target jurisdiction") -> Sequence[Mapping[str, Any]]:
        ...


class UnavailableLiveSearchProvider:
    """Explicitly unavailable until a reviewed provider integration is added."""

    def search(self, query: str, scope: str = "Target jurisdiction") -> Sequence[Mapping[str, Any]]:
        raise RuntimeError("Live legal search is unavailable; enter and verify authorities manually.")


@dataclass(frozen=True)
class ResearchPlan:
    issue: str
    search_scope: str = "All"
    query: str = ""


def make_research_plan(
    issue: str,
    target_jurisdiction: str = "",
    court_level: str = "Any",
    decision_date_from: str = "",
    decision_date_to: str = "",
    fact_keywords: str = "",
    search_scope: str = "Target jurisdiction",
    query: str = "",
) -> dict[str, str]:
    if issue not in ISSUE_OPTIONS:
        raise ValueError("Select a supported research issue.")
    if search_scope not in SEARCH_SCOPES:
        raise ValueError("Select a supported search scope.")
    if court_level not in COURT_LEVELS:
        raise ValueError("Select a supported court level.")
    return {
        "issue": issue,
        "target_jurisdiction": target_jurisdiction.strip(),
        "jurisdictions_searched": search_scope,
        "court_level": court_level,
        "decision_date_from": decision_date_from.strip(),
        "decision_date_to": decision_date_to.strip(),
        "fact_keywords": fact_keywords.strip(),
        "search_scope": search_scope,
        "query": query.strip(),
    }


def make_authority_record(
    *,
    authority_id: str = "",
    citation: str = "",
    title: str = "",
    court: str = "",
    year: str = "",
    decision_date: str = "",
    url: str = "",
    document_type: str = "Judicial opinion",
    relevant_passage: str = "",
    pinpoint_location: str = "",
    issue_addressed: str = "",
    procedural_posture: str = "",
    disposition: str = "",
    possible_relevance: str = "",
    factual_differences: str = "",
    linked_finding_ids: Sequence[str] = (),
    reviewer_status: str = "Unreviewed",
    reviewer_notes: str = "",
    source_identity_verified: str = "Not checked",
    passage_checked: str = "Not checked",
    subsequent_treatment: str = "Not checked",
    treatment_check_source: str = "",
    treatment_check_date: str = "",
    treatment_check_reviewer: str = "",
    treatment_check_notes: str = "",
    proposition: str = "",
    holding: str = "",
    party_arguments: str = "",
    citation_verification: str = "Unchecked",
    current_law_verification: str = "Unchecked",
    is_fictional: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    """Create a manual record; arguments and holdings remain separate fields."""
    if citation_verification not in VERIFICATION_STATES or current_law_verification not in VERIFICATION_STATES:
        raise ValueError("Unknown verification state.")
    if document_type not in DOCUMENT_TYPES or reviewer_status not in REVIEWER_STATUSES:
        raise ValueError("Unknown authority record type or review status.")
    if source_identity_verified not in VERIFICATION_STATES or passage_checked not in VERIFICATION_STATES:
        raise ValueError("Unknown source verification state.")
    if subsequent_treatment not in TREATMENT_STATES:
        raise ValueError("Unknown subsequent treatment state.")
    citation, title, court, year, url = (str(value or "").strip() for value in (citation, title, court, year, url))
    proposition, holding, party_arguments, notes = (
        str(value or "").strip() for value in (proposition, holding, party_arguments, notes)
    )
    if url and urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("Authority links must use http or https.")
    return {
        "authority_id": authority_id or str(uuid.uuid4()),
        "citation": citation,
        "title": title,
        "court": court,
        "year": year,
        "decision_date": str(decision_date or "").strip(),
        "url": url,
        "document_type": document_type,
        "relevant_passage": str(relevant_passage or "").strip(),
        "pinpoint_location": str(pinpoint_location or "").strip(),
        "issue_addressed": str(issue_addressed or "").strip(),
        "procedural_posture": str(procedural_posture or "").strip(),
        "disposition": str(disposition or "").strip(),
        "possible_relevance": str(possible_relevance or "").strip(),
        "factual_differences": str(factual_differences or "").strip(),
        "linked_finding_ids": list(linked_finding_ids),
        "reviewer_status": reviewer_status,
        "reviewer_notes": str(reviewer_notes or "").strip(),
        "source_identity_verified": source_identity_verified,
        "passage_checked": passage_checked,
        "subsequent_treatment": subsequent_treatment,
        "treatment_check_source": str(treatment_check_source or "").strip(),
        "treatment_check_date": str(treatment_check_date or "").strip(),
        "treatment_check_reviewer": str(treatment_check_reviewer or "").strip(),
        "treatment_check_notes": str(treatment_check_notes or "").strip(),
        "proposition": proposition,
        "holding": holding,
        "party_arguments": party_arguments,
        "citation_verification": citation_verification,
        "current_law_verification": current_law_verification,
        "is_fictional": bool(is_fictional),
        "notes": notes,
    }


def normalize_authority_record(record: Mapping[str, Any]) -> dict[str, Any]:
    defaults = {
        "document_type": "Judicial opinion",
        "reviewer_status": "Unreviewed",
        "source_identity_verified": "Not checked",
        "passage_checked": "Not checked",
        "subsequent_treatment": "Not checked",
        "citation_verification": "Not checked",
        "current_law_verification": "Not checked",
        "linked_finding_ids": (),
    }
    defaults["authority_id"] = str(record.get("authority_id") or uuid.uuid4())
    values = make_authority_record(**{key: record.get(key, defaults.get(key, "")) for key in (
        "authority_id",
        "citation", "title", "court", "year", "url", "proposition", "holding",
        "party_arguments", "citation_verification", "current_law_verification",
        "is_fictional", "notes", "decision_date", "document_type",
        "relevant_passage", "pinpoint_location", "issue_addressed",
        "procedural_posture", "disposition", "possible_relevance",
        "factual_differences", "linked_finding_ids", "reviewer_status",
        "reviewer_notes", "source_identity_verified", "passage_checked",
        "subsequent_treatment", "treatment_check_source", "treatment_check_date",
        "treatment_check_reviewer", "treatment_check_notes",
    )})
    # A fictional record must be visibly labeled wherever it is rendered/exported.
    if values["is_fictional"] and values["title"] and not values["title"].startswith("[Fictional]"):
        values["title"] = "[Fictional] " + values["title"]
    return values


def normalize_research(research: Mapping[str, Any] | None) -> dict[str, Any]:
    research = research or {}
    plan = research.get("plan") or make_research_plan("Other")
    authorities = [normalize_authority_record(item) for item in research.get("authorities", [])]
    arguments = []
    for argument in research.get("argument_examples", []):
        item = dict(argument)
        item["fictional"] = bool(
            item.get("fictional", False)
            or "fictional" in str(item.get("label", "")).lower()
        )
        item["label"] = item.get("label") or (
            "Fictional example — not legal authority" if item["fictional"] else "Manual argument example"
        )
        arguments.append(item)
    return {
        "plan": plan,
        "authorities": authorities,
        "argument_examples": arguments,
        "research_issue": research.get("research_issue", plan.get("issue", "Other")),
    }


def export_research_json(research: Mapping[str, Any] | None) -> str:
    return json.dumps(normalize_research(research), indent=2, ensure_ascii=False)


def export_research_markdown(research: Mapping[str, Any] | None) -> str:
    data = normalize_research(research)
    plan = data["plan"]
    lines = [
        "## Authorities and arguments",
        "",
        f"- Issue: {plan.get('issue', '')}",
        f"- Search scope: {plan.get('search_scope', '')}",
        f"- Query: {plan.get('query', '')}",
        "- Live search: unavailable; authorities below are manual records.",
        "",
    ]
    for index, authority in enumerate(data["authorities"], 1):
        label = authority["title"] or authority["citation"] or f"Authority {index}"
        lines.extend([
            f"### {label}",
            f"- Citation: {authority['citation']}",
            f"- Link: {authority['url'] or 'Not provided'}",
            f"- Document type: {authority['document_type']}",
            f"- Passage/pinpoint: {authority['relevant_passage']} ({authority['pinpoint_location']})",
            f"- Issue: {authority['issue_addressed']}",
            f"- Posture/disposition: {authority['procedural_posture']} / {authority['disposition']}",
            f"- Possible relevance: {authority['possible_relevance']}",
            f"- Factual/procedural differences: {authority['factual_differences']}",
            f"- Linked finding IDs: {', '.join(authority['linked_finding_ids']) or 'None'}",
            f"- Proposition: {authority['proposition']}",
            f"- Holding: {authority['holding']}",
            f"- Party arguments (not holdings): {authority['party_arguments']}",
            f"- Citation verification: {authority['citation_verification']}",
            f"- Source identity verified: {authority['source_identity_verified']}",
            f"- Passage checked: {authority['passage_checked']}",
            f"- Subsequent treatment: {authority['subsequent_treatment']}",
            f"- Treatment check: {authority['treatment_check_source']} / {authority['treatment_check_date']} / {authority['treatment_check_reviewer']}",
            f"- Reviewer status/notes: {authority['reviewer_status']} / {authority['reviewer_notes']}",
            "",
        ])
    if data["argument_examples"]:
        lines.append("### Fictional argument examples (not real cases or quotes)")
        for argument in data["argument_examples"]:
            lines.append(
                f"- {argument.get('label')}: {argument.get('text', '')} "
                f"(made by: {argument.get('made_by', 'Not provided')}; "
                f"linked authority/docket: {argument.get('linked_authority_or_docket', 'Not provided')}; "
                f"court addressed: {argument.get('court_addressed', 'Unknown')})"
            )
    return "\n".join(lines)
