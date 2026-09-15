# Title VII intake field rationale

Review date: 2026-09-15

This document maps the draft intake fields in the milestone 1 app to relevant official sources. It is a software design and research aid, not a statement of current controlling law. The app is intentionally limited to synthetic examples and does not calculate deadlines or legal conclusions.

## 1. Working relationship and coverage

This section captures facts relevant to whether the worker is a current or former employee, applicant, or worker with an uncertain relationship, and whether the matter is within Title VII coverage. The fields are designed for staff review and intake triage, not automated eligibility decisions.

- Applicant, current worker, former worker, or unknown: intended to capture the worker's relationship to the employer and whether the intake record is complete.
- Entities involved, including staffing agency or intermediary: relevant to whether a staffing agency, labor intermediary, or other entity may be involved in the work relationship.
- Who hires, pays, assigns work, supervises, and can end the relationship: connected to the threshold issue of who controls the work relationship and relevant employer relationships.
- Scheduling, equipment, helpers, payment, expenses, duration, outside work, and relevant contract terms: these are practical facts used to assess an intake matter without treating them as a legal conclusion.
- Work location and employer type: helps identify the workplace context and relevant employer category.
- Approximate employer size, source of estimate, and uncertainty: a staff triage aid, not a legal requirement.

Official source:
- EEOC, Section 2: Threshold Issues, https://www.eeoc.gov/laws/guidance/section-2-threshold-issues

## 2. Alleged discrimination

This section records worker descriptions of what happened, the basis alleged, and the context of the alleged treatment. It is deliberately optional and separate from automated legal assessment.

- What happened and what changed in the worker's employment: preserves the reported sequence and context without presuming the legal conclusion.
- Dates or approximate dates; preserve date uncertainty: a legal intake issue, but this workflow stores uncertainty instead of converting it to a precise claim.
- People involved and their roles: helps track witnesses, decision-makers, and other participants.
- Why the worker believes the treatment was discriminatory: preserves the worker's account without treating it as proven.
- Worker-reported possible basis: race, color, religion, sex, national origin, unsure, or not provided: the app allows multiple selections and optional explanatory text and does not infer sensitive traits from names or writing.
- Relevant statements, witnesses, documents, employer's stated reason, and treatment of others if known: these are facts for review and comparison.
- Possible religious accommodation request and response, if relevant: relevant to Title VII and accommodation contexts, but not required for every intake.
- Workplace policy or practice the worker identifies: preserves context without assuming a formal practice is proven.
- Applicant/failure-to-hire path: records the position, advertised and applicant qualifications, application and rejection dates, hiring stages, relevant statements, employer's stated reason, and why discrimination is suspected. These are allegations and intake facts, not an automated determination.
- Proposed role type: records whether the proposed role was employee, contractor, or unknown. For an applicant who never performed the work, proposed conditions are kept separate from actual work experience.
- Applicant evidence sources: job advertisements, applications, interview notes, and recruitment or rejection messages are available as source types. A contract, comparator, prior work history with the employer, or document is not required to continue intake.

Official source:
- Title VII of the Civil Rights Act of 1964, https://www.eeoc.gov/statutes/title-vii-civil-rights-act-1964
- EEOC guidance on threshold issues, https://www.eeoc.gov/laws/guidance/section-2-threshold-issues
- EEOC, Prohibited Employment Policies/Practices, https://www.eeoc.gov/prohibited-employment-policiespractices

## 3. Harassment follow-up, when relevant

These fields track the factual context for a possible harassment matter.

- Specific conduct, frequency, context, and effect on work
- Who engaged in it and their relationship to the organization
- Whether anyone was notified, when, and how the organization responded

Official source:
- EEOC, Harassment, https://www.eeoc.gov/harassment

## 4. Retaliation follow-up, when relevant

These fields capture the factual sequence for possible retaliation claims.

- What the worker reported, opposed, or participated in, and when
- Who knew about it
- What happened afterward and when

Official source:
- EEOC, Retaliation, https://www.eeoc.gov/retaliation

## 5. Procedural information

These fields summarize contact with agencies and available documents without supplying legal advice or deadline calculations.

- Any EEOC or state agency contact or charge and its date
- Any agency notice, date received, and available document
- Filing deadlines require prompt staff review

Official source:
- EEOC, Time Limits for Filing a Charge, https://www.eeoc.gov/time-limits-filing-charge

## 6. Software design choices

This prototype intentionally does not:

- calculate deadlines or determine lateness
- derive a case rejection or employee-indicator score
- infer sensitive characteristics from names or writing
- replace legal review with a rule engine
- claim a validated model or external AI analysis

The software therefore keeps legal conclusions out of automation and leaves judgment to staff review and separate legal analysis.

## 7. Applicant and failure-to-hire design boundary

The applicant path is a separate intake branch within the same evidence-review and export workflow. A fictional applicant example is provided for testing. The app preserves unknown and approximate dates, does not require a contract, comparator, work history with the employer, or documentary evidence, and does not infer discrimination, coverage, deadlines, or likelihood of success. The prediction panel remains unavailable; a future misclassification model must not score general failure-to-hire discrimination matters.
