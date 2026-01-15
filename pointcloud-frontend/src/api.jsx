import axios from "axios";

// All API URLs from environment variables - no hardcoding
const API_URL = import.meta.env.VITE_BACKEND_API_URL || "http://127.0.0.1:8000";
const APS_API_URL =
  import.meta.env.VITE_APS_API_URL
  || (String(window.location.port) === "3001" ? window.location.origin : "http://127.0.0.1:3001");

export async function uploadPointCloud(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post(`${API_URL}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function chatWithScene(question, scene_id = null) {
  const payload = { question };
  if (scene_id) payload.scene_id = scene_id;

  const res = await axios.post(`${API_URL}/chat`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 60000,
  });
  return res.data;
}

export async function getApsTwoLeggedToken() {
  const res = await axios.get(`${APS_API_URL}/aps/token`, {
    timeout: 30000,
    headers: { "Accept": "application/json" },
  });
  return res.data;
}