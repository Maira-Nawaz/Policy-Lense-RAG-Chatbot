"""
Generates the PolicyLens synthetic corpus: markdown policy documents with
metadata front-matter, plus a manifest.csv/manifest.json index.

Run: python3 generate_corpus.py
Output: ./corpus/*.md, ./corpus/manifest.json, ./corpus/manifest.csv
"""
import json
import csv
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "corpus")
os.makedirs(OUT_DIR, exist_ok=True)

# Each entry: id, area, jurisdiction, segment (nullable), status, effective_from,
# effective_to (nullable), supersedes (id, nullable), department, confidentiality,
# title, body (policy text)
DOCS = [

    # ---------------- REFUNDS ----------------
    dict(id="refunds_DE_enterprise_v1", area="refunds", jurisdiction="DE",
         segment="enterprise", status="superseded",
         effective_from="2022-01-01", effective_to="2024-12-31", supersedes=None,
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 Enterprise Customers (Germany) [SUPERSEDED]",
         body="""This policy governs refund eligibility for Enterprise-tier customers contracted in Germany.

Enterprise customers may request a full refund within 30 calendar days of invoice date, provided
the service has not been used beyond a limited evaluation threshold (10% of contracted usage).
Refund requests must be submitted in writing to finance-de@company.com and are processed within
14 business days. Partial-term cancellations are refunded on a pro-rata basis for unused months
remaining on the annual contract.

Note: this policy predates the 2025 contract terms update and should not be used for invoices
dated on or after 1 January 2025."""),

    dict(id="refunds_DE_enterprise_v2", area="refunds", jurisdiction="DE",
         segment="enterprise", status="current",
         effective_from="2025-01-01", effective_to=None,
         supersedes="refunds_DE_enterprise_v1",
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 Enterprise Customers (Germany)",
         body="""This policy governs refund eligibility for Enterprise-tier customers contracted in Germany,
effective for all invoices dated on or after 1 January 2025.

As Enterprise agreements are business-to-business (B2B) contracts, the statutory 14-day consumer
withdrawal right under German distance-selling law (Fernabsatzrecht) does not apply. Refunds for
Enterprise customers are governed solely by the commercial contract terms: a full refund is
available only within 14 calendar days of invoice date, and only if usage has not exceeded 5% of
contracted volume. After this window, no refunds are issued except pro-rata credit for unused
months on annual contracts terminated for cause. Requests must be submitted via the Enterprise
Success Portal, not email, and are processed within 10 business days."""),

    dict(id="refunds_DE_smb_v1", area="refunds", jurisdiction="DE",
         segment="smb", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 SMB / Consumer-Class Customers (Germany)",
         body="""This policy governs refund eligibility for SMB and sole-proprietor customers in Germany who
qualify as consumers under German distance-selling law.

Where the customer qualifies as a consumer (Verbraucher), the statutory 14-day withdrawal right
(Fernabsatzrecht, \u00a7355 BGB) applies regardless of usage: the customer may cancel and receive a
full refund within 14 calendar days of contract confirmation, with no deduction for usage during
that period unless the customer was clearly informed of loss of the withdrawal right upon
service commencement and explicitly consented. Refund requests should be sent to
support-de@company.com and are processed within 14 calendar days, in line with statutory
requirements."""),

    dict(id="refunds_US_enterprise_v1", area="refunds", jurisdiction="US",
         segment="enterprise", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 Enterprise Customers (United States)",
         body="""This policy governs refund eligibility for Enterprise-tier customers contracted in the United
States. There is no federal statutory cooling-off period for B2B software contracts, so refund
eligibility is governed entirely by contract terms.

Enterprise customers may request a full refund within 30 calendar days of the contract start
date under our standard money-back guarantee, regardless of usage level. After 30 days, no
refunds are issued for the current term; customers may instead request non-renewal for the
following term. Requests must be submitted to the assigned Customer Success Manager and are
processed within 15 business days."""),

    dict(id="refunds_US_smb_v1", area="refunds", jurisdiction="US",
         segment="smb", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 SMB Customers (United States)",
         body="""This policy governs refund eligibility for SMB customers contracted in the United States.

SMB customers on monthly plans may cancel at any time; the current month is non-refundable but no
further charges apply after cancellation. SMB customers on annual plans qualify for the standard
14-day money-back guarantee from initial purchase date. Some states (e.g. California) provide
additional automatic-renewal disclosure requirements; where applicable, customers who were not
properly notified of renewal may request a full refund of the renewal charge regardless of the
14-day window. Requests are submitted via the in-app billing portal and processed within 10
business days."""),

    dict(id="refunds_UK_smb_v1", area="refunds", jurisdiction="UK",
         segment="smb", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Refund Policy \u2014 SMB / Consumer-Class Customers (United Kingdom)",
         body="""This policy governs refund eligibility for SMB and sole-trader customers in the United Kingdom
who qualify as consumers under the Consumer Contracts (Information, Cancellation and Additional
Charges) Regulations 2013.

Qualifying consumer customers have a 14-calendar-day cancellation right from the day after the
contract is agreed, during which a full refund must be given, less a reasonable deduction for any
service already supplied at the customer's request. Requests should be submitted to
support-uk@company.com and are processed within 14 calendar days in line with statutory
requirements."""),

    # refunds_UK_enterprise: DELIBERATELY MISSING (gap case)

    # ---------------- DATA RETENTION ----------------
    dict(id="data_retention_DE_v1", area="data_retention", jurisdiction="DE",
         segment=None, status="current",
         effective_from="2023-06-01", effective_to=None, supersedes=None,
         department="Legal", confidentiality="internal",
         title="Data Retention Policy (Germany)",
         body="""This policy sets retention periods for customer and business data processed in connection with
German operations, in line with the GDPR and German commercial/tax law (HGB, AO).

Personal data collected for service delivery is retained only as long as necessary for the
purpose collected, and deleted or anonymised within 90 days of contract termination unless a
longer statutory retention period applies. Financial records (invoices, accounting documents)
must be retained for 10 years under \u00a7147 AO, regardless of customer deletion requests, and are
held in a restricted-access archive during that period. Support ticket data is retained for 24
months for quality and dispute-resolution purposes, then deleted."""),

    dict(id="data_retention_US_v1", area="data_retention", jurisdiction="US",
         segment=None, status="superseded",
         effective_from="2021-01-01", effective_to="2025-02-28", supersedes=None,
         department="Legal", confidentiality="internal",
         title="Data Retention Policy (United States) [SUPERSEDED]",
         body="""This policy sets retention periods for customer data processed in connection with US
operations.

Customer account data is retained for 7 years following account closure, to support historical
reporting and potential dispute resolution. Support ticket data is retained indefinitely for
quality-assurance training purposes.

Note: this policy was replaced effective 1 March 2025 to align with updated privacy commitments
and should not be used for retention decisions made on or after that date."""),

    dict(id="data_retention_US_v2", area="data_retention", jurisdiction="US",
         segment=None, status="current",
         effective_from="2025-03-01", effective_to=None,
         supersedes="data_retention_US_v1",
         department="Legal", confidentiality="internal",
         title="Data Retention Policy (United States)",
         body="""This policy sets retention periods for customer data processed in connection with US
operations, effective 1 March 2025.

Customer account data is now retained for 3 years following account closure, reduced from the
prior 7-year period, to align with updated privacy commitments and data-minimisation practice.
Support ticket data is retained for 24 months, no longer indefinitely. California residents may
additionally request earlier deletion of personal information under the CCPA/CPRA, subject to
standard verification and any applicable legal-hold exceptions; such requests are processed
within 45 days."""),

    dict(id="data_retention_UK_v1", area="data_retention", jurisdiction="UK",
         segment=None, status="current",
         effective_from="2023-06-01", effective_to=None, supersedes=None,
         department="Legal", confidentiality="internal",
         title="Data Retention Policy (United Kingdom)",
         body="""This policy sets retention periods for customer and business data processed in connection with
UK operations, in line with UK GDPR and the Data Protection Act 2018.

Personal data is retained only as long as necessary for the purpose collected and is deleted or
anonymised within 90 days of contract termination, unless a longer statutory retention period
applies. Financial records are retained for 6 years in line with HMRC record-keeping
requirements. Support ticket data is retained for 24 months, then deleted."""),

    # ---------------- PTO ----------------
    dict(id="pto_DE_fulltime_v1", area="pto", jurisdiction="DE",
         segment="full_time", status="current",
         effective_from="2022-01-01", effective_to=None, supersedes=None,
         department="HR", confidentiality="internal",
         title="Paid Time Off Policy \u2014 Full-Time Employees (Germany)",
         body="""This policy applies to full-time employees on German employment contracts.

The statutory minimum annual leave under the Bundesurlaubsgesetz (BUrlG) for a 5-day working week
is 20 working days. The company grants 28 working days of paid annual leave, exceeding the
statutory minimum. Public holidays are additional and vary by federal state (Bundesland).
Untaken leave may be carried over into Q1 of the following year only in exceptional
circumstances (e.g. approved long-term illness) and must otherwise be used within the calendar
year, consistent with German case law on leave forfeiture."""),

    # pto_DE_contractor: DELIBERATELY MISSING (gap case \u2014 contractors are governed by
    # individual service agreements, not a general PTO policy)

    dict(id="pto_US_fulltime_v1", area="pto", jurisdiction="US",
         segment="full_time", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="HR", confidentiality="internal",
         title="Paid Time Off Policy \u2014 Full-Time Employees (United States)",
         body="""This policy applies to full-time employees in the United States. There is no federal statutory
minimum paid leave entitlement in the US.

The company grants 15 days of paid time off per year for full-time employees, accrued monthly,
plus 9 designated company holidays. Unused PTO up to 5 days may be carried over into the
following year; amounts above that are forfeited unless state law requires payout (e.g.
California, which treats accrued PTO as earned wages and prohibits forfeiture \u2014 employees in
California instead have unused PTO paid out at termination)."""),

    # pto_US_contractor: DELIBERATELY MISSING (gap case)

    dict(id="pto_UK_fulltime_v1", area="pto", jurisdiction="UK",
         segment="full_time", status="superseded",
         effective_from="2021-01-01", effective_to="2024-12-31", supersedes=None,
         department="HR", confidentiality="internal",
         title="Paid Time Off Policy \u2014 Full-Time Employees (United Kingdom) [SUPERSEDED]",
         body="""This policy applies to full-time employees in the United Kingdom.

The company grants 25 days of paid annual leave plus 8 UK bank holidays, consistent with the
statutory minimum of 5.6 weeks under the Working Time Regulations 1998. Untaken leave may be
carried over up to 5 days into the following year with manager approval.

Note: this policy was replaced effective 1 January 2025 and should not be used for leave years
starting on or after that date."""),

    dict(id="pto_UK_fulltime_v2", area="pto", jurisdiction="UK",
         segment="full_time", status="current",
         effective_from="2025-01-01", effective_to=None,
         supersedes="pto_UK_fulltime_v1",
         department="HR", confidentiality="internal",
         title="Paid Time Off Policy \u2014 Full-Time Employees (United Kingdom)",
         body="""This policy applies to full-time employees in the United Kingdom, effective for leave years
starting on or after 1 January 2025.

The company grants 27 days of paid annual leave plus 8 UK bank holidays, an increase from the
prior 25-day entitlement, remaining above the statutory minimum of 5.6 weeks under the Working
Time Regulations 1998. Untaken leave may now be carried over up to 10 days into the following
year with manager approval, increased from the prior 5-day carry-over limit."""),

    dict(id="pto_UK_contractor_v1", area="pto", jurisdiction="UK",
         segment="contractor", status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="HR", confidentiality="internal",
         title="Paid Time Off Policy \u2014 Contractors (United Kingdom)",
         body="""This policy applies to contractors engaged in the United Kingdom via an umbrella company or
personal service company (PSC).

Contractors engaged via an umbrella company accrue statutory holiday pay (12.07% of hours worked)
in accordance with the Working Time Regulations 1998, administered and paid out by the umbrella
company, not directly by the company. Contractors engaged via a PSC on a business-to-business
basis are not entitled to company-provided PTO or holiday pay; time off is scheduled directly
with the engaging manager and does not affect invoiced fees."""),

    # ---------------- EXPENSE REIMBURSEMENT ----------------
    dict(id="expense_DE_v1", area="expense_reimbursement", jurisdiction="DE",
         segment=None, status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Expense Reimbursement Policy (Germany)",
         body="""This policy applies to employees and contractors submitting business expenses incurred in
Germany.

Expenses must be submitted within 6 months of the expense date to be eligible for reimbursement.
Original itemised receipts showing VAT (Umsatzsteuer) are required for all claims over \u20ac20, as
VAT-compliant receipts are necessary for the company's input tax deduction (Vorsteuerabzug).
Reimbursement is processed via monthly payroll run. Per-diem meal allowances follow the official
German Spesensatz rates published annually by the Federal Ministry of Finance."""),

    dict(id="expense_US_v1", area="expense_reimbursement", jurisdiction="US",
         segment=None, status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Finance", confidentiality="internal",
         title="Expense Reimbursement Policy (United States)",
         body="""This policy applies to employees submitting business expenses incurred in the United States,
under an IRS-compliant accountable plan.

Expenses must be submitted with itemised receipts within 60 days of the expense date to qualify
for tax-free reimbursement under the accountable plan rules; late submissions may be reimbursed
at manager discretion but are treated as taxable income per IRS guidance. Per-diem rates for
meals and lodging follow the applicable GSA per-diem rate for the travel location. Reimbursement
is processed within 2 pay cycles of approval."""),

    dict(id="expense_UK_v1", area="expense_reimbursement", jurisdiction="UK",
         segment=None, status="superseded",
         effective_from="2021-01-01", effective_to="2023-12-31", supersedes=None,
         department="Finance", confidentiality="internal",
         title="Expense Reimbursement Policy (United Kingdom) [SUPERSEDED]",
         body="""This policy applies to employees submitting business expenses incurred in the United Kingdom.

Original paper receipts must be mailed to the Finance team within 90 days of the expense date.
Claims are processed manually and reimbursed via the following month's payroll run.

Note: this policy was replaced effective 1 January 2024 and should not be used for expenses
incurred on or after that date."""),

    dict(id="expense_UK_v2", area="expense_reimbursement", jurisdiction="UK",
         segment=None, status="current",
         effective_from="2024-01-01", effective_to=None,
         supersedes="expense_UK_v1",
         department="Finance", confidentiality="internal",
         title="Expense Reimbursement Policy (United Kingdom)",
         body="""This policy applies to employees submitting business expenses incurred in the United Kingdom,
effective 1 January 2024.

Receipts must now be submitted digitally via the expense app within 90 days of the expense date;
paper receipts mailed to Finance are no longer accepted. VAT-itemised receipts are required for
claims over \u00a325 to support input VAT reclaim. Claims are auto-approved under \u00a325 with a valid
receipt and reimbursed within 5 business days; claims over \u00a325 require manager approval."""),

    # ---------------- DATA PRIVACY (SAR handling) ----------------
    dict(id="data_privacy_DE_v1", area="data_privacy", jurisdiction="DE",
         segment=None, status="superseded",
         effective_from="2022-01-01", effective_to="2024-12-31", supersedes=None,
         department="Legal", confidentiality="internal",
         title="Data Subject Access Request Policy (Germany) [SUPERSEDED]",
         body="""This policy governs handling of data subject access requests (DSARs) from individuals in
Germany under the GDPR.

Requests may be submitted to any employee or to support-de@company.com and are logged manually
by the receiving team before being routed to Legal. The company aims to respond within the
statutory one-month period, extendable by two further months for complex requests.

Note: this intake process was replaced effective 1 January 2025 and should not be used for
requests received on or after that date."""),

    dict(id="data_privacy_DE_v2", area="data_privacy", jurisdiction="DE",
         segment=None, status="current",
         effective_from="2025-01-01", effective_to=None,
         supersedes="data_privacy_DE_v1",
         department="Legal", confidentiality="internal",
         title="Data Subject Access Request Policy (Germany)",
         body="""This policy governs handling of data subject access requests (DSARs) from individuals in
Germany under the GDPR, effective 1 January 2025.

All requests must now be submitted through the dedicated Privacy Request Portal rather than to
individual employees or a general support inbox, ensuring consistent logging and SLA tracking.
The statutory response period remains one month, extendable by two further months for complex
requests, with the extension requiring documented justification recorded in the portal."""),

    dict(id="data_privacy_US_v1", area="data_privacy", jurisdiction="US",
         segment=None, status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Legal", confidentiality="internal",
         title="Consumer Privacy Request Policy (United States)",
         body="""This policy governs handling of consumer privacy requests (access, deletion, correction) from
individuals in the United States, primarily under the CCPA/CPRA for California residents, with
equivalent handling extended company-wide for consistency.

Requests are submitted through the Privacy Request Portal and verified using a two-factor
identity check before processing. The company responds within 45 days, with one 45-day extension
permitted for complex requests provided the requester is notified of the extension within the
initial 45-day period."""),

    dict(id="data_privacy_UK_v1", area="data_privacy", jurisdiction="UK",
         segment=None, status="current",
         effective_from="2023-01-01", effective_to=None, supersedes=None,
         department="Legal", confidentiality="internal",
         title="Data Subject Access Request Policy (United Kingdom)",
         body="""This policy governs handling of data subject access requests (DSARs) from individuals in the
United Kingdom under UK GDPR and the Data Protection Act 2018.

Requests are submitted through the Privacy Request Portal. The company responds within one
calendar month, extendable by two further months for complex or numerous requests, consistent
with ICO guidance, with the requester notified of any extension and the reasons for it within
the initial one-month period."""),
]


def front_matter(d):
    lines = ["---"]
    lines.append(f'id: "{d["id"]}"')
    lines.append(f'title: "{d["title"]}"')
    lines.append(f'area: "{d["area"]}"')
    lines.append(f'jurisdiction: "{d["jurisdiction"]}"')
    lines.append(f'segment: {json.dumps(d["segment"])}')
    lines.append(f'status: "{d["status"]}"')
    lines.append(f'effective_from: "{d["effective_from"]}"')
    lines.append(f'effective_to: {json.dumps(d["effective_to"])}')
    lines.append(f'supersedes: {json.dumps(d["supersedes"])}')
    lines.append(f'department: "{d["department"]}"')
    lines.append(f'confidentiality: "{d["confidentiality"]}"')
    lines.append("---\n")
    return "\n".join(lines)


def main():
    manifest_rows = []
    for d in DOCS:
        md_path = os.path.join(OUT_DIR, f"{d['id']}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(front_matter(d))
            f.write(f"# {d['title']}\n\n")
            f.write(d["body"].strip() + "\n")

        manifest_rows.append({
            "id": d["id"],
            "title": d["title"],
            "area": d["area"],
            "jurisdiction": d["jurisdiction"],
            "segment": d["segment"] or "",
            "status": d["status"],
            "effective_from": d["effective_from"],
            "effective_to": d["effective_to"] or "",
            "supersedes": d["supersedes"] or "",
            "department": d["department"],
            "confidentiality": d["confidentiality"],
            "filename": f"{d['id']}.md",
        })

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_rows, f, indent=2)

    with open(os.path.join(OUT_DIR, "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)

    gaps = [
        {"area": "refunds", "jurisdiction": "UK", "segment": "enterprise",
         "reason": "No distinct UK enterprise refund policy document exists."},
        {"area": "pto", "jurisdiction": "DE", "segment": "contractor",
         "reason": "German contractors are governed by individual service agreements, not a general PTO policy."},
        {"area": "pto", "jurisdiction": "US", "segment": "contractor",
         "reason": "No US contractor PTO document exists."},
    ]
    with open(os.path.join(OUT_DIR, "known_gaps.json"), "w", encoding="utf-8") as f:
        json.dump(gaps, f, indent=2)

    print(f"Generated {len(DOCS)} documents.")
    print(f"  current: {sum(1 for d in DOCS if d['status']=='current')}")
    print(f"  superseded: {sum(1 for d in DOCS if d['status']=='superseded')}")
    print(f"Known deliberate gaps: {len(gaps)}")


if __name__ == "__main__":
    main()
