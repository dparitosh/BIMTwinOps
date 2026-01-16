// Agent Interface Component - Chat with BIM AI Agents
import React, { useState, useEffect, useRef } from "react";
import { queryAgents, streamAgentUpdates } from "../agentApi";
import AgentComponentRenderer from "./AgentComponentRenderer";

export default function AgentInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Cleanup SSE on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input, timestamp: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Send query to agent system
      const response = await queryAgents(input, threadId);
      
      // Set thread ID for conversation continuity
      if (response.thread_id && !threadId) {
        setThreadId(response.thread_id);
      }

      // Add agent response
      const agentMessage = {
        role: "agent",
        content: response.response || response.message || "Processing complete",
        components: response.components || [],
        agent: response.agent || "system",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, agentMessage]);

      // If there's a thread_id, subscribe to streaming updates
      if (response.thread_id && response.streaming !== false) {
        setStreaming(true);
        eventSourceRef.current = streamAgentUpdates(
          response.thread_id,
          (update) => {
            // Handle streaming updates (progress, intermediate results)
            if (update.type === "progress") {
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg.role === "agent") {
                  lastMsg.progress = update.progress;
                  lastMsg.status = update.status;
                }
                return updated;
              });
            } else if (update.type === "component") {
              // Add new component to last agent message
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg.role === "agent") {
                  lastMsg.components = [...(lastMsg.components || []), update.component];
                }
                return updated;
              });
            } else if (update.type === "complete") {
              setStreaming(false);
              if (eventSourceRef.current) {
                eventSourceRef.current.close();
              }
            }
          },
          (error) => {
            console.error("Streaming error:", error);
            setStreaming(false);
          }
        );
      }
    } catch (error) {
      console.error("Agent query failed:", error);
      const errorMessage = {
        role: "agent",
        content: `Error: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setThreadId(null);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
  };

  return (
    <div className="agent-interface" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{
        padding: "1rem",
        borderBottom: "1px solid #e5e7eb",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        backgroundColor: "#f9fafb"
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 600 }}>BIM AI Assistant</h2>
          <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem", color: "#6b7280" }}>
            Query, Action, and Planning Agents
          </p>
        </div>
        <button
          onClick={clearChat}
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#ef4444",
            color: "white",
            border: "none",
            borderRadius: "0.375rem",
            cursor: "pointer",
            fontSize: "0.875rem"
          }}
        >
          Clear Chat
        </button>
      </div>

      {/* Messages Area */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem",
        backgroundColor: "#ffffff"
      }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem", color: "#9ca3af" }}>
            <svg style={{ width: "4rem", height: "4rem", margin: "0 auto 1rem" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p style={{ fontSize: "1.125rem", fontWeight: 500, marginBottom: "0.5rem" }}>Start a conversation</p>
            <p style={{ fontSize: "0.875rem" }}>
              Try: "Show me all walls" or "Find conference rooms then analyze their utilization"
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: "1.5rem",
                display: "flex",
                flexDirection: msg.role === "user" ? "row-reverse" : "row",
              }}
            >
              {/* Avatar */}
              <div style={{
                width: "2.5rem",
                height: "2.5rem",
                borderRadius: "50%",
                backgroundColor: msg.role === "user" ? "#3b82f6" : "#10b981",
                color: "white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                margin: msg.role === "user" ? "0 0 0 0.75rem" : "0 0.75rem 0 0"
              }}>
                {msg.role === "user" ? "U" : "A"}
              </div>

              {/* Message Content */}
              <div style={{
                maxWidth: "70%",
                backgroundColor: msg.isError ? "#fee2e2" : (msg.role === "user" ? "#eff6ff" : "#f0fdf4"),
                padding: "0.75rem 1rem",
                borderRadius: "0.5rem",
                border: `1px solid ${msg.isError ? "#fecaca" : (msg.role === "user" ? "#dbeafe" : "#d1fae5")}`,
              }}>
                <div style={{ fontSize: "0.875rem", marginBottom: "0.5rem" }}>
                  <strong>{msg.role === "user" ? "You" : msg.agent || "Agent"}</strong>
                  <span style={{ color: "#9ca3af", marginLeft: "0.5rem", fontSize: "0.75rem" }}>
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                
                <div style={{ whiteSpace: "pre-wrap", lineHeight: "1.5" }}>
                  {msg.content}
                </div>

                {/* Render agent-generated components */}
                {msg.components && msg.components.length > 0 && (
                  <div style={{ marginTop: "1rem" }}>
                    {msg.components.map((component, compIdx) => (
                      <AgentComponentRenderer key={compIdx} component={component} />
                    ))}
                  </div>
                )}

                {/* Progress indicator */}
                {msg.progress && (
                  <div style={{ marginTop: "0.75rem", fontSize: "0.75rem", color: "#6b7280" }}>
                    <div style={{ marginBottom: "0.25rem" }}>{msg.status || "Processing..."}</div>
                    <div style={{
                      width: "100%",
                      height: "0.25rem",
                      backgroundColor: "#e5e7eb",
                      borderRadius: "0.125rem",
                      overflow: "hidden"
                    }}>
                      <div style={{
                        width: `${msg.progress}%`,
                        height: "100%",
                        backgroundColor: "#10b981",
                        transition: "width 0.3s ease"
                      }} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div style={{ textAlign: "center", color: "#9ca3af" }}>
            <div className="loader-dots">
              <span>●</span><span>●</span><span>●</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{
        padding: "1rem",
        borderTop: "1px solid #e5e7eb",
        backgroundColor: "#f9fafb"
      }}>
        {streaming && (
          <div style={{
            marginBottom: "0.5rem",
            padding: "0.5rem",
            backgroundColor: "#fef3c7",
            border: "1px solid #fde68a",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            color: "#92400e"
          }}>
            ⚡ Streaming updates in progress...
          </div>
        )}
        
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about your BIM model... (e.g., 'Show me all walls with fire rating > 60')"
            disabled={loading}
            style={{
              flex: 1,
              padding: "0.75rem",
              border: "1px solid #d1d5db",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              resize: "none",
              minHeight: "3rem",
              fontFamily: "inherit"
            }}
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              padding: "0.75rem 1.5rem",
              backgroundColor: loading || !input.trim() ? "#9ca3af" : "#3b82f6",
              color: "white",
              border: "none",
              borderRadius: "0.375rem",
              cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              fontSize: "0.875rem",
              fontWeight: 500
            }}
          >
            Send
          </button>
        </div>
      </div>

      <style>{`
        .loader-dots span {
          animation: blink 1.4s infinite both;
          display: inline-block;
          margin: 0 2px;
        }
        .loader-dots span:nth-child(2) {
          animation-delay: 0.2s;
        }
        .loader-dots span:nth-child(3) {
          animation-delay: 0.4s;
        }
        @keyframes blink {
          0%, 80%, 100% { opacity: 0; }
          40% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
