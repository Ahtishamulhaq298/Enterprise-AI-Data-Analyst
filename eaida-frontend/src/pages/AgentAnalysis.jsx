import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function AgentAnalysis() {
  const { user } = useAuth();
  const canWrite = user.role === "admin" || user.role === "analyst";

  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState("");
  const [question, setQuestion] = useState("");
  const [targetColumn, setTargetColumn] = useState("");
  const [result, setResult] = useState(null);
  const [tools, setTools] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listDatasets().then(setDatasets).catch((e) => setError(e.message));
    api
      .listTools()
      .then((r) => setTools(r.tools))
      .catch(() => {});
  }, []);

  async function run(e) {
    e.preventDefault();
    if (!datasetId || !question.trim()) {
      setError("Pick a dataset and enter a question.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.runAgentAnalysis({
        dataset_id: Number(datasetId),
        question,
        target_column: targetColumn || null,
      });
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Multi-Agent Analysis</h1>
      <p className="muted">
        Runs the planner - profiler - modeler - insight workflow (LangGraph) and returns a
        business-facing answer grounded in your data and knowledge base.
      </p>

      {error && <div className="alert alert-error">{error}</div>}

      {canWrite && (
        <form className="card" onSubmit={run}>
          <label>Dataset</label>
          <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} required>
            <option value="">Select a dataset...</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                #{d.id} - {d.name}
              </option>
            ))}
          </select>

          <label>Target column (optional - enables modeling)</label>
          <input
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            placeholder="e.g. churn"
          />

          <label>Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={2}
            placeholder="What is driving churn in this dataset and what should we do about it?"
            required
          />

          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Running agents (can take a minute)..." : "Run analysis"}
          </button>
        </form>
      )}

      {result && (
        <div className="card">
          <h2>Answer</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{result.final_answer}</p>

          <h3>Agent steps</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {result.steps.map((s, i) => (
                <tr key={i}>
                  <td>{s.agent}</td>
                  <td>
                    <pre className="pre-wrap">{JSON.stringify(s.output, null, 2)}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tools.length > 0 && (
        <div className="card">
          <h2>Available agent tools (function calling)</h2>
          <ul>
            {tools.map((t) => (
              <li key={t.function.name}>
                <strong>{t.function.name}</strong> - {t.function.description}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}