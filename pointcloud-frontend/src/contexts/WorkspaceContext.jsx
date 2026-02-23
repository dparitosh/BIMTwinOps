// @refresh reset
import React, { useState, useCallback } from 'react';
import { WorkspaceContext } from './WorkspaceContextDef';

export function WorkspaceProvider({ children }) {
  const [workspace, setWorkspace] = useState({
    currentProject: null,
    currentFile: null,
    sceneData: null,
    selectedElement: null,
    loading: false,
    error: null,
  });

  const setCurrentProject = useCallback((project) => {
    setWorkspace((prev) => ({
      ...prev,
      currentProject: project,
    }));
  }, []);

  const setCurrentFile = useCallback((file) => {
    setWorkspace((prev) => ({
      ...prev,
      currentFile: file,
    }));
  }, []);

  const setSceneData = useCallback((data) => {
    setWorkspace((prev) => ({
      ...prev,
      sceneData: data,
    }));
  }, []);

  const setSelectedElement = useCallback((element) => {
    setWorkspace((prev) => ({
      ...prev,
      selectedElement: element,
    }));
  }, []);

  const setLoading = useCallback((loading) => {
    setWorkspace((prev) => ({
      ...prev,
      loading,
    }));
  }, []);

  const setError = useCallback((error) => {
    setWorkspace((prev) => ({
      ...prev,
      error,
      loading: false,
    }));
  }, []);

  const clearWorkspace = useCallback(() => {
    setWorkspace({
      currentProject: null,
      currentFile: null,
      sceneData: null,
      selectedElement: null,
      loading: false,
      error: null,
    });
  }, []);

  const value = {
    ...workspace,
    setCurrentProject,
    setCurrentFile,
    setSceneData,
    setSelectedElement,
    setLoading,
    setError,
    clearWorkspace,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
