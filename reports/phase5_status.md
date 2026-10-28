# Phase 5 local preparation and native Tableau handoff

**Status: local SQL/CSV exports and XML workbook drafts are prepared and tested. Native Tableau authoring/acceptance is pending. Phase 6 has not started.**

## Completed local work

- Verified installed Tableau Public for Apple silicon **2026.3.0** from app metadata. No installation/update performed.
- Read the roadmap, business/KPI/architecture definitions, Phase 3 cleaning report and Phase 4 methods/findings/verification before implementation.
- Reused the approved source, accepted target-role cohort, geography, cleaning rules and database schema unchanged. Database semantic and byte checks remain valid.
- Created commented read-only SQL/Python exports, a field/grain/key/denominator/null dictionary and source/rule/query/file-hash manifest. No new job data or raw acquisition was performed.

| Export | Rows | Grain |
|---|---:|---|
| dashboard_metrics.csv | 128,678 | metric category in one geography/role slice |
| scope_catalog.csv | 118 | scope parameter value |
| role_catalog.csv | 5 | role parameter value |

Metric rows are aggregates across alternative selections, **not 128,678 job postings**. The accepted regional cohort remains 12,631 records.

- Generated `dashboard/bay_area_2023_DRAFT.twb` and `.twbx`: two dashboard definitions, ten worksheets and single-choice Scope/Role/geography-view controls. The package contains only the draft, aggregate CSV, attribution and Apache-2.0 license.
- The draft defines role counts/shares, inherited tags, city/county/community associations, explicit seniority, coverage, global classification audit and alphabetical skill counts. Skill comparisons require >=10 usable lists; missing lists are not negatives.
- Salary amounts/comparisons, posting/hiring trends and arrangement shares are disabled. Annual-field availability is separately labeled coverage only.

## Actual validation results

- **211 passed in 23.04s** across the full suite (13 new Phase 5 tests). Synthetic TEST_ONLY fixtures do not enter project findings.
- **138 direct SQL versus CSV controls matched across seven states**: default, DA, SF+DA, Santa Clara County, Stanford community, San Jose+ML sparse and Alameda+ML zero-result.
- All metric keys, numerator/denominator conditions, null/suppression behavior and UTF-8 numeric/text round trips validated; Phase 4 SQL/pandas reconciliation remains required before export.
- Repeated export content checksums match; deterministic draft/package generation is tested. No source/schema/cleaning/database change occurred.
- XML parses and package members/CSV hashes match the manifest. These checks **do not prove native Tableau opening, rendering, calculations or filter behavior**.

## Concrete blocker and remaining native steps

Desktop automation returned **"Computer Use permissions are not granted"**. The agent could not inspect/operate the Tableau window, save through Tableau, or capture native screenshots. No UI-permission workaround, publication or fake screenshot was used.

1. Open the local DRAFT package in installed Tableau Public.
2. Resolve the CSV/create a local extract if prompted. If XML is rejected, follow the complete CSV-based sheet/calculation recipe.
3. Check both dashboards, parameter behavior, counts/denominators, suppression, labels and layout against the reconciliation checklist.
4. Fill actual Tableau values (currently blank) and preserve discrepancies; save a separate local native workbook and capture real screenshots.

Native acceptance remains **NOT RUN**, not passed. The generated draft is unvalidated; the agent does not claim a finished, functioning Tableau dashboard.

## Files and reproducibility

- [Authoring, native checks and refresh guide](../docs/phase5_tableau_authoring.md)
- [Export dictionary](../docs/phase5_export_dictionary.md)
- [Expected versus actual checklist](phase5_reconciliation.csv)
- [Manifest](phase5_export_manifest.json), [test/verification record](phase5_verification.json), [workbook status](phase5_workbook_status.json)
- [Commented export SQL](../sql/004_phase5_exports.sql), [export script](../src/tableau_exports.py), [draft builder](../src/tableau_workbook.py)
- [Publication inventory](../docs/phase5_publication_review.md) and [screenshot handoff](../dashboard/screenshots/README.md)

Run `python -m src.tableau_exports` then `python -m src.tableau_workbook`. Filled manual Tableau actuals are protected from overwrite; archive them before regeneration. Packaged CSVs do not refresh when external files change; repeat native acceptance after refresh.

No publication, new job-data download, Git commit/push or Phase 6 work occurred. Packaged data/screenshots remain ignored by Git. A later public release needs license/attribution/embedded-data review and separate explicit approval.
