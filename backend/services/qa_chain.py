from typing import Dict, Any, List
from groq import AsyncGroq
from services.vector_store import VectorStoreService
from config import settings

SYSTEM_PROMPT = """You are an expert document analyst. Answer questions based ONLY on the provided context from the user's documents.
Rules:
1. Only use information from the provided context
2. If the context doesn't contain enough information, say: "I couldn't find relevant information in the uploaded documents to answer this question."
3. Always be precise and cite which document your answer comes from
4. Format your answer clearly using markdown when helpful
"""

class QAChainService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.groq = AsyncGroq(api_key=settings.openai_api_key)

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No relevant documents found."
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"[Source {i}: {chunk['filename']}, chunk {chunk['chunk_index'] + 1}]"
            context_parts.append(f"{source}\n{chunk['text']}")
        return "\n\n---\n\n".join(context_parts)

    def _build_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        sources = []
        for chunk in chunks:
            key = f"{chunk['document_id']}-{chunk['chunk_index']}"
            if key not in seen:
                seen.add(key)
                sources.append({
                    "filename": chunk["filename"],
                    "chunk_index": chunk["chunk_index"],
                    "relevance_score": round(chunk["score"], 3),
                    "excerpt": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
                })
        return sources

    async def answer(self, question: str, namespace: str = "default", top_k: int = 5) -> Dict[str, Any]:
        relevant_chunks = await self.vector_store.similarity_search(
            query=question, namespace=namespace, top_k=top_k
        )
        context = self._build_context(relevant_chunks)
        user_message = f"Context from documents:\n{context}\n\nQuestion: {question}\n\nPlease answer based on the context above."
        response = await self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        return {
            "answer": response.choices[0].message.content,
            "sources": self._build_sources(relevant_chunks),
            "model": "llama-3.3-70b-versatile",
            "chunks_retrieved": len(relevant_chunks)
        }
