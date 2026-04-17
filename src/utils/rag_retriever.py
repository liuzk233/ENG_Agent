"""
RAG Retriever Module

Core functionality:
- Semantic search over 考研英语真题语料库
- Top-K retrieval with relevance filtering
- Query construction for multi-word scenarios
- Dynamic style filtering based on metadata
"""

import logging
from typing import List, Optional

import chromadb
from openai import OpenAI

from src.utils.config import DASHSCOPE_API_KEY, BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    RAG Retriever for 考研英语真题风格 grounding

    Design decisions:
    1. Use cosine similarity for semantic matching
    2. Apply relevance threshold (0.75) to filter noisy results
    3. Top-K=5 to balance context quality vs token budget
    4. Support metadata filtering by style/category
    """

    def __init__(
        self,
        collection_name: str = "vocabweaver_rag",
        persist_dir: str = "data/vector_store/chromadb",
        embedding_model: str = "text-embedding-v3",
        embedding_dim: int = 1024,
        top_k: int = 5,
        relevance_threshold: float = 0.75,
    ):
        self.top_k = top_k
        self.relevance_threshold = relevance_threshold
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_dir)

        # Load collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"✅ RAG Retriever initialized: {collection_name} (Top-K={top_k}, Threshold={relevance_threshold})")
        except Exception as e:
            logger.error(f"❌ Failed to load collection '{collection_name}': {e}")
            raise

        # Initialize embedding client for query embedding
        self.embedding_client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)

        # Cache available styles/categories
        self._available_styles = None

    def _get_available_styles(self) -> List[str]:
        """Get list of available styles/categories from the collection metadata"""
        if self._available_styles is None:
            try:
                # Get a sample to check metadata structure
                sample = self.collection.get(limit=10, include=["metadatas"])
                metadatas = sample["metadatas"]
                # Extract unique categories
                self._available_styles = list(set(
                    [m.get("category") for m in metadatas if m.get("category")]
                ))
                logger.info(f"📚 Available styles: {self._available_styles}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get available styles: {e}")
                self._available_styles = []
        return self._available_styles

    def _embed_query(self, query: str) -> List[float]:
        """Embed the query text using DashScope embedding"""
        try:
            response = self.embedding_client.embeddings.create(
                model=self.embedding_model,
                input=query,
                dimensions=self.embedding_dim,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Query embedding failed: {e}")
            raise

    def _build_query(
        self,
        target_words: List[str],
        style: str = None
    ) -> str:
        """
        Build optimized query for retrieval

        Strategy:
        - Combine target words for semantic coverage
        - Add style keywords for better matching
        - If no style specified, use target words only
        """
        if not target_words:
            return style if style else ""

        # Join words with space for multi-word context
        words_part = " ".join(target_words)

        if style:
            query = f"{words_part} {style}"
        else:
            query = words_part

        return query

    def retrieve(
        self,
        target_words: List[str],
        style: str = None
    ) -> List[str]:
        """
        Retrieve reference texts from vector database

        Args:
            target_words: Target vocabulary words
            style: Style/category filter (e.g., "exam_paper")

        Returns:
            List of relevant reference texts (filtered by threshold)
        """
        try:
            query = self._build_query(target_words, style)
            logger.info(f"🔍 Query: {query}")

            # Embed the query
            query_embedding = self._embed_query(query)

            # Build query with optional style filter
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": self.top_k
            }

            # Add metadata filter if style is specified
            if style:
                query_kwargs["where"] = {"category": style}
                logger.info(f"🎯 Filtering by style: {style}")

            # Execute semantic search
            results = self.collection.query(**query_kwargs)

            # Extract texts and distances
            texts = results['documents'][0]
            distances = results['distances'][0]

            # Apply relevance threshold filter
            # ChromaDB returns distance, convert to similarity: similarity = 1 - distance
            filtered_results = [
                text for text, dist in zip(texts, distances)
                if (1 - dist) >= self.relevance_threshold
            ]

            if not filtered_results:
                logger.warning(f"⚠️  No results above threshold {self.relevance_threshold}")
                return []

            logger.info(f"✅ Retrieved {len(filtered_results)}/{len(texts)} references (threshold={self.relevance_threshold})")
            return filtered_results

        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []

    def should_retrieve(self, target_words: List[str]) -> bool:
        """
        Semantic Gating: Decide whether to perform retrieval

        Criteria:
        1. At least 2 target words (multi-word context better)
        2. Words not too common (skip if too generic)

        Returns:
            bool: True if retrieval is beneficial
        """
        # Basic gating: at least 2 words
        if len(target_words) < 2:
            logger.info(f"⚡ Semantic Gating: Skip retrieval (only {len(target_words)} word(s))")
            return False

        return True
