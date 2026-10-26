"""Offline Phase 2 preflight and raw Greenhouse snapshot profiling.

No network client, cleaning, classification, skill extraction, or database loading.
A reviewed local permission record is an attestation, not a grant of rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

COUNTIES = (
    "Alameda", "Contra Costa", "Marin", "Napa", "San Francisco",
    "San Mateo", "Santa Clara", "Solano", "Sonoma",
)
ROLES = ("Data Analyst", "Data Scientist", "Data Engineer", "Machine Learning Engineer")
FIELDS = ("id", "internal_job_id", "title", "location.name", "content", "updated_at", "absolute_url")
PERMISSIONS = ("automated_collection", "local_storage", "local_analysis")
MAX_RAW_BYTES = 10_000_000


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object.")
    return value


def plan_digest(plan: dict[str, Any]) -> str:
    """Hash a canonical JSON plan; retain the exact plan with a permitted run."""
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assess_plan(plan: dict[str, Any], access: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    """Fail closed on missing evidence, frame, retention scope, or expiration."""
    today = today or datetime.now(timezone.utc).date()
    blockers: list[str] = []
    if plan.get("source") != "greenhouse" or access.get("source") != "greenhouse":
        blockers.append("source_not_supported_or_mismatched")
    if plan.get("version") != "phase2-pilot-v1":
        blockers.append("unsupported_plan_version")
    if plan.get("geography_counties") != list(COUNTIES) or plan.get("target_roles") != list(ROLES):
        blockers.append("scope_differs_from_phase1")
    boards = plan.get("board_tokens")
    valid_boards = (
        isinstance(boards, list) and bool(boards)
        and all(isinstance(b, str) and re.fullmatch(r"[A-Za-z0-9_-]+", b) for b in boards)
        and len(boards) == len(set(boards))
    )
    if not valid_boards:
        blockers.append("missing_or_invalid_permission_scoped_board_frame")
    if access.get("review_status") != "cleared":
        blockers.append("source_permission_not_cleared")
    for field in ("reviewed_by", "evidence_reference", "retention_policy"):
        if not isinstance(access.get(field), str) or not access[field].strip():
            blockers.append(f"missing_{field}")
    permission_values = access.get("permissions")
    if not isinstance(permission_values, dict):
        permission_values = {}
    for field in PERMISSIONS:
        if permission_values.get(field) is not True:
            blockers.append(f"permission_missing_{field}")
    approved_boards = access.get("permitted_board_tokens")
    if (not isinstance(approved_boards, list) or not all(isinstance(b, str) for b in approved_boards)
            or not valid_boards or not set(boards).issubset(approved_boards)):
        blockers.append("frame_not_covered_by_permission")
    try:
        reviewed = date.fromisoformat(access["reviewed_on"])
        expires = date.fromisoformat(access["valid_until"])
        if not reviewed <= today <= expires:
            blockers.append("permission_review_outside_validity_window")
    except (KeyError, TypeError, ValueError):
        blockers.append("missing_or_invalid_permission_dates")
    if (valid_boards and type(plan.get("pilot_max_requests")) is int
            and len(boards) > plan["pilot_max_requests"]):
        blockers.append("board_frame_exceeds_project_request_cap")
    if plan.get("collection_mode") != "single_snapshot_after_clearance":
        blockers.append("unsupported_collection_mode")
    # These are project pilot caps, never a claim about a provider's quota.
    if type(plan.get("pilot_max_requests")) is not int or not 1 <= plan["pilot_max_requests"] <= 10:
        blockers.append("invalid_project_request_cap")
    if type(plan.get("request_interval_seconds")) is not int or plan["request_interval_seconds"] < 2:
        blockers.append("invalid_project_request_interval")
    return {
        "status": "blocked" if blockers else "ready_for_permission_scoped_pilot",
        "source": plan.get("source"),
        "plan_sha256": plan_digest(plan),
        "blockers": blockers,
        "network_requests_made": 0,
        "observed_record_count": None,
        "phase2_acceptance": "not_met_no_verified_live_snapshot",
    }


def _value(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _missing(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, str) and not value.strip()) or value == [] or value == {}


def profile_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Raw inventory diagnostics only, not canonical posting KPIs or scope labels."""
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError("jobs must be a list of objects; malformed rows are not silently dropped.")
    n = len(records)
    ids = [str(r["id"]) for r in records if not _missing(r.get("id"))]
    id_counts = Counter(ids)
    hashes = [hashlib.sha256(json.dumps(r, sort_keys=True, allow_nan=False).encode()).hexdigest() for r in records]
    fields = {}
    for field in FIELDS:
        values = [_value(r, field) for r in records]
        missing = sum(_missing(v) for v in values)
        fields[field] = {
            "missing_count": missing,
            "missing_percentage": None if not n else round(100 * missing / n, 4),
            "observed_types": dict(sorted(Counter(type(v).__name__ for v in values if v is not None).items())),
        }
    invalid_updated = 0
    for record in records:
        value = record.get("updated_at")
        if _missing(value):
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                invalid_updated += 1
        except (AttributeError, TypeError, ValueError):
            invalid_updated += 1
    return {
        "status": "profiled_raw_inventory_only",
        "raw_record_count": n,
        "fields": fields,
        "distinct_nonmissing_source_ids": len(id_counts),
        "repeated_source_id_rows": sum(count - 1 for count in id_counts.values()),
        "exact_repeated_payload_rows": len(hashes) - len(set(hashes)),
        "missing_source_id_rows": n - len(ids),
        "updated_at_invalid_or_timezone_missing": invalid_updated,
        "publication_time_kpi_available": False,
        "role_city_salary_skill_kpis": "not_calculated_phase3_rules_and_validation_required",
        "warnings": [
            "One board only; repeated source IDs are diagnostics, not deduplication decisions.",
            "updated_at is an update timestamp, not a verified publication date.",
            "Text presence does not establish full-text usability or skill requirements.",
            "Field absence does not establish the absence of salary or arrangement evidence in text.",
        ],
    }


def profile_snapshot(raw: Path, manifest_path: Path, plan: dict[str, Any], access: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    """Validate permission and provenance before reading a stored raw snapshot."""
    readiness = assess_plan(plan, access, today=today)
    if readiness["blockers"]:
        raise PermissionError("Profiling blocked: reviewed source permission and scoped plan are required.")
    manifest = read_object(manifest_path)
    if manifest.get("source") != "greenhouse" or manifest.get("snapshot_status") != "complete":
        raise ValueError("An explicitly complete Greenhouse snapshot is required; failed/partial is not empty.")
    board = manifest.get("board_token")
    if board not in plan["board_tokens"]:
        raise ValueError("Snapshot board is outside the permission-scoped frame.")
    if manifest.get("plan_sha256") != plan_digest(plan):
        raise ValueError("Snapshot plan checksum mismatch.")
    if manifest.get("raw_file") != raw.name:
        raise ValueError("Raw filename does not match manifest.")
    expected_request = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    if manifest.get("request_url") != expected_request:
        raise ValueError("Manifest URL must be the exact public, credential-free board request.")
    try:
        observed = datetime.fromisoformat(manifest["retrieved_at_utc"].replace("Z", "+00:00"))
        if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
            raise ValueError
        reviewed = date.fromisoformat(access["reviewed_on"])
        expires = date.fromisoformat(access["valid_until"])
        if not reviewed <= observed.date() <= expires:
            raise ValueError
        if observed > datetime.now(timezone.utc):
            raise ValueError
    except (KeyError, AttributeError, TypeError, ValueError):
        raise ValueError("Invalid, future, or permission-incompatible UTC retrieval timestamp.") from None
    if (type(manifest.get("http_status")) is not int or manifest["http_status"] != 200
            or type(manifest.get("completed_requests")) is not int or manifest["completed_requests"] != 1):
        raise ValueError("A successful one-request board snapshot is required.")
    if raw.stat().st_size > MAX_RAW_BYTES:
        raise ValueError("Snapshot exceeds the project pilot size cap; review separately.")
    content = raw.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest.get("sha256"):
        raise ValueError("Raw content checksum mismatch; do not profile changed evidence.")
    payload = json.loads(content)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Raw snapshot must contain a jobs list.")
    jobs = payload["jobs"]
    total = payload.get("meta", {}).get("total") if isinstance(payload.get("meta"), dict) else None
    if type(total) is not int or type(manifest.get("row_count")) is not int or total != len(jobs) or manifest["row_count"] != len(jobs):
        raise ValueError("Documented total, manifest row count, and actual jobs length must reconcile.")
    report = profile_records(jobs)
    report["provenance"] = {
        "source": "greenhouse", "board_token": board,
        "retrieved_at_utc": manifest["retrieved_at_utc"],
        "raw_sha256": manifest["sha256"], "plan_sha256": manifest["plan_sha256"],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "profile"))
    parser.add_argument("--plan", type=Path, default=Path("config/greenhouse_plan.json"))
    parser.add_argument("--access", type=Path, default=Path("config/greenhouse_access.json"))
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        plan, access = read_object(args.plan), read_object(args.access)
        if args.command == "preflight":
            report = assess_plan(plan, access)
        else:
            if not args.raw or not args.manifest:
                parser.error("profile requires --raw and --manifest")
            report = profile_snapshot(args.raw, args.manifest, plan, access)
    except (ValueError, PermissionError, OSError) as error:
        # Do not echo raw paths, records, URLs or exception contents into logs.
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__, "detail": "Check input shape, reviewed permissions, and manifest integrity."}))
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 2 if report.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
