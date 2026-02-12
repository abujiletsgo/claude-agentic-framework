import * as THREE from 'three';

/**
 * Creates a cute hammer for build tasks
 */
export function createHammer(): THREE.Group {
  const hammer = new THREE.Group();

  // Handle
  const handleGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.8, 8);
  const handleMaterial = new THREE.MeshStandardMaterial({ color: 0x8B4513 });
  const handle = new THREE.Mesh(handleGeometry, handleMaterial);
  handle.position.y = -0.2;

  // Head
  const headGeometry = new THREE.BoxGeometry(0.3, 0.15, 0.15);
  const headMaterial = new THREE.MeshStandardMaterial({ color: 0x888888 });
  const head = new THREE.Mesh(headGeometry, headMaterial);
  head.position.y = 0.3;

  // Claw (back of hammer)
  const clawGeometry = new THREE.BoxGeometry(0.1, 0.15, 0.15);
  const claw = new THREE.Mesh(clawGeometry, headMaterial);
  claw.position.set(-0.15, 0.3, 0);

  hammer.add(handle, head, claw);
  return hammer;
}

/**
 * Creates a magnifying glass for code-review
 */
export function createMagnifyingGlass(): THREE.Group {
  const magnifier = new THREE.Group();

  // Handle
  const handleGeometry = new THREE.CylinderGeometry(0.04, 0.04, 0.5, 8);
  const handleMaterial = new THREE.MeshStandardMaterial({ color: 0x654321 });
  const handle = new THREE.Mesh(handleGeometry, handleMaterial);
  handle.position.y = -0.4;
  handle.rotation.z = Math.PI / 6;

  // Rim
  const rimGeometry = new THREE.TorusGeometry(0.25, 0.03, 16, 32);
  const rimMaterial = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 });
  const rim = new THREE.Mesh(rimGeometry, rimMaterial);
  rim.position.y = 0.1;
  rim.rotation.x = Math.PI / 2;

  // Lens
  const lensGeometry = new THREE.CircleGeometry(0.25, 32);
  const lensMaterial = new THREE.MeshStandardMaterial({
    color: 0x87CEEB,
    transparent: true,
    opacity: 0.3,
    side: THREE.DoubleSide
  });
  const lens = new THREE.Mesh(lensGeometry, lensMaterial);
  lens.position.y = 0.1;

  magnifier.add(handle, rim, lens);
  return magnifier;
}

/**
 * Creates a book for Read tool
 */
export function createBook(): THREE.Group {
  const book = new THREE.Group();

  // Cover
  const coverGeometry = new THREE.BoxGeometry(0.4, 0.5, 0.05);
  const coverMaterial = new THREE.MeshStandardMaterial({ color: 0x8B0000 });
  const cover = new THREE.Mesh(coverGeometry, coverMaterial);

  // Pages
  const pagesGeometry = new THREE.BoxGeometry(0.38, 0.48, 0.04);
  const pagesMaterial = new THREE.MeshStandardMaterial({ color: 0xFFFACD });
  const pages = new THREE.Mesh(pagesGeometry, pagesMaterial);
  pages.position.z = 0.01;

  // Bookmark
  const bookmarkGeometry = new THREE.BoxGeometry(0.05, 0.3, 0.01);
  const bookmarkMaterial = new THREE.MeshStandardMaterial({ color: 0xFF6347 });
  const bookmark = new THREE.Mesh(bookmarkGeometry, bookmarkMaterial);
  bookmark.position.set(0.1, 0.15, 0.03);

  book.add(cover, pages, bookmark);
  book.rotation.y = Math.PI / 8;
  return book;
}

/**
 * Creates a pencil for Write/Edit
 */
export function createPencil(): THREE.Group {
  const pencil = new THREE.Group();

  // Body
  const bodyGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.8, 6);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xFFD700 });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
  body.rotation.z = Math.PI / 2;

  // Tip (wood part)
  const tipGeometry = new THREE.ConeGeometry(0.05, 0.15, 6);
  const tipMaterial = new THREE.MeshStandardMaterial({ color: 0xD2691E });
  const tip = new THREE.Mesh(tipGeometry, tipMaterial);
  tip.position.x = 0.475;
  tip.rotation.z = -Math.PI / 2;

  // Lead
  const leadGeometry = new THREE.ConeGeometry(0.02, 0.08, 6);
  const leadMaterial = new THREE.MeshStandardMaterial({ color: 0x333333 });
  const lead = new THREE.Mesh(leadGeometry, leadMaterial);
  lead.position.x = 0.52;
  lead.rotation.z = -Math.PI / 2;

  // Eraser
  const eraserGeometry = new THREE.CylinderGeometry(0.06, 0.06, 0.1, 8);
  const eraserMaterial = new THREE.MeshStandardMaterial({ color: 0xFFB6C1 });
  const eraser = new THREE.Mesh(eraserGeometry, eraserMaterial);
  eraser.position.x = -0.45;
  eraser.rotation.z = Math.PI / 2;

  pencil.add(body, tip, lead, eraser);
  return pencil;
}

/**
 * Creates a terminal window for Bash
 */
export function createTerminal(): THREE.Group {
  const terminal = new THREE.Group();

  // Screen
  const screenGeometry = new THREE.BoxGeometry(0.6, 0.4, 0.05);
  const screenMaterial = new THREE.MeshStandardMaterial({ color: 0x1E1E1E });
  const screen = new THREE.Mesh(screenGeometry, screenMaterial);

  // Frame
  const frameGeometry = new THREE.BoxGeometry(0.65, 0.45, 0.03);
  const frameMaterial = new THREE.MeshStandardMaterial({ color: 0x505050 });
  const frame = new THREE.Mesh(frameGeometry, frameMaterial);
  frame.position.z = -0.04;

  // Prompt indicator (green cursor)
  const cursorGeometry = new THREE.BoxGeometry(0.08, 0.08, 0.02);
  const cursorMaterial = new THREE.MeshStandardMaterial({ color: 0x00FF00 });
  const cursor = new THREE.Mesh(cursorGeometry, cursorMaterial);
  cursor.position.set(-0.15, -0.05, 0.03);

  // Text lines simulation
  for (let i = 0; i < 3; i++) {
    const lineGeometry = new THREE.BoxGeometry(0.4, 0.03, 0.01);
    const lineMaterial = new THREE.MeshStandardMaterial({ color: 0x00FF00 });
    const line = new THREE.Mesh(lineGeometry, lineMaterial);
    line.position.set(-0.05, 0.15 - i * 0.1, 0.03);
    terminal.add(line);
  }

  terminal.add(frame, screen, cursor);
  return terminal;
}

/**
 * Creates a flask for tests
 */
export function createFlask(): THREE.Group {
  const flask = new THREE.Group();

  // Bottom (round)
  const bottomGeometry = new THREE.SphereGeometry(0.2, 16, 16);
  const glassMaterial = new THREE.MeshStandardMaterial({
    color: 0xADD8E6,
    transparent: true,
    opacity: 0.6
  });
  const bottom = new THREE.Mesh(bottomGeometry, glassMaterial);
  bottom.position.y = -0.2;
  bottom.scale.y = 0.8;

  // Neck
  const neckGeometry = new THREE.CylinderGeometry(0.08, 0.15, 0.3, 16);
  const neck = new THREE.Mesh(neckGeometry, glassMaterial);
  neck.position.y = 0.05;

  // Opening
  const openingGeometry = new THREE.CylinderGeometry(0.1, 0.08, 0.05, 16);
  const opening = new THREE.Mesh(openingGeometry, glassMaterial);
  opening.position.y = 0.225;

  // Liquid
  const liquidGeometry = new THREE.SphereGeometry(0.18, 16, 16);
  const liquidMaterial = new THREE.MeshStandardMaterial({
    color: 0x00FF7F,
    transparent: true,
    opacity: 0.7
  });
  const liquid = new THREE.Mesh(liquidGeometry, liquidMaterial);
  liquid.position.y = -0.2;
  liquid.scale.y = 0.7;

  flask.add(bottom, neck, opening, liquid);
  return flask;
}

/**
 * Creates a telescope for research
 */
export function createTelescope(): THREE.Group {
  const telescope = new THREE.Group();

  // Main tube
  const tubeGeometry = new THREE.CylinderGeometry(0.08, 0.12, 0.8, 16);
  const tubeMaterial = new THREE.MeshStandardMaterial({ color: 0x2F4F4F });
  const tube = new THREE.Mesh(tubeGeometry, tubeMaterial);
  tube.rotation.z = Math.PI / 4;

  // Lens end
  const lensGeometry = new THREE.CylinderGeometry(0.13, 0.13, 0.05, 16);
  const lensMaterial = new THREE.MeshStandardMaterial({ color: 0x4682B4 });
  const lens = new THREE.Mesh(lensGeometry, lensMaterial);
  lens.position.set(-0.56, -0.56, 0);
  lens.rotation.z = Math.PI / 4;

  // Eyepiece
  const eyepieceGeometry = new THREE.CylinderGeometry(0.06, 0.06, 0.1, 16);
  const eyepiece = new THREE.Mesh(eyepieceGeometry, tubeMaterial);
  eyepiece.position.set(0.56, 0.56, 0);
  eyepiece.rotation.z = Math.PI / 4;

  // Decorative ring
  const ringGeometry = new THREE.TorusGeometry(0.1, 0.02, 8, 16);
  const ringMaterial = new THREE.MeshStandardMaterial({ color: 0xDAA520 });
  const ring = new THREE.Mesh(ringGeometry, ringMaterial);
  ring.rotation.y = Math.PI / 2;
  ring.rotation.z = Math.PI / 4;

  telescope.add(tube, lens, eyepiece, ring);
  return telescope;
}

/**
 * Creates a wrench for debugging
 */
export function createWrench(): THREE.Group {
  const wrench = new THREE.Group();

  // Handle
  const handleGeometry = new THREE.BoxGeometry(0.08, 0.6, 0.05);
  const handleMaterial = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 });
  const handle = new THREE.Mesh(handleGeometry, handleMaterial);
  handle.position.y = -0.2;

  // Head
  const headGeometry = new THREE.TorusGeometry(0.12, 0.04, 8, 16, Math.PI);
  const head = new THREE.Mesh(headGeometry, handleMaterial);
  head.position.y = 0.2;
  head.rotation.z = -Math.PI / 2;

  // Jaw
  const jawGeometry = new THREE.BoxGeometry(0.06, 0.15, 0.05);
  const jaw = new THREE.Mesh(jawGeometry, handleMaterial);
  jaw.position.set(0.1, 0.2, 0);

  wrench.add(handle, head, jaw);
  return wrench;
}

/**
 * Creates a lightbulb for ideas/planning
 */
export function createLightbulb(): THREE.Group {
  const bulb = new THREE.Group();

  // Glass bulb
  const bulbGeometry = new THREE.SphereGeometry(0.2, 16, 16);
  const bulbMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFFFE0,
    transparent: true,
    opacity: 0.7,
    emissive: 0xFFFF00,
    emissiveIntensity: 0.3
  });
  const glass = new THREE.Mesh(bulbGeometry, bulbMaterial);
  glass.position.y = 0.1;
  glass.scale.y = 1.2;

  // Base threads
  const baseGeometry = new THREE.CylinderGeometry(0.12, 0.12, 0.15, 16);
  const baseMaterial = new THREE.MeshStandardMaterial({ color: 0xA9A9A9 });
  const base = new THREE.Mesh(baseGeometry, baseMaterial);
  base.position.y = -0.15;

  // Filament
  const filamentGeometry = new THREE.TorusGeometry(0.08, 0.01, 8, 16);
  const filamentMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFA500,
    emissive: 0xFF6600,
    emissiveIntensity: 0.5
  });
  const filament = new THREE.Mesh(filamentGeometry, filamentMaterial);
  filament.position.y = 0.08;
  filament.rotation.x = Math.PI / 2;

  bulb.add(glass, base, filament);
  return bulb;
}

/**
 * Creates a compass for navigation
 */
export function createCompass(): THREE.Group {
  const compass = new THREE.Group();

  // Base
  const baseGeometry = new THREE.CylinderGeometry(0.25, 0.25, 0.05, 32);
  const baseMaterial = new THREE.MeshStandardMaterial({ color: 0xCD7F32 });
  const base = new THREE.Mesh(baseGeometry, baseMaterial);

  // Face
  const faceGeometry = new THREE.CircleGeometry(0.23, 32);
  const faceMaterial = new THREE.MeshStandardMaterial({ color: 0xFFFFF0 });
  const face = new THREE.Mesh(faceGeometry, faceMaterial);
  face.position.y = 0.026;
  face.rotation.x = -Math.PI / 2;

  // Needle (red)
  const needleGeometry = new THREE.ConeGeometry(0.03, 0.2, 8);
  const needleMaterial = new THREE.MeshStandardMaterial({ color: 0xFF0000 });
  const needle = new THREE.Mesh(needleGeometry, needleMaterial);
  needle.position.y = 0.06;
  needle.rotation.x = Math.PI / 2;
  needle.rotation.y = Math.PI / 4;

  // Needle (white)
  const needleMaterial2 = new THREE.MeshStandardMaterial({ color: 0xFFFFFF });
  const needle2 = new THREE.Mesh(needleGeometry, needleMaterial2);
  needle2.position.y = 0.06;
  needle2.rotation.x = -Math.PI / 2;
  needle2.rotation.y = Math.PI / 4;

  compass.add(base, face, needle, needle2);
  return compass;
}

/**
 * Creates a gear for processing/work
 */
export function createGear(): THREE.Group {
  const gear = new THREE.Group();

  // Center disc
  const centerGeometry = new THREE.CylinderGeometry(0.15, 0.15, 0.08, 32);
  const centerMaterial = new THREE.MeshStandardMaterial({ color: 0x708090 });
  const center = new THREE.Mesh(centerGeometry, centerMaterial);
  center.rotation.x = Math.PI / 2;

  // Teeth
  const toothGeometry = new THREE.BoxGeometry(0.06, 0.08, 0.12);
  const toothMaterial = new THREE.MeshStandardMaterial({ color: 0x708090 });

  for (let i = 0; i < 8; i++) {
    const tooth = new THREE.Mesh(toothGeometry, toothMaterial);
    const angle = (i / 8) * Math.PI * 2;
    tooth.position.x = Math.cos(angle) * 0.2;
    tooth.position.z = Math.sin(angle) * 0.2;
    tooth.rotation.y = angle;
    gear.add(tooth);
  }

  // Center hole
  const holeGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.1, 16);
  const holeMaterial = new THREE.MeshStandardMaterial({ color: 0x404040 });
  const hole = new THREE.Mesh(holeGeometry, holeMaterial);
  hole.rotation.x = Math.PI / 2;

  gear.add(center, hole);
  return gear;
}

/**
 * Creates a rocket for deployment
 */
export function createRocket(): THREE.Group {
  const rocket = new THREE.Group();

  // Body
  const bodyGeometry = new THREE.CylinderGeometry(0.12, 0.12, 0.6, 16);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xDC143C });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
  body.position.y = 0.1;

  // Nose cone
  const noseGeometry = new THREE.ConeGeometry(0.12, 0.25, 16);
  const noseMaterial = new THREE.MeshStandardMaterial({ color: 0xFFFFFF });
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.y = 0.525;

  // Fins
  const finGeometry = new THREE.BoxGeometry(0.05, 0.2, 0.15);
  const finMaterial = new THREE.MeshStandardMaterial({ color: 0x4169E1 });

  for (let i = 0; i < 3; i++) {
    const fin = new THREE.Mesh(finGeometry, finMaterial);
    const angle = (i / 3) * Math.PI * 2;
    fin.position.x = Math.cos(angle) * 0.12;
    fin.position.z = Math.sin(angle) * 0.12;
    fin.position.y = -0.15;
    fin.rotation.y = angle;
    rocket.add(fin);
  }

  // Window
  const windowGeometry = new THREE.CircleGeometry(0.06, 16);
  const windowMaterial = new THREE.MeshStandardMaterial({ color: 0x87CEEB });
  const window1 = new THREE.Mesh(windowGeometry, windowMaterial);
  window1.position.set(0.121, 0.2, 0);
  window1.rotation.y = Math.PI / 2;

  rocket.add(body, nose, window1);
  return rocket;
}

/**
 * Creates a shield for security/protection
 */
export function createShield(): THREE.Group {
  const shield = new THREE.Group();

  // Main shield body
  const shieldGeometry = new THREE.BoxGeometry(0.4, 0.5, 0.05);
  const shieldMaterial = new THREE.MeshStandardMaterial({ color: 0x4169E1 });
  const main = new THREE.Mesh(shieldGeometry, shieldMaterial);

  // Shield point (bottom)
  const pointGeometry = new THREE.ConeGeometry(0.2, 0.15, 4);
  const point = new THREE.Mesh(pointGeometry, shieldMaterial);
  point.position.y = -0.325;
  point.rotation.z = Math.PI / 4;

  // Emblem (cross)
  const emblemGeometry1 = new THREE.BoxGeometry(0.08, 0.3, 0.02);
  const emblemMaterial = new THREE.MeshStandardMaterial({ color: 0xFFD700 });
  const emblem1 = new THREE.Mesh(emblemGeometry1, emblemMaterial);
  emblem1.position.z = 0.04;

  const emblemGeometry2 = new THREE.BoxGeometry(0.2, 0.08, 0.02);
  const emblem2 = new THREE.Mesh(emblemGeometry2, emblemMaterial);
  emblem2.position.z = 0.04;

  shield.add(main, point, emblem1, emblem2);
  return shield;
}

/**
 * Creates a puzzle piece for integration
 */
export function createPuzzlePiece(): THREE.Group {
  const puzzle = new THREE.Group();

  // Main body
  const bodyGeometry = new THREE.BoxGeometry(0.3, 0.3, 0.08);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x9370DB });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);

  // Tab (top)
  const tabGeometry = new THREE.CylinderGeometry(0.06, 0.06, 0.08, 16);
  const tab = new THREE.Mesh(tabGeometry, bodyMaterial);
  tab.position.y = 0.18;
  tab.rotation.x = Math.PI / 2;

  // Tab (right)
  const tab2 = new THREE.Mesh(tabGeometry, bodyMaterial);
  tab2.position.x = 0.18;
  tab2.rotation.z = Math.PI / 2;

  puzzle.add(body, tab, tab2);
  return puzzle;
}

/**
 * Creates a target for goals/objectives
 */
export function createTarget(): THREE.Group {
  const target = new THREE.Group();

  // Outer ring
  const ring1Geometry = new THREE.TorusGeometry(0.25, 0.05, 16, 32);
  const ring1Material = new THREE.MeshStandardMaterial({ color: 0xFF0000 });
  const ring1 = new THREE.Mesh(ring1Geometry, ring1Material);
  ring1.rotation.x = Math.PI / 2;

  // Middle ring
  const ring2Geometry = new THREE.TorusGeometry(0.18, 0.04, 16, 32);
  const ring2Material = new THREE.MeshStandardMaterial({ color: 0xFFFFFF });
  const ring2 = new THREE.Mesh(ring2Geometry, ring2Material);
  ring2.rotation.x = Math.PI / 2;

  // Inner ring
  const ring3Geometry = new THREE.TorusGeometry(0.11, 0.03, 16, 32);
  const ring3 = new THREE.Mesh(ring3Geometry, ring1Material);
  ring3.rotation.x = Math.PI / 2;

  // Center
  const centerGeometry = new THREE.CircleGeometry(0.08, 32);
  const centerMaterial = new THREE.MeshStandardMaterial({ color: 0xFF0000 });
  const center = new THREE.Mesh(centerGeometry, centerMaterial);
  center.rotation.x = -Math.PI / 2;

  target.add(ring1, ring2, ring3, center);
  return target;
}

/**
 * Creates a clipboard for tasks/todos
 */
export function createClipboard(): THREE.Group {
  const clipboard = new THREE.Group();

  // Board
  const boardGeometry = new THREE.BoxGeometry(0.35, 0.5, 0.03);
  const boardMaterial = new THREE.MeshStandardMaterial({ color: 0x8B4513 });
  const board = new THREE.Mesh(boardGeometry, boardMaterial);

  // Paper
  const paperGeometry = new THREE.BoxGeometry(0.3, 0.42, 0.01);
  const paperMaterial = new THREE.MeshStandardMaterial({ color: 0xFFFFF0 });
  const paper = new THREE.Mesh(paperGeometry, paperMaterial);
  paper.position.set(0, -0.02, 0.02);

  // Clip
  const clipGeometry = new THREE.BoxGeometry(0.12, 0.06, 0.04);
  const clipMaterial = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 });
  const clip = new THREE.Mesh(clipGeometry, clipMaterial);
  clip.position.set(0, 0.27, 0.035);

  // Checkmarks
  for (let i = 0; i < 3; i++) {
    const checkGeometry = new THREE.BoxGeometry(0.04, 0.04, 0.01);
    const checkMaterial = new THREE.MeshStandardMaterial({ color: 0x32CD32 });
    const check = new THREE.Mesh(checkGeometry, checkMaterial);
    check.position.set(-0.1, 0.1 - i * 0.12, 0.025);
    clipboard.add(check);
  }

  clipboard.add(board, paper, clip);
  return clipboard;
}

/**
 * Creates binoculars for observation/monitoring
 */
export function createBinoculars(): THREE.Group {
  const binoculars = new THREE.Group();

  // Left barrel
  const barrelGeometry = new THREE.CylinderGeometry(0.1, 0.1, 0.3, 16);
  const barrelMaterial = new THREE.MeshStandardMaterial({ color: 0x2F4F4F });
  const leftBarrel = new THREE.Mesh(barrelGeometry, barrelMaterial);
  leftBarrel.position.set(-0.12, 0, 0);
  leftBarrel.rotation.x = Math.PI / 2;

  // Right barrel
  const rightBarrel = new THREE.Mesh(barrelGeometry, barrelMaterial);
  rightBarrel.position.set(0.12, 0, 0);
  rightBarrel.rotation.x = Math.PI / 2;

  // Bridge
  const bridgeGeometry = new THREE.BoxGeometry(0.24, 0.08, 0.08);
  const bridge = new THREE.Mesh(bridgeGeometry, barrelMaterial);
  bridge.position.z = -0.05;

  // Left lens
  const lensGeometry = new THREE.CircleGeometry(0.1, 32);
  const lensMaterial = new THREE.MeshStandardMaterial({ color: 0x4682B4 });
  const leftLens = new THREE.Mesh(lensGeometry, lensMaterial);
  leftLens.position.set(-0.12, 0, 0.15);

  // Right lens
  const rightLens = new THREE.Mesh(lensGeometry, lensMaterial);
  rightLens.position.set(0.12, 0, 0.15);

  binoculars.add(leftBarrel, rightBarrel, bridge, leftLens, rightLens);
  return binoculars;
}

/**
 * Map of tool names to their creation functions
 */
export const toolModels: Record<string, () => THREE.Group> = {
  hammer: createHammer,
  magnifyingGlass: createMagnifyingGlass,
  book: createBook,
  pencil: createPencil,
  terminal: createTerminal,
  flask: createFlask,
  telescope: createTelescope,
  wrench: createWrench,
  lightbulb: createLightbulb,
  compass: createCompass,
  gear: createGear,
  rocket: createRocket,
  shield: createShield,
  puzzlePiece: createPuzzlePiece,
  target: createTarget,
  clipboard: createClipboard,
  binoculars: createBinoculars,
};

/**
 * Get a tool model by name, with fallback to a default
 */
export function getToolModel(toolName: string): THREE.Group {
  const normalizedName = toolName.toLowerCase().replace(/[^a-z]/g, '');

  // Direct match
  if (toolModels[normalizedName]) {
    return toolModels[normalizedName]();
  }

  // Fuzzy matching for common tool types
  if (normalizedName.includes('build') || normalizedName.includes('compile')) {
    return createHammer();
  }
  if (normalizedName.includes('review') || normalizedName.includes('inspect')) {
    return createMagnifyingGlass();
  }
  if (normalizedName.includes('read') || normalizedName.includes('view')) {
    return createBook();
  }
  if (normalizedName.includes('write') || normalizedName.includes('edit')) {
    return createPencil();
  }
  if (normalizedName.includes('bash') || normalizedName.includes('command') || normalizedName.includes('shell')) {
    return createTerminal();
  }
  if (normalizedName.includes('test')) {
    return createFlask();
  }
  if (normalizedName.includes('research') || normalizedName.includes('search')) {
    return createTelescope();
  }
  if (normalizedName.includes('debug') || normalizedName.includes('fix')) {
    return createWrench();
  }
  if (normalizedName.includes('plan') || normalizedName.includes('idea')) {
    return createLightbulb();
  }
  if (normalizedName.includes('deploy')) {
    return createRocket();
  }
  if (normalizedName.includes('security') || normalizedName.includes('protect')) {
    return createShield();
  }
  if (normalizedName.includes('integrate')) {
    return createPuzzlePiece();
  }
  if (normalizedName.includes('task') || normalizedName.includes('todo')) {
    return createClipboard();
  }
  if (normalizedName.includes('monitor') || normalizedName.includes('observe')) {
    return createBinoculars();
  }

  // Default fallback
  return createGear();
}
