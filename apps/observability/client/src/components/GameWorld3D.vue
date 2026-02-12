<template>
  <div ref="containerRef" class="game-world-container">
    <canvas ref="canvasRef"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

interface Agent {
  name: string;
  tool: string;
  activity: string;
}

interface Props {
  activeAgents?: Agent[];
}

const props = withDefaults(defineProps<Props>(), {
  activeAgents: () => []
});

const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let animationFrameId: number;
let workstationPositions: THREE.Vector3[] = [];

const WORKSTATION_COUNT = 8;
const WORKSTATION_RADIUS = 8;

function initScene() {
  if (!canvasRef.value || !containerRef.value) return;

  // Scene setup
  scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x87ceeb, 20, 50);

  // Camera setup - isometric-like perspective
  camera = new THREE.PerspectiveCamera(
    45,
    containerRef.value.clientWidth / containerRef.value.clientHeight,
    0.1,
    1000
  );
  camera.position.set(15, 15, 15);
  camera.lookAt(0, 0, 0);

  // Renderer setup
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: true,
    alpha: true
  });
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x87ceeb, 1);

  // Controls setup
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.minDistance = 10;
  controls.maxDistance = 40;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.target.set(0, 0, 0);

  createEnvironment();
  createLighting();
  createWorkstations();

  // Handle window resize
  window.addEventListener('resize', handleResize);
}

function createEnvironment() {
  // Ground plane with grass texture
  const groundGeometry = new THREE.CircleGeometry(25, 64);
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: 0x4a7c3d,
    roughness: 0.8,
    metalness: 0.2
  });
  const ground = new THREE.Mesh(groundGeometry, groundMaterial);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // Add some texture variation to ground
  const groundDetailGeometry = new THREE.CircleGeometry(24, 64);
  const groundDetailMaterial = new THREE.MeshStandardMaterial({
    color: 0x5a8c4d,
    roughness: 0.9,
    metalness: 0.1,
    transparent: true,
    opacity: 0.5
  });
  const groundDetail = new THREE.Mesh(groundDetailGeometry, groundDetailMaterial);
  groundDetail.rotation.x = -Math.PI / 2;
  groundDetail.position.y = 0.01;
  scene.add(groundDetail);

  // Create decorative trees around the perimeter
  createTrees();

  // Create bushes for decoration
  createBushes();

  // Sky gradient (using hemisphere light will help too)
  scene.background = new THREE.Color(0x87ceeb);
}

function createTrees() {
  const treePositions = [
    { x: -12, z: -12 },
    { x: 12, z: -12 },
    { x: -12, z: 12 },
    { x: 12, z: 12 },
    { x: -15, z: 0 },
    { x: 15, z: 0 },
    { x: 0, z: -15 },
    { x: 0, z: 15 }
  ];

  treePositions.forEach(pos => {
    const tree = createTree();
    tree.position.set(pos.x, 0, pos.z);
    scene.add(tree);
  });
}

function createTree(): THREE.Group {
  const tree = new THREE.Group();

  // Tree trunk
  const trunkGeometry = new THREE.CylinderGeometry(0.3, 0.4, 2.5, 8);
  const trunkMaterial = new THREE.MeshStandardMaterial({
    color: 0x4a3520,
    roughness: 0.9
  });
  const trunk = new THREE.Mesh(trunkGeometry, trunkMaterial);
  trunk.position.y = 1.25;
  trunk.castShadow = true;
  tree.add(trunk);

  // Tree foliage (simplified stylized)
  const foliageGeometry = new THREE.SphereGeometry(1.5, 8, 8);
  const foliageMaterial = new THREE.MeshStandardMaterial({
    color: 0x2d5016,
    roughness: 0.8,
    flatShading: true
  });

  const foliage1 = new THREE.Mesh(foliageGeometry, foliageMaterial);
  foliage1.position.y = 3.5;
  foliage1.scale.set(1, 1.2, 1);
  foliage1.castShadow = true;
  tree.add(foliage1);

  const foliage2 = new THREE.Mesh(foliageGeometry, foliageMaterial);
  foliage2.position.y = 4.5;
  foliage2.scale.set(0.7, 0.8, 0.7);
  foliage2.castShadow = true;
  tree.add(foliage2);

  return tree;
}

function createBushes() {
  const bushPositions = [
    { x: -8, z: -6 },
    { x: 8, z: -6 },
    { x: -8, z: 6 },
    { x: 8, z: 6 },
    { x: -6, z: -8 },
    { x: 6, z: -8 },
    { x: -6, z: 8 },
    { x: 6, z: 8 }
  ];

  bushPositions.forEach(pos => {
    const bush = createBush();
    bush.position.set(pos.x, 0, pos.z);
    scene.add(bush);
  });
}

function createBush(): THREE.Group {
  const bush = new THREE.Group();

  const bushGeometry = new THREE.SphereGeometry(0.8, 6, 6);
  const bushMaterial = new THREE.MeshStandardMaterial({
    color: 0x3a6b2f,
    roughness: 0.9,
    flatShading: true
  });

  const bushMesh = new THREE.Mesh(bushGeometry, bushMaterial);
  bushMesh.scale.set(1, 0.6, 1);
  bushMesh.position.y = 0.3;
  bushMesh.castShadow = true;
  bush.add(bushMesh);

  return bush;
}

function createLighting() {
  // Ambient light for overall illumination
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  // Hemisphere light for sky/ground gradient
  const hemisphereLight = new THREE.HemisphereLight(0x87ceeb, 0x4a7c3d, 0.4);
  scene.add(hemisphereLight);

  // Directional light (sun) for shadows
  const directionalLight = new THREE.DirectionalLight(0xfff8dc, 0.8);
  directionalLight.position.set(10, 15, 5);
  directionalLight.castShadow = true;

  // Shadow camera setup
  directionalLight.shadow.camera.left = -20;
  directionalLight.shadow.camera.right = 20;
  directionalLight.shadow.camera.top = 20;
  directionalLight.shadow.camera.bottom = -20;
  directionalLight.shadow.camera.near = 0.1;
  directionalLight.shadow.camera.far = 50;
  directionalLight.shadow.mapSize.width = 2048;
  directionalLight.shadow.mapSize.height = 2048;
  directionalLight.shadow.bias = -0.0001;

  scene.add(directionalLight);

  // Add a subtle fill light
  const fillLight = new THREE.DirectionalLight(0xadd8e6, 0.3);
  fillLight.position.set(-10, 5, -5);
  scene.add(fillLight);
}

function createWorkstations() {
  workstationPositions = [];

  // Create workstations in a circle
  for (let i = 0; i < WORKSTATION_COUNT; i++) {
    const angle = (i / WORKSTATION_COUNT) * Math.PI * 2;
    const x = Math.cos(angle) * WORKSTATION_RADIUS;
    const z = Math.sin(angle) * WORKSTATION_RADIUS;

    const position = new THREE.Vector3(x, 0, z);
    workstationPositions.push(position);

    createWorkstationPlatform(position);
  }
}

function createWorkstationPlatform(position: THREE.Vector3) {
  // Create a small platform for each workstation
  const platformGeometry = new THREE.CylinderGeometry(1.2, 1.2, 0.2, 8);
  const platformMaterial = new THREE.MeshStandardMaterial({
    color: 0x8b7355,
    roughness: 0.7,
    metalness: 0.1
  });

  const platform = new THREE.Mesh(platformGeometry, platformMaterial);
  platform.position.copy(position);
  platform.position.y = 0.1;
  platform.castShadow = true;
  platform.receiveShadow = true;
  scene.add(platform);

  // Add a marker/outline
  const outlineGeometry = new THREE.TorusGeometry(1.2, 0.05, 8, 16);
  const outlineMaterial = new THREE.MeshStandardMaterial({
    color: 0x6b5345,
    roughness: 0.5
  });

  const outline = new THREE.Mesh(outlineGeometry, outlineMaterial);
  outline.position.copy(position);
  outline.position.y = 0.2;
  outline.rotation.x = Math.PI / 2;
  scene.add(outline);

  // Add a small sign post
  const postGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.8, 8);
  const postMaterial = new THREE.MeshStandardMaterial({
    color: 0x4a3520
  });

  const post = new THREE.Mesh(postGeometry, postMaterial);
  post.position.copy(position);
  post.position.y = 0.6;
  post.position.x += 1;
  post.castShadow = true;
  scene.add(post);
}

function animate() {
  animationFrameId = requestAnimationFrame(animate);

  controls.update();
  renderer.render(scene, camera);
}

function handleResize() {
  if (!containerRef.value) return;

  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
}

function cleanup() {
  window.removeEventListener('resize', handleResize);

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  if (controls) {
    controls.dispose();
  }

  if (renderer) {
    renderer.dispose();
  }

  // Dispose of geometries and materials
  scene?.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry?.dispose();
      if (object.material instanceof THREE.Material) {
        object.material.dispose();
      }
    }
  });
}

// Watch for agent changes (will be used when we add animals)
watch(() => props.activeAgents, (newAgents) => {
  console.log('Active agents updated:', newAgents);
  // TODO: Update animal positions and states based on agents
}, { deep: true });

onMounted(() => {
  initScene();
  animate();
});

onUnmounted(() => {
  cleanup();
});
</script>

<style scoped>
.game-world-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: linear-gradient(to bottom, #87ceeb 0%, #e0f6ff 100%);
}

canvas {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
