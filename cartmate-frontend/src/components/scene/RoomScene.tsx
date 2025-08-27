import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

const RoomScene: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa); // Light gray background

    // Camera setup - optimized for front view of room
    const camera = new THREE.PerspectiveCamera(
      45, // Natural field of view
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 1.6, 8); // Standard eye height, positioned to see the room well
    camera.lookAt(0, 1.2, -3); // Look toward the center back of the room

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mountRef.current.appendChild(renderer.domElement);

    // Room dimensions - shopping mall proportions
    const roomWidth = 12;   // Wider for mall feel
    const roomHeight = 4;   // Higher ceiling
    const roomDepth = 16;   // Deeper for mall perspective

    // Materials - clean shopping mall style
    const wallMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xffffff,        // Pure white walls
      roughness: 0.5,
      metalness: 0.1
    });
    
    const floorMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xf8f8f8,        // Off-white floor
      roughness: 0.8,
      metalness: 0.0
    });

    // Orange accent material for highlights
    const accentMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xFF9E00,        // Orange accents
      roughness: 0.7,
      metalness: 0.2
    });

    // Create room (walls, floor, ceiling)
    // Back wall
    const backWallGeometry = new THREE.PlaneGeometry(roomWidth, roomHeight);
    const backWall = new THREE.Mesh(backWallGeometry, wallMaterial);
    backWall.position.z = -roomDepth / 2;
    backWall.position.y = roomHeight / 2;
    backWall.receiveShadow = true;
    scene.add(backWall);

    // Left wall
    const leftWallGeometry = new THREE.PlaneGeometry(roomDepth, roomHeight);
    const leftWall = new THREE.Mesh(leftWallGeometry, wallMaterial);
    leftWall.position.x = -roomWidth / 2;
    leftWall.position.y = roomHeight / 2;
    leftWall.rotation.y = Math.PI / 2;
    leftWall.receiveShadow = true;
    scene.add(leftWall);

    // Right wall
    const rightWallGeometry = new THREE.PlaneGeometry(roomDepth, roomHeight);
    const rightWall = new THREE.Mesh(rightWallGeometry, wallMaterial);
    rightWall.position.x = roomWidth / 2;
    rightWall.position.y = roomHeight / 2;
    rightWall.rotation.y = -Math.PI / 2;
    rightWall.receiveShadow = true;
    scene.add(rightWall);

    // Floor
    const floorGeometry = new THREE.PlaneGeometry(roomWidth, roomDepth);
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // Ceiling
    const ceilingGeometry = new THREE.PlaneGeometry(roomWidth, roomDepth);
    const ceiling = new THREE.Mesh(ceilingGeometry, wallMaterial);
    ceiling.position.y = roomHeight;
    ceiling.rotation.x = Math.PI / 2;
    ceiling.receiveShadow = true;
    scene.add(ceiling);

    // Shopping mall features - orange accent strips
    // Ceiling accent strip
    const ceilingStripGeometry = new THREE.PlaneGeometry(roomWidth * 0.8, 0.3);
    const ceilingStrip = new THREE.Mesh(ceilingStripGeometry, accentMaterial);
    ceilingStrip.position.set(0, roomHeight - 0.3, -roomDepth * 0.3);
    ceilingStrip.rotation.x = Math.PI / 2;
    scene.add(ceilingStrip);

    // Floor accent strip
    const floorStripGeometry = new THREE.PlaneGeometry(roomWidth * 0.8, 0.3);
    const floorStrip = new THREE.Mesh(floorStripGeometry, accentMaterial);
    floorStrip.position.set(0, 0.01, -roomDepth * 0.3);
    floorStrip.rotation.x = -Math.PI / 2;
    scene.add(floorStrip);

    // Left wall accent strip
    const leftWallStripGeometry = new THREE.PlaneGeometry(roomDepth * 0.6, 0.3);
    const leftWallStrip = new THREE.Mesh(leftWallStripGeometry, accentMaterial);
    leftWallStrip.position.set(-roomWidth / 2 + 0.01, roomHeight * 0.7, -roomDepth * 0.2);
    leftWallStrip.rotation.y = Math.PI / 2;
    scene.add(leftWallStrip);

    // Right wall accent strip
    const rightWallStripGeometry = new THREE.PlaneGeometry(roomDepth * 0.6, 0.3);
    const rightWallStrip = new THREE.Mesh(rightWallStripGeometry, accentMaterial);
    rightWallStrip.position.set(roomWidth / 2 - 0.01, roomHeight * 0.7, -roomDepth * 0.2);
    rightWallStrip.rotation.y = -Math.PI / 2;
    scene.add(rightWallStrip);

    // Lighting - bright, clean shopping mall lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);

    // Main ceiling lights
    const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
    mainLight.position.set(0, roomHeight * 0.9, 0);
    mainLight.castShadow = true;
    mainLight.shadow.mapSize.width = 2048;
    mainLight.shadow.mapSize.height = 2048;
    scene.add(mainLight);

    // Front lighting for better depth
    const frontLight = new THREE.DirectionalLight(0xffffff, 0.5);
    frontLight.position.set(0, roomHeight * 0.7, roomDepth * 0.4);
    scene.add(frontLight);

    // Orange accent lighting
    const accentLight = new THREE.DirectionalLight(0xFF9E00, 0.3);
    accentLight.position.set(0, roomHeight, -roomDepth * 0.3);
    scene.add(accentLight);

    // Handle window resize
    const handleResize = () => {
      if (!mountRef.current) return;
      
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };

    window.addEventListener('resize', handleResize);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (mountRef.current) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div 
      ref={mountRef} 
      style={{ 
        width: '100%', 
        height: '100%',
        borderRadius: '12px',
        overflow: 'hidden'
      }} 
    />
  );
};

export default RoomScene;