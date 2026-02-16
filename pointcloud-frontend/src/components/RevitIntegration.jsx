/**
 * Revit bSDD Plugin Integration Component
 * 
 * Provides UI for:
 * - Uploading IFC files from Revit with bSDD classifications
 * - Parsing and viewing classifications
 * - Importing to Neo4j knowledge graph
 * - Validating BIM vs Point Cloud classifications
 */
import React, { useState } from 'react';
import './RevitIntegration.css';

const RevitIntegration = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFileId, setUploadedFileId] = useState(null);
  const [parseResult, setParseResult] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('upload'); // upload, parse, import, validate

  const API_BASE = 'http://localhost:8001';

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.name.endsWith('.ifc')) {
      setSelectedFile(file);
      setError(null);
    } else {
      setError('Please select a valid IFC file (.ifc extension)');
      setSelectedFile(null);
    }
  };

  // Upload IFC file
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_BASE}/api/revit-integration/upload-ifc`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setUploadedFileId(data.file_id);
      setActiveTab('parse');
      
      // Auto-parse after upload
      await handleParse(data.file_id);
      
    } catch (err) {
      setError(`Upload error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Parse IFC file
  const handleParse = async (fileId = uploadedFileId) => {
    if (!fileId) {
      setError('No file uploaded');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/revit-integration/parse-ifc/${fileId}`);
      
      if (!response.ok) {
        throw new Error(`Parse failed: ${response.statusText}`);
      }

      const data = await response.json();
      setParseResult(data);
      
    } catch (err) {
      setError(`Parse error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Import to Neo4j
  const handleImport = async () => {
    if (!uploadedFileId) {
      setError('No file uploaded');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/revit-integration/import-to-neo4j`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: uploadedFileId,
          project_id: null,
          merge_existing: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Import failed: ${response.statusText}`);
      }

      const data = await response.json();
      setImportResult(data);
      setActiveTab('import');
      
    } catch (err) {
      setError(`Import error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Validate against point cloud
  const handleValidate = async () => {
    if (!uploadedFileId) {
      setError('No file uploaded');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Mock point cloud segments for demo
      const mockSegments = [
        { segment_id: 'seg_1', semantic_label: 'wall', confidence: 0.95 },
        { segment_id: 'seg_2', semantic_label: 'floor', confidence: 0.92 },
        { segment_id: 'seg_3', semantic_label: 'door', confidence: 0.88 },
      ];

      const response = await fetch(`${API_BASE}/api/revit-integration/validate-bim-vs-pointcloud`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_id: uploadedFileId,
          point_cloud_segments: mockSegments,
          spatial_tolerance: 0.5,
        }),
      });

      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }

      const data = await response.json();
      setValidationResult(data);
      setActiveTab('validate');
      
    } catch (err) {
      setError(`Validation error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="revit-integration">
      <div className="header">
        <h2>🏗️ Revit bSDD Plugin Integration</h2>
        <p className="subtitle">
          Import IFC files with buildingSMART Data Dictionary classifications from Revit
        </p>
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          1. Upload
        </button>
        <button
          className={`tab ${activeTab === 'parse' ? 'active' : ''}`}
          onClick={() => setActiveTab('parse')}
          disabled={!parseResult}
        >
          2. Parse
        </button>
        <button
          className={`tab ${activeTab === 'import' ? 'active' : ''}`}
          onClick={() => setActiveTab('import')}
          disabled={!importResult}
        >
          3. Import
        </button>
        <button
          className={`tab ${activeTab === 'validate' ? 'active' : ''}`}
          onClick={() => setActiveTab('validate')}
          disabled={!validationResult}
        >
          4. Validate
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="upload-section">
            <h3>Upload IFC File</h3>
            <p>Select an IFC file exported from Revit with bSDD Plugin classifications</p>
            
            <div className="file-input">
              <input
                type="file"
                accept=".ifc"
                onChange={handleFileSelect}
                disabled={loading}
              />
            </div>

            {selectedFile && (
              <div className="file-info">
                <strong>Selected:</strong> {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={!selectedFile || loading}
              className="primary-button"
            >
              {loading ? '⏳ Uploading...' : '📤 Upload & Parse'}
            </button>
          </div>
        )}

        {/* Parse Tab */}
        {activeTab === 'parse' && parseResult && (
          <div className="parse-section">
            <h3>Parse Results</h3>
            
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{parseResult.total_elements}</div>
                <div className="stat-label">Total Elements</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{parseResult.classified_elements}</div>
                <div className="stat-label">Classified</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{parseResult.classification_coverage.toFixed(1)}%</div>
                <div className="stat-label">Coverage</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{parseResult.bsdd_classifications}</div>
                <div className="stat-label">bSDD Classes</div>
              </div>
            </div>

            <div className="info-section">
              <h4>IFC Schema</h4>
              <p>{parseResult.ifc_schema}</p>

              <h4>Dictionaries Used</h4>
              <ul>
                {parseResult.dictionaries_used.map((dict, idx) => (
                  <li key={idx}>{dict}</li>
                ))}
              </ul>

              <h4>Classifications by Type</h4>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>IFC Type</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(parseResult.classifications_by_type).map(([type, count]) => (
                    <tr key={type}>
                      <td>{type}</td>
                      <td>{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={handleImport}
              className="primary-button"
              disabled={loading}
            >
              {loading ? '⏳ Importing...' : '💾 Import to Neo4j'}
            </button>
          </div>
        )}

        {/* Import Tab */}
        {activeTab === 'import' && importResult && (
          <div className="import-section">
            <h3>Import Results</h3>
            
            <div className="success-banner">
              ✅ Successfully imported {importResult.imported_count} classifications to Neo4j
            </div>

            <div className="info-section">
              <h4>Status</h4>
              <p><strong>{importResult.status}</strong></p>

              <h4>Created Nodes (first 10)</h4>
              <ul>
                {importResult.created_nodes.slice(0, 10).map((nodeId, idx) => (
                  <li key={idx}><code>{nodeId}</code></li>
                ))}
              </ul>

              {importResult.errors.length > 0 && (
                <>
                  <h4>Errors</h4>
                  <ul className="error-list">
                    {importResult.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>

            <button
              onClick={handleValidate}
              className="primary-button"
              disabled={loading}
            >
              {loading ? '⏳ Validating...' : '🔍 Validate vs Point Cloud'}
            </button>
          </div>
        )}

        {/* Validate Tab */}
        {activeTab === 'validate' && validationResult && (
          <div className="validate-section">
            <h3>Validation Results</h3>
            
            <div className="stats-grid">
              <div className="stat-card success">
                <div className="stat-value">{validationResult.match_count}</div>
                <div className="stat-label">Matches</div>
              </div>
              <div className="stat-card warning">
                <div className="stat-value">{validationResult.mismatch_count}</div>
                <div className="stat-label">Mismatches</div>
              </div>
              <div className="stat-card info">
                <div className="stat-value">{validationResult.missing_pc_count}</div>
                <div className="stat-label">Missing in PC</div>
              </div>
              <div className="stat-card primary">
                <div className="stat-value">{validationResult.overall_accuracy.toFixed(1)}%</div>
                <div className="stat-label">Accuracy</div>
              </div>
            </div>

            <div className="info-section">
              <h4>Validation Details</h4>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>BIM Class</th>
                    <th>Point Cloud Class</th>
                    <th>Status</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {validationResult.validation_results.map((result, idx) => (
                    <tr key={idx}>
                      <td>{result.element_type}</td>
                      <td><code>{result.bim_classification}</code></td>
                      <td><code>{result.point_cloud_classification || 'N/A'}</code></td>
                      <td>
                        <span className={`status-badge ${result.match_status.toLowerCase()}`}>
                          {result.match_status}
                        </span>
                      </td>
                      <td>{(result.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default RevitIntegration;
