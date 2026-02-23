/**
 * ProjectScheduling.jsx
 * Enterprise-grade project scheduling page with Gantt chart integration
 * Integrates with PhasingExtension from APS Extensions
 * CRUD backed by /api/schedules REST endpoints
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import ApsViewerExtended from "./ApsViewerExtended";

const API_URL = import.meta.env.VITE_BACKEND_API_URL || "http://127.0.0.1:8008";

const STATUS_COLORS = {
  "completed": "#10b981",
  "in-progress": "var(--tcs-blue)",
  "not-started": "var(--text-secondary)",
  "delayed": "#ef4444"
};

const STATUS_OPTIONS = ["not-started", "in-progress", "completed", "delayed"];
const CATEGORY_OPTIONS = ["Foundation", "Structural", "MEP", "Envelope", "Finishes", "Commissioning", "Other"];

// ---------- API helpers ----------
async function fetchTasks(projectId = "default") {
  const res = await fetch(`${API_URL}/api/schedules/projects/${projectId}/tasks`);
  if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`);
  return res.json();
}

async function createTaskAPI(task, projectId = "default") {
  const res = await fetch(`${API_URL}/api/schedules/projects/${projectId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task),
  });
  if (!res.ok) throw new Error(`Failed to create task: ${res.status}`);
  return res.json();
}

async function updateTaskAPI(taskId, updates, projectId = "default") {
  const res = await fetch(`${API_URL}/api/schedules/projects/${projectId}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update task: ${res.status}`);
  return res.json();
}

async function deleteTaskAPI(taskId, projectId = "default") {
  const res = await fetch(`${API_URL}/api/schedules/projects/${projectId}/tasks/${taskId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete task: ${res.status}`);
  return res.json();
}

// ---------- Component ----------
export default function ProjectScheduling({ apsBaseUrl, viewerUrn, viewerAuth }) {
  const viewerRef = useRef(null);
  const [scheduleData, setScheduleData] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [viewMode, setViewMode] = useState("split");
  const [highlightMode, setHighlightMode] = useState("status");

  // CRUD state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [formData, setFormData] = useState({ name: "", start: "", end: "", progress: 0, status: "not-started", category: "", db_ids: "", notes: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  // ------ Load tasks from backend ------
  const loadTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tasks = await fetchTasks();
      const normalized = tasks.map(t => ({
        ...t,
        dbIds: t.db_ids || t.dbIds || [],
      }));
      setScheduleData(normalized);
    } catch (err) {
      console.error("Failed to load schedule:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTasks(); }, [loadTasks]);

  // ------ Derived timeline ------
  const projectStart = scheduleData.length > 0
    ? new Date(Math.min(...scheduleData.map(t => new Date(t.start))))
    : new Date();
  const projectEnd = scheduleData.length > 0
    ? new Date(Math.max(...scheduleData.map(t => new Date(t.end))))
    : new Date();
  const totalDays = Math.max(1, Math.ceil((projectEnd - projectStart) / (1000 * 60 * 60 * 24)));

  // ------ Handlers ------
  const handleTaskClick = (task) => {
    setSelectedTask(task);
    if (viewerRef.current && task.dbIds?.length > 0) {
      viewerRef.current.isolate(task.dbIds);
      viewerRef.current.fitToView(task.dbIds);
      const rawColor = STATUS_COLORS[task.status] || "#666666";
      const rgb = hexToRgb(rawColor) || cssColorToRgb(rawColor);
      if (rgb && window.Autodesk?.Viewing?.THREE) {
        const color = new window.Autodesk.Viewing.THREE.Vector4(...rgb, 1);
        task.dbIds.forEach(dbId => viewerRef.current.setThemingColor(dbId, color));
      }
    }
  };

  const clearSelection = () => {
    setSelectedTask(null);
    if (viewerRef.current) {
      viewerRef.current.isolate([]);
      viewerRef.current.clearThemingColors();
    }
  };

  const applyHighlighting = useCallback(() => {
    if (!viewerRef.current || highlightMode === "none") {
      viewerRef.current?.clearThemingColors();
      return;
    }
    scheduleData.forEach(task => {
      let color;
      if (highlightMode === "status") color = STATUS_COLORS[task.status];
      else if (highlightMode === "progress") {
        const hue = (task.progress / 100) * 120;
        color = `hsl(${hue}, 70%, 50%)`;
      }
      if (color && task.dbIds) {
        const rgb = hexToRgb(color) || hslToRgb(color) || cssColorToRgb(color);
        if (rgb && window.Autodesk?.Viewing?.THREE) {
          const threeColor = new window.Autodesk.Viewing.THREE.Vector4(...rgb, 1);
          task.dbIds.forEach(dbId => viewerRef.current?.setThemingColor(dbId, threeColor));
        }
      }
    });
  }, [highlightMode, scheduleData]);

  useEffect(() => { applyHighlighting(); }, [applyHighlighting]);

  // ------ CRUD handlers ------
  const resetForm = () => {
    setFormData({ name: "", start: "", end: "", progress: 0, status: "not-started", category: "", db_ids: "", notes: "" });
    setShowAddForm(false);
    setEditingTask(null);
  };

  const handleAddTask = async () => {
    if (!formData.name || !formData.start || !formData.end) return;
    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        start: formData.start,
        end: formData.end,
        progress: Number(formData.progress) || 0,
        status: formData.status,
        category: formData.category || null,
        db_ids: formData.db_ids ? formData.db_ids.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n)) : [],
        notes: formData.notes || null,
      };
      await createTaskAPI(payload);
      await loadTasks();
      resetForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateTask = async (taskId, updates) => {
    setSaving(true);
    try {
      if (updates.dbIds !== undefined) {
        updates.db_ids = updates.dbIds;
        delete updates.dbIds;
      }
      await updateTaskAPI(taskId, updates);
      await loadTasks();
      setEditingTask(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!confirm("Delete this task?")) return;
    setSaving(true);
    try {
      await deleteTaskAPI(taskId);
      if (selectedTask?.id === taskId) clearSelection();
      await loadTasks();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (task) => {
    setEditingTask(task.id);
    setFormData({
      name: task.name,
      start: task.start,
      end: task.end,
      progress: task.progress,
      status: task.status,
      category: task.category || "",
      db_ids: (task.dbIds || task.db_ids || []).join(", "),
      notes: task.notes || "",
    });
  };

  const handleProgressSlider = async (task, newProgress) => {
    await handleUpdateTask(task.id, { progress: newProgress });
  };

  // ------ Gantt bar position ------
  const getBarStyle = (task) => {
    const start = new Date(task.start);
    const end = new Date(task.end);
    const startOffset = (start - projectStart) / (1000 * 60 * 60 * 24);
    const duration = (end - start) / (1000 * 60 * 60 * 24);
    return {
      left: `${(startOffset / totalDays) * 100}%`,
      width: `${Math.max((duration / totalDays) * 100, 1)}%`
    };
  };

  // ------ Summary stats ------
  const stats = {
    total: scheduleData.length,
    completed: scheduleData.filter(t => t.status === "completed").length,
    inProgress: scheduleData.filter(t => t.status === "in-progress").length,
    notStarted: scheduleData.filter(t => t.status === "not-started").length,
    delayed: scheduleData.filter(t => t.status === "delayed").length,
    avgProgress: scheduleData.length > 0 ? Math.round(scheduleData.reduce((s, t) => s + t.progress, 0) / scheduleData.length) : 0,
  };

  // ========== RENDER ==========
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* Error banner */}
      {error && (
        <div style={{ padding: '8px 16px', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 8, color: '#dc2626', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontWeight: 700 }}>×</button>
        </div>
      )}

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', background: 'var(--surface)', borderRadius: 12,
        border: '1px solid var(--border-light)', flexWrap: 'wrap', gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Project Schedule</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              4D BIM Construction Sequencing &bull; {stats.total} tasks &bull; {stats.avgProgress}% avg
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => { resetForm(); setShowAddForm(true); }}
            style={{ padding: '6px 14px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'var(--tcs-blue)', color: 'white', fontWeight: 600, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
            + Add Task
          </button>
          <button onClick={loadTasks} disabled={loading}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 12 }}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--bg-tertiary)', borderRadius: 8 }}>
          {["split", "gantt", "model"].map(id => (
            <button key={id} onClick={() => setViewMode(id)}
              style={{ padding: '6px 12px', borderRadius: 6, border: 'none', cursor: 'pointer', background: viewMode === id ? 'var(--tcs-blue)' : 'transparent', color: viewMode === id ? 'white' : 'var(--text-secondary)', fontWeight: 500, fontSize: 12, textTransform: 'capitalize' }}>
              {id}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Color by:</span>
          <select value={highlightMode} onChange={(e) => setHighlightMode(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-light)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: 12 }}>
            <option value="status">Status</option>
            <option value="progress">Progress</option>
            <option value="none">None</option>
          </select>
        </div>
      </div>

      {/* Summary Stats Row */}
      <div style={{ display: 'flex', gap: 12 }}>
        {[
          { label: "Completed", value: stats.completed, color: "#10b981" },
          { label: "In Progress", value: stats.inProgress, color: "#3b82f6" },
          { label: "Not Started", value: stats.notStarted, color: "#6b7280" },
          { label: "Delayed", value: stats.delayed, color: "#ef4444" },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, padding: '10px 14px', background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{s.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Task Form */}
      {showAddForm && (
        <TaskForm title="Add New Task" formData={formData} setFormData={setFormData}
          onSubmit={handleAddTask} onCancel={resetForm} saving={saving}
          submitLabel="Create Task" borderColor="var(--tcs-blue)" />
      )}

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        {/* Gantt Chart */}
        {(viewMode === 'split' || viewMode === 'gantt') && (
          <div style={{ flex: viewMode === 'gantt' ? 1 : '0 0 55%', display: 'flex', flexDirection: 'column', background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border-light)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border-light)', background: 'var(--bg-tertiary)' }}>
              <div style={{ width: 220, padding: 12, fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', flexShrink: 0 }}>Task</div>
              <div style={{ width: 50, padding: 12, fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center' }}>%</div>
              <div style={{ flex: 1, padding: 12, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)' }}>
                <span>{projectStart.toLocaleDateString()}</span>
                <span>{projectEnd.toLocaleDateString()}</span>
              </div>
              <div style={{ width: 70, padding: 12, fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center' }}>Acts</div>
            </div>

            {loading && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>Loading schedule...</div>}
            {!loading && scheduleData.length === 0 && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>No tasks yet. Click "Add Task" to create one.</div>}

            <div style={{ flex: 1, overflow: 'auto' }}>
              {scheduleData.map(task => (
                <div key={task.id} onClick={() => handleTaskClick(task)}
                  style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--border-light)', cursor: 'pointer', background: selectedTask?.id === task.id ? 'rgba(0,120,215,0.1)' : 'transparent', transition: 'background 0.2s' }}>
                  <div style={{ width: 220, padding: '10px 12px', flexShrink: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: STATUS_COLORS[task.status], flexShrink: 0 }} />
                      {task.name}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginLeft: 14 }}>{task.category || "\u2014"} &bull; {task.dbIds?.length || 0} el.</div>
                  </div>
                  <div style={{ width: 50, textAlign: 'center', flexShrink: 0 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 6px', borderRadius: 10, background: task.progress >= 100 ? '#d1fae5' : task.progress > 0 ? '#dbeafe' : '#f3f4f6', color: task.progress >= 100 ? '#065f46' : task.progress > 0 ? '#1e40af' : '#6b7280' }}>{task.progress}%</span>
                  </div>
                  <div style={{ flex: 1, padding: '10px 16px', position: 'relative', height: 40 }}>
                    <div style={{ position: 'absolute', top: '50%', transform: 'translateY(-50%)', height: 22, borderRadius: 4, background: 'var(--bg-tertiary)', ...getBarStyle(task) }}>
                      <div style={{ height: '100%', width: `${task.progress}%`, borderRadius: 4, background: STATUS_COLORS[task.status], transition: 'width 0.3s', minWidth: task.progress > 0 ? 4 : 0 }} />
                    </div>
                  </div>
                  <div style={{ width: 70, display: 'flex', gap: 4, justifyContent: 'center', flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                    <button onClick={() => startEdit(task)} title="Edit" style={iconBtnStyle}>&#9998;</button>
                    <button onClick={() => handleDeleteTask(task.id)} title="Delete" style={{ ...iconBtnStyle, color: '#ef4444' }}>&times;</button>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 16, padding: 10, borderTop: '1px solid var(--border-light)', background: 'var(--bg-tertiary)' }}>
              {Object.entries(STATUS_COLORS).map(([status, color]) => (
                <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 12, height: 12, borderRadius: 3, background: color }} />
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{status.replace('-', ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 3D Viewer */}
        {(viewMode === 'split' || viewMode === 'model') && (
          <div style={{ flex: viewMode === 'model' ? 1 : '0 0 45%', borderRadius: 12, overflow: 'hidden', background: '#1a1a2e' }}>
            <ApsViewerExtended ref={viewerRef} apsBaseUrl={apsBaseUrl} urn={viewerUrn} auth={viewerAuth}
              enabledExtensions={["PhasingExtension"]} style={{ height: '100%' }} />
          </div>
        )}
      </div>

      {/* Inline Edit Form */}
      {editingTask && (
        <TaskForm title="Edit Task" formData={formData} setFormData={setFormData}
          onSubmit={() => handleUpdateTask(editingTask, {
            name: formData.name, start: formData.start, end: formData.end,
            progress: Number(formData.progress), status: formData.status,
            category: formData.category || null,
            db_ids: formData.db_ids ? formData.db_ids.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n)) : [],
            notes: formData.notes || null,
          })}
          onCancel={resetForm} saving={saving} submitLabel="Save Changes" borderColor="#f59e0b" />
      )}

      {/* Task Details Panel */}
      {selectedTask && !editingTask && (
        <div style={{ padding: 16, background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{ width: 12, height: 12, borderRadius: 3, background: STATUS_COLORS[selectedTask.status] }} />
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{selectedTask.name}</h3>
              {selectedTask.category && <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>{selectedTask.category}</span>}
            </div>
            <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
              <span>Start: {new Date(selectedTask.start).toLocaleDateString()}</span>
              <span>End: {new Date(selectedTask.end).toLocaleDateString()}</span>
              <span>Elements: {selectedTask.dbIds?.length || 0}</span>
              {selectedTask.notes && <span style={{ fontStyle: 'italic' }}>{selectedTask.notes}</span>}
            </div>
          </div>
          <div style={{ width: 200 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Progress</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>{selectedTask.progress}%</span>
            </div>
            <input type="range" min={0} max={100} value={selectedTask.progress}
              onChange={e => handleProgressSlider(selectedTask, Number(e.target.value))}
              style={{ width: '100%' }} />
          </div>
          <button onClick={clearSelection} style={btnOutlineStyle}>Clear</button>
        </div>
      )}
    </div>
  );
}

// =============== Reusable Task Form ===============
function TaskForm({ title, formData, setFormData, onSubmit, onCancel, saving, submitLabel, borderColor }) {
  return (
    <div style={{ padding: 16, background: 'var(--surface)', borderRadius: 12, border: `2px solid ${borderColor}`, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
        <button onClick={onCancel} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-secondary)' }}>&times;</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 }}>
        <label style={labelStyle}>Name<input value={formData.name} onChange={e => setFormData(f => ({ ...f, name: e.target.value }))} style={inputStyle} placeholder="Task name" /></label>
        <label style={labelStyle}>Start<input type="date" value={formData.start} onChange={e => setFormData(f => ({ ...f, start: e.target.value }))} style={inputStyle} /></label>
        <label style={labelStyle}>End<input type="date" value={formData.end} onChange={e => setFormData(f => ({ ...f, end: e.target.value }))} style={inputStyle} /></label>
        <label style={labelStyle}>Category
          <select value={formData.category} onChange={e => setFormData(f => ({ ...f, category: e.target.value }))} style={inputStyle}>
            <option value="">--</option>
            {CATEGORY_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr', gap: 10 }}>
        <label style={labelStyle}>Status
          <select value={formData.status} onChange={e => setFormData(f => ({ ...f, status: e.target.value }))} style={inputStyle}>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label style={labelStyle}>Progress ({formData.progress}%)
          <input type="range" min={0} max={100} value={formData.progress} onChange={e => setFormData(f => ({ ...f, progress: Number(e.target.value) }))} style={{ width: '100%' }} />
        </label>
        <label style={labelStyle}>Element DB IDs (comma-separated)
          <input value={formData.db_ids} onChange={e => setFormData(f => ({ ...f, db_ids: e.target.value }))} style={inputStyle} placeholder="e.g. 1, 2, 3" />
        </label>
      </div>
      <label style={labelStyle}>Notes<input value={formData.notes} onChange={e => setFormData(f => ({ ...f, notes: e.target.value }))} style={inputStyle} placeholder="Optional notes" /></label>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={btnOutlineStyle}>Cancel</button>
        <button onClick={onSubmit} disabled={saving || !formData.name || !formData.start || !formData.end}
          style={{ ...btnPrimaryStyle, background: borderColor, opacity: saving ? 0.6 : 1 }}>
          {saving ? "Saving..." : submitLabel}
        </button>
      </div>
    </div>
  );
}

// =============== Styles ===============
const labelStyle = { display: 'flex', flexDirection: 'column', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', gap: 4 };
const inputStyle = { padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-light)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: 13 };
const btnPrimaryStyle = { padding: '7px 18px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'var(--tcs-blue)', color: 'white', fontWeight: 600, fontSize: 12 };
const btnOutlineStyle = { padding: '7px 18px', borderRadius: 6, border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 12 };
const iconBtnStyle = { width: 26, height: 26, borderRadius: 4, border: '1px solid var(--border-light)', background: 'transparent', cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' };

// =============== Color Utilities ===============
function hexToRgb(hex) {
  if (!hex || typeof hex !== 'string' || hex.startsWith('var(')) return null;
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return r ? [parseInt(r[1], 16) / 255, parseInt(r[2], 16) / 255, parseInt(r[3], 16) / 255] : null;
}

function hslToRgb(hsl) {
  if (!hsl || typeof hsl !== 'string' || !hsl.startsWith('hsl')) return null;
  const m = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!m) return null;
  let h = parseInt(m[1]) / 360, s = parseInt(m[2]) / 100, l = parseInt(m[3]) / 100;
  if (s === 0) return [l, l, l];
  const hue2rgb = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1/6) return p + (q - p) * 6 * t; if (t < 1/2) return q; if (t < 2/3) return p + (q - p) * (2/3 - t) * 6; return p; };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  return [hue2rgb(p, q, h + 1/3), hue2rgb(p, q, h), hue2rgb(p, q, h - 1/3)];
}

const CSS_COLOR_FALLBACKS = { 'var(--tcs-blue)': [0.13, 0.39, 0.84], 'var(--tcs-navy)': [0.05, 0.13, 0.33], 'var(--tcs-orange)': [0.96, 0.49, 0.0], 'var(--text-secondary)': [0.42, 0.45, 0.49], 'var(--text-primary)': [0.13, 0.15, 0.18] };

function cssColorToRgb(cssVar) {
  if (!cssVar || typeof cssVar !== 'string' || !cssVar.startsWith('var(')) return null;
  if (CSS_COLOR_FALLBACKS[cssVar]) return CSS_COLOR_FALLBACKS[cssVar];
  try { const v = cssVar.match(/var\(([^)]+)\)/)?.[1]; if (v) { const r = getComputedStyle(document.documentElement).getPropertyValue(v).trim(); if (r) return hexToRgb(r); } } catch { /* ignore */ }
  return [0.4, 0.4, 0.4];
}
