import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Datasets from "./pages/Datasets.jsx";
import DatasetDetail from "./pages/DatasetDetail.jsx";
import KnowledgeBase from "./pages/KnowledgeBase.jsx";
import AgentAnalysis from "./pages/AgentAnalysis.jsx";
import Reports from "./pages/Reports.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";

export default function App() {
  return (
    <>
      <Navbar />
      <main className="main">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/datasets"
            element={
              <ProtectedRoute>
                <Datasets />
              </ProtectedRoute>
            }
          />
          <Route
            path="/datasets/:id"
            element={
              <ProtectedRoute>
                <DatasetDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/knowledge-base"
            element={
              <ProtectedRoute>
                <KnowledgeBase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent"
            element={
              <ProtectedRoute>
                <AgentAnalysis />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <Reports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminUsers />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<div className="page">Page not found.</div>} />
        </Routes>
      </main>
    </>
  );
}