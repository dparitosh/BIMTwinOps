// @refresh reset
import React, { useState, useCallback } from 'react';
import { AgentContext } from './AgentContextDef';

export function AgentProvider({ children }) {
  const [agentState, setAgentState] = useState({
    isRunning: false,
    currentTask: null,
    messages: [],
    lastResponse: null,
    error: null,
  });

  const startAgent = useCallback((task) => {
    setAgentState((prev) => ({
      ...prev,
      isRunning: true,
      currentTask: task,
      error: null,
    }));
  }, []);

  const stopAgent = useCallback(() => {
    setAgentState((prev) => ({
      ...prev,
      isRunning: false,
      currentTask: null,
    }));
  }, []);

  const addMessage = useCallback((message) => {
    setAgentState((prev) => ({
      ...prev,
      messages: [...prev.messages, { ...message, timestamp: Date.now() }],
    }));
  }, []);

  const setLastResponse = useCallback((response) => {
    setAgentState((prev) => ({
      ...prev,
      lastResponse: response,
    }));
  }, []);

  const setError = useCallback((error) => {
    setAgentState((prev) => ({
      ...prev,
      error,
      isRunning: false,
    }));
  }, []);

  const clearMessages = useCallback(() => {
    setAgentState((prev) => ({
      ...prev,
      messages: [],
    }));
  }, []);

  const value = {
    ...agentState,
    startAgent,
    stopAgent,
    addMessage,
    setLastResponse,
    setError,
    clearMessages,
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}
