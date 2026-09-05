import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Datasets() {
  const { user } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);

  const canWrite = user.role === "admin" || user.role === "analyst";

  async function refresh() {
    setLoading(true);
    try {
      setDatasets(await api.listDatasets());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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
      await api.uploadDataset(file, name, description);
      setFile(null);
      setName("");
      setDescription("");
      e.target.reset();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this dataset? This cannot be undone.")) return;
    try {
      await api.deleteDataset(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <h1>Datasets</h1>

      {error && <div className="alert alert-error">{error}</div>}

      {canWrite && (
        <form className="card" onSubmit={handleUpload}>
          <h2>Upload a dataset</h2>
          <p className="muted">Accepted: .csv .xlsx .xls .json .parquet .txt</p>
          <label>File</label>
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.json,.parquet,.txt"
            onChange={(e) => setFile(e.target.files[0])}
            required
          />
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="customers" />
          <label>Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
          <button className="btn btn-primary" type="submit" disabled={uploading || !file}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
      )}

      <div className="card">
        <h2>All datasets</h2>
        {loading && <p>Loading...</p>}
        {!loading && datasets.length === 0 && <p className="muted">No datasets yet.</p>}
        {datasets.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Type</th>
                <th>Rows</th>
                <th>Columns</th>
                <th>Uploaded</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>
                    <Link to={`/datasets/${d.id}`}>{d.name}</Link>
                  </td>
                  <td>{d.file_type}</td>
                  <td>{d.n_rows}</td>
                  <td>{d.n_cols}</td>
                  <td>{new Date(d.created_at).toLocaleString()}</td>
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
    </div>
  );
}