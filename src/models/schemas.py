
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=64, description="Ticker or company name, e.g. NVDA, TATAMOTORS.NS, Tata Motors")
    question: str = Field(..., min_length=3)


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str


class AgentStepEvent(BaseModel):
    run_id: str
    step: str
    status: Literal["started", "completed", "failed"]
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    ticker: str
    intent: str
    tasks: list[str]


class NewsSignal(BaseModel):
    title: str
    summary: str
    sentiment: Literal["positive", "negative", "neutral"]
    source: str
    date: str | None = None


class ResearchOutput(BaseModel):
    positive_signals: list[NewsSignal] = Field(default_factory=list)
    negative_signals: list[NewsSignal] = Field(default_factory=list)
    fundamental_score: float = Field(ge=0, le=10)
    earnings_trend: Literal["positive", "negative", "neutral"]
    trend: Literal["bullish", "bearish", "neutral"]
    volatility: Literal["low", "medium", "high"]
    price_change_pct: float | None = None
    volume_trend: str | None = None


class EvidenceItem(BaseModel):
    doc_id: str
    source: str
    source_type: str
    document_date: str | None = None
    snippet: str
    bm25_score: float | None = None
    vector_score: float | None = None
    fused_score: float | None = None
    citation_id: str


class RAGOutput(BaseModel):
    evidence: list[EvidenceItem] = Field(default_factory=list)
    rewritten_query: str


class RiskCategoryScore(BaseModel):
    category: str
    score: float = Field(ge=0, le=10)
    rationale: str


class RiskOutput(BaseModel):
    opportunity_score: float = Field(ge=0, le=10)
    risk_score: float = Field(ge=0, le=10)
    confidence: ConfidenceLevel
    risk_categories: list[RiskCategoryScore] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    key_opportunities: list[str] = Field(default_factory=list)


class CitedClaim(BaseModel):
    claim: str
    citation_ids: list[str]
    verified: bool = False


class ReportOutput(BaseModel):
    title: str
    outlook: str
    executive_summary: str
    bullish_signals: list[str] = Field(default_factory=list)
    bearish_signals: list[str] = Field(default_factory=list)
    opportunity_score: float
    risk_score: float
    confidence: ConfidenceLevel
    top_evidence: list[EvidenceItem] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    claims: list[CitedClaim] = Field(default_factory=list)
    verification_passed: bool = True
    market_chart: list[dict[str, Any]] = Field(default_factory=list)


class ReportDecisionRequest(BaseModel):
    action: Literal["approve", "reject", "rerun"]
    actor: str = "user"
    notes: str | None = None


class AgentRunSummary(BaseModel):
    id: str
    ticker: str
    query: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    latency_ms: int | None = None


class RetrievedDocumentResponse(BaseModel):
    id: str
    doc_id: str
    source: str
    source_type: str
    document_date: str | None
    snippet: str
    bm25_score: float | None
    vector_score: float | None
    fused_score: float | None


class ReportResponse(BaseModel):
    id: str
    run_id: str
    status: str
    report: ReportOutput
    opportunity_score: float | None
    risk_score: float | None
    confidence: str | None


class AuditLogResponse(BaseModel):
    id: str
    run_id: str
    action: str
    actor: str
    timestamp: datetime
    metadata: dict[str, Any] | None = None
