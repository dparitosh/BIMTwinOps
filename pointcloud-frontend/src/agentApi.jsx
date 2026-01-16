// Agent API Functions
import axios from "axios";

const API_URL = import.meta.env.VITE_BACKEND_API_URL || "http://127.0.0.1:8000";

/**
 * Send query to agent system and get response
 * @param {string} userInput - User's natural language query
 * @param {string} threadId - Optional thread ID for conversation context
 * @returns {Promise<Object>} Agent response with components
 */
export async function queryAgents(userInput, threadId = null) {
  const payload = { user_input: userInput };
  if (threadId) payload.thread_id = threadId;

  const res = await axios.post(`${API_URL}/api/ui/generate`, payload, {
    headers: { "Content-Type": "application/json" },
    timeout: 60000,
  });
  return res.data;
}

/**
 * Subscribe to SSE stream for real-time agent updates
 * @param {string} threadId - Thread ID to stream
 * @param {function} onMessage - Callback for each message
 * @param {function} onError - Callback for errors
 * @returns {EventSource} EventSource instance (call .close() to stop)
 */
export function streamAgentUpdates(threadId, onMessage, onError) {
  const eventSource = new EventSource(`${API_URL}/api/ui/stream/${threadId}`);
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error("Failed to parse SSE message:", e);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error("SSE Error:", error);
    if (onError) onError(error);
    eventSource.close();
  };
  
  return eventSource;
}
