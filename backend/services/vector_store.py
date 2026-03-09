from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from config import settings


class VectorStoreService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self._ensure_index()

    def _ensure_index(self):
        existing = [idx.name for idx in self.pc.list_indexes()]
        if self.index_name not in existing:
            self.pc.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=settings.pinecone_environment)
            )
        self.index = self.pc.Index(self.index_name)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts).tolist()
        return embeddings

    async def upsert_documents(self, chunks: List[Dict[str, Any]], namespace: str, filename: str) -> str:
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embed_texts(texts)
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vectors.append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": {**chunk["metadata"], "text": chunk["text"]}
            })
        BATCH_SIZE = 100
        for i in range(0, len(vectors), BATCH_SIZE):
            self.index.upsert(vectors=vectors[i:i + BATCH_SIZE], namespace=namespace)
        return chunks[0]["metadata"]["document_id"]

    async def similarity_search(self, query: str, namespace: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embeddings = await self.embed_texts([query])
        results = self.index.query(
            vector=query_embeddings[0],
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )
        matches = []
        for match in results.matches:
            matches.append({
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "filename": match.metadata.get("filename", "unknown"),
                "chunk_index": match.metadata.get("chunk_index", 0),
                "document_id": match.metadata.get("document_id", "")
            })
        return matches

    async def list_documents(self, namespace: str) -> List[Dict[str, Any]]:
        try:
            stats = self.index.describe_index_stats()
            ns_stats = stats.namespaces.get(namespace, {})
            return [{"namespace": namespace, "vector_count": ns_stats.get("vector_count", 0)}]
        except Exception:
            return []

    async def delete_document(self, document_id: str, namespace: str):
        results = self.index.query(
            vector=[0.0] * 384,
            top_k=10000,
            namespace=namespace,
            filter={"document_id": {"$eq": document_id}},
            include_metadata=False
        )
        ids_to_delete = [m.id for m in results.matches]
        if ids_to_delete:
            self.index.delete(ids=ids_to_delete, namespace=namespace)

    async def clear_namespace(self, namespace: str):
        self.index.delete(delete_all=True, namespace=namespace)
