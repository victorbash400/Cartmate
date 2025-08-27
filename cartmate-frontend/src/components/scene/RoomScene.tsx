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
    camera.position.set(0, 1.6, 7); // Standard eye height, positioned to see the room well
    camera.lookAt(0, 1.2, -3); // Look toward the center back of the room

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // Room dimensions - balanced proportions
    const roomWidth = 7;    // Width
    const roomHeight = 3;   // Ceiling height
    const roomDepth = 12;   // Depth (makes it feel deeper)

    // Materials
    const wallMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xf5f5f5,
      roughness: 0.7,
      metalness: 0.1
    });
    
    const floorMaterial = new THREE.MeshStandardMaterial({ 
      color: 0xe8e8e8,
      roughness: 0.8,
      metalness: 0.05
    });

    // Create room (walls, floor, ceiling)
    // Back wall
    const backWallGeometry = new THREE.PlaneGeometry(roomWidth, roomHeight);
    const backWall = new THREE.Mesh(backWallGeometry, wallMaterial);
    backWall.position.z = -roomDepth / 2;
    backWall.position.y = roomHeight / 2;
    scene.add(backWall);

    // Left wall
    const leftWallGeometry = new THREE.PlaneGeometry(roomDepth, roomHeight);
    const leftWall = new THREE.Mesh(leftWallGeometry, wallMaterial);
    leftWall.position.x = -roomWidth / 2;
    leftWall.position.y = roomHeight / 2;
    leftWall.rotation.y = Math.PI / 2;
    scene.add(leftWall);

    // Right wall
    const rightWallGeometry = new THREE.PlaneGeometry(roomDepth, roomHeight);
    const rightWall = new THREE.Mesh(rightWallGeometry, wallMaterial);
    rightWall.position.x = roomWidth / 2;
    rightWall.position.y = roomHeight / 2;
    rightWall.rotation.y = -Math.PI / 2;
    scene.add(rightWall);

    // Floor
    const floorGeometry = new THREE.PlaneGeometry(roomWidth, roomDepth);
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    // Ceiling
    const ceilingGeometry = new THREE.PlaneGeometry(roomWidth, roomDepth);
    const ceiling = new THREE.Mesh(ceilingGeometry, wallMaterial);
    ceiling.position.y = roomHeight;
    ceiling.rotation.x = Math.PI / 2;
    scene.add(ceiling);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
    directionalLight.position.set(4, 5, 2);
    scene.add(directionalLight);

    // Fill light for better depth
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.25);
    fillLight.position.set(-4, 2, 0);
    scene.add(fillLight);

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