import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "analyst",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.register(form);
      // auto sign-in right after registering
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <h1>Create account</h1>
        <p className="muted">Self-registration always caps at analyst/viewer.</p>

        {error && <div className="alert alert-error">{error}</div>}

        <label>Full name</label>
        <input
          value={form.full_name}
          onChange={(e) => update("full_name", e.target.value)}
          required
        />

        <label>Email</label>
        <input
          type="email"
          value={form.email}
          onChange={(e) => update("email", e.target.value)}
          required
        />

        <label>Password</label>
        <input
          type="password"
          minLength={8}
          value={form.password}
          onChange={(e) => update("password", e.target.value)}
          required
        />

        <label>Role</label>
        <select value={form.role} onChange={(e) => update("role", e.target.value)}>
          <option value="analyst">Analyst - upload data, run analyses</option>
          <option value="viewer">Viewer - read only</option>
        </select>

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Creating account..." : "Register"}
        </button>

        <p className="muted center">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}