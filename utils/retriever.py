# utils/retriever.py

"""
Retriever module for PDF Q&A prototype.

Handles:
- Embedding generation
- FAISS indexing
- Semantic retrieval
- Page-aware chunk retrieval
"""

from typing import List, Tuple, Dict
import faiss
from sentence_transformers import SentenceTransformer


class DocumentRetriever:
    """
    Handles embedding generation and semantic retrieval using FAISS.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []
        self.embeddings = None

    def build_index(self, chunks: List[Dict]) -> None:
        """
        Build a FAISS index from document chunks.

        Args:
            chunks (List[Dict]): [{"page": 1, "chunk_text": "..."}]
        """
        if not chunks:
            raise ValueError("No chunks provided to build the index.")

        self.chunks = chunks

        texts = [chunk["chunk_text"] for chunk in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        faiss.normalize_L2(embeddings)
        self.embeddings = embeddings

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

    def retrieve(self, query: str, top_k: int = 6) -> List[Tuple[str, float, int, int]]:
        """
        Retrieve top-k relevant chunks.

        Returns:
            List of tuples:
            (chunk_text, similarity_score, chunk_index, page_number)
        """
        if self.index is None:
            raise ValueError("FAISS index is not built yet. Call build_index() first.")

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                chunk_data = self.chunks[idx]
                results.append((
                    chunk_data["chunk_text"],
                    float(score),
                    int(idx),
                    int(chunk_data["page"])
                ))

        return results