from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from src.config import get_settings
from src.database.models import AgentRun, AuditLog, Report, RetrievedDocument, SessionLocal, get_db, init_db
from src.graph.workflow import StockIntelligenceGraph
from src.logging_config import configure_logging, get_logger
from src.models.schemas import (
    AgentRunSummary,
    AnalyzeRequest,
    AnalyzeResponse,
    AuditLogResponse,
    ReportDecisionRequest,
    ReportResponse,
    RetrievedDocumentResponse,
)
from src.rag.retriever import HybridRetriever
from src.tools.ticker_resolver import resolve_symbol

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title="Agentic Stock Intelligence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever = HybridRetriever()
graph = StockIntelligenceGraph(retriever)
run_events: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
run_results: dict[str, dict[str, Any]] = {}


@app.on_event("startup")
async def startup() -> None:
    init_db()
    if settings.seed_data_on_startup:
        try:
            count = retriever.load_bm25_only(settings.sample_data_dir)
            logger.info("startup_bm25_seed_complete", documents=count)
        except Exception as exc:
            logger.warning("startup_bm25_seed_failed", error=str(exc))

        if settings.enable_qdrant:
            async def index_vectors() -> None:
                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(None, lambda: retriever.qdrant.upsert_documents(retriever.records))
                    logger.info("startup_vector_seed_complete", documents=len(retriever.records))
                except Exception as exc:
                    logger.warning("startup_vector_seed_failed", error=str(exc))

            asyncio.create_task(index_vectors())
        else:
            logger.info("qdrant_disabled", mode="bm25_only")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs", response_model=list[AgentRunSummary])
def list_runs(db: Session = Depends(get_db)) -> list[AgentRunSummary]:
    runs = db.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(20).all()
    return [
        AgentRunSummary(
            id=run.id,
            ticker=run.ticker,
            query=run.query,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            latency_ms=run.latency_ms,
        )
        for run in runs
    ]


async def _execute_run(run_id: str, ticker: str, query: str, resolved_display: str, resolved_market: str, resolved_news_query: str) -> None:
    started = datetime.utcnow()
    queue = run_events[run_id]
    db = SessionLocal()

    async def callback(event: dict[str, Any]) -> None:
        await queue.put(event)

    run = db.query(AgentRun).filter(AgentRun.id == run_id).one()
    run.status = "running"
    db.commit()

    try:
        state = await graph.run(
            run_id,
            ticker,
            query,
            event_callback=callback,
            display_name=resolved_display,
            market=resolved_market,
            news_query=resolved_news_query,
        )
        for item in state["rag"].evidence:
            db.add(
                RetrievedDocument(
                    run_id=run_id,
                    doc_id=item.doc_id,
                    source=item.source,
                    source_type=item.source_type,
                    document_date=item.document_date,
                    snippet=item.snippet,
                    bm25_score=item.bm25_score,
                    vector_score=item.vector_score,
                    fused_score=item.fused_score,
                )
            )
        report = state["report"]
        db.add(
            Report(
                run_id=run_id,
                json_report=report.model_dump(),
                status="draft",
                opportunity_score=report.opportunity_score,
                risk_score=report.risk_score,
                confidence=report.confidence.value,
            )
        )
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.latency_ms = int((run.completed_at - started).total_seconds() * 1000)
        db.commit()
        run_results[run_id] = {"status": "completed", "report_id": run_id}
        await queue.put({"run_id": run_id, "step": "done", "status": "completed", "message": "Run finished"})
    except Exception as exc:
        logger.exception("run_failed", run_id=run_id, error=str(exc))
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.utcnow()
        db.commit()
        await queue.put({"run_id": run_id, "step": "error", "status": "failed", "message": str(exc)})
    finally:
        db.close()


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> AnalyzeResponse:
    resolved = resolve_symbol(request.ticker)
    run = AgentRun(ticker=resolved.yfinance_symbol, query=request.question, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    run_events[run.id] = asyncio.Queue()
    background_tasks.add_task(
        _execute_run,
        run.id,
        resolved.yfinance_symbol,
        request.question,
        resolved.display_name,
        resolved.market,
        resolved.news_query,
    )
    return AnalyzeResponse(run_id=run.id, status="pending")


@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str) -> EventSourceResponse:
    if run_id not in run_events:
        run_events[run_id] = asyncio.Queue()

    async def event_generator():
        queue = run_events[run_id]
        while True:
            event = await queue.get()
            yield {"event": "agent_step", "data": __import__("json").dumps(event, default=str)}
            if event.get("step") in {"done", "error"}:
                break

    return EventSourceResponse(event_generator())


@app.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> AgentRunSummary:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return AgentRunSummary(
        id=run.id,
        ticker=run.ticker,
        query=run.query,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        latency_ms=run.latency_ms,
    )


@app.get("/runs/{run_id}/documents", response_model=list[RetrievedDocumentResponse])
def get_documents(run_id: str, db: Session = Depends(get_db)) -> list[RetrievedDocumentResponse]:
    docs = db.query(RetrievedDocument).filter(RetrievedDocument.run_id == run_id).all()
    return [
        RetrievedDocumentResponse(
            id=doc.id,
            doc_id=doc.doc_id,
            source=doc.source,
            source_type=doc.source_type,
            document_date=doc.document_date,
            snippet=doc.snippet,
            bm25_score=doc.bm25_score,
            vector_score=doc.vector_score,
            fused_score=doc.fused_score,
        )
        for doc in docs
    ]


@app.get("/reports/{run_id}", response_model=ReportResponse)
def get_report(run_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    report = db.query(Report).filter(Report.run_id == run_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    from src.models.schemas import ReportOutput

    return ReportResponse(
        id=report.id,
        run_id=report.run_id,
        status=report.status,
        report=ReportOutput(**report.json_report),
        opportunity_score=report.opportunity_score,
        risk_score=report.risk_score,
        confidence=report.confidence,
    )


@app.post("/reports/{run_id}/decision")
def report_decision(run_id: str, request: ReportDecisionRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    report = db.query(Report).filter(Report.run_id == run_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if request.action == "approve":
        report.status = "approved"
    elif request.action == "reject":
        report.status = "rejected"
    elif request.action == "rerun":
        report.status = "rerun_requested"

    db.add(
        AuditLog(
            run_id=run_id,
            action=request.action,
            actor=request.actor,
            metadata_json={"notes": request.notes},
        )
    )
    db.commit()
    return {"status": report.status}


@app.get("/runs/{run_id}/audit", response_model=list[AuditLogResponse])
def get_audit_logs(run_id: str, db: Session = Depends(get_db)) -> list[AuditLogResponse]:
    logs = db.query(AuditLog).filter(AuditLog.run_id == run_id).order_by(AuditLog.timestamp.asc()).all()
    return [
        AuditLogResponse(
            id=log.id,
            run_id=log.run_id,
            action=log.action,
            actor=log.actor,
            timestamp=log.timestamp,
            metadata=log.metadata_json,
        )
        for log in logs
    ]
