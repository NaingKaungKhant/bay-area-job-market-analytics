"""Pure, testable cleaning rules for the approved historical Luke snapshot.

These functions never download data. Unknown evidence stays unknown; source labels
are retained separately so our transformations can be explained and reversed.
"""
from __future__ import annotations

import ast
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import re
import unicodedata

MISSING = {'', 'none', 'null', 'nan'}


def clean_text(value):
    """Standardize Unicode/whitespace, without erasing punctuation such as C++."""
    value = ' '.join(unicodedata.normalize('NFKC', value or '').split())
    return None if value.casefold() in MISSING else value


def classify_role(title, publisher_label, rules):
    title = clean_text(title) or ''
    matches = [role for role, pattern in rules['role_patterns'].items()
               if re.search(pattern, title, flags=re.I)]
    publisher = (clean_text(publisher_label) or '').removeprefix('Senior ')
    evidence = {'matched_roles': matches, 'method': 'title_regex_with_publisher_check', 'review_decision': None}
    # A narrowly reviewed exception distinguishes a prior-background requirement
    # from a second advertised occupation; do not generalize it to other titles.
    for override in rules.get('reviewed_role_overrides', []):
        if title == override['title'] and publisher_label == override['publisher_label']:
            if override['role'] not in matches:
                raise ValueError('Reviewed role override must have explicit title evidence.')
            evidence.update(method='reviewed_title_exception', review_decision=override['reason'])
            return override['role'], 'accepted_title_only', evidence
    non_target = bool(re.search(rules['non_target_title_pattern'], title, flags=re.I))
    # Contradicting target labels are review cases, not an arbitrary precedence rule.
    if len(matches) > 1 or (matches and non_target) or (len(matches) == 1 and publisher in rules['role_patterns']
                            and publisher != matches[0]):
        return None, 'ambiguous', evidence
    if len(matches) == 1:
        return matches[0], 'accepted_title_only', evidence
    # A generic analyst/BI title needs duties we do not have. Only an explicit
    # non-target occupation receives out_of_scope; the rest stays unclassified.
    return None, ('out_of_scope' if non_target else 'unclassified'), evidence


def classify_seniority(title):
    text = clean_text(title) or ''
    groups = {
        'entry/junior': r'\b(?:junior|jr|entry[ -]level|intern(?:ship)?)\b',
        'mid': r'\b(?:mid[ -]level|intermediate)\b',
        'senior': r'\b(?:senior|sr)\b',
        'lead/staff/principal': r'\b(?:lead|staff|principal)\b',
        'management': r'\b(?:manager|director|head|vp|vice president)\b',
    }
    found = [key for key, pattern in groups.items() if re.search(pattern, text, re.I)]
    # "Senior Manager" is compatible management evidence; junior/senior is not.
    if 'management' in found and set(found) <= {'management', 'senior'}:
        return 'management'
    if 'lead/staff/principal' in found and set(found) <= {'lead/staff/principal', 'senior'}:
        return 'lead/staff/principal'
    return found[0] if len(found) == 1 else ('mixed/conflicting' if found else 'unknown')


def resolve_locations(value, country, reference, rules):
    """Resolve explicit locations only; never use search location/headquarters.

    Semicolon/pipe separates complete locations. If any segment is unresolved,
    quarantine the record: retaining only the easy segment would lose evidence.
    """
    if (clean_text(country) or '').casefold() not in {'united states', 'usa', 'us'}:
        return [], 'country_missing_or_outside_us'
    lookup = {name.casefold(): (name, county, 'city') for name, county in reference['cities'].items()}
    lookup.update({name.casefold(): (name, county, 'community')
                   for name, county in rules['additional_places'].items()})
    counties = {name.casefold(): name for name in reference['counties']}
    resolved = []
    for segment in re.split(r'[;|]', clean_text(value) or ''):
        match = re.fullmatch(r'\s*([^,;|/]+),\s*([A-Za-z ]+?)(?:,\s*(?:United States|USA))?\s*', segment, re.I)
        if not match:
            return [], 'unresolved_geography'
        place, state = match.group(1).strip(), match.group(2).strip()
        if state.casefold() in {'ca', 'california'}:
            place = rules['location_aliases'].get(place.casefold(), place)
            if place.casefold() in {name.casefold() for name in rules['ambiguous_places']}:
                return [], 'unresolved_geography'
            if place.casefold() in lookup:
                name, county, precision = lookup[place.casefold()]
                item = (name, county, 'CA', 'US', precision, 1)
            elif place.casefold().endswith(' county') and place[:-7].casefold() in counties:
                item = (None, counties[place[:-7].casefold()], 'CA', 'US', 'county', 1)
            else:
                # Not in our lookup does not establish that a California town is outside the Bay Area.
                return [], 'unresolved_geography'
        elif re.fullmatch(r'[A-Z]{2}', state.upper()) and state.upper() in US_STATES:
            item = (place, None, state.upper(), 'US', 'city', 0)
        else:
            return [], 'unresolved_geography'
        if item not in resolved:
            resolved.append(item)
    return resolved, ('eligible_geography' if any(item[-1] for item in resolved) else 'outside_bay_area')


US_STATES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())


def parse_date(value, year):
    try:
        parsed = datetime.fromisoformat(clean_text(value) or '')
    except ValueError:
        return None, 'invalid_or_missing_date'
    if parsed.year != year:
        return None, 'outside_historical_year'
    # No timezone is attached: the source supplies no evidence for one.
    return parsed.isoformat(), None


def parse_salary(value):
    """Integer hundredths avoid binary rounding; these are NOT verified USD cents."""
    value = clean_text(value)
    if value is None:
        return None, None
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            return None, 'invalid_salary'
        hundredths = amount * 100
        rounded = hundredths.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
        if rounded <= 0 or rounded > 9223372036854775807:
            return None, 'salary_outside_storage_range'
        return int(rounded), ('salary_rounded_to_hundredths' if rounded != hundredths else None)
    except (InvalidOperation, ValueError, OverflowError):
        return None, 'invalid_salary'


def parse_skills(value, rules):
    if clean_text(value) is None:
        return 'missing', {}, 0
    try:
        tags = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError, RecursionError):
        return 'malformed', {}, 0
    if not isinstance(tags, list) or any(not isinstance(tag, str) or clean_text(tag) is None for tag in tags):
        return 'malformed', {}, 0
    skills, corrections = {}, 0
    for tag in tags:
        normalized = clean_text(tag).casefold()
        canonical = rules['skill_aliases'].get(normalized, normalized)
        corrections += int(canonical != tag)
        skills.setdefault(canonical, []).append(tag)
    return ('populated' if skills else 'empty'), skills, corrections


def employment_types(value):
    """Preserve multi-label employment evidence; do not infer contractual hours."""
    text = (clean_text(value) or '').casefold()
    known = ['full-time', 'part-time', 'contractor', 'temp work', 'internship', 'per diem', 'volunteer']
    return [label for label in known if label in text]
