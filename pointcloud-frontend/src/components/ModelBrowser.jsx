/**
 * ModelBrowser.jsx
 * Hierarchical tree browser for BIM model structure with search
 */
import React, { useState, useEffect, useCallback } from 'react';

export default function ModelBrowser({ viewer, onElementSelect }) {
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  const buildTree = useCallback(async () => {
    if (!viewer || !viewer.model) return;

    setLoading(true);
    try {
      const model = viewer.model;
      const instanceTree = model.getInstanceTree();
      
      if (!instanceTree) {
        setLoading(false);
        return;
      }

      const rootId = instanceTree.getRootId();
      const treeNode = await buildTreeNode(instanceTree, rootId, model);
      setTree(treeNode);
      
      // Auto-expand root
      setExpandedNodes(new Set([rootId]));
    } catch (err) {
      console.error('[ModelBrowser] Failed to build tree:', err);
    } finally {
      setLoading(false);
    }
  }, [viewer]);

  useEffect(() => {
    if (!viewer) {
      setTree(null);
      return;
    }

    buildTree();
  }, [viewer, buildTree]);

  const buildTreeNode = (instanceTree, nodeId, model) => {
    return new Promise((resolve) => {
      const childIds = [];
      instanceTree.enumNodeChildren(nodeId, (childId) => {
        childIds.push(childId);
      });

      model.getProperties(nodeId, (result) => {
        const name = result.name || `Node ${nodeId}`;
        const type = result.properties?.find(p => p.displayName === 'Category')?.displayValue || '';
        
        resolve({
          id: nodeId,
          name,
          type,
          children: childIds,
          hasChildren: childIds.length > 0
        });
      }, () => {
        resolve({
          id: nodeId,
          name: `Node ${nodeId}`,
          type: '',
          children: childIds,
          hasChildren: childIds.length > 0
        });
      });
    });
  };

  const toggleNode = async (nodeId) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    
    if (!query.trim() || !viewer || !viewer.model) {
      setSearchResults(null);
      return;
    }

    const model = viewer.model;
    const instanceTree = model.getInstanceTree();
    if (!instanceTree) return;

    const results = [];
    const queryLower = query.toLowerCase();

    // Search through all nodes
    instanceTree.enumNodeChildren(instanceTree.getRootId(), (nodeId) => {
      model.getProperties(nodeId, (result) => {
        const name = result.name || '';
        if (name.toLowerCase().includes(queryLower)) {
          results.push({
            id: nodeId,
            name,
            type: result.properties?.find(p => p.displayName === 'Category')?.displayValue || ''
          });
        }
      });
    }, true); // Recursive

    // Update results after a short delay to batch updates
    setTimeout(() => {
      setSearchResults(results.slice(0, 50)); // Limit to 50 results
    }, 300);
  };

  const handleElementClick = (nodeId) => {
    if (onElementSelect) {
      onElementSelect([nodeId]);
    }
    // Isolate and zoom to element in viewer
    if (viewer) {
      viewer.isolate([nodeId]);
      viewer.fitToView([nodeId]);
      viewer.select([nodeId]);
    }
  };

  if (!viewer) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        padding: 24,
        color: 'var(--text-secondary)',
        textAlign: 'center'
      }}>
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginBottom: 16, opacity: 0.5 }}>
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No Model Loaded</div>
        <div style={{ fontSize: 12 }}>Load a model to browse its structure</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Building model tree...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-light)',
        background: 'var(--surface)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
            Model Browser
          </span>
        </div>

        {/* Search */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder="Search elements..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 32px 8px 12px',
              borderRadius: 8,
              border: '1px solid var(--border-light)',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              fontSize: 12,
              outline: 'none'
            }}
          />
          <svg 
            viewBox="0 0 24 24" 
            width="16" 
            height="16" 
            fill="none" 
            stroke="var(--text-secondary)" 
            strokeWidth="2"
            style={{
              position: 'absolute',
              right: 10,
              top: '50%',
              transform: 'translateY(-50%)'
            }}
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>
      </div>

      {/* Tree/Results */}
      <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
        {searchResults ? (
          // Search results
          <>
            <div style={{ 
              padding: '8px 12px', 
              fontSize: 11, 
              color: 'var(--text-secondary)',
              borderBottom: '1px solid var(--border-light)',
              marginBottom: 8
            }}>
              Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
              {searchResults.length === 50 && ' (showing first 50)'}
            </div>
            {searchResults.map((result) => (
              <TreeNode
                key={result.id}
                node={result}
                level={0}
                isExpanded={false}
                onToggle={() => {}}
                onSelect={handleElementClick}
                viewer={viewer}
                isSearchResult
              />
            ))}
          </>
        ) : (
          // Tree view
          tree && (
            <TreeNode
              node={tree}
              level={0}
              isExpanded={expandedNodes.has(tree.id)}
              onToggle={toggleNode}
              onSelect={handleElementClick}
              expandedNodes={expandedNodes}
              viewer={viewer}
            />
          )
        )}
      </div>
    </div>
  );
}

// TreeNode component
function TreeNode({ node, level, isExpanded, onToggle, onSelect, expandedNodes, viewer, isSearchResult }) {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadChildren = useCallback(async () => {
    if (!viewer || loading || !node.children) return;

    setLoading(true);
    const model = viewer.model;
    const instanceTree = model.getInstanceTree();

    const childNodes = await Promise.all(
      node.children.map(async (childId) => {
        return new Promise((resolve) => {
          const hasChildren = instanceTree.getChildCount(childId) > 0;
          
          model.getProperties(childId, (result) => {
            resolve({
              id: childId,
              name: result.name || `Node ${childId}`,
              type: result.properties?.find(p => p.displayName === 'Category')?.displayValue || '',
              hasChildren,
              children: hasChildren ? Array.from({ length: instanceTree.getChildCount(childId) }, (_, i) => {
                let child = 0;
                instanceTree.enumNodeChildren(childId, (c) => { if (i === 0) child = c; }, false);
                return child;
              }) : []
            });
          }, () => {
            resolve({
              id: childId,
              name: `Node ${childId}`,
              type: '',
              hasChildren,
              children: []
            });
          });
        });
      })
    );

    setChildren(childNodes);
    setLoading(false);
  }, [viewer, loading, node.children]);

  useEffect(() => {
    if (isExpanded && node.hasChildren && children.length === 0 && !isSearchResult) {
      // Schedule to avoid synchronous setState inside effect body
      const id = requestAnimationFrame(() => loadChildren());
      return () => cancelAnimationFrame(id);
    }
  }, [isExpanded, node.hasChildren, children.length, isSearchResult, loadChildren]);

  const handleClick = (e) => {
    e.stopPropagation();
    if (node.hasChildren && !isSearchResult) {
      onToggle(node.id);
    }
  };

  const handleSelect = (e) => {
    e.stopPropagation();
    onSelect(node.id);
  };

  const indent = level * 16;

  return (
    <>
      <div
        style={{
          paddingLeft: indent + 8,
          paddingRight: 8,
          paddingTop: 6,
          paddingBottom: 6,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          borderRadius: 6,
          transition: 'background 0.15s'
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        onClick={handleSelect}
      >
        {/* Expand/collapse icon */}
        {node.hasChildren && !isSearchResult ? (
          <div onClick={handleClick} style={{ width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg 
              viewBox="0 0 24 24" 
              width="14" 
              height="14" 
              fill="none" 
              stroke="var(--text-secondary)" 
              strokeWidth="2"
              style={{ 
                transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s'
              }}
            >
              <path d="M9 6l6 6-6 6" />
            </svg>
          </div>
        ) : (
          <div style={{ width: 16 }} />
        )}

        {/* Node icon */}
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke={node.type ? 'var(--tcs-blue)' : 'var(--text-secondary)'} strokeWidth="2">
          {node.hasChildren ? (
            <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          ) : (
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          )}
        </svg>

        {/* Node name */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <span style={{ 
            fontSize: 12, 
            color: 'var(--text-primary)', 
            fontWeight: 500,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {node.name}
          </span>
          {node.type && (
            <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
              {node.type}
            </span>
          )}
        </div>

        {/* Node ID badge */}
        <span style={{
          fontSize: 10,
          padding: '2px 6px',
          borderRadius: 4,
          background: 'var(--bg-tertiary)',
          color: 'var(--text-secondary)',
          fontFamily: 'monospace'
        }}>
          {node.id}
        </span>
      </div>

      {/* Children */}
      {isExpanded && !isSearchResult && !loading && children.map((child) => (
        <TreeNode
          key={child.id}
          node={child}
          level={level + 1}
          isExpanded={expandedNodes?.has(child.id)}
          onToggle={onToggle}
          onSelect={onSelect}
          expandedNodes={expandedNodes}
          viewer={viewer}
        />
      ))}

      {/* Loading indicator */}
      {isExpanded && loading && (
        <div style={{ 
          paddingLeft: indent + 32, 
          paddingTop: 4, 
          paddingBottom: 4,
          fontSize: 11, 
          color: 'var(--text-secondary)' 
        }}>
          Loading...
        </div>
      )}
    </>
  );
}
