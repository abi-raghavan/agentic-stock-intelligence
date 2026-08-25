
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.planner import run_planner
from src.agents.rag_agent import run_rag
from src.agents.report import run_report_verify
from src.agents.research import run_research
from src.agents.risk import run_risk
from src.config import get_settings
from src.graph.state import GraphState
from src.logging_config import get_logger
from src.rag.retriever import HybridRetriever
from src.tools.news import news_to_rag_documents

logger = get_logger(__name__)
settings = get_settings()


class StockIntelligenceGraph:
    def __init__(self, retriever: HybridRetriever, event_callback=None) -> None:
        self.retriever = retriever
        self.event_callback = event_callback
        self.app = self._build()

    async def _emit(self, event: dict[str, Any]) -> None:
        if self.event_callback:
            result = self.event_callback(event)
            if hasattr(result, "__await__"):
                await result

    def _build(self):
        graph = StateGraph(GraphState)

        async def planning_node(state: GraphState) -> GraphState:
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "planning",
                    "status": "started",
                    "message": "Creating investigation plan",
                }
            )
            planner = await run_planner(state["ticker"], state["query"])
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "planning",
                    "status": "completed",
                    "message": "Investigation plan ready",
                }
            )
            return {"planner": planner}

        async def research_node(state: GraphState) -> GraphState:
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "research",
                    "status": "started",
                    "message": "Collecting news, market, and fundamentals",
                }
            )
            research, chart = await run_research(
                state["ticker"],
                display_name=state.get("display_name"),
                news_query=state.get("news_query"),
            )
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "research",
                    "status": "completed",
                    "message": "Research collection complete",
                }
            )
            return {"research": research, "market_chart": chart}

        async def retrieval_node(state: GraphState) -> GraphState:
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "retrieval",
                    "status": "started",
                    "message": "Ingesting live evidence and running hybrid RAG retrieval",
                }
            )
            if settings.enable_live_data and state.get("research"):
                signals = state["research"].positive_signals + state["research"].negative_signals
                live_docs = news_to_rag_documents(signals)
                self.retriever.ingest_runtime_documents(state["ticker"], live_docs)
            rag = await run_rag(self.retriever, state["query"], state["ticker"])
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "retrieval",
                    "status": "completed",
                    "message": f"Retrieved {len(rag.evidence)} evidence documents",
                }
            )
            return {"rag": rag}

        async def risk_node(state: GraphState) -> GraphState:
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "risk",
                    "status": "started",
                    "message": "Synthesizing risk and opportunity scores",
                }
            )
            risk = await run_risk(state["research"], len(state["rag"].evidence))
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "risk",
                    "status": "completed",
                    "message": "Risk synthesis complete",
                }
            )
            return {"risk": risk}

        async def report_node(state: GraphState) -> GraphState:
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "verification",
                    "status": "started",
                    "message": "Verifying claims against evidence",
                }
            )
            report = await run_report_verify(
                ticker=state["ticker"],
                query=state["query"],
                research=state["research"],
                risk=state["risk"],
                evidence=state["rag"].evidence,
                market_chart=state.get("market_chart", []),
                display_name=state.get("display_name"),
            )
            retry = False
            if not report.verification_passed and not state.get("retry_rag"):
                retry = True
                rag = await run_rag(self.retriever, f"{state['query']} evidence support", state["ticker"])
                report = await run_report_verify(
                    ticker=state["ticker"],
                    query=state["query"],
                    research=state["research"],
                    risk=state["risk"],
                    evidence=rag.evidence,
                    market_chart=state.get("market_chart", []),
                    display_name=state.get("display_name"),
                )
                await self._emit(
                    {
                        "run_id": state["run_id"],
                        "step": "verification",
                        "status": "completed",
                        "message": "Verification complete after re-retrieval",
                    }
                )
                return {"report": report, "rag": rag, "retry_rag": True}

            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "verification",
                    "status": "completed",
                    "message": "Verification complete" if report.verification_passed else "Verification completed with caveats",
                }
            )
            await self._emit(
                {
                    "run_id": state["run_id"],
                    "step": "report",
                    "status": "completed",
                    "message": "Final report generated",
                }
            )
            return {"report": report, "retry_rag": retry}

        graph.add_node("planning", planning_node)
        graph.add_node("research", research_node)
        graph.add_node("retrieval", retrieval_node)
        graph.add_node("risk", risk_node)
        graph.add_node("report", report_node)

        graph.add_edge(START, "planning")
        graph.add_edge("planning", "research")
        graph.add_edge("research", "retrieval")
        graph.add_edge("retrieval", "risk")
        graph.add_edge("risk", "report")
        graph.add_edge("report", END)

        return graph.compile()

    async def run(self, run_id: str, ticker: str, query: str, event_callback=None, display_name: str | None = None, market: str | None = None, news_query: str | None = None) -> GraphState:
        self.event_callback = event_callback
        initial: GraphState = {
            "run_id": run_id,
            "ticker": ticker.upper(),
            "display_name": display_name or ticker.upper(),
            "market": market or "UNKNOWN",
            "news_query": news_query or f"{display_name or ticker} stock",
            "query": query,
            "events": [],
            "retry_rag": False,
        }
        result = await self.app.ainvoke(initial)
        logger.info("graph_run_completed", run_id=run_id, ticker=ticker)
        return result
