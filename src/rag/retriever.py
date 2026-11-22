import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def make_doc_id(ticker: str, source: str, idx: int) -> str:
    raw = f"{ticker}:{source}:{idx}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class DocumentRecord:
    doc_id: str
    ticker: str
    company: str
    source: str
    source_type: str
    document_date: str | None
    title: str
    content: str


class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(settings.embedding_model)
        return cls._model

    @classmethod
    def embed(cls, texts: list[str]) -> list[list[float]]:
        model = cls.get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


class QdrantStore:
    def __init__(self) -> None:
        self.client = None
        self.collection = settings.qdrant_collection
        if settings.enable_qdrant:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(url=settings.qdrant_url)

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.http import models as qmodels

        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
            )

    def upsert_documents(self, records: list[DocumentRecord]) -> None:
        if not settings.enable_qdrant or not records:
            return
        from qdrant_client.http import models as qmodels

        vectors = EmbeddingService.embed([f"{r.title}\n{r.content}" for r in records])
        self.ensure_collection(len(vectors[0]))
        points = []
        for idx, (record, vector) in enumerate(zip(records, vectors, strict=True)):
            points.append(
                qmodels.PointStruct(
                    id=idx + 1,
                    vector=vector,
                    payload={
                        "doc_id": record.doc_id,
                        "ticker": record.ticker.upper(),
                        "company": record.company,
                        "source": record.source,
                        "source_type": record.source_type,
                        "document_date": record.document_date,
                        "title": record.title,
                        "content": record.content,
                    },
                )
            )
        self.client.upsert(collection_name=self.collection, points=points)

    def vector_search(
        self,
        query: str,
        ticker: str | None = None,
        source_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not settings.enable_qdrant or self.client is None:
            return []
        from qdrant_client.http import models as qmodels

        vector = EmbeddingService.embed([query])[0]
        must: list[qmodels.FieldCondition] = []
        if ticker:
            must.append(qmodels.FieldCondition(key="ticker", match=qmodels.MatchValue(value=ticker.upper())))
        if source_type:
            must.append(qmodels.FieldCondition(key="source_type", match=qmodels.MatchValue(value=source_type)))

        query_filter = qmodels.Filter(must=must) if must else None
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        output = []
        for hit in results:
            payload = hit.payload or {}
            output.append(
                {
                    "doc_id": payload.get("doc_id", str(hit.id)),
                    "source": payload.get("source", "unknown"),
                    "source_type": payload.get("source_type", "unknown"),
                    "document_date": payload.get("document_date"),
                    "snippet": (payload.get("content") or "")[:500],
                    "title": payload.get("title", ""),
                    "vector_score": float(hit.score),
                }
            )
        return output


class BM25Index:
    def __init__(self) -> None:
        self.records: list[DocumentRecord] = []
        self.index: BM25Okapi | None = None

    def build(self, records: list[DocumentRecord]) -> None:
        self.records = records
        corpus = [tokenize(f"{r.title} {r.content}") for r in records]
        self.index = BM25Okapi(corpus) if corpus else None

    def search(
        self,
        query: str,
        ticker: str | None = None,
        source_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not self.index or not self.records:
            return []
        scores = self.index.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked:
            record = self.records[idx]
            if ticker and record.ticker.upper() != ticker.upper():
                continue
            if source_type and record.source_type != source_type:
                continue
            results.append(
                {
                    "doc_id": record.doc_id,
                    "source": record.source,
                    "source_type": record.source_type,
                    "document_date": record.document_date,
                    "snippet": record.content[:500],
                    "title": record.title,
                    "bm25_score": float(score),
                }
            )
            if len(results) >= limit:
                break
        return results


class TfidfIndex:
    """In-process sparse TF-IDF vector channel — free, fast, no model download."""

    def __init__(self) -> None:
        self.records: list[DocumentRecord] = []
        self.doc_vectors: list[dict[str, float]] = []
        self.idf: dict[str, float] = {}

    def build(self, records: list[DocumentRecord]) -> None:
        self.records = records
        tokenized = [tokenize(f"{r.title} {r.content}") for r in records]
        df: Counter[str] = Counter()
        for tokens in tokenized:
            df.update(set(tokens))
        n_docs = max(len(tokenized), 1)
        self.idf = {term: math.log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()}
        self.doc_vectors = []
        for tokens in tokenized:
            tf = Counter(tokens)
            length = max(len(tokens), 1)
            vector = {term: (count / length) * self.idf.get(term, 0.0) for term, count in tf.items()}
            self.doc_vectors.append(vector)

    def _query_vector(self, query: str) -> dict[str, float]:
        tokens = tokenize(query)
        if not tokens:
            return {}
        tf = Counter(tokens)
        length = max(len(tokens), 1)
        return {term: (count / length) * self.idf.get(term, 0.0) for term, count in tf.items()}

    def search(
        self,
        query: str,
        ticker: str | None = None,
        source_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not self.records or not self.doc_vectors:
            return []
        qvec = self._query_vector(query)
        scored: list[tuple[float, int]] = []
        for idx, record in enumerate(self.records):
            if ticker and record.ticker.upper() != ticker.upper():
                continue
            if source_type and record.source_type != source_type:
                continue
            score = _cosine(qvec, self.doc_vectors[idx])
            if score > 0:
                scored.append((score, idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scored[:limit]:
            record = self.records[idx]
            results.append(
                {
                    "doc_id": record.doc_id,
                    "source": record.source,
                    "source_type": record.source_type,
                    "document_date": record.document_date,
                    "snippet": record.content[:500],
                    "title": record.title,
                    "vector_score": float(score),
                }
            )
        return results


def reciprocal_rank_fusion(
    result_lists: list[list[dict[str, Any]]],
    score_key: str,
    fused_key: str = "fused_score",
    k: int = 60,
) -> list[dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            doc_id = item["doc_id"]
            rrf_score = 1.0 / (k + rank)
            if doc_id not in fused:
                fused[doc_id] = {**item, fused_key: rrf_score}
            else:
                fused[doc_id][fused_key] = fused[doc_id].get(fused_key, 0.0) + rrf_score
                if item.get(score_key) is not None:
                    fused[doc_id][score_key] = item.get(score_key)
            for key in ("bm25_score", "vector_score", "source", "source_type", "document_date", "snippet", "title"):
                if key in item and fused[doc_id].get(key) is None:
                    fused[doc_id][key] = item[key]
    return sorted(fused.values(), key=lambda x: x.get(fused_key, 0.0), reverse=True)


def rewrite_query(query: str, ticker: str) -> str:
    normalized = query.strip()
    if ticker.upper() not in normalized.upper():
        normalized = f"{ticker.upper()} {normalized}"
    if "risk" in normalized.lower() or "worried" in normalized.lower():
        normalized += " risks regulatory export restrictions valuation volatility"
    elif "opportunity" in normalized.lower() or "bullish" in normalized.lower():
        normalized += " growth earnings demand revenue guidance"
    return normalized


def assign_citation_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for idx, item in enumerate(items, start=1):
        item["citation_id"] = f"E{idx}"
    return items


class HybridRetriever:
    def __init__(self) -> None:
        self.qdrant = QdrantStore()
        self.bm25 = BM25Index()
        self.tfidf = TfidfIndex()
        self.records: list[DocumentRecord] = []

    def _rebuild_indexes(self) -> None:
        self.bm25.build(self.records)
        if settings.enable_hybrid_tfidf:
            self.tfidf.build(self.records)

    def load_bm25_only(self, data_dir: str | Path) -> int:
        path = Path(data_dir)
        records: list[DocumentRecord] = []
        for file_path in sorted(path.glob("*.json")):
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            for idx, doc in enumerate(payload.get("documents", [])):
                records.append(
                    DocumentRecord(
                        doc_id=make_doc_id(payload.get("ticker", "UNK"), doc.get("source", file_path.stem), idx),
                        ticker=payload.get("ticker", "UNK").upper(),
                        company=payload.get("company", payload.get("ticker", "Unknown")),
                        source=doc.get("source", "unknown"),
                        source_type=doc.get("source_type", "news"),
                        document_date=doc.get("document_date"),
                        title=doc.get("title", "Untitled"),
                        content=doc.get("content", ""),
                    )
                )
        self.records = records
        self._rebuild_indexes()
        logger.info("hybrid_sample_data_loaded", count=len(records), tfidf=settings.enable_hybrid_tfidf)
        return len(records)

    def ingest_runtime_documents(self, ticker: str, documents: list[dict[str, str]]) -> int:
        if not documents:
            return 0
        ticker = ticker.upper()
        base_records = [r for r in self.records if not (r.ticker == ticker and r.source_type == "live_news")]
        live_records = [
            DocumentRecord(
                doc_id=make_doc_id(ticker, doc.get("source", "live"), idx + 10_000),
                ticker=ticker,
                company=ticker,
                source=doc.get("source", "Live News"),
                source_type=doc.get("source_type", "live_news"),
                document_date=doc.get("document_date"),
                title=doc.get("title", "Live headline"),
                content=doc.get("content", ""),
            )
            for idx, doc in enumerate(documents)
        ]
        self.records = base_records + live_records
        self._rebuild_indexes()
        self.qdrant.upsert_documents(live_records)
        return len(live_records)

    def retrieve(
        self,
        query: str,
        ticker: str,
        source_type: str | None = None,
        limit: int = 8,
    ) -> tuple[str, list[dict[str, Any]]]:
        rewritten = rewrite_query(query, ticker)
        bm25_results = self.bm25.search(rewritten, ticker=ticker, source_type=source_type, limit=limit)

        vector_channels: list[list[dict[str, Any]]] = []
        if settings.enable_hybrid_tfidf:
            tfidf_results = self.tfidf.search(rewritten, ticker=ticker, source_type=source_type, limit=limit)
            if tfidf_results:
                vector_channels.append(tfidf_results)

        qdrant_results = self.qdrant.vector_search(rewritten, ticker=ticker, source_type=source_type, limit=limit)
        if qdrant_results:
            vector_channels.append(qdrant_results)

        if vector_channels:
            fused = reciprocal_rank_fusion([bm25_results, *vector_channels], score_key="bm25_score")[:limit]
        else:
            fused = [{**item, "fused_score": item.get("bm25_score", 0.0)} for item in bm25_results[:limit]]
        return rewritten, assign_citation_ids(fused)
