import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [reports, setReports] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [ds, rp] = await Promise.all([api.listDatasets(), api.listReports()]);
        setDatasets(ds);
        setReports(rp);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="page">
      <h1>Welcome, {user.full_name || user.email}</h1>
      <p className="muted">
        Role: <strong>{user.role}</strong> - here's a quick overview of your workspace.
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <p>Loading...</p>}

      <div className="grid-3">
        <div className="stat-card">
          <span className="stat-value">{datasets.length}</span>
          <span className="stat-label">Datasets uploaded</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{reports.length}</span>
          <span className="stat-label">Reports generated</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{user.role}</span>
          <span className="stat-label">Your access level</span>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Recent datasets</h2>
          <Link className="btn btn-primary" to="/datasets">
            Go to Datasets
          </Link>
        </div>
        {datasets.length === 0 && !loading ? (
          <p className="muted">No datasets yet. Upload one to get started.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Rows</th>
                <th>Columns</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {datasets.slice(0, 5).map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/datasets/${d.id}`}>{d.name}</Link>
                  </td>
                  <td>{d.n_rows}</td>
                  <td>{d.n_cols}</td>
                  <td>{new Date(d.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}