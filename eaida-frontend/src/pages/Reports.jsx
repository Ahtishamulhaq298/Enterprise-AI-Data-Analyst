import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listReports()
      .then(setReports)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function download(job) {
    try {
      const blob = await api.downloadReport(job.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${job.id}.${job.result.format === "pdf" ? "pdf" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <h1>Reports</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {loading && <p>Loading...</p>}
      {!loading && reports.length === 0 && (
        <p className="muted">
          No reports yet. Generate one from a dataset's "Report" tab.
        </p>
      )}
      {reports.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Dataset</th>
              <th>Status</th>
              <th>Format</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.dataset_id}</td>
                <td>{r.status}</td>
                <td>{r.result?.format || "-"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  {r.status === "success" && (
                    <button className="btn btn-secondary btn-sm" onClick={() => download(r)}>
                      Download
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}