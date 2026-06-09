from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import Config
from src.clients.llms.openai_client import OpenAIClient
from src.agents.query_rewriter_agent import QueryRewriterAgent
from src.agents.intent_agent import IntentAgent
from src.agents.sql_agent import SQLAgent
from src.agents.synthesizer_agent import SynthesizerAgent
from src.agents.guardrail_agent import GuardrailAgent
from src.tools.vector_search_tool import VectorSearchTool
from src.tools.pandas_analyzer_tool import PandasAnalyzerTool
from src.graph.nodes import GraphNodes
from src.graph.workflow import SQLOrchestrator
from src.utils.schema_loader import SchemaManager
from src.utils.route_client import VectorDBProvider, RDBMSProvider
from src.schemas.pydantic_models import (
    ChatRequest,
    ChatResponse,
    ClarificationPayload,
    DashboardResponse,
    MetadataPayload,
)
from src.utils.logger import logger
import redis.asyncio as redis
import uuid


orchestrator: Optional[SQLOrchestrator] = None
sessions: dict[str, list] = {}
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator,redis_client

    logger.info("API: Initialising agent dependencies.")
    llm_client = OpenAIClient(model_name=Config.LLM_MODEL)
    schema_manager  = SchemaManager()
    vector_client   = VectorDBProvider.get_vector_client()
    db_client       = RDBMSProvider.get_rdbms_client()
    redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True,protocol=2)
    guardrail_agent = GuardrailAgent(llm_client)
    query_rewriter  = QueryRewriterAgent(llm_client)
    intent_agent    = IntentAgent(llm_client, schema_manager)
    sql_agent       = SQLAgent(llm_client, db_client, schema_manager,vector_client)
    synthesizer     = SynthesizerAgent(llm_client)
    vector_tool     = VectorSearchTool(vector_client, db_client, schema_manager)
    pandas_tool     = PandasAnalyzerTool()

    nodes = GraphNodes(
        query_rewriter, intent_agent, sql_agent,
        synthesizer, vector_tool, pandas_tool, db_client, guardrail_agent
    )

    orchestrator = SQLOrchestrator(nodes)
    logger.info("API: Agent graph ready.")

    yield
    if redis_client:
        await redis_client.aclose()
    logger.info("API: Shutting down.")

app = FastAPI(
    title="SQL AGENT ",
    version="1.0.0",
    description="Natural language interface over your HR database.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def build_response(state: dict, debug: bool = False) -> ChatResponse:
    """
    Single transformation point between LangGraph state and the API contract.
    No agent or node touches ChatResponse — only this function does.
    """
    response_type = state.get("response_type", "text")
    text          = state.get("final_response") or "No response was generated."

    dashboard     : Optional[DashboardResponse]    = None
    clarification : Optional[ClarificationPayload] = None
    metadata      : Optional[MetadataPayload]      = None

    if response_type == "clarification":
        options = state.get("clarification_options") or []
        clarification = ClarificationPayload(
            message=text,
            options=options,
        )

    elif response_type == "dashboard":
        payload = state.get("dashboard_payload")
        raw_data = state.get("raw_db_results", [])
        if payload:
            try:
                cache_id = str(uuid.uuid4())
                if redis_client:
                    await redis_client.setex(name = cache_id,time = 3600,value=json.dumps(raw_data))
                for chart in payload.get("charts",[]):
                    chart["data_url"] = f"/api/data/{cache_id}"
                dashboard = DashboardResponse(**payload)
            except Exception as e:
                logger.error(f"build_response: Failed to deserialise dashboard payload: {e}")
                response_type = "text"

    if debug:
        metadata = MetadataPayload(
            sql_queries=state.get("sql_queries") or [],
            route=state.get("route"),
            category=state.get("category"),
        )

    return ChatResponse(
        response_type=response_type,
        text=text,
        dashboard=dashboard,
        clarification=clarification,
        metadata=metadata,
    )


@app.post("/chat", response_model=ChatResponse, summary="Send a natural language query")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised yet.")

    history = sessions.get(request.session_id, [])

    state = {
        "current_query": request.message,
        "messages": history,
        "user_id": request.user_id,
        "module": request.module,
        "language": request.language
    }

    try:
        result = await orchestrator.invoke(state)
    except Exception as e:
        logger.error(f"Orchestrator error for session {request.session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your query.")

    final_answer = result.get("final_response", "")
    history.append({"role": "user",      "content": request.message})
    history.append({"role": "assistant", "content": final_answer})
    sessions[request.session_id] = history

    return await build_response(result, debug=request.debug)

@app.get("/api/data/{cache_id}", summary="Fetch cached raw chart data", status_code=200)
async def get_chart_data(cache_id: str):
    """
    Frontend calls this endpoint using the data_url provided in the chat response
    to fetch the heavy JSON data arrays required to render the charts.
    """
    cached_data = await redis_client.get(cache_id)
    if not cached_data:
        raise HTTPException(status_code= 404, detail = "data has expired or does not exist")
    return {"data":json.loads(cached_data)}

@app.get("/health", summary="Health check", status_code=200)
async def health():
    return {"status": "ok", "orchestrator_ready": orchestrator is not None}