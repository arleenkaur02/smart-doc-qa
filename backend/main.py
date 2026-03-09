from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from services.document_processor import DocumentProcessor
from services.vector_store import VectorStoreService
from services.qa_chain import QAChainService
from config import settings

app = FastAPI(
    title="Smart Document Q&A API",
    description="RAG-powered document question answering system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
doc_processor = DocumentProcessor()
vector_store = VectorStoreService()
qa_service = QAChainService(vector_store)


class QuestionRequest(BaseModel):
    question: str
    namespace: Optional[str] = "default"
    top_k: Optional[int] = 5


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    question: str


@app.get("/")
async def root():
    return {"message": "Smart Document Q&A API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    namespace: str = "default"
):
    """Upload and process a document into the vector store."""
    
    # Validate file type
    allowed_types = ["application/pdf", "text/plain", "text/markdown",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not supported. Allowed: PDF, TXT, MD, DOCX"
        )
    
    # Read file content
    content = await file.read()
    
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large. Max size is 50MB.")
    
    try:
        # Process document into chunks
        chunks = doc_processor.process(
            content=content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # Store embeddings in Pinecone
        doc_id = await vector_store.upsert_documents(
            chunks=chunks,
            namespace=namespace,
            filename=file.filename
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Document '{file.filename}' processed successfully",
            "document_id": doc_id,
            "chunks_created": len(chunks),
            "namespace": namespace
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question against the uploaded documents."""
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        result = await qa_service.answer(
            question=request.question,
            namespace=request.namespace,
            top_k=request.top_k
        )
        
        return QuestionResponse(
            answer=result["answer"],
            sources=result["sources"],
            question=request.question
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")


@app.get("/documents/{namespace}")
async def list_documents(namespace: str = "default"):
    """List all documents in a namespace."""
    try:
        docs = await vector_store.list_documents(namespace=namespace)
        return {"documents": docs, "namespace": namespace}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{namespace}/{document_id}")
async def delete_document(namespace: str, document_id: str):
    """Delete a document from the vector store."""
    try:
        await vector_store.delete_document(
            document_id=document_id,
            namespace=namespace
        )
        return {"success": True, "message": f"Document {document_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/namespace/{namespace}")
async def clear_namespace(namespace: str):
    """Clear all documents in a namespace."""
    try:
        await vector_store.clear_namespace(namespace=namespace)
        return {"success": True, "message": f"Namespace '{namespace}' cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)