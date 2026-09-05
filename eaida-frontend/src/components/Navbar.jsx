import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/datasets", label: "Datasets" },
  { to: "/knowledge-base", label: "Knowledge Base" },
  { to: "/agent", label: "Agent Analysis" },
  { to: "/reports", label: "Reports" },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <div className="navbar-brand">Enterprise AI Data Analyst</div>
      <nav className="navbar-links">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {l.label}
          </NavLink>
        ))}
        {user.role === "admin" && (
          <NavLink to="/admin/users" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Users
          </NavLink>
        )}
      </nav>
      <div className="navbar-user">
        <span className="role-badge" data-role={user.role}>
          {user.role}
        </span>
        <span>{user.full_name || user.email}</span>
        <button className="btn btn-ghost" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}