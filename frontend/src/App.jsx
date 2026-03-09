import { useState, useRef, useCallback } from "react";
import { Upload, Send, FileText, Loader2, Zap, X, ChevronDown, ChevronUp } from "lucide-react";

const API_BASE = "https://smart-doc-qa-backend.onrender.com";
const NAMESPACE = "default";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" });

  const uploadFile = async (file) => {
    setIsUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("namespace", NAMESPACE);
    try {
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setDocuments((prev) => [...prev, {
        id: data.document_id, name: file.name,
        chunks: data.chunks_created, size: (file.size / 1024).toFixed(1) + " KB",
      }]);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileSelect = (files) => Array.from(files).forEach(uploadFile);
  const handleDrop = useCallback((e) => { e.preventDefault(); setDragOver(false); handleFileSelect(e.dataTransfer.files); }, []);

  const askQuestion = async () => {
    if (!question.trim() || isAsking) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setQuestion("");
    setIsAsking(true);
    setTimeout(scrollToBottom, 100);
    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, namespace: NAMESPACE }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer, sources: data.sources, id: Date.now() }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err.message}`, isError: true, id: Date.now() }]);
    } finally {
      setIsAsking(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  const handleKeyDown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askQuestion(); } };
  const toggleSources = (msgId) => setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));

  return (
    <div style={{ fontFamily: "Times New Roman, Times, serif", fontSize: "16px" }} className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between bg-gray-950">
        <div className="flex flex-col items-start gap-1">
          <img src="/logo.png" alt="DocuMind" className="h-24 object-contain" />
          
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
          <span style={{ fontSize: "14px" }} className="text-gray-400">API Connected</span>
        </div>
      </header>
      <div className="flex h-[calc(100vh-95px)]">
        <aside className="w-72 border-r border-gray-800 flex flex-col bg-gray-950">
          <div className="p-4 border-b border-gray-800">
            <p style={{ fontSize: "13px" }} className="text-gray-400 uppercase tracking-wider mb-3 font-bold">Documents</p>
            <div onDrop={handleDrop} onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded p-4 text-center cursor-pointer transition-all ${dragOver ? "border-emerald-500 bg-emerald-500/10" : "border-gray-700 hover:border-gray-500 hover:bg-gray-900"}`}>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.md,.docx" className="hidden" onChange={(e) => handleFileSelect(e.target.files)} />
              {isUploading ? (
                <div className="flex flex-col items-center gap-2">
                  <Loader2 size={20} className="animate-spin text-emerald-500" />
                  <p style={{ fontSize: "14px" }} className="text-gray-400">Processing...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload size={20} className={dragOver ? "text-emerald-500" : "text-gray-500"} />
                  <p style={{ fontSize: "14px" }} className="text-gray-400">Drop files or click to upload</p>
                  <p style={{ fontSize: "13px" }} className="text-gray-600">PDF, TXT, MD, DOCX</p>
                </div>
              )}
            </div>
            {uploadError && <div className="mt-2 p-2 bg-red-950 border border-red-800 rounded text-red-400" style={{ fontSize: "13px" }}>{uploadError}</div>}
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {documents.length === 0 ? (
              <div className="text-center py-8">
                <FileText size={32} className="text-gray-700 mx-auto mb-2" />
                <p style={{ fontSize: "14px" }} className="text-gray-600">No documents yet</p>
              </div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="bg-gray-900 border border-gray-800 rounded p-3 group">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0">
                      <FileText size={14} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0">
                        <p style={{ fontSize: "14px" }} className="text-white truncate font-medium">{doc.name}</p>
                        <p style={{ fontSize: "13px" }} className="text-gray-500">{doc.chunks} chunks</p>
                      </div>
                    </div>
                    <button onClick={() => setDocuments((prev) => prev.filter((d) => d.id !== doc.id))} className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all">
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
        <main className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 bg-gray-900 border border-gray-800 rounded-xl flex items-center justify-center mb-4">
                  <Zap size={28} className="text-emerald-500" />
                </div>
                <h2 style={{ fontSize: "22px" }} className="font-bold text-white mb-2">Ready to Answer</h2>
                <p style={{ fontSize: "16px" }} className="text-gray-500 max-w-md">Upload documents on the left, then ask anything.</p>
                <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-md">
                  {["What are the main topics covered?", "Summarize the key findings", "What conclusions does the author draw?"].map((hint) => (
                    <button key={hint} onClick={() => setQuestion(hint)} style={{ fontSize: "15px" }} className="text-left text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded p-3 transition-all">
                      "{hint}"
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-2xl ${msg.role === "user" ? "w-auto" : "w-full"}`}>
                    <p style={{ fontSize: "13px" }} className={`mb-1 font-bold uppercase tracking-wider ${msg.role === "user" ? "text-right text-emerald-600" : "text-gray-600"}`}>
                      {msg.role === "user" ? "You" : "DocuMind"}
                    </p>
                    <div style={{ fontSize: "16px" }} className={`rounded-lg p-4 leading-relaxed ${msg.role === "user" ? "bg-emerald-600 text-white ml-auto w-fit max-w-lg" : msg.isError ? "bg-red-950 border border-red-800 text-red-300" : "bg-gray-900 border border-gray-800 text-gray-200"}`}>
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2">
                        <button onClick={() => toggleSources(msg.id)} style={{ fontSize: "13px" }} className="flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors">
                          {expandedSources[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""} used
                        </button>
                        {expandedSources[msg.id] && (
                          <div className="mt-2 space-y-2">
                            {msg.sources.map((src, si) => (
                              <div key={si} className="bg-gray-900 border border-gray-800 rounded p-3">
                                <div className="flex items-center justify-between mb-1">
                                  <span style={{ fontSize: "13px" }} className="text-emerald-500 font-medium">{src.filename}</span>
                                  <span style={{ fontSize: "12px" }} className="text-gray-600">score: {src.relevance_score}</span>
                                </div>
                                <p style={{ fontSize: "13px" }} className="text-gray-500 leading-relaxed">{src.excerpt}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isAsking && (
              <div className="flex justify-start">
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center gap-3">
                  <Loader2 size={16} className="animate-spin text-emerald-500" />
                  <span style={{ fontSize: "15px" }} className="text-gray-400">Searching documents and generating answer...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="border-t border-gray-800 p-4 bg-gray-950">
            {documents.length === 0 && <p style={{ fontSize: "14px" }} className="text-yellow-600 mb-2 text-center">Upload documents first to enable Q&A</p>}
            <div className="flex gap-3 items-end">
              <textarea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={handleKeyDown}
                placeholder="Ask anything about your documents... (Enter to send)"
                disabled={documents.length === 0} rows={2}
                style={{ fontFamily: "Times New Roman, Times, serif", fontSize: "16px" }}
                className="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-3 text-white placeholder-gray-600 resize-none focus:outline-none focus:border-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors" />
              <button onClick={askQuestion} disabled={!question.trim() || isAsking || documents.length === 0}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-lg p-3 transition-all flex-shrink-0">
                {isAsking ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
