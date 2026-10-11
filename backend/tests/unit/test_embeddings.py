"""
DevPilot AI - Unit Tests for Embedding Engine and Vector Math.
"""

import math
from app.rag.embeddings import EmbeddingEngine, EMBEDDING_DIM
from app.rag.vector_store import cosine_similarity


def test_embedding_dimensions_and_normalization() -> None:
    """Verify that embeddings are 384 dimensions and unit-normalized."""
    engine = EmbeddingEngine()
    vectors = engine.encode(["Test query for API automation", "Another test string"])

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == EMBEDDING_DIM
        # Check unit norm: sqrt(sum(v_i^2)) == 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-3


def test_cosine_similarity() -> None:
    """Test cosine similarity calculation on unit vectors."""
    engine = EmbeddingEngine()
    vec1 = engine.encode("negative order quantity validation")[0]
    vec2 = engine.encode("negative order quantity validation")[0]
    vec3 = engine.encode("completely unrelated audio frequency analysis")[0]

    # Identical vectors should have similarity ~ 1.0
    sim_identical = cosine_similarity(vec1, vec2)
    assert abs(sim_identical - 1.0) < 1e-4

    # Related query should be higher than unrelated
    vec_related = engine.encode("negative item boundary checks in orders")[0]
    sim_related = cosine_similarity(vec1, vec_related)
    sim_unrelated = cosine_similarity(vec1, vec3)

    assert sim_related > sim_unrelated
