import axios from "axios";

// All API URLs from environment variables - no hardcoding
const API_URL = import.meta.env.VITE_BACKEND_API_URL || (import.meta.env.DEV ? "" : "http://127.0.0.1:8008");
const APS_API_URL =
  import.meta.env.VITE_APS_API_URL
  || (import.meta.env.DEV ? "" : "http://127.0.0.1:3001");

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

/**
 * Get all semantic classes with bSDD mappings
 */
export async function getSemanticClasses() {
  const res = await axios.get(`${API_URL}/api/pointcloud/semantic-classes`, {
    timeout: 10000,
  });
  return res.data;
}

/**
 * Enrich a single point cloud segment with bSDD data
 * @param {number} semanticLabel - 0-12 (ceiling, floor, wall, etc.)
 * @param {Array<Array<number>>} points - Point coordinates [[x,y,z], ...]
 * @param {string} sceneId - Optional scene identifier
 */
export async function enrichSegment(semanticLabel, points, sceneId = null) {
  const payload = {
    semantic_label: semanticLabel,
    points: points,
    scene_id: sceneId,
  };
  const res = await axios.post(`${API_URL}/api/pointcloud/enrich`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 30000,
  });
  return res.data;
}

/**
 * Enrich multiple segments in batch
 * @param {Array<Object>} segments - [{id, semantic_label, points}, ...]
 */
export async function enrichBatch(segments) {
  const payload = { segments };
  const res = await axios.post(`${API_URL}/api/pointcloud/enrich/batch`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 60000,
  });
  return res.data;
}

/**
 * Check Point Cloud Semantic API health
 */
export async function checkPointCloudHealth() {
  const res = await axios.get(`${API_URL}/api/pointcloud/health`, {
    timeout: 5000,
  });
  return res.data;
}