import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

const ROLES = ["viewer", "analyst", "admin"];

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      setUsers(await api.listUsers());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function changeRole(userId, role) {
    try {
      await api.updateUserRole(userId, role);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deactivate(userId) {
    if (!confirm("Deactivate this user? They will no longer be able to log in.")) return;
    try {
      await api.deactivateUser(userId);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <h1>User Management</h1>
      <p className="muted">Admin only - manage roles and access.</p>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Active</th>
              <th>Joined</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.email}</td>
                <td>{u.full_name}</td>
                <td>
                  <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)}>
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{u.is_active ? "Yes" : "No"}</td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td>
                  {u.is_active && (
                    <button className="btn btn-danger btn-sm" onClick={() => deactivate(u.id)}>
                      Deactivate
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