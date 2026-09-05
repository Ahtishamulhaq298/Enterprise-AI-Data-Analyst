/**
 * Thin fetch wrapper around the FastAPI backend.
 * Reads the JWT from localStorage and attaches it automatically.
 * Every function throws an Error with a readable message on failure,
 * so pages can just try/catch and show err.message.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

function getToken() {
  return localStorage.getItem("eaida_token");
}

export function setToken(token) {
  if (token) localStorage.setItem("eaida_token", token);
  else localStorage.removeItem("eaida_token");
}

/** Fetch a protected binary/file endpoint and return it as a Blob (adds the auth header, unlike a plain <a href>). */
async function requestBlob(path) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* body wasn't JSON, keep default message */
    }
    throw new Error(detail);
  }
  return res.blob();
}

async function request(path, { method = "GET", body, isForm = false, params } = {}) {
  let url = `${BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
    ).toString();
    if (qs) url += `?${qs}`;
  }

  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      `Request failed with status ${res.status}`;
    const err = new Error(
      typeof message === "string" ? message : JSON.stringify(message)
    );
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  // ---- auth ----
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  me: () => request("/auth/me"),
  listUsers: () => request("/auth/users"),
  updateUserRole: (userId, role) =>
    request(`/auth/users/${userId}/role`, { method: "PATCH", body: { role } }),
  deactivateUser: (userId) => request(`/auth/users/${userId}/deactivate`, { method: "PATCH" }),

  // ---- datasets ----
  uploadDataset: (file, name, description) => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name || "");
    form.append("description", description || "");
    return request("/datasets/upload", { method: "POST", body: form, isForm: true });
  },
  listDatasets: () => request("/datasets"),
  getDataset: (id) => request(`/datasets/${id}`),
  previewDataset: (id, rows = 20) => request(`/datasets/${id}/preview`, { params: { rows } }),
  datasetSchema: (id) => request(`/datasets/${id}/schema`),
  deleteDataset: (id) => request(`/datasets/${id}`, { method: "DELETE" }),

  // ---- profiling ----
  runProfiling: (dataset_id) => request("/profiling/run", { method: "POST", body: { dataset_id } }),
  qualityCheck: (id) => request(`/profiling/dataset/${id}/quality`),
  correlations: (id) => request(`/profiling/dataset/${id}/correlations`),

  // ---- features ----
  suggestFeatures: (id, target_column) =>
    request(`/features/suggest/${id}`, { params: { target_column } }),
  applyFeatures: (payload) => request("/features/apply", { method: "POST", body: payload }),

  // ---- automl ----
  trainAutoML: (payload) => request("/automl/train", { method: "POST", body: payload }),
  listAutoMLJobs: (dataset_id) => request("/automl/jobs", { params: { dataset_id } }),
  getAutoMLJob: (jobId) => request(`/automl/jobs/${jobId}`),
  leaderboard: (jobId) => request(`/automl/jobs/${jobId}/leaderboard`),
  predict: (payload) => request("/automl/predict", { method: "POST", body: payload }),

  // ---- explain ----
  explainGlobal: (payload) => request("/explain/global", { method: "POST", body: payload }),
  explainLocal: (payload) => request("/explain/local", { method: "POST", body: payload }),

  // ---- rag ----
  uploadDocument: (file, title, visibility_role) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title || "");
    form.append("visibility_role", visibility_role || "viewer");
    return request("/rag/documents", { method: "POST", body: form, isForm: true });
  },
  listDocuments: () => request("/rag/documents"),
  deleteDocument: (id) => request(`/rag/documents/${id}`, { method: "DELETE" }),
  ragSearch: (payload) => request("/rag/search", { method: "POST", body: payload }),
  ragQuery: (payload) => request("/rag/query", { method: "POST", body: payload }),

  // ---- agents ----
  listTools: () => request("/agents/tools"),
  runAgentAnalysis: (payload) => request("/agents/analyze", { method: "POST", body: payload }),

  // ---- reports ----
  generateReport: (payload) => request("/reports/generate", { method: "POST", body: payload }),
  listReports: () => request("/reports"),
  downloadReport: (jobId) => requestBlob(`/reports/${jobId}/download`),
  downloadModel: (jobId) => requestBlob(`/automl/jobs/${jobId}/model`),

  // ---- evaluation ----
  evaluateRag: (payload) => request("/evaluation/rag", { method: "POST", body: payload }),
  modelMetrics: () => request("/evaluation/models"),

  // ---- health ----
  health: () => request("/health"),
};