import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function KnowledgeBase() {
  const { user } = useAuth();
  const canWrite = user.role === "admin" || user.role === "analyst";

  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");

  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);

  async function refresh() {
    try {
      setDocs(await api.listDocuments());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadDocument(file, title, "viewer");
      setFile(null);
      setTitle("");
      e.target.reset();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this document from the knowledge base?")) return;
    try {
      await api.deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    setError("");
    try {
      setAnswer(await api.ragQuery({ question, top_k: 5, mode: "hybrid" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="page">
      <h1>Knowledge Base & RAG</h1>
      <p className="muted">
        Upload documents to index them (hybrid semantic + keyword search), then ask grounded
        questions with citations.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {canWrite && (
        <form className="card" onSubmit={handleUpload}>
          <h2>Upload a document</h2>
          <p className="muted">Accepted: .pdf .docx .txt .md .csv</p>
          <label>File</label>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,.csv"
            onChange={(e) => setFile(e.target.files[0])}
            required
          />
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
          <button className="btn btn-primary" type="submit" disabled={uploading || !file}>
            {uploading ? "Indexing..." : "Upload & index"}
          </button>
        </form>
      )}

      <div className="card">
        <h2>Indexed documents</h2>
        {docs.length === 0 ? (
          <p className="muted">No documents indexed yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Chunks</th>
                <th>Visibility</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.title}</td>
                  <td>{d.n_chunks}</td>
                  <td>{d.visibility_role}</td>
                  <td>
                    {user.role === "admin" && (
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(d.id)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <form className="card" onSubmit={handleAsk}>
        <h2>Ask a question</h2>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is the refund policy?"
        />
        <button className="btn btn-primary" type="submit" disabled={asking}>
          {asking ? "Thinking..." : "Ask"}
        </button>

        {answer && (
          <div className="answer-box">
            <p>{answer.answer}</p>
            {answer.citations.length > 0 && (
              <>
                <h4>Sources</h4>
                <ul>
                  {answer.citations.map((c, i) => (
                    <li key={i}>
                      <strong>{c.title}</strong> (score {c.score}) - {c.snippet}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </form>
    </div>
  );
}