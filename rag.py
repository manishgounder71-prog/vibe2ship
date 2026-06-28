"""
FutureShield AI - Retrieval-Augmented Generation (RAG) Engine

Dual-backend vector search:
  1. ChromaDB (preferred) — full semantic search with embeddings
  2. Pure-Python fallback — character n-gram TF-IDF + cosine similarity
     (zero native dependencies, works on any platform)

Enhances Gemini AI prompts with contextually relevant past data
from goals, threats, focus sessions, and focus records.
"""

import os
import re
import math
import logging
import collections
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag")

CHROMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

_engine: Optional["RAGEngine"] = None


# ---------------------------------------------------------------------------
# Pure-Python fallback: TF-IDF with character n-grams + cosine similarity
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _ngrams(tokens: list[str], n: int = 2) -> list[str]:
    """Generate character n-grams from tokens for fuzzy matching."""
    chars = " ".join(tokens)
    return [chars[i:i + n] for i in range(max(1, len(chars) - n + 1))]


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors (dicts)."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for k, v in vec_a.items():
        norm_a += v * v
        if k in vec_b:
            dot += v * vec_b[k]
    for v in vec_b.values():
        norm_b += v * v
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class _FallbackStore:
    """In-memory document store with TF-IDF retrieval using character n-grams."""

    def __init__(self):
        self.documents: list[dict] = []       # {"doc": str, "meta": dict, "id": str}
        self.vectors: list[dict[str, float]] = []  # sparse TF-IDF vectors
        self.idf: dict[str, float] = {}
        self._dirty = True

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        for doc, meta, did in zip(documents, metadatas, ids):
            self.documents.append({"doc": doc, "meta": meta, "id": did})
        self._dirty = True

    def _rebuild_index(self):
        """Rebuild TF-IDF vectors and IDF weights."""
        if not self._dirty:
            return
        self.vectors = []
        doc_count = len(self.documents)
        if doc_count == 0:
            self.idf = {}
            return

        # Collect all term frequencies
        all_tf: list[dict[str, int]] = []
        term_doc_count: dict[str, int] = collections.defaultdict(int)

        for entry in self.documents:
            tokens = _tokenize(entry["doc"])
            grams = _ngrams(tokens, n=3)  # trigrams for fuzzy matching
            tf = collections.Counter(grams)
            all_tf.append(dict(tf))
            for g in set(grams):
                term_doc_count[g] += 1

        # Compute IDF
        self.idf = {
            term: math.log((doc_count + 1) / (count + 1)) + 1
            for term, count in term_doc_count.items()
        }

        # Build TF-IDF vectors
        for tf_vec in all_tf:
            vec = {}
            for term, freq in tf_vec.items():
                vec[term] = freq * self.idf.get(term, 1.0)
            self.vectors.append(vec)

        self._dirty = False

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """Return top-n_results documents sorted by cosine similarity."""
        self._rebuild_index()
        if not self.documents:
            return []

        # Vectorize query
        query_tokens = _tokenize(query_text)
        query_grams = _ngrams(query_tokens, n=3)
        query_tf = collections.Counter(query_grams)
        query_vec = {
            term: freq * self.idf.get(term, 1.0)
            for term, freq in query_tf.items()
        }

        # Score all documents
        scored = []
        for i, vec in enumerate(self.vectors):
            sim = _cosine_similarity(query_vec, vec)
            if sim > 0:
                scored.append((sim, i))

        scored.sort(key=lambda x: -x[0])

        results = []
        for sim, idx in scored[:n_results]:
            entry = self.documents[idx]
            results.append({
                "document": entry["doc"],
                "metadata": entry["meta"],
                "distance": 1.0 - sim  # convert similarity to distance
            })
        return results

    def count(self) -> int:
        return len(self.documents)

    def clear(self):
        self.documents.clear()
        self.vectors.clear()
        self.idf.clear()
        self._dirty = True


# ---------------------------------------------------------------------------
# RAG Engine — tries ChromaDB first, falls back to pure Python
# ---------------------------------------------------------------------------

class RAGEngine:
    """
    Retrieval-Augmented Generation engine.

    Uses ChromaDB when available; otherwise uses a pure-Python TF-IDF
    fallback that works on any platform with zero native dependencies.
    """

    def __init__(self):
        self._chroma_collection = None
        self._chroma_client = None
        self._fallback: Optional[_FallbackStore] = None
        self._chroma_mode = False
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the engine. Tries ChromaDB first, falls back to pure Python."""
        if self._initialized:
            return True

        # Try ChromaDB
        try:
            import chromadb
            from chromadb.config import Settings

            self._chroma_client = chromadb.PersistentClient(
                path=CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False)
            )
            # Get or create collection — don't delete existing data on restart
            try:
                self._chroma_collection = self._chroma_client.get_collection("futureshield")
                logger.info("Found existing ChromaDB collection with %d documents", self._chroma_collection.count())
            except ValueError:
                self._chroma_collection = self._chroma_client.create_collection(
                    name="futureshield",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("Created new ChromaDB collection")
            except Exception:
                self._chroma_collection = self._chroma_client.create_collection(
                    name="futureshield",
                    metadata={"hnsw:space": "cosine"}
                )
            self._chroma_mode = True
            self._initialized = True
            logger.info("RAG engine using ChromaDB (full semantic search)")
            return True
        except Exception as e:
            logger.info(f"ChromaDB not available ({e}), using pure-Python fallback engine")

        # Fallback
        try:
            self._fallback = _FallbackStore()
            self._chroma_mode = False
            self._initialized = True
            logger.info("RAG engine using pure-Python fallback (TF-IDF n-gram search)")
            return True
        except Exception as e:
            logger.warning(f"RAG fallback initialization failed: {e}")
            self._initialized = False
            return False

    # -- Indexing helpers ---------------------------------------------------

    def _make_goal_doc(self, goal: dict) -> str:
        return (
            f"Goal: {goal.get('title', '')}. "
            f"Status: {goal.get('status', '')}. "
            f"Progress: {goal.get('progress', 0)}%. "
            f"Deadline: {goal.get('deadline', '')}."
        )

    def _make_threat_doc(self, threat: dict) -> str:
        return (
            f"Threat: {threat.get('name', '')}. "
            f"Urgency: {threat.get('urgency', '')}. "
            f"Probability: {threat.get('probability', 0)}%. "
            f"Success rate: {threat.get('success_rate', '')}. "
            f"Type: {threat.get('type', '')}."
        )

    def _make_focus_session_doc(self, session: dict) -> str:
        return (
            f"Focus session: {session.get('session_type', 'focus')}. "
            f"Duration: {session.get('duration_minutes', 0)} minutes. "
            f"Actual duration: {session.get('actual_duration_seconds', 0)} seconds. "
            f"Energy rating: {session.get('energy_rating', 'N/A')}. "
            f"Status: {session.get('status', '')}."
        )

    def _make_focus_record_doc(self, record: dict) -> str:
        return (
            f"Energy record: level {record.get('energy_level', 50)}. "
            f"Timestamp: {record.get('timestamp', 'N/A')}."
        )

    def index_goal(self, goal: dict):
        """Index a goal document."""
        doc = self._make_goal_doc(goal)
        gid = f"goal_{goal.get('id', '')}"
        meta = {
            "type": "goal", "id": str(goal.get("id", "")),
            "status": goal.get("status", ""),
            "progress": goal.get("progress", 0),
            "deadline": goal.get("deadline", ""),
            "title": goal.get("title", "")
        }
        if self._chroma_mode and self._chroma_collection is not None:
            try:
                self._chroma_collection.add(documents=[doc], metadatas=[meta], ids=[gid])
            except Exception as e:
                logger.warning(f"Failed to index goal: {e}")
        elif self._fallback is not None:
            self._fallback.add([doc], [meta], [gid])

    def index_threat(self, threat: dict):
        """Index a threat document."""
        doc = self._make_threat_doc(threat)
        tid = f"threat_{threat.get('id', '')}"
        meta = {
            "type": "threat", "id": str(threat.get("id", "")),
            "urgency": threat.get("urgency", ""),
            "probability": threat.get("probability", 0),
            "threat_type": threat.get("type", ""),
            "resolved": threat.get("resolved", 0)
        }
        if self._chroma_mode and self._chroma_collection is not None:
            try:
                self._chroma_collection.add(documents=[doc], metadatas=[meta], ids=[tid])
            except Exception as e:
                logger.warning(f"Failed to index threat: {e}")
        elif self._fallback is not None:
            self._fallback.add([doc], [meta], [tid])

    def index_focus_session(self, session: dict):
        """Index a focus session document."""
        doc = self._make_focus_session_doc(session)
        sid = f"focus_session_{session.get('id', '')}"
        meta = {
            "type": "focus_session", "id": str(session.get("id", "")),
            "session_type": session.get("session_type", ""),
            "duration_minutes": session.get("duration_minutes", 0),
            "energy_rating": session.get("energy_rating", 0),
            "status": session.get("status", "")
        }
        if self._chroma_mode and self._chroma_collection is not None:
            try:
                self._chroma_collection.add(documents=[doc], metadatas=[meta], ids=[sid])
            except Exception as e:
                logger.warning(f"Failed to index focus session: {e}")
        elif self._fallback is not None:
            self._fallback.add([doc], [meta], [sid])

    def index_focus_record(self, record: dict):
        """Index a focus record (energy level) document."""
        doc = self._make_focus_record_doc(record)
        rid = f"focus_record_{record.get('id', '')}"
        meta = {
            "type": "focus_record", "id": str(record.get("id", "")),
            "energy_level": record.get("energy_level", 50)
        }
        if self._chroma_mode and self._chroma_collection is not None:
            try:
                self._chroma_collection.add(documents=[doc], metadatas=[meta], ids=[rid])
            except Exception as e:
                logger.warning(f"Failed to index focus record: {e}")
        elif self._fallback is not None:
            self._fallback.add([doc], [meta], [rid])

    def index_all_data(self) -> bool:
        """Index all data from the database into the engine."""
        try:
            import database as db

            goals = db.query_db("SELECT * FROM goals")
            for g in goals:
                self.index_goal(g)

            threats = db.query_db("SELECT * FROM threats")
            for t in threats:
                self.index_threat(t)

            sessions = db.query_db("SELECT * FROM focus_sessions")
            for s in sessions:
                self.index_focus_session(s)

            records = db.query_db("SELECT * FROM focus_records")
            for r in records:
                self.index_focus_record(r)

            if self._chroma_mode and self._chroma_collection is not None:
                count = self._chroma_collection.count()
            elif self._fallback is not None:
                count = self._fallback.count()
            else:
                count = 0
            logger.info(f"Indexed {count} documents into RAG engine")
            return True
        except Exception as e:
            logger.warning(f"Failed to index all data: {e}")
            return False

    def query(self, query_text: str, n_results: int = 5) -> list[dict]:
        """
        Query the vector store for semantically similar documents.

        Returns list of dicts with 'document', 'metadata', and 'distance' keys.
        """
        if self._chroma_mode and self._chroma_collection is not None:
            try:
                results = self._chroma_collection.query(
                    query_texts=[query_text], n_results=n_results
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]
                output = []
                for i in range(len(docs)):
                    output.append({
                        "document": docs[i],
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": dists[i] if i < len(dists) else 0.0
                    })
                return output
            except Exception as e:
                logger.warning(f"ChromaDB query failed: {e}")
                return []
        elif self._fallback is not None:
            return self._fallback.query(query_text, n_results=n_results)
        return []

    def format_context(self, results: list[dict]) -> str:
        """Format RAG results into a context string for prompt injection."""
        if not results:
            return ""
        sections = []
        for item in results:
            meta = item.get("metadata", {})
            doc_type = meta.get("type", "unknown")
            doc_text = item.get("document", "")
            sections.append(f"[{doc_type.upper()}] {doc_text}")
        return "\n".join(sections)

    def get_stats(self) -> dict:
        """Return statistics about the RAG engine's document store."""
        stats = {
            "initialized": self._initialized,
            "backend": "chromadb" if self._chroma_mode else "fallback_tfidf",
            "total_documents": 0,
            "documents_by_type": {},
            "chromadb_available": self._chroma_mode,
        }

        if self._chroma_mode and self._chroma_collection is not None:
            try:
                stats["total_documents"] = self._chroma_collection.count()
                # Compute type breakdown from metadata
                try:
                    all_metas = self._chroma_collection.get()["metadatas"]
                    type_counts: dict[str, int] = {}
                    for m in all_metas:
                        t = m.get("type", "unknown") if m else "unknown"
                        type_counts[t] = type_counts.get(t, 0) + 1
                    stats["documents_by_type"] = type_counts
                except Exception:
                    stats["documents_by_type"] = {}
            except Exception:
                stats["total_documents"] = 0
        elif self._fallback is not None:
            stats["total_documents"] = self._fallback.count()
            # Count by type from metadata
            type_counts: dict[str, int] = {}
            for doc in self._fallback.documents:
                t = doc.get("meta", {}).get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
            stats["documents_by_type"] = type_counts
            stats["vocabulary_size"] = len(self._fallback.idf)

        return stats

    def list_documents(self, limit: int = 20, offset: int = 0, type_filter: str | None = None) -> list[dict]:
        """List indexed documents with pagination and optional type filter.

        Returns a list of dicts with 'id', 'type', 'document' (truncated),
        and 'metadata' keys.
        """
        results: list[dict] = []

        if self._chroma_mode and self._chroma_collection is not None:
            try:
                # ChromaDB doesn't support offset natively, so get a large batch
                all_data = self._chroma_collection.get(limit=limit + offset)
                ids = all_data.get("ids", [])
                docs = all_data.get("documents", [])
                metas = all_data.get("metadatas", [])
                for i in range(len(ids)):
                    if i < offset:
                        continue
                    if len(results) >= limit:
                        break
                    meta = metas[i] if i < len(metas) else {}
                    doc_type = meta.get("type", "unknown") if meta else "unknown"
                    if type_filter and doc_type != type_filter:
                        continue
                    results.append({
                        "id": ids[i],
                        "type": doc_type,
                        "document": docs[i][:200] if docs[i] else "",
                        "metadata": meta or {},
                    })
            except Exception as e:
                logger.warning(f"ChromaDB list failed: {e}")
        elif self._fallback is not None:
            for i, entry in enumerate(self._fallback.documents):
                if i < offset:
                    continue
                if len(results) >= limit:
                    break
                meta = entry.get("meta", {})
                doc_type = meta.get("type", "unknown")
                if type_filter and doc_type != type_filter:
                    continue
                results.append({
                    "id": entry.get("id", ""),
                    "type": doc_type,
                    "document": entry.get("doc", "")[:200],
                    "metadata": meta,
                })

        return results


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def get_engine() -> Optional[RAGEngine]:
    """Get the global RAG engine instance."""
    return _engine


def init_engine() -> Optional[RAGEngine]:
    """Initialize and return the global RAG engine instance."""
    global _engine
    if _engine is None:
        _engine = RAGEngine()
        if _engine.initialize():
            _engine.index_all_data()
    return _engine
