import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

/**
 * Wrap any page that requires login.
 * Pass allowedRoles=["admin"] etc. to also enforce RBAC on the frontend
 * (the backend enforces it for real - this just avoids showing a page
 * the user can't use, and a friendlier message than a raw 403).
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="page-center">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="card">
        <h2>Access restricted</h2>
        <p>
          Your role is <strong>{user.role}</strong>. This page requires:{" "}
          {allowedRoles.join(" or ")}.
        </p>
      </div>
    );
  }

  return children;
}