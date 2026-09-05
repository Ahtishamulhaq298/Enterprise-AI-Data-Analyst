import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

const TABS = ["Preview", "Profiling", "Feature Engineering", "AutoML", "Explainability", "Report"];

export default function DatasetDetail() {
  const { id } = useParams();
  const datasetId = Number(id);
  const { user } = useAuth();
  const canWrite = user.role === "admin" || user.role === "analyst";

  const [dataset, setDataset] = useState(null);
  const [tab, setTab] = useState("Preview");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDataset(datasetId).then(setDataset).catch((e) => setError(e.message));
  }, [datasetId]);

  return (
    <div className="page">
      <h1>{dataset ? dataset.name : `Dataset #${datasetId}`}</h1>
      {dataset && (
        <p className="muted">
          {dataset.n_rows} rows x {dataset.n_cols} columns - {dataset.file_type} - uploaded{" "}
          {new Date(dataset.created_at).toLocaleString()}
        </p>
      )}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={t === tab ? "tab tab-active" : "tab"}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === "Preview" && <PreviewTab datasetId={datasetId} />}
        {tab === "Profiling" && <ProfilingTab datasetId={datasetId} canWrite={canWrite} />}
        {tab === "Feature Engineering" && (
          <FeatureTab datasetId={datasetId} canWrite={canWrite} />
        )}
        {tab === "AutoML" && <AutoMLTab datasetId={datasetId} canWrite={canWrite} />}
        {tab === "Explainability" && <ExplainTab datasetId={datasetId} />}
        {tab === "Report" && <ReportTab datasetId={datasetId} canWrite={canWrite} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Preview
function PreviewTab({ datasetId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .previewDataset(datasetId, 20)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [datasetId]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return <p>Loading...</p>;

  return (
    <div className="card">
      <h2>First {data.rows.length} rows</h2>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              {data.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i}>
                {data.columns.map((c) => (
                  <td key={c}>{String(row[c] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Profiling
function ProfilingTab({ datasetId, canWrite }) {
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    try {
      setJob(await api.runProfiling(datasetId));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Data profiling</h2>
        {canWrite && (
          <button className="btn btn-primary" onClick={run} disabled={busy}>
            {busy ? "Profiling..." : "Run profiling"}
          </button>
        )}
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {job && job.status === "failed" && <div className="alert alert-error">{job.error}</div>}
      {job && job.status === "success" && (
        <>
          <div className="grid-3">
            <div className="stat-card">
              <span className="stat-value">{job.result.shape.rows}</span>
              <span className="stat-label">Rows</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{job.result.shape.columns}</span>
              <span className="stat-label">Columns</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{job.result.duplicate_rows}</span>
              <span className="stat-label">Duplicate rows</span>
            </div>
          </div>

          {job.result.quality_issues.length > 0 && (
            <>
              <h3>Data quality issues</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Issue</th>
                    <th>Severity</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {job.result.quality_issues.map((i, idx) => (
                    <tr key={idx}>
                      <td>{i.column}</td>
                      <td>{i.issue}</td>
                      <td>
                        <span className={`badge badge-${i.severity}`}>{i.severity}</span>
                      </td>
                      <td>{i.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h3>Columns</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Missing %</th>
                <th>Unique</th>
              </tr>
            </thead>
            <tbody>
              {job.result.columns.map((c) => (
                <tr key={c.name}>
                  <td>{c.name}</td>
                  <td>{c.dtype}</td>
                  <td>{c.missing_pct}%</td>
                  <td>{c.unique}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Features
function FeatureTab({ datasetId, canWrite }) {
  const [target, setTarget] = useState("");
  const [suggestions, setSuggestions] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState(null);

  async function fetchSuggestions() {
    setBusy(true);
    setError("");
    try {
      const res = await api.suggestFeatures(datasetId, target || undefined);
      setSuggestions(res.suggestions);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    setBusy(true);
    setError("");
    try {
      const res = await api.applyFeatures({
        dataset_id: datasetId,
        target_column: target || null,
        save_as_new_dataset: true,
      });
      setApplied(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Feature engineering</h2>
      <label>Target column (optional)</label>
      <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="e.g. churn" />
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={fetchSuggestions} disabled={busy}>
          Suggest transformations
        </button>
        {canWrite && (
          <button className="btn btn-primary" onClick={apply} disabled={busy}>
            Apply & save as new dataset
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {suggestions && (
        <table className="table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Suggested action</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {suggestions.map((s, i) => (
              <tr key={i}>
                <td>{s.column}</td>
                <td>{s.action}</td>
                <td>{s.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {applied && (
        <div className="alert alert-success">
          Created dataset #{applied.new_dataset_id} - new shape: {applied.new_shape.rows} rows x{" "}
          {applied.new_shape.columns} columns.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- AutoML
function AutoMLTab({ datasetId, canWrite }) {
  const [target, setTarget] = useState("");
  const [maxModels, setMaxModels] = useState(4);
  const [cvFolds, setCvFolds] = useState(3);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function train() {
    if (!target) {
      setError("Target column is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api.trainAutoML({
        dataset_id: datasetId,
        target_column: target,
        max_models: Number(maxModels),
        cv_folds: Number(cvFolds),
      });
      setJob(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>AutoML - train & compare models</h2>
      {canWrite && (
        <>
          <label>Target column</label>
          <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="e.g. churn" />
          <div className="grid-2">
            <div>
              <label>Max models to try</label>
              <input
                type="number"
                min={1}
                max={10}
                value={maxModels}
                onChange={(e) => setMaxModels(e.target.value)}
              />
            </div>
            <div>
              <label>Cross-validation folds</label>
              <input
                type="number"
                min={2}
                max={10}
                value={cvFolds}
                onChange={(e) => setCvFolds(e.target.value)}
              />
            </div>
          </div>
          <button className="btn btn-primary" onClick={train} disabled={busy}>
            {busy ? "Training (this can take a minute)..." : "Train models"}
          </button>
        </>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {job && job.status === "failed" && <div className="alert alert-error">{job.error}</div>}

      {job && job.status === "success" && (
        <>
          <div className="alert alert-success">
            Job #{job.id} - best model: <strong>{job.result.best_model.name}</strong> (task:{" "}
            {job.result.task_type})
          </div>
          <h3>Leaderboard</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Status</th>
                <th>Metrics</th>
                <th>CV mean</th>
                <th>Train (s)</th>
              </tr>
            </thead>
            <tbody>
              {job.result.leaderboard.map((row) => (
                <tr key={row.model}>
                  <td>{row.model}</td>
                  <td>{row.status}</td>
                  <td>
                    {row.metrics
                      ? Object.entries(row.metrics)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")
                      : "-"}
                  </td>
                  <td>{row.cv_mean ?? "-"}</td>
                  <td>{row.train_seconds ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">Job ID {job.id} - use it in the Explainability and Report tabs.</p>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Explain
function ExplainTab({ datasetId }) {
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!jobId) {
      setError("Enter the AutoML job ID first (from the AutoML tab).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setResult(await api.explainGlobal({ job_id: Number(jobId), top_k: 10 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Explainability</h2>
      <label>AutoML job ID</label>
      <input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="e.g. 3" />
      <button className="btn btn-primary" onClick={run} disabled={busy}>
        {busy ? "Explaining..." : "Explain top features"}
      </button>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <>
          <p className="muted">Method: {result.method}</p>
          <table className="table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Importance</th>
              </tr>
            </thead>
            <tbody>
              {result.features.map((f) => (
                <tr key={f.feature}>
                  <td>{f.feature}</td>
                  <td>{f.importance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Report
function ReportTab({ datasetId, canWrite }) {
  const [automlJobId, setAutomlJobId] = useState("");
  const [format, setFormat] = useState("markdown");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      const res = await api.generateReport({
        dataset_id: datasetId,
        automl_job_id: automlJobId ? Number(automlJobId) : null,
        format,
        title: "Automated Data Analysis Report",
      });
      setJob(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // A plain <a href> would not include the Authorization header, so the
  // protected download endpoint would reject it with 401. Fetch the file
  // with our authenticated client instead, then hand the browser a blob URL.
  async function download() {
    try {
      const blob = await api.downloadReport(job.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${job.id}.${format === "pdf" ? "pdf" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card">
      <h2>Generate report</h2>
      {canWrite && (
        <>
          <label>AutoML job ID (optional)</label>
          <input
            value={automlJobId}
            onChange={(e) => setAutomlJobId(e.target.value)}
            placeholder="e.g. 3"
          />
          <label>Format</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="markdown">Markdown</option>
            <option value="pdf">PDF</option>
          </select>
          <button className="btn btn-primary" onClick={generate} disabled={busy}>
            {busy ? "Generating..." : "Generate report"}
          </button>
        </>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {job && job.status === "success" && (
        <div className="alert alert-success">
          Report ready.{" "}
          <button className="btn btn-secondary btn-sm" onClick={download}>
            Download
          </button>
        </div>
      )}
      {job && job.status === "failed" && <div className="alert alert-error">{job.error}</div>}
    </div>
  );
}