# Phase 5 Tableau authoring and acceptance guide

## Actual status

Installed locally: **Tableau Public for Apple silicon 2026.3.0**, bundle
`/Applications/Tableau Public (Apple silicon).app`. Version was read from its Info.plist.
No installation/update is needed for this task. Desktop automation returned
**"Computer Use permissions are not granted"**. No app authoring, native rendering,
filter interaction, native Save, or Tableau screenshot has been performed by the agent.

Completed locally: verified SQL exports/manifest, backend reconciliation controls,
a generated XML `.twb` draft and self-contained `.twbx` draft with attribution/license,
plus structural tests. **The drafts have not been accepted by the Tableau engine.**
Well-formed XML and passing Python tests do not prove that Tableau can open/render them.
Manual native acceptance remains part of Phase 5; Phase 6 is not authorized.

## Open the local draft

1. Launch the installed Tableau Public application from Applications.
2. Use **File > Open**, choosing `dashboard/bay_area_2023_DRAFT.twbx` in this repository.
   This package contains the aggregate CSV and license/attribution. It does not publish.
3. If Tableau requests a data connection, point to
   `data/processed/phase5/dashboard_metrics.csv`. The standalone `.twb` uses a relative
   reference to that file; opening the `.twbx` should use its packaged Data directory.
4. If the edition requires an extract, create/save it **locally** under
   `data/processed/phase5/`. Do not choose Save to Tableau Public or upload to solve an error.
5. Check both dashboard tabs: **Historical overview** and **Coverage and classification**.
   If the generated XML fails to load or a calculation is invalid, use the complete
   CSV-based authoring recipe below. Do not label the draft as verified until native
   checks pass. The draft is an aid, not a substitute for native Tableau validation.
6. After checking/revising the workbook in Tableau, **File > Save As** to a new local
   `dashboard/bay_area_2023_LOCAL.twbx`. Keep the generated DRAFT as the reproducible
   starting point; rebuilding it will overwrite DRAFT files only.

Tableau documents local saving in its [Public Edition local-save announcement](https://www.tableau.com/blog/local-file-save-tableau-desktop-public-edition)
and [Save Your Work guide](https://help.tableau.com/current/pro/desktop/en-us/save_savework.htm).
Packaged workbooks include copies of local sources and are no longer linked to the
original CSV. These official pages were checked during Phase 5 research on October 27, 2026.

## Build/recover directly from CSV if necessary

Connect **Text File** to `dashboard_metrics.csv` only. Do not join the scope/role catalogs
or join this aggregate source to job-skill/location tables. The long table supplies all
panels, with exactly one metric-category row after the required filters.

Confirm `numerator`, `denominator`, `category_order`, `comparison_allowed` are whole
numbers; `rate` is decimal; all identifiers/category/revision fields are strings. Null
rate stays null. Set default aggregation of denominator/rate to **Maximum**, not Sum.
Never display SUM(rate), COUNT(rows), AVG(subgroup percentages), grand totals or subtotals.

Create three **String/List parameters** (Data pane > Create Parameter):

| Parameter | Allowed values | Default / affected views |
|---|---|---|
| Scope | Add values from `scope_key` (catalog is the exact list) | All Bay Area; all analytical views |
| Role | All roles, Data Analyst, Data Engineer, Data Scientist, Machine Learning Engineer | All roles; all analytical views |
| Geography view | County, City, Community, County-only | City; Location associations only |

Show the controls on both dashboards. They are single-choice workbook parameters,
not ordinary multi-select dimension filters. Parameter changes must be used by the
calculated filters below. See Tableau's [parameter documentation](https://help.tableau.com/current/pro/desktop/en-us/parameters_create.htm).
No date, salary, arrangement, multi-city, skill-as-global-filter or seniority-global
filter is supported by this export design. Clicking marks can highlight; do not enable
"Use as Filter" or add cross-sheet filter actions that change denominators.

### Calculated fields and why they exist

**Selected slice** (Boolean; put on Filters = True on EVERY worksheet):

```tableau
[scope_key] = [Parameters].[Scope]
AND [role_selection] = [Parameters].[Role]
```

This retains one precomputed alternative. Without it, duplicated rollup alternatives
would be summed. In the calculation editor insert the corresponding parameter from
the Parameters list if Tableau displays its qualified name differently.

**Display rate** (aggregate; format Percentage with one decimal):

```tableau
IF MIN([comparison_allowed]) = 1 AND MAX([denominator]) > 0 THEN
    SUM([numerator]) / MAX([denominator])
END
```

Each mark must include category (and one panel/type) so numerator is one metric row.
MAX preserves the contextual denominator. Zero denominator or suppressed skill group
returns null, not 0%. It does not make cross-slice sums valid.

**Skill top twelve** (Boolean, skill percentage sheet only):

```tableau
[category_order] <= 12 AND [comparison_allowed] = 1
```

SQL ranks within the exact slice; do not use a Tableau global Top N filter that could
run before the selectors. Groups with <10 usable lists have no ranked percentage bars.

**Selected geography** (Boolean, location sheet only):

```tableau
[category_type] = [Parameters].[Geography view]
AND [category_order] <= 15
```

This chooses one location precision and its top 15 associations. City does not silently
include communities. An explicit Community view is needed for a community-only slice.

**Count and denominator** (aggregate text label):

```tableau
STR(SUM([numerator])) + " / " + STR(MAX([denominator])) +
IF MIN([comparison_allowed]) = 0 THEN " — comparison suppressed"
ELSEIF MAX([denominator]) = 0 THEN " — unavailable"
ELSE " (" + STR(ROUND(100*SUM([numerator])/MAX([denominator]),1)) + "%)"
END
```

**Skill coverage message** (aggregate text on the usable-tag coverage row):

```tableau
IF SUM([numerator]) < 10 THEN
    "Skill comparisons suppressed: fewer than 10 usable lists. n="
ELSE "Usable inherited lists: n="
END + STR(SUM([numerator])) + " / " + STR(MAX([denominator]))
```

This warning remains visible even when all percentage bars are suppressed.

### Worksheet recipe

All sheets require Selected slice=True and the specified `panel` filter. Use full labels,
readable fonts, zero-based count axes, one-decimal percent labels and counts in tooltips.
In every tooltip add `warning`, numerator/denominator and the historical-source caveat.
Do not interpret missing lists as absent skills or unknown seniority as entry level.

| Sheet | Additional filters | Rows | Columns / Marks |
|---|---|---|---|
| Selected records | panel=coverage; category=Selected records | none | Text: SUM(numerator) |
| Role records | panel=roles | category | Bar: SUM(numerator) |
| Role shares | panel=roles | category | Bar: Display rate; denominator remains all four roles in chosen geography |
| Inherited skill percentages | panel=skills; Skill top twelve=True | category | Bar: Display rate; tooltip n/usable n |
| Location associations | panel=geography; Selected geography=True | category | Bar: SUM(numerator); show small-group/non-additivity warning |
| Explicit seniority | panel=seniority | category | Bar: Display rate, retain unknown/conflicting, order by category_order |
| Data coverage | panel=coverage | category | Text: Count and denominator; annual field presence is not salary comparison |
| Classification audit | panel=classification | category | Text: Count and denominator; GLOBAL retained dataset, unaffected by selectors |
| Skill detail counts | panel=skills; **no Top N/rank filter** | category, alphabetically | Text: Count and denominator; preserve counts when comparison suppressed |
| Skill coverage warning | panel=coverage; category=Usable inherited tags | none | Text: Skill coverage message |

For comparative charts sort bars by descending SUM(numerator), with stable alphabetical
skill ties; the SQL top-12 membership is already selected. Keep Skill detail counts
alphabetical, especially when rates are suppressed. Do not sort sparse skill groups into
a demand ranking. The ten sheets are definitions in the generated draft, not proof of
successful native rendering.

### Dashboard layout

Use a fixed approximately 1440×1200 desktop canvas. Main view: historical title/limits,
three controls, selected-record KPI and skill-coverage warning; role counts/shares side
by side; skills/location associations side by side; seniority/coverage side by side;
source/limitations footer. Second view: global classification audit, coverage table and
scrollable alphabetical Skill detail counts. Fit widths and wrap long city/community
labels; inspect at normal zoom, without clipping or tiny text. Adjust native sizes if
the XML draft does not render well; the agent could not inspect Tableau visually.

Required visible text:

> 2023 Bay Area historical observed records. Not current market demand, actual hires,
> or verified unique vacancies. Source: Luke Barousse data_jobs (Apache-2.0), pinned
> historical release. Title-only accepted cohort; inherited skill tags; missing lists
> are not negatives. Geographic associations are non-additive. Salary amounts, hiring
> trends and arrangement shares are disabled.

Display ambiguous/unclassified/non-target counts as **global retained-data context**.
They are not part of the accepted role denominator. Do not suggest those audit counts
respond to filters when they deliberately do not. Include sample sizes and coverage;
the n=10 rule is a reporting threshold, not a reliability guarantee.

## Native acceptance checklist (still pending)

Open `reports/phase5_reconciliation.csv`. For each exact case/state, use parameter values
in the row, inspect the corresponding sheet/tooltip and fill **Tableau actual** columns.
Expected SQL and CSV columns are already verified backend values; do not replace them.
Counts/denominators must match exactly; compare underlying rates within 1e-10, or the
same one-decimal display rounding when only a rendered label is accessible. Clearly
record whether the comparison used underlying or displayed precision.

The seven cases cover default, DA role, SF+DA, Santa Clara County, Stanford community,
San Jose+ML sparse and Alameda+ML zero-result states. Check:

- Default selected n=12,631; skill usable n=11,101. DA selected n=4,829, usable n=4,093.
- DA role share stays 4,829/12,631 (38.2%), rather than becoming 100% under the Role selector.
- SF+DA selected n=1,233; usable n=1,113; SQL tag n=851 (76.5% of usable DA lists).
- San Jose+ML selected n=4; usable n=4: skill percentages/rankings suppressed while counts/warning remain.
- Zero accepted results show count 0 and unavailable rates, with no divide-by-zero/error.
- County, City and Community views respect the distinct precision labels and top-15 limit.
- Classification audit stays global: ambiguous 209, unclassified 3,103, non-target 280 (retained n=16,223).
- No grand totals across overlapping scopes, no physical joins, no hidden global filters,
  no unsupported salary/trend/arrangement chart, and no publication action.

Capture actual native screenshots listed in `dashboard/screenshots/README.md`. Save/reopen
locally and recheck defaults/filters. Set Tableau status to passed only after actual
native checks. Preserve any discrepancies with notes; do not change source/cleaning
rules or schema to force a match. The agent has not filled any Tableau actual value.

## Regenerate and refresh

```bash
source .venv/bin/activate
python -m src.tableau_exports
python -m src.tableau_workbook
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Completed manual actuals are protected: archive a filled reconciliation CSV before export
regeneration. If unchanged input/code produces different output hashes, investigate.
The exporter verifies the existing database byte/semantic identity before/after; no
acquisition or ETL rerun is needed. Raw acquisition integrity remains recorded Phase 3
evidence; the Phase 4 raw-read limitation is not bypassed by fetching new data.

The builder overwrites DRAFT files, not your separate LOCAL native workbook. A TWBX
contains a CSV copy, so external CSV updates do not refresh its embedded source. Build a
new DRAFT package, or replace/refresh the CSV/extract locally in your LOCAL workbook,
then repeat reconciliation and save/repackage. Preserve any native design changes and
update parameter lists if export scope values change. Refresh/republication is manual;
no automatic Public refresh or live SQLite connection is claimed.

## Publication remains prohibited in this task

The [Tableau Public FAQ](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm)
explains that published work is publicly accessible. Hiding worksheets/disabling downloads
is not a confidentiality control. Do not upload a workbook to work around local save or
connection errors. Review the [local publication inventory](phase5_publication_review.md),
license/attribution, all data/extract fields and hidden sheets first, then obtain separate
user approval for any GitHub/Tableau/public screenshot release. Phase 6 is not started.
