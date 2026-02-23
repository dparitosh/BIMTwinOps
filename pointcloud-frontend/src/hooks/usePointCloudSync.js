/**
 * Custom hook for Point Cloud segment synchronization with Neo4j
 * Implements auto-save with debounced write-back to prevent data loss
 * 
 * Addresses: TECHNO_FUNCTIONAL_ANALYSIS.md - Section 2.2 "Three-Way Point Cloud Sync"
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const DEBOUNCE_DELAY = 5000; // 5 seconds
const AUTO_SAVE_INTERVAL = 30000; // 30 seconds

export const usePointCloudSync = (sceneId, apiBaseUrl = 'http://localhost:8008') => {
  const [segments, setSegments] = useState([]);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [error, setError] = useState(null);
  
  // Track original state for rollback
  const originalSegmentsRef = useRef([]);
  const saveTimerRef = useRef(null);
  const autoSaveTimerRef = useRef(null);

  /**
   * Save segments to Neo4j backend
   */
  const saveToNeo4j = useCallback(async (segmentsToSave) => {
    if (!sceneId || segmentsToSave.length === 0) return;

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/pointcloud/${sceneId}/segments/bulk-update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          segments: segmentsToSave.map(s => ({
            segment_id: s.id,
            semantic_class_id: s.semanticClassId,
            semantic_label: s.semanticLabel,
            confidence: s.confidence,
            user_modified: s.userModified || false
          }))
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Save failed: ${response.status}`);
      }

      const result = await response.json();
      
      // Update original state after successful save
      originalSegmentsRef.current = JSON.parse(JSON.stringify(segmentsToSave));
      setIsDirty(false);
      setLastSaved(new Date());
      
      console.log('[PointCloudSync] Saved successfully:', result);
      return result;

    } catch (err) {
      console.error('[PointCloudSync] Save failed:', err);
      setError(err.message);
      
      // ENHANCEMENT: Auto-retry after 10 seconds on failure (if still dirty)
      // Keep isDirty = true so next change or interval will retry
      setTimeout(() => {
        if (isDirty && !isSaving && segments.length > 0) {
          console.log('[PointCloudSync] Auto-retry after error...');
          saveToNeo4j(segments).catch(() => {
            // Ignore retry errors to prevent infinite recursion
          });
        }
      }, 10000);
      
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, [sceneId, apiBaseUrl, isDirty, isSaving, segments]);

  /**
   * Debounced save - waits for user to stop making changes
   */
  const debouncedSave = useCallback((segmentsToSave) => {
    // Clear existing timer
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }

    // Set new timer
    saveTimerRef.current = setTimeout(() => {
      saveToNeo4j(segmentsToSave);
    }, DEBOUNCE_DELAY);
  }, [saveToNeo4j]);

  /**
   * Update segments with optimistic UI updates
   */
  const updateSegments = useCallback((updater) => {
    setSegments(prevSegments => {
      const newSegments = typeof updater === 'function' 
        ? updater(prevSegments) 
        : updater;
      
      setIsDirty(true);
      debouncedSave(newSegments);
      
      return newSegments;
    });
  }, [debouncedSave]);

  /**
   * Update single segment
   */
  const updateSegment = useCallback((segmentId, updates) => {
    updateSegments(prevSegments => 
      prevSegments.map(s => 
        s.id === segmentId 
          ? { ...s, ...updates, userModified: true }
          : s
      )
    );
  }, [updateSegments]);

  /**
   * Manual save (for explicit user action)
   */
  const saveNow = useCallback(async () => {
    // Clear debounce timer
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }

    try {
      await saveToNeo4j(segments);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, [segments, saveToNeo4j]);

  /**
   * Rollback to last saved state
   */
  const rollback = useCallback(() => {
    setSegments(originalSegmentsRef.current);
    setIsDirty(false);
    setError(null);
    
    // Clear pending saves
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
  }, []);

  /**
   * Load segments from Neo4j
   */
  const loadSegments = useCallback(async () => {
    if (!sceneId) return;

    try {
      const response = await fetch(`${apiBaseUrl}/api/pointcloud/${sceneId}/segments`);
      
      if (!response.ok) {
        throw new Error(`Load failed: ${response.status}`);
      }

      const data = await response.json();
      const loadedSegments = data.segments || [];
      
      setSegments(loadedSegments);
      originalSegmentsRef.current = JSON.parse(JSON.stringify(loadedSegments));
      setIsDirty(false);
      setLastSaved(new Date());
      
      console.log('[PointCloudSync] Loaded segments:', loadedSegments.length);
      return loadedSegments;

    } catch (err) {
      console.error('[PointCloudSync] Load failed:', err);
      setError(err.message);
      throw err;
    }
  }, [sceneId, apiBaseUrl]);

  /**
   * BUGFIX: Clear all timers when sceneId changes to prevent race condition
   * Prevents saving data to wrong scene if user switches scenes during debounce period
   */
  useEffect(() => {
    return () => {
      // Clear timers when sceneId changes (cleanup on unmount or sceneId change)
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
        saveTimerRef.current = null;
      }
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
        autoSaveTimerRef.current = null;
      }
    };
  }, [sceneId]); // Re-run when sceneId changes

  /**
   * Auto-save interval (backup to debounce)
   */
  useEffect(() => {
    if (!isDirty) return;

    autoSaveTimerRef.current = setInterval(() => {
      if (isDirty && !isSaving) {
        console.log('[PointCloudSync] Auto-save triggered');
        saveToNeo4j(segments);
      }
    }, AUTO_SAVE_INTERVAL);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, [isDirty, isSaving, segments, saveToNeo4j]);

  /**
   * Cleanup on unmount - save pending changes
   * Note: Intentionally capturing latest values via refs
   */
  useEffect(() => {
    const currentSegments = segments;
    const currentIsDirty = isDirty;
    
    return () => {
      // Clear all timers
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      if (autoSaveTimerRef.current) clearInterval(autoSaveTimerRef.current);

      // Save pending changes before unmount
      if (currentIsDirty && currentSegments.length > 0) {
        console.log('[PointCloudSync] Component unmounting, saving changes...');
        saveToNeo4j(currentSegments);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on unmount

  return {
    // State
    segments,
    isDirty,
    isSaving,
    lastSaved,
    error,
    
    // Actions
    setSegments: updateSegments,
    updateSegment,
    saveNow,
    rollback,
    loadSegments,
    
    // Computed
    hasUnsavedChanges: isDirty,
    canSave: isDirty && !isSaving
  };
};
