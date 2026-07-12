from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

from config import CORS_ORIGINS, DEBUG, BACKEND_PORT
from utils.logger import logger
from utils.validators import EntityExtractionRequest, FilterResponse, ErrorResponse

from modules.intent_parser import parse_intent
from modules.semantic_resolver import semantic_resolver
from modules.reasoning_engine import reasoning_engine
from modules.dax_generator import dax_generator
from modules.filter_validator import filter_validator
from modules.filter_applier import filter_applier
from modules.semantic_enrichment import enrich_schema

_MONTH_NAME_TO_INT = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12
}

app = FastAPI(
    title="Power BI Bot Backend",
    description="AI-powered query parser for any Power BI dashboard",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return {"status": "ok"}

current_schema = None
current_mappings = None


class QueryRequest(BaseModel):
    query: str
    apply_filters: bool = True


class QueryResponse(BaseModel):
    query: str
    intent: str
    entities: Dict[str, Any]
    filters: List[Dict[str, Any]]
    dax_query: str
    status: str


class SchemaRequest(BaseModel):
    tables: List[str]
    columns: Dict[str, Dict[str, Any]]
    date_columns: Optional[List[str]] = []
    categorical_columns: Optional[List[str]] = []
    numeric_columns: Optional[List[str]] = []
    table_name: Optional[str] = None


class MappingsRequest(BaseModel):
    alias_mappings: Optional[Dict[str, str]] = {}
    synonym_mappings: Optional[Dict[str, List[str]]] = {}
    time_period_mappings: Optional[Dict[str, Dict[str, Any]]] = {}


def load_default_schema():
    global current_schema, current_mappings
    try:
        with open("schemas/dashboard_schema.json", "r") as f:
            current_schema = json.load(f)
        with open("schemas/column_mappings.json", "r") as f:
            current_mappings = json.load(f)
        logger.info("Default schema loaded")
    except FileNotFoundError:
        logger.warning("Default schema files not found, using empty schema")
        current_schema = {"tables": [], "columns": {}}
        current_mappings = {"alias_mappings": {}, "synonym_mappings": {}, "time_period_mappings": {}}


@app.on_event("startup")
async def startup_event():
    load_default_schema()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Power BI Bot Backend",
        "schema_loaded": current_schema is not None
    }


@app.post("/api/schema/register")
async def register_schema(schema: SchemaRequest):
    global current_schema
    try:
        incoming_col_count = len(schema.columns)
        existing_col_count = len(current_schema.get("columns", {})) if current_schema else 0

        # Only update if incoming schema has more or equal columns
        if incoming_col_count < existing_col_count:
            logger.info(f"Ignoring partial schema ({incoming_col_count} cols) - keeping existing ({existing_col_count} cols)")
            return {"status": "skipped", "columns_registered": existing_col_count}

        logger.info(f"Registering schema with {incoming_col_count} columns: {list(schema.columns.keys())}")

        new_schema = {
            "tables": schema.tables,
            "columns": schema.columns,
            "date_columns": schema.date_columns or [],
            "categorical_columns": schema.categorical_columns or [],
            "numeric_columns": schema.numeric_columns or [],
            "table_name": schema.table_name or (schema.tables[0] if schema.tables else "data")
        }

        # Merge distinct_values from existing schema if new schema is missing them
        # Never merge onto date columns — stale integer distinct_values cause type crashes
        new_date_cols = set(new_schema.get("date_columns", []))
        if current_schema:
            for col_name, col_info in new_schema["columns"].items():
                if col_name in new_date_cols:
                    continue
                if not col_info.get("distinct_values") and col_name in current_schema.get("columns", {}):
                    existing_vals = current_schema["columns"][col_name].get("distinct_values", [])
                    if existing_vals:
                        col_info["distinct_values"] = existing_vals

        current_schema = enrich_schema(new_schema)
        logger.info(f"Schema registered: {list(current_schema.get('columns', {}).keys())}, table: {current_schema.get('table_name')}")
        return {"status": "success", "columns_registered": incoming_col_count}
    except Exception as e:
        logger.error(f"Error registering schema: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/mappings/register")
async def register_mappings(mappings: MappingsRequest):
    global current_mappings
    try:
        current_mappings = {
            "alias_mappings": mappings.alias_mappings or {},
            "synonym_mappings": mappings.synonym_mappings or {},
            "time_period_mappings": mappings.time_period_mappings or {}
        }
        logger.info("Mappings registered")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error registering mappings: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/parse", response_model=QueryResponse)
async def parse_query(request: QueryRequest):
    try:
        if not current_schema:
            raise HTTPException(status_code=400, detail="No schema registered")

        logger.info(f"Processing query: {request.query}")
        table_name = current_schema.get("table_name", "data")

        if not current_schema.get("columns"):
            logger.warning("Schema has no columns - visual may not have registered schema yet")
            return QueryResponse(
                query=request.query,
                intent="error",
                entities={},
                filters=[],
                dax_query="",
                status="Schema not ready - please wait for the visual to load and try again"
            )

        intent_data = parse_intent(request.query, current_schema)

        if "error" in intent_data:
            logger.error(f"Intent parsing error: {intent_data['error']}")
            raise HTTPException(status_code=400, detail=f"Failed to parse query: {intent_data['error']}")

        # If pre-LLM / rule engine returned filters directly, use them as-is
        # and fix the table name to match the actual registered schema
        if intent_data.get("source") == "rule_engine" and (intent_data.get("filters") or intent_data.get("advanced_filters")):
            pbi_filters = []
            for f in intent_data.get("filters", []):
                col = f["target"]["column"]
                values = f["conditions"][0]["values"]
                # Convert string month names to integers if this is the Month column
                if col.lower() == "month":
                    converted = []
                    for v in values:
                        if isinstance(v, str) and v.lower() in _MONTH_NAME_TO_INT:
                            converted.append(_MONTH_NAME_TO_INT[v.lower()])
                        else:
                            converted.append(v)
                    values = converted
                pbi_filters.append({
                    "filterType": "basic",
                    "$schema": "http://powerbi.com/product/schema#basic",
                    "target": {"table": table_name, "column": col},
                    "operator": "In",
                    "values": values
                })
            for f in intent_data.get("advanced_filters", []):
                col = f["target_column"]
                conditions = f["conditions"]
                col_info = current_schema.get("columns", {}).get(col, {})
                distinct = col_info.get("distinct_values", [])
                v1 = conditions[0]["value"]
                # Only convert to BasicFilter when: column has numeric distinct_values
                # AND the filter value itself is numeric (not an ISO date string)
                is_numeric_distinct = (
                    distinct
                    and isinstance(v1, (int, float))
                    and all(isinstance(v, (int, float)) for v in distinct)
                )
                if is_numeric_distinct and len(conditions) <= 2:
                    lo = hi = None
                    op1 = conditions[0]["operator"]
                    v1 = conditions[0]["value"]
                    if len(conditions) == 2:
                        v2 = conditions[1]["value"]
                        lo, hi = min(v1, v2), max(v1, v2)
                        matching = [v for v in distinct if lo <= v <= hi]
                    elif op1 in ("GreaterThan",):
                        matching = [v for v in distinct if v > v1]
                    elif op1 in ("GreaterThanOrEqual",):
                        matching = [v for v in distinct if v >= v1]
                    elif op1 in ("LessThan",):
                        matching = [v for v in distinct if v < v1]
                    elif op1 in ("LessThanOrEqual",):
                        matching = [v for v in distinct if v <= v1]
                    else:
                        matching = [v for v in distinct if v == v1]
                    if matching:
                        pbi_filters.append({
                            "filterType": "basic",
                            "$schema": "http://powerbi.com/product/schema#basic",
                            "target": {"table": table_name, "column": col},
                            "operator": "In",
                            "values": matching
                        })
                else:
                    pbi_filters.append({
                        "filterType": "advanced",
                        "$schema": "http://powerbi.com/product/schema#advanced",
                        "target": {"table": table_name, "column": col},
                        "logicalOperator": f.get("logicalOperator", "And"),
                        "conditions": conditions
                    })
            logger.info(f"Using rule_engine filters directly: {len(pbi_filters)} filters")
            return QueryResponse(
                query=request.query,
                intent=intent_data.get("intent", "filter_data"),
                entities=intent_data.get("entities", {}),
                filters=pbi_filters,
                dax_query="",
                status="success"
            )

        # LLM path - run full pipeline
        entities = intent_data.get("entities", {})
        confidence = intent_data.get("confidence", 0)

        if confidence < 0.3:
            logger.warning(f"Low confidence parse: {confidence}")

        semantic_result = semantic_resolver(entities, current_schema, current_mappings)
        resolved_entities = semantic_result.get("resolved_entities", {})
        logger.info(f"Resolved entities: {resolved_entities}")

        reasoning_result = reasoning_engine(resolved_entities, current_mappings)
        filters = reasoning_result.get("filters", {})
        logger.info(f"Reasoning filters: {filters}")

        dax_result = dax_generator(filters)
        dax_query = dax_result.get("dax_where_clause", "")

        validator_result = filter_validator(dax_query, filters, current_schema)
        if not validator_result.get("valid", False):
            logger.warning(f"Validation warning: {validator_result.get('errors', [])}")

        applier_result = filter_applier(dax_query, filters, table_name,
                                         advanced_filters=intent_data.get("advanced_filters"))
        pbi_filters = applier_result.get("filters", [])

        logger.info(f"Query processed successfully with {len(pbi_filters)} filters")

        return QueryResponse(
            query=request.query,
            intent=intent_data.get("intent", "filter_data"),
            entities=entities,
            filters=pbi_filters,
            dax_query=dax_query,
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/intent")
async def extract_intent(request: QueryRequest):
    try:
        if not current_schema:
            raise HTTPException(status_code=400, detail="No schema registered")
        intent_data = parse_intent(request.query, current_schema)
        return intent_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting intent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schema")
async def get_schema():
    if not current_schema:
        raise HTTPException(status_code=404, detail="No schema registered")
    return current_schema


@app.get("/api/mappings")
async def get_mappings():
    if not current_mappings:
        raise HTTPException(status_code=404, detail="No mappings registered")
    return current_mappings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        reload=DEBUG
    )
