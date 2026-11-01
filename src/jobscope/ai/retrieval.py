from typing import Any, Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class Retriever(Protocol):
    """Finds the documents most similar to a query text."""

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        ...


class TfidfRetriever:
    def __init__(self, documents: dict[int, str]) -> None:
        self._ids = list(documents)
        self._vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self._matrix: Any = None
        if self._ids:
            try:
                self._matrix = self._vectorizer.fit_transform(documents[i] for i in self._ids)
            except ValueError:  # every document was empty or only stop words
                self._matrix = None

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        if self._matrix is None or not query.strip():
            return []
        scores = linear_kernel(self._vectorizer.transform([query]), self._matrix).ravel()
        ranked = sorted(zip(self._ids, scores, strict=True), key=lambda pair: (-pair[1], pair[0]))
        return [(doc_id, float(score)) for doc_id, score in ranked[:k] if score > 0]