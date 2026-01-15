// src/components/PointCloudViewer.jsx
import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

// Semantic segmentation color palette - shared across all viewers
const SEMANTIC_COLORS = [
  0xff5555, 0x55ff55, 0x5555ff, 0xffff55, 0xff55ff,
  0x55ffff, 0xffffff, 0x999999, 0xff9955, 0x55ff99,
  0x9955ff, 0x3333cc, 0x22aa88,
];

// Get color hex string for a label (for canvas rendering)
export function getColorForLabel(label) {
  const colorHex = SEMANTIC_COLORS[label % SEMANTIC_COLORS.length];
  return '#' + colorHex.toString(16).padStart(6, '0');
}

/**
 PointCloudViewer
  - Uses your orientation mapping: posArray.push(x, z, -y)
  - Double-click selects entire segment and also highlights the exact point (pulsing sphere)
  - Reacts to external `selectedSegmentId` prop to highlight segments clicked in GraphViewer
  - Scene/camera/controls/renderer created once; geometry replaced on data updates

 Props:
  - data: { points: [[x,y,z],...], labels: [int,...], scene_id: string }
  - onSegmentClick({ pointIndex, label, segmentId, sceneId })
  - selectedSegmentId: string | null         // e.g. "scene1_sem_5"
  - autoFocusOnSelect: boolean (default false)
  - width, height
*/

export default function PointCloudViewer({
  data,
  onSegmentClick,
  selectedSegmentId = null,
  autoFocusOnSelect = false,
  width = "100%",
  height = 400,
}) {
  const mountRef = useRef(null);

  // persistent refs for scene lifecycle
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const pointsMeshRef = useRef(null);
  const animationRef = useRef(null);

  // highlight per-segment via attribute; highlightPointRef for selected exact point
  const segmentMapRef = useRef({});
  const cloudRadiusRef = useRef(1);
  const highlightPointRef = useRef(null); // small pulsing sphere for exact point
  const pulseTimeRef = useRef(0);

  // Initialize scene once
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // create scene + renderer + camera + controls
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc); // TCS light background
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    // set initial size
    const w = mount.clientWidth || 800;
    const h = mount.clientHeight || 600;
    renderer.setSize(w, h);
    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    const camera = new THREE.PerspectiveCamera(75, w / h, 0.01, 1000);
    camera.up.set(0, 1, 0);
    camera.position.set(0, 0, 3);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.screenSpacePanning = true;
    controls.minPolarAngle = 0.01;
    controls.maxPolarAngle = Math.PI - 0.01;

    sceneRef.current = scene;
    rendererRef.current = renderer;
    cameraRef.current = camera;
    controlsRef.current = controls;

    // animation loop (includes pulsing highlightPoint)
    const animate = () => {
      controls.update();

      // pulse small selected-point sphere if present
      if (highlightPointRef.current) {
        pulseTimeRef.current += 0.06;
        const scale = 1 + 0.35 * Math.sin(pulseTimeRef.current);
        highlightPointRef.current.scale.set(scale, scale, scale);
      }

      renderer.render(scene, camera);
      animationRef.current = requestAnimationFrame(animate);
    };
    animate();

    // resize handler
    const onResize = () => {
      if (!mount) return;
      const newW = mount.clientWidth || 800;
      const newH = mount.clientHeight || 600;
      renderer.setSize(newW, newH);
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    // guard context menu
    renderer.domElement.addEventListener("contextmenu", (e) => e.preventDefault());

    return () => {
      window.removeEventListener("resize", onResize);
      renderer.domElement.removeEventListener("contextmenu", (e) => e.preventDefault());
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      controls.dispose();
      renderer.dispose();
      // dispose any existing mesh / highlight point
      if (pointsMeshRef.current) {
        try {
          pointsMeshRef.current.geometry.dispose();
          pointsMeshRef.current.material.dispose();
        } catch (e) {}
      }
      if (highlightPointRef.current) {
        try {
          highlightPointRef.current.geometry.dispose();
          highlightPointRef.current.material.dispose();
        } catch (e) {}
      }
      sceneRef.current = null;
      rendererRef.current = null;
      cameraRef.current = null;
      controlsRef.current = null;
      pointsMeshRef.current = null;
      highlightPointRef.current = null;
    };
  }, []); // Remove height dependency

  // Update geometry when `data` changes
  useEffect(() => {
    const scene = sceneRef.current;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!scene || !renderer || !camera || !controls) return;

    // remove old mesh cleanly (but keep scene/camera/controls)
    if (pointsMeshRef.current) {
      scene.remove(pointsMeshRef.current);
      try {
        pointsMeshRef.current.geometry.dispose();
        pointsMeshRef.current.material.dispose();
      } catch (e) {}
      pointsMeshRef.current = null;
    }

    if (!data || !Array.isArray(data.points) || data.points.length === 0) {
      // nothing to show
      return;
    }

    const { points, labels = [], scene_id } = data;

    // Build segment map: label -> indices
    const segmentMap = {};
    labels.forEach((lbl, i) => {
      const key = lbl ?? 0;
      if (!segmentMap[key]) segmentMap[key] = [];
      segmentMap[key].push(i);
    });
    segmentMapRef.current = segmentMap;
    
    console.log('[PointCloudViewer] Built segment map with keys:', Object.keys(segmentMap), 'for scene:', scene_id);

    // Geometry buffers
    const n = points.length;
    const posArray = new Float32Array(n * 3);
    const colorArray = new Float32Array(n * 3);
    const highlightArray = new Float32Array(n * 3); // initially zeros

    for (let i = 0; i < n; i++) {
      const p = points[i];
      const x = p[0], y = p[1], z = p[2];

      // preserve your orientation fix: x, z, -y
      posArray[3 * i] = x;
      posArray[3 * i + 1] = z;
      posArray[3 * i + 2] = -y;

      const lbl = labels[i] ?? 0;
      const c = new THREE.Color(SEMANTIC_COLORS[lbl % SEMANTIC_COLORS.length]);
      colorArray[3 * i] = c.r;
      colorArray[3 * i + 1] = c.g;
      colorArray[3 * i + 2] = c.b;

      highlightArray[3 * i] = 0;
      highlightArray[3 * i + 1] = 0;
      highlightArray[3 * i + 2] = 0;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colorArray, 3));
    geometry.setAttribute("highlightColor", new THREE.BufferAttribute(highlightArray, 3)); // custom attribute
    geometry.computeBoundingSphere();

    const bs = geometry.boundingSphere || { center: new THREE.Vector3(0, 0, 0), radius: 1 };
    const center = bs.center.clone();
    const radius = Math.max(0.001, bs.radius);
    cloudRadiusRef.current = radius;

    // PointsMaterial + onBeforeCompile to mix highlightColor
    const material = new THREE.PointsMaterial({
      size: Math.max(0.005, radius * 0.01),
      vertexColors: true,
      sizeAttenuation: true,
    });

    // Patch shader to mix highlightColor with base color
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        "varying vec3 vColor;",
        `varying vec3 vColor;
         attribute vec3 highlightColor;
         varying vec3 vHighlightColor;`
      );

      shader.vertexShader = shader.vertexShader.replace(
        "vColor = color;",
        `vColor = color;
         vHighlightColor = highlightColor;`
      );

      shader.fragmentShader = shader.fragmentShader.replace(
        "varying vec3 vColor;",
        `varying vec3 vColor;
         varying vec3 vHighlightColor;`
      );

      shader.fragmentShader = shader.fragmentShader.replace(
        "gl_FragColor = vec4( vColor, opacity );",
        `// Only apply highlight if highlightColor is non-zero
         float highlightIntensity = length(vHighlightColor);
         vec3 finalColor = highlightIntensity > 0.1 ? vHighlightColor : vColor;
         gl_FragColor = vec4( finalColor, opacity );`
      );
    };

    const pointsMesh = new THREE.Points(geometry, material);
    // store labels so picking consults them quickly
    pointsMesh.userData = { labels, scene_id, pointsArray: posArray };
    pointsMesh.position.set(-center.x, -center.y, -center.z);

    scene.add(pointsMesh);
    pointsMeshRef.current = pointsMesh;

    // camera placement: auto-fit only if camera is still at default (no saved user view)
    const camPos = camera.position;
    const distanceToCenter = camPos.distanceTo(new THREE.Vector3(0, 0, 0));
    // naive test: if camera is very near default, auto place (first load)
    if (!camera.userData._initialized || distanceToCenter < 0.0001) {
      camera.position.copy(center.clone().add(new THREE.Vector3(0, 0, radius * 2.5)));
      controls.target.copy(center);
      controls.update();
      camera.userData._initialized = true;
    } else {
      // preserve user's camera/controls
      controls.update();
    }

    // Raycaster for picking entire segment + point
    const raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = radius * 0.01;
    const mouse = new THREE.Vector2();

    // selection handler — double click to avoid conflicts with drag
    const onDoubleClick = (ev) => {
      if (!pointsMeshRef.current) return;
      const canvasRect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((ev.clientX - canvasRect.left) / canvasRect.width) * 2 - 1;
      mouse.y = -((ev.clientY - canvasRect.top) / canvasRect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObject(pointsMeshRef.current, false);
      if (!hits.length) return;

      const hit = hits[0];
      const idx = hit.index;
      const lbl = (pointsMeshRef.current.userData.labels && pointsMeshRef.current.userData.labels[idx]) ?? 0;

      // Update highlightColor attribute for the whole segment
      const highlightAttr = geometry.getAttribute("highlightColor");
      // zero out previous highlights
      highlightAttr.array.fill(0);

      const indices = segmentMap[lbl] || [];
      for (let k = 0; k < indices.length; k++) {
        const ii = indices[k];
        // highlight bright yellow-ish
        highlightAttr.array[ii * 3 + 0] = 1.0;
        highlightAttr.array[ii * 3 + 1] = 0.9;
        highlightAttr.array[ii * 3 + 2] = 0.0;
      }
      highlightAttr.needsUpdate = true;

      // place or move the small pulsing sphere at the exact selected point (world coords)
      const worldPoint = hit.point.clone(); // Three gives world coordinate already
      const pointSize = Math.max(0.02, radius * 0.02);
      if (!highlightPointRef.current) {
        const sphGeom = new THREE.SphereGeometry(pointSize, 16, 12);
        const sphMat = new THREE.MeshBasicMaterial({ color: 0xffea00 });
        const sph = new THREE.Mesh(sphGeom, sphMat);
        sph.castShadow = false;
        sph.receiveShadow = false;
        scene.add(sph);
        highlightPointRef.current = sph;
      } else {
        // adjust sphere size if radius changed
        const sph = highlightPointRef.current;
        const geom = sph.geometry;
        try {
          geom.dispose();
        } catch (e) {}
        highlightPointRef.current.geometry = new THREE.SphereGeometry(pointSize, 16, 12);
      }
      highlightPointRef.current.position.copy(worldPoint);
      pulseTimeRef.current = 0;

      // callback to parent
      const segmentId = `${scene_id}_sem_${lbl}`;
      onSegmentClick?.({ pointIndex: idx, label: lbl, segmentId, sceneId: scene_id });
    };

    renderer.domElement.addEventListener("dblclick", onDoubleClick);

    // cleanup when data changes
    return () => {
      try {
        renderer.domElement.removeEventListener("dblclick", onDoubleClick);
      } catch (e) {}
      // keep scene/camera alive
    };
  }, [data]); // Only rebuild when data changes, not on every render

  // --- Robust: react to external selectedSegmentId prop ---
  useEffect(() => {
    console.log('[PointCloudViewer] 🔵 useEffect triggered - selectedSegmentId:', selectedSegmentId);
    const pointsMesh = pointsMeshRef.current;
    console.log('[PointCloudViewer] 🔵 pointsMesh exists:', !!pointsMesh);

    // helper: clear highlights
    const clearHighlights = () => {
      if (pointsMesh && pointsMesh.geometry) {
        const highlightAttr = pointsMesh.geometry.getAttribute("highlightColor");
        if (highlightAttr) {
          highlightAttr.array.fill(0);
          highlightAttr.needsUpdate = true;
        }
      }
      if (highlightPointRef.current) {
        try { sceneRef.current.remove(highlightPointRef.current); } catch(e) {}
        try { highlightPointRef.current.geometry.dispose(); highlightPointRef.current.material.dispose(); } catch(e){}
        highlightPointRef.current = null;
      }
    };

    if (!pointsMesh || !selectedSegmentId) {
      clearHighlights();
      return;
    }

    // Extract candidate label string: use last occurrence of "_sem_"
    const parts = String(selectedSegmentId).split("_sem_");
    const lastPart = parts[parts.length - 1];
    // try numeric parse first
    let selLabel = Number(lastPart);
    let labelFound = !Number.isNaN(selLabel);

    // If not numeric, try to match by constructed id from known labels (defensive)
    const sceneIdFromMesh = pointsMesh.userData && pointsMesh.userData.scene_id;
    if (!labelFound) {
      const segMap = segmentMapRef.current || {};
      for (const lblKey of Object.keys(segMap)) {
        const candidateId = `${sceneIdFromMesh}_sem_${lblKey}`;
        if (candidateId === selectedSegmentId) {
          selLabel = Number(lblKey);
          labelFound = true;
          break;
        }
      }
    }

    // If still not found, attempt fallback: strip digits from lastPart
    if (!labelFound) {
      const digits = lastPart.match(/-?\d+/);
      if (digits) {
        selLabel = Number(digits[0]);
        if (!Number.isNaN(selLabel)) labelFound = true;
      }
    }

    if (!labelFound) {
      console.warn("[PointCloudViewer] Could not parse numeric label from selectedSegmentId:", selectedSegmentId);
      clearHighlights();
      return;
    }

    console.log("[PointCloudViewer] Highlighting segment:", { 
      selectedSegmentId, 
      parsedLabel: selLabel,
      segmentMapKeys: Object.keys(segmentMapRef.current || {})
    });

    // At this point selLabel is the numeric label we want to highlight
    const geometry = pointsMesh.geometry;
    const labels = pointsMesh.userData.labels || [];
    const highlightAttr = geometry.getAttribute("highlightColor");
    if (!highlightAttr) {
      console.warn("[PointCloudViewer] No highlightColor attribute found");
      return;
    }

    // zero out
    highlightAttr.array.fill(0);

    // find indices - try both numeric and string keys
    let indices = [];
    const segMap = segmentMapRef.current || {};
    
    // Try numeric key first
    if (segMap[selLabel]) {
      indices = segMap[selLabel];
    }
    // Try string key
    else if (segMap[String(selLabel)]) {
      indices = segMap[String(selLabel)];
    }
    // Try all keys to find a match
    else {
      for (const key of Object.keys(segMap)) {
        if (Number(key) === selLabel || key === String(selLabel)) {
          indices = segMap[key];
          break;
        }
      }
    }

    console.log("[PointCloudViewer] Found indices:", indices?.length || 0, "for label:", selLabel);

    if (indices.length === 0) {
      console.warn("[PointCloudViewer] No points found for label:", selLabel, "Available labels:", Object.keys(segMap));
      clearHighlights();
      return;
    }

    for (let k = 0; k < indices.length; k++) {
      const ii = indices[k];
      highlightAttr.array[ii * 3 + 0] = 1.0;
      highlightAttr.array[ii * 3 + 1] = 0.9;
      highlightAttr.array[ii * 3 + 2] = 0.0;
    }
    highlightAttr.needsUpdate = true;

    // compute centroid (cloud-local coords) from the selected points and place pulsing sphere there
    if (indices.length > 0) {
      const posAttr = geometry.getAttribute("position");
      const worldPos = new THREE.Vector3(0,0,0);
      for (let i = 0; i < indices.length; i++) {
        const idx = indices[i];
        const x = posAttr.array[idx*3 + 0];
        const y = posAttr.array[idx*3 + 1];
        const z = posAttr.array[idx*3 + 2];
        worldPos.x += x;
        worldPos.y += y;
        worldPos.z += z;
      }
      worldPos.multiplyScalar(1 / indices.length);

      // convert cloud-local position to scene world by adding pointsMesh.position (you translated cloud to center)
      const worldPoint = worldPos.clone().add(pointsMesh.position);

      const radius = cloudRadiusRef.current || 1;
      const pointSize = Math.max(0.02, radius * 0.02);
      if (!highlightPointRef.current) {
        const sphGeom = new THREE.SphereGeometry(pointSize, 16, 12);
        const sphMat = new THREE.MeshBasicMaterial({ color: 0xffea00 });
        const sph = new THREE.Mesh(sphGeom, sphMat);
        sph.castShadow = false;
        sph.receiveShadow = false;
        sceneRef.current.add(sph);
        highlightPointRef.current = sph;
      } else {
        try { highlightPointRef.current.geometry.dispose(); } catch(e){}
        highlightPointRef.current.geometry = new THREE.SphereGeometry(pointSize, 16, 12);
      }
      highlightPointRef.current.position.copy(worldPoint);
      pulseTimeRef.current = 0;

      // optional: smoothly move camera / focus on the selected centroid
      if (autoFocusOnSelect) {
        try {
          const cam = cameraRef.current;
          const controls = controlsRef.current;
          const offset = new THREE.Vector3(0, 0, cloudRadiusRef.current * 1.8);
          const newCamPos = worldPoint.clone().add(offset);
          cam.position.copy(newCamPos);
          controls.target.copy(worldPoint);
          controls.update();
        } catch (e) {}
      }
    } else {
      // no points found for label -> remove sphere (safety)
      if (highlightPointRef.current) {
        try { sceneRef.current.remove(highlightPointRef.current); } catch(e){}
        try { highlightPointRef.current.geometry.dispose(); highlightPointRef.current.material.dispose(); } catch(e){}
        highlightPointRef.current = null;
      }
    }

  }, [selectedSegmentId, autoFocusOnSelect, data]); // Reapply highlights after data rebuild

  // Zoom and camera controls
  const handleZoomIn = () => {
    if (controlsRef.current && cameraRef.current) {
      const controls = controlsRef.current;
      const camera = cameraRef.current;
      const direction = new THREE.Vector3();
      camera.getWorldDirection(direction);
      const distance = camera.position.distanceTo(controls.target);
      const moveAmount = distance * 0.2;
      camera.position.add(direction.multiplyScalar(moveAmount));
      controls.update();
    }
  };

  const handleZoomOut = () => {
    if (controlsRef.current && cameraRef.current) {
      const controls = controlsRef.current;
      const camera = cameraRef.current;
      const direction = new THREE.Vector3();
      camera.getWorldDirection(direction);
      const distance = camera.position.distanceTo(controls.target);
      const moveAmount = distance * 0.2;
      camera.position.sub(direction.multiplyScalar(moveAmount));
      controls.update();
    }
  };

  const handleResetView = () => {
    if (cameraRef.current && controlsRef.current) {
      const camera = cameraRef.current;
      const controls = controlsRef.current;
      camera.position.set(0, 0, cloudRadiusRef.current * 3);
      controls.target.set(0, 0, 0);
      controls.update();
    }
  };

  const handleTopView = () => {
    if (cameraRef.current && controlsRef.current) {
      const camera = cameraRef.current;
      const controls = controlsRef.current;
      camera.position.set(0, cloudRadiusRef.current * 3, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    }
  };

  const handleFrontView = () => {
    if (cameraRef.current && controlsRef.current) {
      const camera = cameraRef.current;
      const controls = controlsRef.current;
      camera.position.set(0, 0, cloudRadiusRef.current * 3);
      controls.target.set(0, 0, 0);
      controls.update();
    }
  };

  const handleSideView = () => {
    if (cameraRef.current && controlsRef.current) {
      const camera = cameraRef.current;
      const controls = controlsRef.current;
      camera.position.set(cloudRadiusRef.current * 3, 0, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    }
  };

  return (
    <div style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '100%',
          overflow: "hidden",
        }}
      />
      
      {/* Corporate-Grade Viewer Controls */}
      <div style={{
        position: 'absolute',
        top: '12px',
        right: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '1px',
        zIndex: 10,
        background: 'white',
        borderRadius: '8px',
        border: '1px solid rgba(0, 118, 206, 0.2)',
        boxShadow: '0 4px 12px rgba(0, 61, 121, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Zoom Controls */}
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-blue)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>

        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-blue)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>

        <button
          onClick={handleResetView}
          title="Reset View"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-blue)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M3 12a9 9 0 1 0 18 0 9 9 0 1 0-18 0"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        </button>

        {/* Camera View Divider */}
        <div style={{ height: '2px', background: 'rgba(0, 118, 206, 0.2)' }}></div>

        {/* Camera Views */}
        <button
          onClick={handleTopView}
          title="Top View (XZ Plane)"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-navy)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            fontWeight: '700',
            letterSpacing: '0.5px',
            transition: 'all 0.2s',
            borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-orange)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-navy)'; }}
        >
          TOP
        </button>

        <button
          onClick={handleFrontView}
          title="Front View (XY Plane)"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-navy)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '9px',
            fontWeight: '700',
            letterSpacing: '0.3px',
            transition: 'all 0.2s',
            borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-orange)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-navy)'; }}
        >
          FRONT
        </button>

        <button
          onClick={handleSideView}
          title="Side View (YZ Plane)"
          style={{
            width: '40px',
            height: '40px',
            border: 'none',
            background: 'white',
            color: 'var(--tcs-navy)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            fontWeight: '700',
            letterSpacing: '0.5px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-orange)'; e.currentTarget.style.color = 'white'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-navy)'; }}
        >
          SIDE
        </button>
      </div>
    </div>
  );
}
