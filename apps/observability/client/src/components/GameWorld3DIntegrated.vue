<template>
  <div class="game-world-wrapper">
    <div ref="containerRef" class="game-world-container">
      <canvas ref="canvasRef"></canvas>

      <!-- Agent name tags floating above animals -->
      <div
        v-for="agent in activeAgentPositions"
        :key="agent.name"
        class="agent-nametag"
        :style="{
          left: agent.screenX + 'px',
          top: agent.screenY + 'px',
          borderColor: agent.color,
          backgroundColor: agent.color + '20'
        }"
      >
        <span class="agent-emoji">{{ agent.emoji }}</span>
        <span class="agent-name" :style="{ color: agent.color }">{{ agent.name }}</span>
        <span class="agent-activity">{{ agent.activity }}</span>
      </div>
    </div>

    <!-- Game Logs Overlay -->
    <div class="logs-overlay">
      <GameLogs :events="events" :max-visible="8" />
    </div>

    <!-- Debug Info Overlay -->
    <div style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.8); color: white; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 12px; z-index: 1000;">
      <div>Recent Agents: {{ recentActiveAgents.length }}</div>
      <div>Active in Scene: {{ activeAgents.size }}</div>
      <div>Total Events: {{ events.length }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { HookEvent } from '../types';
import { getAgentAnimal, getToolObject, getAnimalColorScheme } from '../config/animalMapping';
import * as AnimalModels from '../utils/animalModels';
import { getToolModel } from '../utils/toolModels';
import { getWalkSpeed, getBobIntensity } from '../utils/animalPersonalities';
import GameLogs from './GameLogs.vue';

interface Props {
  events: HookEvent[];
}

const props = defineProps<Props>();

const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const activeAgentPositions = ref<Array<{
  name: string;
  screenX: number;
  screenY: number;
  color: string;
  emoji: string;
  activity: string;
}>>([]);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let animationFrameId: number;
let workstationPositions: THREE.Vector3[] = [];
let workstationPlatforms: THREE.Mesh[] = [];

// Track active agents and their 3D models
const activeAgents = new Map<string, {
  animal: AnimalModels.AnimalModel;
  tool: THREE.Group | null;
  position: THREE.Vector3;
  targetPosition: THREE.Vector3;
  lastActivity: number;
  isWorking: boolean;
  platform: THREE.Mesh | null;
  progressIndicator: THREE.Group | null;
  particles: THREE.Points | null;
  walkDustParticles: THREE.Points | null;
  toolLight: THREE.PointLight | null;
  currentAnimation: 'idle' | 'typing' | 'hammering' | 'reading' | 'writing' | 'using';
  state: 'spawning' | 'walking' | 'arriving' | 'working' | 'idle';
  walkProgress: number;
  toolType: string;
}>();

const WORKSTATION_COUNT = 16;
const WORKSTATION_RADIUS = 10;
const ACTIVITY_TIMEOUT = 30000; // 5 seconds to consider agent idle
const WORKING_BOB_SPEED = 3.0; // Fast bobbing when working
const IDLE_BOB_SPEED = 0.8; // Slow bobbing when idle
const WORKING_BOB_HEIGHT = 0.15; // Higher bounce when working
const IDLE_BOB_HEIGHT = 0.05; // Subtle movement when idle

// Extract active agents from recent events
const recentActiveAgents = computed(() => {
  const now = Date.now();
  const recentWindow = 300000; // 5 minutes

  const agentMap = new Map<string, {
    tool: string;
    activity: string;
    timestamp: number;
    lastWorkingEvent: number;
    agentType: string;
  }>();

  // Track unique instances per agent type
  const agentTypeCounters = new Map<string, number>();

  // Process events from newest to oldest
  for (let i = props.events.length - 1; i >= 0; i--) {
    const event = props.events[i];
    const timestamp = event.timestamp || now;

    if (now - timestamp > recentWindow) break;

    const agentType = event.payload?.agent_type || event.payload?.subagent_type || 'unknown';
    if (agentType === 'unknown') continue;

    // Create unique agent ID using session_id or agent_id
    const agentId = event.payload?.agent_id || event.session_id || `${agentType}-${i}`;
    const uniqueKey = `${agentType}:${agentId}`;

    if (agentMap.has(uniqueKey)) continue;

    const eventType = event.hook_event_type;

    // Show agents for any event (not just specific working events)
    // This ensures all active agents appear, regardless of what they're doing
    const isWorkingEvent =
      eventType === 'PreToolUse' ||
      eventType === 'PostToolUse' ||
      eventType === 'SubagentStart' ||
      eventType === 'SubagentStop' ||
      eventType === 'SessionStart' ||
      eventType === 'UserPromptSubmit' ||
      eventType === 'Notification';

    // Keep agents visible longer after events
    const effectiveTimestamp = timestamp + 5000; // Visible for 5 seconds after any event

    // Get or create instance number for this agent type
    const instanceNum = agentTypeCounters.get(agentType) || 0;
    agentTypeCounters.set(agentType, instanceNum + 1);

    // Create display name with instance number if needed
    const displayName = instanceNum > 0 ? `${agentType}-${instanceNum + 1}` : agentType;

    const tool = event.payload?.tool_name || event.hook_event_type || 'working';
    const activity = getActivityDescription(event);

    agentMap.set(uniqueKey, {
      tool,
      activity,
      timestamp,
      lastWorkingEvent: isWorkingEvent ? effectiveTimestamp : 0,
      agentType: displayName
    });
  }

  return Array.from(agentMap.entries()).map(([key, data]) => ({
    name: data.agentType,
    tool: data.tool,
    activity: data.activity,
    timestamp: Math.max(data.timestamp, data.lastWorkingEvent),
    uniqueKey: key
  }));
});

function getActivityDescription(event: HookEvent): string {
  const type = event.hook_event_type;
  const tool = event.payload?.tool_name;

  if (type === 'SubagentStart') return '🚀 Starting work...';
  if (type === 'SubagentStop') return '✅ Task complete!';
  if (type === 'PreToolUse' && tool) return `🔧 Using ${tool}`;
  if (type === 'PostToolUse' && tool) return `✨ Finished ${tool}`;
  if (type === 'SessionStart') return '👋 Session started';
  if (type === 'SessionEnd') return '👋 Session ended';
  if (type === 'UserPromptSubmit') return '💭 Thinking...';
  if (type === 'Notification') return '📢 Notification';
  if (type === 'PermissionRequest') return '🔐 Requesting permission';

  return '⚙️ Working...';
}

function getAnimationTypeFromTool(toolName: string): 'idle' | 'typing' | 'hammering' | 'reading' | 'writing' | 'using' {
  const toolLower = toolName.toLowerCase();

  // Bash/terminal tools → typing
  if (toolLower.includes('bash') || toolLower.includes('terminal') || toolLower.includes('shell') || toolLower.includes('command')) {
    return 'typing';
  }

  // Build/hammer tools → hammering
  if (toolLower.includes('build') || toolLower.includes('hammer') || toolLower.includes('compile') || toolLower.includes('make')) {
    return 'hammering';
  }

  // Read tools → reading
  if (toolLower.includes('read') || toolLower.includes('book') || toolLower.includes('view') || toolLower.includes('cat') || toolLower.includes('grep')) {
    return 'reading';
  }

  // Write tools → writing
  if (toolLower.includes('write') || toolLower.includes('edit') || toolLower.includes('pencil') || toolLower.includes('create')) {
    return 'writing';
  }

  // Default → generic tool use
  return 'using';
}

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

  window.addEventListener('resize', handleResize);
}

function createEnvironment() {
  // Ground plane
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

  createTrees();
  createBushes();

  scene.background = new THREE.Color(0x87ceeb);
}

function createTrees() {
  const treePositions = [
    { x: -12, z: -12 }, { x: 12, z: -12 },
    { x: -12, z: 12 }, { x: 12, z: 12 },
    { x: -15, z: 0 }, { x: 15, z: 0 },
    { x: 0, z: -15 }, { x: 0, z: 15 }
  ];

  treePositions.forEach(pos => {
    const tree = createTree();
    tree.position.set(pos.x, 0, pos.z);
    scene.add(tree);
  });
}

function createTree(): THREE.Group {
  const tree = new THREE.Group();

  const trunkGeometry = new THREE.CylinderGeometry(0.3, 0.4, 2.5, 8);
  const trunkMaterial = new THREE.MeshStandardMaterial({ color: 0x4a3520, roughness: 0.9 });
  const trunk = new THREE.Mesh(trunkGeometry, trunkMaterial);
  trunk.position.y = 1.25;
  trunk.castShadow = true;
  tree.add(trunk);

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

  return tree;
}

function createBushes() {
  const bushPositions = [
    { x: -8, z: -6 }, { x: 8, z: -6 },
    { x: -8, z: 6 }, { x: 8, z: 6 }
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
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const hemisphereLight = new THREE.HemisphereLight(0x87ceeb, 0x4a7c3d, 0.4);
  scene.add(hemisphereLight);

  const directionalLight = new THREE.DirectionalLight(0xfff8dc, 0.8);
  directionalLight.position.set(10, 15, 5);
  directionalLight.castShadow = true;
  directionalLight.shadow.camera.left = -20;
  directionalLight.shadow.camera.right = 20;
  directionalLight.shadow.camera.top = 20;
  directionalLight.shadow.camera.bottom = -20;
  directionalLight.shadow.mapSize.width = 2048;
  directionalLight.shadow.mapSize.height = 2048;
  scene.add(directionalLight);
}

function createWorkstations() {
  workstationPositions = [];
  workstationPlatforms = [];

  for (let i = 0; i < WORKSTATION_COUNT; i++) {
    const angle = (i / WORKSTATION_COUNT) * Math.PI * 2;
    const x = Math.cos(angle) * WORKSTATION_RADIUS;
    const z = Math.sin(angle) * WORKSTATION_RADIUS;
    const position = new THREE.Vector3(x, 0, z);
    workstationPositions.push(position);
    const platform = createWorkstationPlatform(position);
    workstationPlatforms.push(platform);
  }
}

function createWorkstationPlatform(position: THREE.Vector3): THREE.Mesh {
  const platformGeometry = new THREE.CylinderGeometry(1.2, 1.2, 0.2, 8);
  const platformMaterial = new THREE.MeshStandardMaterial({
    color: 0x8b7355,
    roughness: 0.7,
    emissive: 0x000000,
    emissiveIntensity: 0
  });
  const platform = new THREE.Mesh(platformGeometry, platformMaterial);
  platform.position.copy(position);
  platform.position.y = 0.1;
  platform.castShadow = true;
  platform.receiveShadow = true;
  scene.add(platform);
  return platform;
}

function createProgressIndicator(): THREE.Group {
  const group = new THREE.Group();

  const ringGeometry = new THREE.TorusGeometry(0.4, 0.05, 8, 16, Math.PI * 1.5);
  const ringMaterial = new THREE.MeshStandardMaterial({
    color: 0x3b82f6,
    emissive: 0x3b82f6,
    emissiveIntensity: 0.5,
    transparent: true,
    opacity: 0.8
  });
  const ring = new THREE.Mesh(ringGeometry, ringMaterial);
  ring.rotation.x = -Math.PI / 2;
  group.add(ring);

  return group;
}

function createParticleSystem(color: number): THREE.Points {
  const particleCount = 20;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const velocities = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 0.5;
    positions[i * 3 + 1] = Math.random() * 0.5;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 0.5;

    velocities[i * 3] = (Math.random() - 0.5) * 0.02;
    velocities[i * 3 + 1] = Math.random() * 0.02 + 0.01;
    velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.02;
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('velocity', new THREE.BufferAttribute(velocities, 3));

  const material = new THREE.PointsMaterial({
    color: color,
    size: 0.08,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true
  });

  return new THREE.Points(geometry, material);
}

function createWalkDustParticles(): THREE.Points {
  const particleCount = 8;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const velocities = new Float32Array(particleCount * 3);
  const lifetimes = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = 0;
    positions[i * 3 + 1] = 0;
    positions[i * 3 + 2] = 0;

    velocities[i * 3] = (Math.random() - 0.5) * 0.05;
    velocities[i * 3 + 1] = Math.random() * 0.02;
    velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.05;

    lifetimes[i] = 0;
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('velocity', new THREE.BufferAttribute(velocities, 3));
  geometry.setAttribute('lifetime', new THREE.BufferAttribute(lifetimes, 1));

  const material = new THREE.PointsMaterial({
    color: 0xD2B48C,
    size: 0.05,
    transparent: true,
    opacity: 0.5,
    sizeAttenuation: true
  });

  return new THREE.Points(geometry, material);
}

function createToolLight(color: number): THREE.PointLight {
  const light = new THREE.PointLight(color, 0, 2);
  light.castShadow = false;
  return light;
}

function updateAgents() {
  console.log('🎯 updateAgents called, recentActiveAgents.value.length:', recentActiveAgents.value.length);

  const currentAgents = new Set<string>();
  const now = Date.now();

  // Track used workstations to avoid overlaps
  const usedWorkstations = new Set<number>();
  for (const data of activeAgents.values()) {
    const stationIndex = workstationPositions.findIndex(pos =>
      pos.distanceTo(data.targetPosition) < 0.1
    );
    if (stationIndex >= 0) usedWorkstations.add(stationIndex);
  }

  recentActiveAgents.value.forEach((agentData, index) => {
    const agentKey = agentData.uniqueKey || agentData.name;
    currentAgents.add(agentKey);

    if (!activeAgents.has(agentKey)) {
      // Add new agent
      const animalConfig = getAgentAnimal(agentData.name);

      if (animalConfig) {
        const animal = createAnimalFromConfig(animalConfig.animal);

        // Find an unused workstation
        let workstationIndex = -1;
        for (let i = 0; i < workstationPositions.length; i++) {
          const tryIndex = (index + i) % workstationPositions.length;
          if (!usedWorkstations.has(tryIndex)) {
            workstationIndex = tryIndex;
            usedWorkstations.add(tryIndex);
            break;
          }
        }

        if (animal && workstationIndex >= 0 && workstationPositions[workstationIndex]) {
          const targetPosition = workstationPositions[workstationIndex].clone();
          targetPosition.y = 1.0;

          // Spawn at center or random edge
          const spawnPosition = new THREE.Vector3();
          if (Math.random() < 0.5) {
            // Spawn at center
            spawnPosition.set(0, 1.0, 0);
          } else {
            // Spawn at random edge
            const angle = Math.random() * Math.PI * 2;
            const radius = 12;
            spawnPosition.set(
              Math.cos(angle) * radius,
              1.0,
              Math.sin(angle) * radius
            );
          }

          animal.position.copy(spawnPosition);

          // Apply animal color
          const colorScheme = getAnimalColorScheme(agentData.name);
          let primaryColor = 0x3b82f6;

          if (colorScheme) {
            animal.traverse((child) => {
              if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
                child.material.color.set(colorScheme.primary);
              }
            });
            primaryColor = new THREE.Color(colorScheme.primary).getHex();
          }

          scene.add(animal);

          // Add tool
          const toolConfig = getToolObject(agentData.tool);
          let toolMesh: THREE.Group | null = null;

          if (toolConfig) {
            const tool = getToolModel(toolConfig.object);
            if (tool) {
              toolMesh = tool;
              toolMesh.scale.set(0.5, 0.5, 0.5);
              animal.holdTool(toolMesh);

              // Make tool material emissive for glow effect
              toolMesh.traverse((child) => {
                if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
                  child.material.emissive = child.material.color.clone();
                  child.material.emissiveIntensity = 0;
                }
              });
            }
          }

          // Create progress indicator
          const progressIndicator = createProgressIndicator();
          progressIndicator.position.copy(targetPosition);
          progressIndicator.position.y = 2.5;
          progressIndicator.visible = false;
          scene.add(progressIndicator);

          // Create particle system
          const particles = createParticleSystem(primaryColor);
          particles.position.copy(targetPosition);
          particles.position.y = 1.0;
          particles.visible = false;
          scene.add(particles);

          // Create walk dust particles
          const walkDustParticles = createWalkDustParticles();
          walkDustParticles.position.copy(spawnPosition);
          walkDustParticles.position.y = 0.1;
          walkDustParticles.visible = false;
          scene.add(walkDustParticles);

          // Create tool light
          const toolLight = createToolLight(primaryColor);
          toolLight.intensity = 0;
          if (toolMesh) {
            toolMesh.add(toolLight);
          }

          // Set base Y position for animations (1.0 so feet touch ground at y=0)
          animal.setBaseY(1.0);

          // Determine initial animation based on tool
          const animationType = getAnimationTypeFromTool(agentData.tool);

          activeAgents.set(agentKey, {
            animal,
            tool: toolMesh,
            position: spawnPosition.clone(),
            targetPosition,
            lastActivity: agentData.timestamp || now,
            isWorking: false,
            platform: workstationPlatforms[workstationIndex],
            progressIndicator,
            particles,
            walkDustParticles,
            toolLight,
            currentAnimation: 'idle',
            state: 'spawning',
            walkProgress: 0,
            toolType: agentData.tool
          });
          console.log('✅ Added agent:', agentData.name);
        }
      }
    } else {
      // Update existing agent activity
      const agentState = activeAgents.get(agentKey)!;
      agentState.lastActivity = agentData.timestamp || now;

      // Update tool type if it changed
      if (agentState.toolType !== agentData.tool) {
        agentState.toolType = agentData.tool;
      }
    }
  });

  // Remove inactive agents
  for (const [name, data] of activeAgents.entries()) {
    if (!currentAgents.has(name)) {
      scene.remove(data.animal);
      if (data.tool) {
        data.animal.remove(data.tool);
      }
      if (data.progressIndicator) {
        scene.remove(data.progressIndicator);
      }
      if (data.particles) {
        scene.remove(data.particles);
      }
      if (data.walkDustParticles) {
        scene.remove(data.walkDustParticles);
      }
      activeAgents.delete(name);
    }
  }

  console.log('📊 Update complete - Active agents:', activeAgents.size, 'Recent agents:', recentActiveAgents.value.length);
}

function createAnimalFromConfig(animalType: string): AnimalModels.AnimalModel | null {
  // Fallback mapping for animals we don't have models for yet
  const fallbackMap: Record<string, string> = {
    phoenix: 'dragon',
    raccoon: 'cat',
    dog: 'bear',
    wolf: 'bear',
    otter: 'beaver',
    panda: 'bear',
    parrot: 'bird',
    peacock: 'bird',
    elephant: 'bear',
    dolphin: 'turtle',
    lemur: 'cat',
    hamster: 'rabbit',
    meerkat: 'squirrel',
    mouse: 'rabbit',
    bird: 'penguin',
    bee: 'rabbit',
    chipmunk: 'squirrel',
    sparrow: 'penguin',
    hummingbird: 'penguin',
    gecko: 'turtle',
    ant: 'rabbit',
    ladybug: 'rabbit',
    butterfly: 'rabbit',
    snail: 'turtle'
  };

  // Use fallback if animal doesn't exist
  const actualType = fallbackMap[animalType] || animalType;

  const creators: Record<string, () => AnimalModels.AnimalModel> = {
    owl: AnimalModels.createOwl,
    beaver: AnimalModels.createBeaver,
    rabbit: AnimalModels.createRabbit,
    dragon: AnimalModels.createDragon,
    fox: AnimalModels.createFox,
    penguin: AnimalModels.createPenguin,
    bear: AnimalModels.createBear,
    cat: AnimalModels.createCat,
    pig: AnimalModels.createPig,
    turtle: AnimalModels.createTurtle,
    squirrel: AnimalModels.createSquirrel,
    koala: AnimalModels.createKoala
  };

  const creator = creators[actualType.toLowerCase()];
  return creator ? creator() : creators['beaver'](); // Ultimate fallback to beaver
}

function updateNametagPositions() {
  if (!camera || !renderer) return;

  const positions: typeof activeAgentPositions.value = [];

  for (const [name, data] of activeAgents.entries()) {
    const vector = data.position.clone();
    vector.y += 3;
    vector.project(camera);

    const x = (vector.x * 0.5 + 0.5) * containerRef.value!.clientWidth;
    const y = (-vector.y * 0.5 + 0.5) * containerRef.value!.clientHeight;

    const animalConfig = getAgentAnimal(name);
    const colorScheme = getAnimalColorScheme(name);
    const agentData = recentActiveAgents.value.find(a => a.name === name);

    if (animalConfig) {
      positions.push({
        name,
        screenX: x,
        screenY: y - 40,
        color: colorScheme?.primary || '#3b82f6',
        emoji: animalConfig.emoji,
        activity: agentData?.activity || 'working...'
      });
    }
  }

  activeAgentPositions.value = positions;
}

function updateWorkingStates() {
  const now = Date.now();

  for (const [name, data] of activeAgents.entries()) {
    // Only update work states if agent has arrived at workstation
    if (data.state !== 'idle' && data.state !== 'working') {
      continue;
    }

    const timeSinceActivity = now - data.lastActivity;
    const shouldBeWorking = timeSinceActivity < ACTIVITY_TIMEOUT;

    // Determine target animation
    const targetAnimation = shouldBeWorking
      ? getAnimationTypeFromTool(data.toolType)
      : 'idle';

    // Update animation state if changed
    if (data.currentAnimation !== targetAnimation) {
      data.currentAnimation = targetAnimation;
      data.animal.resetRotation();
    }

    // State transition
    if (shouldBeWorking !== data.isWorking) {
      data.isWorking = shouldBeWorking;
      data.state = shouldBeWorking ? 'working' : 'idle';

      // Update visual effects
      if (data.progressIndicator) {
        data.progressIndicator.visible = shouldBeWorking;
      }
      if (data.particles) {
        data.particles.visible = shouldBeWorking;
      }

      // Update platform glow
      if (data.platform && data.platform.material instanceof THREE.MeshStandardMaterial) {
        if (shouldBeWorking) {
          const colorScheme = getAnimalColorScheme(name);
          if (colorScheme) {
            data.platform.material.emissive.set(colorScheme.primary);
            data.platform.material.emissiveIntensity = 0.3;
          }
        } else {
          data.platform.material.emissive.set(0x000000);
          data.platform.material.emissiveIntensity = 0;
        }
      }

      // Update tool glow and light
      if (data.tool) {
        data.tool.traverse((child) => {
          if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
            child.material.emissiveIntensity = shouldBeWorking ? 0.6 : 0;
          }
        });

        if (data.toolLight) {
          data.toolLight.intensity = shouldBeWorking ? 1.5 : 0;
        }
      }
    }
  }
}

function animateParticles(delta: number) {
  for (const data of activeAgents.values()) {
    if (data.particles && data.particles.visible) {
      const positions = data.particles.geometry.attributes.position;
      const velocities = data.particles.geometry.attributes.velocity;

      for (let i = 0; i < positions.count; i++) {
        // Update position
        positions.array[i * 3] += velocities.array[i * 3];
        positions.array[i * 3 + 1] += velocities.array[i * 3 + 1];
        positions.array[i * 3 + 2] += velocities.array[i * 3 + 2];

        // Reset particles that go too high
        if (positions.array[i * 3 + 1] > 1.5) {
          positions.array[i * 3] = (Math.random() - 0.5) * 0.5;
          positions.array[i * 3 + 1] = 0;
          positions.array[i * 3 + 2] = (Math.random() - 0.5) * 0.5;
        }
      }

      positions.needsUpdate = true;
    }

    // Animate walk dust particles
    if (data.walkDustParticles && data.walkDustParticles.visible) {
      const positions = data.walkDustParticles.geometry.attributes.position;
      const velocities = data.walkDustParticles.geometry.attributes.velocity;
      const lifetimes = data.walkDustParticles.geometry.attributes.lifetime;

      for (let i = 0; i < positions.count; i++) {
        lifetimes.array[i] += delta;

        if (lifetimes.array[i] < 0.5) {
          // Update position
          positions.array[i * 3] += velocities.array[i * 3];
          positions.array[i * 3 + 1] += velocities.array[i * 3 + 1];
          positions.array[i * 3 + 2] += velocities.array[i * 3 + 2];
        } else {
          // Reset particle at character feet
          positions.array[i * 3] = (Math.random() - 0.5) * 0.2;
          positions.array[i * 3 + 1] = 0;
          positions.array[i * 3 + 2] = (Math.random() - 0.5) * 0.2;
          lifetimes.array[i] = 0;

          // Randomize velocity
          velocities.array[i * 3] = (Math.random() - 0.5) * 0.05;
          velocities.array[i * 3 + 1] = Math.random() * 0.02;
          velocities.array[i * 3 + 2] = (Math.random() - 0.5) * 0.05;
        }
      }

      positions.needsUpdate = true;
      lifetimes.needsUpdate = true;
    }
  }
}

function updateWalkingAgents(delta: number) {
  for (const [name, data] of activeAgents.entries()) {
    // Different speeds and styles per animal type
    const animalConfig = getAgentAnimal(name);
    const baseSpeed = animalConfig ? getWalkSpeed(animalConfig.animal) : 2.0;
    if (data.state === 'spawning') {
      // Transition to walking
      data.state = 'walking';
      data.walkProgress = 0;
      if (data.walkDustParticles) {
        data.walkDustParticles.visible = true;
      }
    } else if (data.state === 'walking') {
      // Calculate distance to target
      const direction = new THREE.Vector3().subVectors(data.targetPosition, data.position);
      const distance = direction.length();

      if (distance > 0.1) {
        // Still walking
        data.walkProgress = Math.min(1, data.walkProgress + (baseSpeed * delta) / distance);

        // Interpolate position
        data.position.lerpVectors(
          data.position,
          data.targetPosition,
          baseSpeed * delta / distance
        );

        // Update animal position
        data.animal.position.copy(data.position);

        // Rotate to face direction of movement
        if (direction.length() > 0.01) {
          const targetRotation = Math.atan2(direction.x, direction.z);
          // Smooth rotation
          const currentRotation = data.animal.rotation.y;
          const rotationDiff = targetRotation - currentRotation;
          // Normalize angle difference to -PI to PI
          const normalizedDiff = Math.atan2(Math.sin(rotationDiff), Math.cos(rotationDiff));
          data.animal.rotation.y += normalizedDiff * delta * 5;
        }

        // Animate walking
        data.animal.walkMotion(delta);

        // Update walk dust particles position
        if (data.walkDustParticles) {
          data.walkDustParticles.position.copy(data.position);
          data.walkDustParticles.position.y = 0.1;
        }
      } else {
        // Arrived at workstation
        data.state = 'arriving';
        data.position.copy(data.targetPosition);
        data.animal.position.copy(data.targetPosition);
        if (data.walkDustParticles) {
          data.walkDustParticles.visible = false;
        }

        // Brief arrival animation (small hop)
        const hopTime = 0.15;
        const startY = data.position.y;
        const hopHeight = 0.2;
        let hopProgress = 0;

        const hopInterval = setInterval(() => {
          hopProgress += 0.016;
          if (hopProgress >= 1) {
            clearInterval(hopInterval);
            data.animal.position.y = startY;
            data.state = 'idle';
          } else {
            const hopY = startY + Math.sin(hopProgress * Math.PI) * hopHeight;
            data.animal.position.y = hopY;
          }
        }, 16);
      }
    }
  }
}

let lastTime = 0;
function animate(time: number) {
  animationFrameId = requestAnimationFrame(animate);

  const delta = (time - lastTime) / 1000;
  lastTime = time;

  controls.update();
  updateWalkingAgents(delta);
  updateWorkingStates();
  animateParticles(delta);

  // Animate all animals with character-specific animations
  for (const data of activeAgents.values()) {
    // Only play work animations if not walking
    if (data.state !== 'walking' && data.state !== 'spawning') {
      // Call the appropriate animation based on current state
      switch (data.currentAnimation) {
        case 'idle':
          data.animal.standIdle(time);
          break;
        case 'typing':
          data.animal.typeMotion(time);
          break;
        case 'hammering':
          data.animal.hammerMotion(time);
          break;
        case 'reading':
          data.animal.readMotion(time);
          break;
        case 'writing':
          data.animal.writeMotion(time);
          break;
        case 'using':
          data.animal.useToolWithHands(time);
          break;
      }

      // Additional tool rotation effect when working (for extra visual flair)
      if (data.tool && data.isWorking && data.currentAnimation !== 'reading') {
        data.tool.rotation.y += delta * 2;
      }
    }
  }

  // Rotate progress indicators
  for (const data of activeAgents.values()) {
    if (data.progressIndicator && data.progressIndicator.visible) {
      data.progressIndicator.rotation.z += delta * 2;
    }
  }

  renderer.render(scene, camera);
  updateNametagPositions();
}

function handleResize() {
  if (!containerRef.value) return;

  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
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

  scene?.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry?.dispose();
      if (object.material instanceof THREE.Material) {
        object.material.dispose();
      }
    }
  });
}

// Throttle updateAgents to prevent excessive calls
let updateAgentsTimeout: number | null = null;
watch(recentActiveAgents, (newAgents) => {
  if (updateAgentsTimeout) return; // Skip if already scheduled

  console.log('🔍 Recent active agents:', newAgents.length, 'agents');

  updateAgentsTimeout = window.setTimeout(() => {
    updateAgents();
    updateAgentsTimeout = null;
  }, 100); // Throttle to max 10 updates per second
}, { deep: true });

onMounted(() => {
  console.log('🎮 GameWorld3D Component Mounted!');
  alert('3D Component Loaded - Check if agents appear!');
  initScene();
  lastTime = performance.now();
  animate(lastTime);
  updateAgents();
});

onUnmounted(() => {
  cleanup();
});
</script>

<style scoped>
.game-world-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

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

.agent-nametag {
  position: absolute;
  transform: translate(-50%, -100%);
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid;
  border-radius: 12px;
  padding: 6px 12px;
  pointer-events: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: 12px;
  font-weight: 600;
  animation: float 2s ease-in-out infinite;
  transition: all 0.3s ease;
}

.agent-nametag:hover {
  transform: translate(-50%, -100%) scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.agent-emoji {
  font-size: 16px;
}

.agent-name {
  font-weight: 700;
}

.agent-activity {
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
}

.logs-overlay {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 400px;
  max-height: 500px;
  pointer-events: auto;
  z-index: 10;
}

@keyframes float {
  0%, 100% { transform: translate(-50%, -100%) translateY(0); }
  50% { transform: translate(-50%, -100%) translateY(-8px); }
}

@media (max-width: 768px) {
  .logs-overlay {
    width: calc(100% - 40px);
    max-height: 300px;
    bottom: 10px;
    right: 20px;
    left: 20px;
  }
}
</style>
