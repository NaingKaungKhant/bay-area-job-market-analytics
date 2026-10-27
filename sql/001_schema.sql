-- Phase 3: one retained historical source record per fact row, NOT a verified vacancy.
-- INTEGER surrogate keys simplify joins. Source revision + data-row ordinal supply
-- lineage because the publisher does not provide a native posting identifier.
PRAGMA foreign_keys = ON;
CREATE TABLE pipeline_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE collection_snapshots (
    snapshot_id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL, source_revision TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL, raw_row_count INTEGER NOT NULL CHECK(raw_row_count >= 0),
    acquired_at_utc TEXT NOT NULL, rule_version TEXT NOT NULL
);
-- A company is a normalized name label; equal names do not verify legal identity.
CREATE TABLE dim_companies (
    company_id INTEGER PRIMARY KEY, display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE
);
CREATE TABLE dim_locations (
    location_id INTEGER PRIMARY KEY, location_key TEXT NOT NULL UNIQUE,
    locality TEXT, county TEXT, state TEXT NOT NULL, country TEXT NOT NULL,
    location_precision TEXT NOT NULL CHECK(location_precision IN ('city','community','county')),
    in_bay_area INTEGER NOT NULL CHECK(in_bay_area IN (0,1)),
    CHECK(location_precision != 'county' OR locality IS NULL),
    CHECK(in_bay_area = 0 OR (county IS NOT NULL AND state = 'CA' AND country = 'US'))
);
CREATE TABLE dim_skills (
    skill_id INTEGER PRIMARY KEY, canonical_name TEXT NOT NULL UNIQUE,
    taxonomy_version TEXT NOT NULL
);
CREATE TABLE fact_job_postings (
    job_posting_id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES dim_companies(company_id),
    original_title TEXT NOT NULL, normalized_title TEXT NOT NULL,
    publisher_role TEXT, role TEXT CHECK(role IN ('Data Analyst','Data Scientist','Data Engineer','Machine Learning Engineer')),
    role_status TEXT NOT NULL CHECK(role_status IN ('accepted_title_only','ambiguous','unclassified','out_of_scope')),
    role_evidence_json TEXT NOT NULL, seniority TEXT NOT NULL,
    source_posted_at TEXT NOT NULL, date_semantics TEXT NOT NULL DEFAULT 'publisher_naive_unverified',
    employment_types_json TEXT NOT NULL, raw_schedule TEXT,
    work_arrangement TEXT NOT NULL DEFAULT 'unknown' CHECK(work_arrangement = 'unknown'),
    raw_work_from_home TEXT, skill_list_status TEXT NOT NULL CHECK(skill_list_status IN ('missing','empty','malformed','populated')),
    salary_year_x100 INTEGER CHECK(salary_year_x100 > 0),
    salary_hour_x100 INTEGER CHECK(salary_hour_x100 > 0),
    raw_salary_year TEXT, raw_salary_hour TEXT, raw_salary_rate TEXT,
    salary_currency TEXT CHECK(salary_currency IS NULL),
    salary_provenance TEXT NOT NULL DEFAULT 'publisher_derived_unverified',
    advertised_salary_eligible INTEGER NOT NULL DEFAULT 0 CHECK(advertised_salary_eligible = 0),
    rule_version TEXT NOT NULL,
    CHECK((role_status = 'accepted_title_only' AND role IS NOT NULL) OR
          (role_status != 'accepted_title_only' AND role IS NULL))
);
-- Bridges allow one record to have many skills/locations without repeating the fact.
-- Composite PKs ensure repeated skill tags/locations do not count twice within a job.
CREATE TABLE bridge_job_skills (
    job_posting_id INTEGER NOT NULL REFERENCES fact_job_postings(job_posting_id),
    skill_id INTEGER NOT NULL REFERENCES dim_skills(skill_id),
    original_tags_json TEXT NOT NULL, evidence_source TEXT NOT NULL DEFAULT 'publisher_tags',
    requirement_status TEXT NOT NULL DEFAULT 'unknown' CHECK(requirement_status = 'unknown'),
    PRIMARY KEY(job_posting_id, skill_id)
);
CREATE TABLE bridge_job_locations (
    job_posting_id INTEGER NOT NULL REFERENCES fact_job_postings(job_posting_id),
    location_id INTEGER NOT NULL REFERENCES dim_locations(location_id),
    raw_location TEXT NOT NULL, PRIMARY KEY(job_posting_id, location_id)
);
CREATE TABLE source_posting_records (
    source_record_id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES collection_snapshots(snapshot_id),
    source_row_number INTEGER NOT NULL CHECK(source_row_number > 0),
    job_posting_id INTEGER NOT NULL REFERENCES fact_job_postings(job_posting_id),
    native_posting_id TEXT CHECK(native_posting_id IS NULL),
    raw_record_sha256 TEXT NOT NULL UNIQUE, raw_record_json TEXT NOT NULL,
    UNIQUE(snapshot_id, source_row_number)
);
CREATE INDEX idx_job_role ON fact_job_postings(role, role_status);
CREATE INDEX idx_skill_jobs ON bridge_job_skills(skill_id, job_posting_id);
CREATE INDEX idx_location_jobs ON bridge_job_locations(location_id, job_posting_id);
-- This view is the later four-role denominator. Audit cases remain in the fact,
-- so their uncertainty is visible without contaminating the accepted cohort.
CREATE VIEW v_target_job_records AS
SELECT * FROM fact_job_postings WHERE role_status = 'accepted_title_only';
