import React, { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * A quiet, engineering-diagram-style 3D backdrop: a sparse network of nodes
 * drifting slowly in depth, with thin lines connecting nearby nodes —
 * meant to evoke "people/skills forming clusters (teams)", not a game
 * background. Kept subtle on purpose: low object count, slow motion, low
 * opacity, disabled entirely under prefers-reduced-motion or on narrow
 * (mobile) viewports where it would just cost battery for no visual payoff.
 */
export default function NetworkBackground() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isNarrow = window.innerWidth < 768;
    if (prefersReducedMotion || isNarrow || !mountRef.current) return;

    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 1, 2000);
    camera.position.z = 620;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    mount.appendChild(renderer.domElement);

    // --- Nodes: a handful of loose clusters (skills forming into teams) ---
    const CLUSTER_COUNT = 4;
    const NODES_PER_CLUSTER = 7;
    const nodeCount = CLUSTER_COUNT * NODES_PER_CLUSTER;

    const positions = new Float32Array(nodeCount * 3);
    const velocities: THREE.Vector3[] = [];
    const clusterCenters: THREE.Vector3[] = [];

    for (let c = 0; c < CLUSTER_COUNT; c++) {
      clusterCenters.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * 700,
          (Math.random() - 0.5) * 420,
          (Math.random() - 0.5) * 300
        )
      );
    }

    for (let i = 0; i < nodeCount; i++) {
      const center = clusterCenters[Math.floor(i / NODES_PER_CLUSTER)];
      const x = center.x + (Math.random() - 0.5) * 160;
      const y = center.y + (Math.random() - 0.5) * 160;
      const z = center.z + (Math.random() - 0.5) * 160;
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      velocities.push(
        new THREE.Vector3((Math.random() - 0.5) * 0.06, (Math.random() - 0.5) * 0.06, (Math.random() - 0.5) * 0.04)
      );
    }

    const nodeGeometry = new THREE.BufferGeometry();
    nodeGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const nodeMaterial = new THREE.PointsMaterial({
      color: 0xb88952, // copper accent — sparing use, consistent with the brand palette
      size: 3.2,
      transparent: true,
      opacity: 0.55,
      sizeAttenuation: true,
    });
    const points = new THREE.Points(nodeGeometry, nodeMaterial);
    scene.add(points);

    // --- Connections: thin lines between nearby nodes (recomputed each frame) ---
    const maxConnections = nodeCount * 4;
    const linePositions = new Float32Array(maxConnections * 2 * 3);
    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x7a263a, transparent: true, opacity: 0.35 });
    const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
    scene.add(lines);

    const CONNECT_DISTANCE = 130;

    function updateConnections() {
      let idx = 0;
      const posAttr = nodeGeometry.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < nodeCount && idx < maxConnections; i++) {
        for (let j = i + 1; j < nodeCount && idx < maxConnections; j++) {
          const dx = posAttr.getX(i) - posAttr.getX(j);
          const dy = posAttr.getY(i) - posAttr.getY(j);
          const dz = posAttr.getZ(i) - posAttr.getZ(j);
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (dist < CONNECT_DISTANCE) {
            linePositions[idx * 6] = posAttr.getX(i);
            linePositions[idx * 6 + 1] = posAttr.getY(i);
            linePositions[idx * 6 + 2] = posAttr.getZ(i);
            linePositions[idx * 6 + 3] = posAttr.getX(j);
            linePositions[idx * 6 + 4] = posAttr.getY(j);
            linePositions[idx * 6 + 5] = posAttr.getZ(j);
            idx++;
          }
        }
      }
      for (let k = idx * 6; k < linePositions.length; k++) linePositions[k] = 0;
      lineGeometry.attributes.position.needsUpdate = true;
      lineGeometry.setDrawRange(0, idx * 2);
    }

    let raf = 0;
    let frame = 0;
    function animate() {
      raf = requestAnimationFrame(animate);
      frame++;
      const posAttr = nodeGeometry.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < nodeCount; i++) {
        const center = clusterCenters[Math.floor(i / NODES_PER_CLUSTER)];
        let x = posAttr.getX(i) + velocities[i].x;
        let y = posAttr.getY(i) + velocities[i].y;
        let z = posAttr.getZ(i) + velocities[i].z;
        x += (center.x - x) * 0.0015;
        y += (center.y - y) * 0.0015;
        z += (center.z - z) * 0.0015;
        posAttr.setXYZ(i, x, y, z);
      }
      posAttr.needsUpdate = true;
      if (frame % 3 === 0) updateConnections();
      scene.rotation.y = Math.sin(frame * 0.0004) * 0.08;
      renderer.render(scene, camera);
    }
    updateConnections();
    animate();

    function handleResize() {
      if (!mount) return;
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", handleResize);
      nodeGeometry.dispose();
      lineGeometry.dispose();
      nodeMaterial.dispose();
      lineMaterial.dispose();
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      aria-hidden="true"
      className="fixed inset-0 -z-10 pointer-events-none hidden md:block"
      style={{ opacity: 0.8 }}
    />
  );
}