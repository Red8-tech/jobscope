from jobscope.ai.retrieval import TfidfRetriever

DOCS = {
    1: "python fastapi backend developer",
    2: "react frontend javascript",
    3: "data analyst sql tableau",
}


def test_most_similar_document_ranks_first() -> None:
    retriever = TfidfRetriever(DOCS)
    assert retriever.top_k("I build fastapi services in python", k=3)[0][0] == 1
    assert retriever.top_k("sql analytics", k=3)[0][0] == 3


def test_unrelated_documents_are_excluded() -> None:
    results = TfidfRetriever(DOCS).top_k("python", k=3)
    assert [doc_id for doc_id, _ in results] == [1]


def test_k_limits_results() -> None:
    docs = {1: "python sql", 2: "python react", 3: "python docker"}
    assert len(TfidfRetriever(docs).top_k("python", k=2)) == 2


def test_empty_inputs_return_nothing() -> None:
    assert TfidfRetriever({}).top_k("python", k=3) == []
    assert TfidfRetriever(DOCS).top_k("   ", k=3) == []
    assert TfidfRetriever({1: "the and of"}).top_k("python", k=3) == []