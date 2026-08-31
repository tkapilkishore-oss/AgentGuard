"""Pure Python BM25 Lexical Retrieval Engine with Symbol-Aware Tokenization."""

import math
import re
from collections import Counter, defaultdict

from backend.app.knowledge.models import KnowledgeUnit
from backend.app.retrieval.models import RetrievalResult, RetrievalScoreBreakdown


class LexicalBM25Matcher:
    """Okapi BM25 Lexical Search with code-aware tokenization and multi-field boosting."""

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
        "between", "both", "but", "by", "could", "did", "do", "does", "doing", "down",
        "during", "each", "few", "for", "from", "further", "had", "has", "have", "having",
        "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i",
        "if", "in", "into", "is", "it", "its", "itself", "me", "more", "most", "my",
        "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
        "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
        "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves",
    }

    def __init__(self, units: list[KnowledgeUnit], k1: float = 1.5, b: float = 0.75) -> None:
        self.units = units
        self.k1 = k1
        self.b = b

        self.doc_count = len(units)
        self.doc_tokens: list[list[str]] = []
        self.doc_token_counts: list[Counter] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_len = 0.0

        self.df: dict[str, int] = defaultdict(int)
        self.idf: dict[str, float] = {}

        self._build_index()

    def tokenize(self, text: str) -> list[str]:
        """Performs symbol-aware tokenization, preserving identifiers and sub-tokens."""
        if not text:
            return []

        # Replace hyphens, underscores, slashes, and dots with spaces for subword tokenization
        subword_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # camelCase split
        tokens = re.findall(r"[a-zA-Z0-9_\-\./]+", subword_text.lower())

        expanded_tokens: list[str] = []
        for t in tokens:
            # Clean token
            clean = t.strip(".,;:()[]{}\"'/\\_-")
            if not clean or clean in self.STOP_WORDS:
                continue

            expanded_tokens.append(clean)

            # Also split snake_case, slash_paths, and dot_qualifiers
            parts = re.split(r"[_\-/\.]", clean)
            if len(parts) > 1:
                for part in parts:
                    if part and len(part) > 1 and part not in self.STOP_WORDS:
                        expanded_tokens.append(part)

        return expanded_tokens

    def _build_index(self) -> None:
        total_len = 0
        for unit in self.units:
            # Multi-field text with weight replication
            title_tokens = self.tokenize(unit.title) * 3
            summary_tokens = self.tokenize(unit.summary) * 2
            content_tokens = self.tokenize(unit.content)
            tag_tokens = self.tokenize(" ".join(unit.tags)) * 2
            path_tokens = self.tokenize(unit.source_path) * 2
            symbol_tokens = (self.tokenize(unit.symbol) * 3) if unit.symbol else []
            route_tokens = (self.tokenize(unit.route) * 3) if unit.route else []

            doc_tokens = (
                title_tokens
                + summary_tokens
                + content_tokens
                + tag_tokens
                + path_tokens
                + symbol_tokens
                + route_tokens
            )

            counts = Counter(doc_tokens)
            doc_len = len(doc_tokens)

            self.doc_tokens.append(doc_tokens)
            self.doc_token_counts.append(counts)
            self.doc_lengths.append(doc_len)
            total_len += doc_len

            for token in counts.keys():
                self.df[token] += 1

        self.avg_doc_len = total_len / max(self.doc_count, 1)

        # Compute Robertson-Spärck Jones IDF
        for token, freq in self.df.items():
            self.idf[token] = math.log(1.0 + (self.doc_count - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        """Executes BM25 search over the indexed knowledge units."""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: list[tuple[int, float]] = []

        for idx in range(self.doc_count):
            doc_len = self.doc_lengths[idx]
            counts = self.doc_token_counts[idx]
            score = 0.0

            for q_token in query_tokens:
                if q_token not in counts:
                    continue
                tf = counts[q_token]
                idf = self.idf.get(q_token, 0.0)
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(self.avg_doc_len, 1.0)))
                score += idf * (numerator / max(denominator, 1e-6))

            if score > 0.0:
                scores.append((idx, score))

        if not scores:
            return []

        # Sort and take top candidates
        scores.sort(key=lambda x: x[1], reverse=True)
        max_score = scores[0][1] if scores else 1.0

        results: list[RetrievalResult] = []
        for idx, raw_score in scores[:top_k]:
            unit = self.units[idx]
            normalized_score = min(1.0, raw_score / max(max_score, 1.0))
            results.append(
                RetrievalResult(
                    knowledge_unit_id=unit.id,
                    title=unit.title,
                    content=unit.content,
                    summary=unit.summary,
                    domain=unit.domain,
                    source_tier=unit.source_tier,
                    authority=unit.authority,
                    source_type=unit.source_type,
                    source_path=unit.source_path,
                    line_start=unit.line_start,
                    line_end=unit.line_end,
                    symbol=unit.symbol,
                    route=unit.route,
                    frontend_action=unit.dynamic_tool_fallback,
                    score=normalized_score,
                    retrieval_method="LEXICAL_BM25",
                    dynamic_live_required=(unit.authority.value == "DYNAMIC_LIVE_REQUIRED"),
                    dynamic_tool_fallback=unit.dynamic_tool_fallback,
                    tags=unit.tags,
                    content_sha256=unit.content_sha256,
                    selection_reason=f"BM25 lexical match (raw={raw_score:.2f}, norm={normalized_score:.2f})",
                    score_breakdown=RetrievalScoreBreakdown(
                        lexical_bm25_score=normalized_score,
                        total_score=normalized_score,
                    ),
                )
            )

        return results
