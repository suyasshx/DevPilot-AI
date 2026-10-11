"""
DevPilot AI - Local Embedding Engine.

Generates 384-dimensional unit-normalized embeddings using Sentence-Transformers (all-MiniLM-L6-v2).
Provides fallback feature-hashing embedding generator for testing without internet or PyTorch.
"""

import math
import hashlib
from typing import List, Union
import logging

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class EmbeddingEngine:
    """Wrapper for local Sentence-Transformers embedding inference."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model = None
        self._is_sentence_transformer_available = False
        self._check_library()

    def _check_library(self) -> None:
        """Check if sentence-transformers is installed and available."""
        try:
            import sentence_transformers
            self._is_sentence_transformer_available = True
        except ImportError:
            self._is_sentence_transformer_available = False
            logger.info("sentence-transformers not installed; using deterministic feature-hashing embeddings.")

    def _get_model(self):
        """Lazy loader for SentenceTransformer model."""
        if self._model is None and self._is_sentence_transformer_available:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Encode text string or list of strings into 384-dimensional unit-normalized vectors.
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        model = self._get_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, normalize_embeddings=True)
                return [e.tolist() for e in embeddings]
            except Exception as exc:
                logger.warning(f"SentenceTransformer encode failed ({exc}); falling back to deterministic projection.")

        # Deterministic 384-dimensional fallback projection
        return [self._hash_encode(t) for t in texts]

    def _hash_encode(self, text: str) -> List[float]:
        """
        Deterministic, unit-normalized 384-dimensional pseudo-semantic vector
        derived from n-gram and token hashing. Used as reliable fallback.
        """
        vec = [0.0] * EMBEDDING_DIM
        tokens = text.lower().split()
        if not tokens:
            return vec

        for idx, token in enumerate(tokens):
            # Primary token hash
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
            h2 = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
            weight = 1.0 / math.sqrt(len(tokens))
            vec[h1] += weight
            vec[h2] -= (weight * 0.5)

            # Bigram hash
            if idx > 0:
                bigram = f"{tokens[idx-1]}_{token}"
                bh = int(hashlib.sha1(bigram.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
                vec[bh] += (weight * 0.75)

        # Unit-normalize vector: v / ||v||
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec


# Global singleton embedding engine
embedding_engine = EmbeddingEngine()
