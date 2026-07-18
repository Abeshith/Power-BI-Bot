import json
import re
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from modules.query_optimizer import get_relevant_columns
from modules.hybrid_intent_engine import classify_query_complexity, extract_simple_filters, format_simple_response

client = Groq(api_key=GROQ_API_KEY)
logger = logging.getLogger("PowerBIBot")

schema = None


def set_schema(dashboard_schema: dict):
    global schema
    schema = dashboard_schema


def extract_filters_from_schema(query: str, dashboard_schema: dict, exclude_tokens: set = None) -> dict:
    """Pre-LLM: Search all categorical columns for exact value matches (word-boundary, case-insensitive)."""
    filters = {}
    query_lower = query.lower()
    exclude = exclude_tokens or set()

    for col_name, col_info in dashboard_schema.get("columns", {}).items():
        distinct_values = col_info.get("distinct_values", [])
        if not distinct_values:
            continue
        for val in distinct_values:
            val_str = str(val).lower()
            if val_str in exclude:
                continue
            # Word-boundary match to avoid '10' matching inside '10000' or '30' inside '30000'
            if re.search(r'\b' + re.escape(val_str) + r'\b', query_lower):
                if col_name not in filters:
                    filters[col_name] = []
                if val not in filters[col_name]:
                    filters[col_name].append(val)

    return filters


# Operator aliases → AdvancedFilter operator strings
_OP_MAP = {
    ">=": "GreaterThanOrEqual", "gte": "GreaterThanOrEqual", "at least": "GreaterThanOrEqual", "minimum": "GreaterThanOrEqual",
    "<=": "LessThanOrEqual", "lte": "LessThanOrEqual", "at most": "LessThanOrEqual", "maximum": "LessThanOrEqual",
    ">": "GreaterThan", "gt": "GreaterThan", "more than": "GreaterThan", "above": "GreaterThan",
    "<": "LessThan", "lt": "LessThan", "under": "LessThan", "below": "LessThan",
    "=": "Is", "==": "Is", "equals": "Is", "equal to": "Is", "exactly": "Is",
}

# Normalize verbose phrases to symbols BEFORE regex matching (order matters - longer first)
_PHRASE_NORMALIZE = [
    (r"greater\s+than\s+or\s+equal\s+to", ">="),
    (r"less\s+than\s+or\s+equal\s+to",    "<="),
    (r"greater\s+than",                    ">"),
    (r"less\s+than",                       "<"),
    (r"more\s+than",                       ">"),
    (r"equal\s+to",                        "="),
]

# Month name → zero-padded number (fully dynamic, not dataset-specific)
_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12"
}


def _match_column(word: str, dashboard_schema: dict) -> str | None:
    """Find a schema column whose name or alias matches the given word (case-insensitive)."""
    word_lower = word.lower().replace("_", " ")
    for col_name, col_info in dashboard_schema.get("columns", {}).items():
        candidates = [col_name.lower().replace("_", " ")]
        candidates += [a.lower().replace("_", " ") for a in col_info.get("aliases", [])]
        if word_lower in candidates:
            return col_name
    return None


def _normalize_query(query: str) -> str:
    """Normalize verbose operator phrases to symbols so regex stays simple."""
    q = query
    for pattern, symbol in _PHRASE_NORMALIZE:
        q = re.sub(pattern, symbol, q, flags=re.IGNORECASE)
    return q


def _parse_natural_date(day: str, month_name: str, year: str) -> str | None:
    """Convert 'May 10 2026' parts to 'YYYY-MM-DD'. Returns None if month not recognised."""
    month_num = _MONTH_MAP.get(month_name.lower())
    if not month_num:
        return None
    return f"{year}-{month_num}-{int(day):02d}"


def extract_numeric_date_filters(query: str, dashboard_schema: dict) -> tuple:
    """
    Regex-based extraction of numeric/date comparison filters.
    Returns (results, exclude_tokens) where:
      - results: list of AdvancedFilter-style dicts
      - exclude_tokens: set of lowercase strings that were consumed as date parts
        so the categorical scanner doesn't pick them up as false positives
    """
    results = []
    exclude_tokens = set()
    numeric_cols = set(dashboard_schema.get("numeric_columns", []))
    date_cols = set(dashboard_schema.get("date_columns", []))
    all_cols = numeric_cols | date_cols

    # --- Natural language date patterns (run before categorical scan) ---
    # Patterns: 'after May 10 2026', 'before June 1 2026', 'on April 22 2026'
    # 'between April 1 and May 31 2026', 'from Jan 1 to Dec 31 2024'
    month_names = "|".join(_MONTH_MAP.keys())

    nl_date_re = re.compile(
        rf"(?P<op>after|since|before|until|on|by)\s+"
        rf"(?P<month>{month_names})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?[,\s]+(?P<year>\d{{4}})",
        re.IGNORECASE
    )
    nl_between_re = re.compile(
        rf"between\s+(?P<m1>{month_names})\s+(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?[,\s]+(?P<y1>\d{{4}})"
        rf"\s+and\s+(?P<m2>{month_names})\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?[,\s]+(?P<y2>\d{{4}})",
        re.IGNORECASE
    )
    # Also handle 'Month Day Year' without explicit operator (e.g. 'admitted May 10 2026')
    nl_bare_re = re.compile(
        rf"(?P<month>{month_names})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?[,\s]+(?P<year>\d{{4}})",
        re.IGNORECASE
    )

    # Find the actual date column - scan ALL column names for *date* pattern, prefer date_cols list
    schema_cols_lower = {c.lower(): c for c in dashboard_schema.get("columns", {}).keys()}
    date_col = next(iter(date_cols)) if date_cols else None
    if not date_col:
        # Prefer columns whose name contains 'date' (admission_date, discharge_date, etc.)
        for col_lower, col_orig in schema_cols_lower.items():
            if "date" in col_lower:
                date_col = col_orig
                break
    if not date_col:
        for candidate in ("admission_date", "date", "admission date"):
            if candidate in schema_cols_lower:
                date_col = schema_cols_lower[candidate]
                break

    if date_col:
        nl_between_spans = {m.span() for m in nl_between_re.finditer(query)}

        for m in nl_between_re.finditer(query):
            d1 = _parse_natural_date(m.group("d1"), m.group("m1"), m.group("y1"))
            d2 = _parse_natural_date(m.group("d2"), m.group("m2"), m.group("y2"))
            if d1 and d2:
                results.append({
                    "filterType": "advanced", "target_column": date_col,
                    "conditions": [
                        {"operator": "GreaterThanOrEqual", "value": d1},
                        {"operator": "LessThanOrEqual",    "value": d2},
                    ],
                    "logicalOperator": "And"
                })
            for grp in ("m1", "d1", "y1", "m2", "d2", "y2"):
                exclude_tokens.add(m.group(grp).lower())
            # Exclude resolved month numbers
            for mgrp in ("m1", "m2"):
                mn = _MONTH_MAP.get(m.group(mgrp).lower())
                if mn:
                    exclude_tokens.add(mn)
                    exclude_tokens.add(str(int(mn)))

        nl_date_spans = {m.span() for m in nl_date_re.finditer(query)}
        for m in nl_date_re.finditer(query):
            if any(m.start() >= s and m.end() <= e for s, e in nl_between_spans):
                continue
            op_word = m.group("op").lower()
            date_str = _parse_natural_date(m.group("day"), m.group("month"), m.group("year"))
            if date_str:
                operator = "GreaterThan" if op_word in ("after", "since") else \
                           "LessThan"    if op_word in ("before", "until", "by") else "Is"
                results.append({
                    "filterType": "advanced", "target_column": date_col,
                    "conditions": [{"operator": operator, "value": date_str}],
                    "logicalOperator": "And"
                })
            for grp in ("op", "month", "day", "year"):
                exclude_tokens.add(m.group(grp).lower())
            # Also exclude the resolved month number so numeric Month column doesn't get picked up
            month_num = _MONTH_MAP.get(m.group("month").lower())
            if month_num:
                exclude_tokens.add(month_num)          # "05"
                exclude_tokens.add(str(int(month_num))) # "5"

        for m in nl_bare_re.finditer(query):
            if any(m.start() >= s and m.end() <= e for s, e in nl_date_spans | nl_between_spans):
                continue
            date_str = _parse_natural_date(m.group("day"), m.group("month"), m.group("year"))
            if date_str:
                results.append({
                    "filterType": "advanced", "target_column": date_col,
                    "conditions": [{"operator": "Is", "value": date_str}],
                    "logicalOperator": "And"
                })
            for grp in ("month", "day", "year"):
                exclude_tokens.add(m.group(grp).lower())

    if not all_cols:
        return results, exclude_tokens

    # --- Normalize query for numeric operator matching ---
    nq = _normalize_query(query)

    # Build column pattern (spaced and underscored variants)
    col_parts = []
    for c in all_cols:
        col_parts.append(re.escape(c.replace("_", " ")))
        col_parts.append(re.escape(c))
    col_pattern = "|".join(col_parts)

    # Symbol-only operator pattern (after normalization)
    sym_ops = r">=|<=|>|<|=="

    # Pattern: <col> between X and Y
    between_re = re.compile(
        rf"({col_pattern})\s+between\s+([\d.]+)\s+and\s+([\d.]+)",
        re.IGNORECASE
    )
    for m in between_re.finditer(nq):
        col = _match_column(m.group(1), dashboard_schema) or m.group(1)
        lo, hi = m.group(2), m.group(3)
        results.append({
            "filterType": "advanced", "target_column": col,
            "conditions": [
                {"operator": "GreaterThanOrEqual", "value": _coerce(lo, col, date_cols)},
                {"operator": "LessThanOrEqual",    "value": _coerce(hi, col, date_cols)},
            ],
            "logicalOperator": "And"
        })
        # exclude the numeric values from categorical scan
        exclude_tokens.update([lo.lower(), hi.lower()])

    # Pattern: <col> <symbol_op> <value>
    single_re = re.compile(
        rf"({col_pattern})\s*({sym_ops})\s*([\d.]+)",
        re.IGNORECASE
    )
    between_spans = {m.span() for m in between_re.finditer(nq)}
    for m in single_re.finditer(nq):
        if any(m.start() >= s and m.end() <= e for s, e in between_spans):
            continue
        sym = m.group(2).strip()
        operator = {">": "GreaterThan", ">=": "GreaterThanOrEqual",
                    "<": "LessThan",    "<=": "LessThanOrEqual", "==": "Is"}.get(sym, "Is")
        col = _match_column(m.group(1), dashboard_schema) or m.group(1)
        val = m.group(3).strip()
        results.append({
            "filterType": "advanced", "target_column": col,
            "conditions": [{"operator": operator, "value": _coerce(val, col, date_cols)}],
            "logicalOperator": "And"
        })
        exclude_tokens.add(val.lower())

    # ISO date patterns: YYYY-MM-DD
    if date_cols:
        date_col = next(iter(date_cols))
        iso_range_re = re.compile(
            r"(?:from\s+)?(\d{4}-\d{2}-\d{2})\s+(?:to|through|until)\s+(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE
        )
        iso_after_re  = re.compile(r"(?:after|since)\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
        iso_before_re = re.compile(r"(?:before|until|up\s+to)\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

        for m in iso_range_re.finditer(query):
            results.append({
                "filterType": "advanced", "target_column": date_col,
                "conditions": [
                    {"operator": "GreaterThanOrEqual", "value": m.group(1)},
                    {"operator": "LessThanOrEqual",    "value": m.group(2)},
                ],
                "logicalOperator": "And"
            })
        for m in iso_after_re.finditer(query):
            results.append({
                "filterType": "advanced", "target_column": date_col,
                "conditions": [{"operator": "GreaterThan", "value": m.group(1)}],
                "logicalOperator": "And"
            })
        for m in iso_before_re.finditer(query):
            results.append({
                "filterType": "advanced", "target_column": date_col,
                "conditions": [{"operator": "LessThan", "value": m.group(1)}],
                "logicalOperator": "And"
            })

    return results, exclude_tokens


def _coerce(value: str, col: str, date_cols: set):
    """Return numeric float/int or keep as string for date columns."""
    if col in date_cols:
        return value
    try:
        return float(value) if '.' in value else int(value)
    except ValueError:
        return value


def get_schema_description_from_schema(sch: dict) -> str:
    if not sch:
        return "No schema available"
    columns_info = []
    for col_name, col_info in sch.get("columns", {}).items():
        data_type = col_info.get("type", col_info.get("data_type", "string"))
        aliases = col_info.get("aliases", [])
        distinct_values = col_info.get("distinct_values", col_info.get("valid_values", []))
        alias_str = f" (also: {', '.join(aliases)})" if aliases else ""
        if distinct_values:
            values_str = ", ".join(str(v) for v in distinct_values[:15])
            columns_info.append(f"- {col_name}{alias_str}: [{values_str}]")
        else:
            columns_info.append(f"- {col_name}{alias_str}: {data_type}")
    return "\n".join(columns_info) if columns_info else "No columns defined"


def get_schema_description() -> str:
    if not schema:
        return "No schema available"
    return get_schema_description_from_schema(schema)


def parse_intent(query: str, dashboard_schema: dict = None) -> dict:
    if dashboard_schema:
        set_schema(dashboard_schema)

    if not schema:
        return {"intent": "unknown", "entities": {}, "confidence": 0.0, "error": "No schema configured"}

    # STEP 1: Regex numeric/date extraction first - returns exclude_tokens to protect categorical scan
    numeric_date_filters, exclude_tokens = extract_numeric_date_filters(query, schema)
    logger.info(f"Numeric/date filters extracted: {numeric_date_filters}")

    # Split out basic (split-date) vs advanced filters
    basic_from_dates = {}
    advanced_filters = []
    for f in numeric_date_filters:
        if f.get("filterType") == "basic":
            col = f["target_column"]
            basic_from_dates.setdefault(col, [])
            basic_from_dates[col].extend(f["values"])
        else:
            advanced_filters.append(f)

    # STEP 2: Categorical scan - exclude tokens already consumed by numeric/date extraction
    pre_extracted = extract_filters_from_schema(query, schema, exclude_tokens)

    # Merge split-date basics into pre_extracted
    for col, vals in basic_from_dates.items():
        pre_extracted.setdefault(col, [])
        for v in vals:
            if v not in pre_extracted[col]:
                pre_extracted[col].append(v)

    if pre_extracted or advanced_filters:
        logger.info(f"Pre-LLM extraction found: {pre_extracted}")
        result = format_simple_response(pre_extracted)
        if advanced_filters:
            result["advanced_filters"] = advanced_filters
        logger.info(f"Returning pre-LLM response: {result}")
        return result

    complexity = classify_query_complexity(query)
    logger.info(f"Query complexity: {complexity}")

    if complexity == "simple":
        simple_filters = extract_simple_filters(query, schema)
        logger.info(f"Simple filters result: {simple_filters}")
        if simple_filters:
            return format_simple_response(simple_filters)

    optimized_schema = get_relevant_columns(query, schema)
    schema_desc = get_schema_description_from_schema(optimized_schema)
    logger.info(f"Schema description sent to LLM:\n{schema_desc}")

    prompt = f"""You are a Power BI filter extractor. Extract ALL filter conditions from the query.

SCHEMA (Available Columns and their EXACT values):
{schema_desc}

USER QUERY: "{query}"

RULES:
1. Match query words to the EXACT values shown in the schema above
2. Use the EXACT case as shown in the schema (e.g. "ICU" not "icu", "Stable" not "stable")
3. Map each value to its correct column
4. For multiple values in same column return as list
5. Return confidence 0.9 if matches found, 0.0 if none

Return ONLY valid JSON like: {{"column_name": ["ExactValue"], "confidence": 0.9}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"LLM raw response: {response_text}")

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Extract JSON even if LLM adds explanation text before/after it
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            response_text = response_text[start:end]

        intent_data = json.loads(response_text)
        logger.info(f"Parsed intent_data: {intent_data}")

        if "intent" not in intent_data:
            extracted = {}
            confidence = intent_data.pop("confidence", 0.7)
            for key, value in intent_data.items():
                if value is not None and key not in ["time_filters"]:
                    extracted[key] = value
            intent_data = {
                "intent": "filter_data",
                "entities": {"extracted_filters": extracted, "time_filters": {}},
                "confidence": confidence
            }

        logger.info(f"Final intent_data: {intent_data}")
        return intent_data

    except json.JSONDecodeError:
        return {
            "intent": "filter_data",
            "entities": {"extracted_filters": {}, "time_filters": {}},
            "confidence": 0.0
        }
    except Exception as e:
        return {"intent": "unknown", "entities": {}, "confidence": 0.0, "error": str(e)}
