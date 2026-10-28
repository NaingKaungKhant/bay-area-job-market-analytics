# Phase 5 local package and future publication review

**No public release is authorized.** This is an inventory/review record, not legal
clearance or proof of native Tableau validation. Source approval for local use remains
the existing Luke dataset decision and Apache-2.0 publisher declaration. Upstream
collection rights were not independently verified; no employer text has been fetched.

## Checked in the generated local artifacts

- The package includes one generated `.twb`, one aggregate `dashboard_metrics.csv`,
  source attribution text and a copy of Apache-2.0. The packaging test uses an explicit
  four-member allowlist and checks CSV hashes against the export manifest.
- The CSV has only scope/role/panel/category labels, aggregate counts/denominators,
  conditional rates/suppression notes and source/rule revision identifiers.
- No original job titles, employer names, descriptions, contacts, salaries/currencies,
  original posting dates, arrangements or native posting IDs are included.
- The generated TWB has one CSV connection, ten defined worksheets and two dashboards,
  with no physical joins. There is no Hyper extract in the generated package. The
  draft builder does not add other hidden data sources/worksheets; native edits and
  any later extracts must be reviewed separately.
- Source attribution identifies Luke Barousse, the exact pinned release and that
  these are modified aggregates after project cleaning. Original source notices are
  preserved in project documentation. No separate source NOTICE was invented.
- Packaged workbooks/extracts, detail exports and screenshots remain ignored by Git.
  The text-only draft TWB contains paths/definitions/parameter labels, not CSV rows.
  Nothing was committed, pushed, emailed or uploaded by this task.

## Still required before a later public release

1. Complete native Tableau authoring/acceptance and inspect the actual saved LOCAL
   package, including every CSV/Hyper extract, unused field, hidden worksheet and
   packaged file. Generated-XML checks do not cover future native modifications.
2. Confirm the current source license/attribution obligations and the public output
   decision against `docs/data_attribution.md`. Aggregating public source records does
   not automatically confer unrelated redistribution rights or resolve upstream uncertainty.
3. Review low-count location/skill cells and the intended portfolio audience. Keep
   scope, historical date, conservative classification, missingness and unsupported
   metrics visible. Do not present the 2023 convenience dataset as the current market.
4. Review screenshots and packaged files as data-bearing artifacts. Hiding views or
   disabling workbook downloads does not make Tableau Public private.
5. Obtain explicit user approval for the exact public destination/artifacts. This
   task authorizes local work only; publishing a viz, workbook, CSV or GitHub update
   remains unapproved. No public link exists as a Phase 5 deliverable at this stage.

Official visibility guidance: [Tableau Public FAQ](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm),
checked October 27, 2026. Native authoring is pending because desktop automation
returned "Computer Use permissions are not granted".
