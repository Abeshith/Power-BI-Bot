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

app = FastAPI(
    title="Power BI Bot Backend",
    description="AI-powered query parser for any Power BI dashboard",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Handle preflight requests
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
        current_schema = {
            "tables": schema.tables,
            "columns": schema.columns,
            "date_columns": schema.date_columns or [],
            "categorical_columns": schema.categorical_columns or [],
            "numeric_columns": schema.numeric_columns or []
        }
        logger.info(f"Schema registered with {len(schema.columns)} columns")
        return {"status": "success", "columns_registered": len(schema.columns)}
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
        
        intent_data = parse_intent(request.query, current_schema)
        
        if "error" in intent_data:
            logger.error(f"Intent parsing error: {intent_data['error']}")
            raise HTTPException(status_code=400, detail=f"Failed to parse query: {intent_data['error']}")
        
        entities = intent_data.get("entities", {})
        confidence = intent_data.get("confidence", 0)
        
        if confidence < 0.3:
            logger.warning(f"Low confidence parse: {confidence}")
        
        semantic_result = semantic_resolver(entities, current_schema, current_mappings)
        resolved_entities = semantic_result.get("resolved_entities", {})
        
        reasoning_result = reasoning_engine(resolved_entities, current_mappings)
        filters = reasoning_result.get("filters", {})
        
        dax_result = dax_generator(filters)
        dax_query = dax_result.get("dax_where_clause", "")
        
        validator_result = filter_validator(dax_query, filters, current_schema)
        
        if not validator_result.get("valid", False):
            raise HTTPException(
                status_code=400,
                detail=f"Filter validation failed: {validator_result.get('errors', [])}"
            )
        
        applier_result = filter_applier(dax_query, filters)
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
