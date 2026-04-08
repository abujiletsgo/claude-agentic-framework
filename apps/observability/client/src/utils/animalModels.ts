import * as THREE from 'three';

// Helper function to create materials with consistent style
const createMaterial = (color: number): THREE.MeshStandardMaterial => {
  return new THREE.MeshStandardMaterial({
    color,
    flatShading: true,
    roughness: 0.8,
    metalness: 0.2,
  });
};

// Animation types for different tool interactions
export type AnimationType =
  | 'standIdle'
  | 'typeMotion'
  | 'hammerMotion'
  | 'readMotion'
  | 'writeMotion'
  | 'useToolWithHands';

// Base humanoid animal class with arms, hands, and animations
class AnimalModel extends THREE.Group {
  private animationTime: number = 0;
  private currentAnimation: AnimationType = 'standIdle';
  private toolHolder: THREE.Object3D;
  private baseY: number = 0;

  // Body parts for animations
  protected leftArm: THREE.Group | null = null;
  protected rightArm: THREE.Group | null = null;
  protected leftHand: THREE.Mesh | null = null;
  protected rightHand: THREE.Mesh | null = null;
  protected torso: THREE.Mesh | null = null;
  protected headGroup: THREE.Group | null = null;
  protected leftLeg: THREE.Mesh | null = null;
  protected rightLeg: THREE.Mesh | null = null;

  constructor() {
    super();
    this.toolHolder = new THREE.Object3D();
    this.toolHolder.position.set(0, 0, 0);
    this.add(this.toolHolder);
  }

  // Create a basic arm with shoulder, elbow, and hand
  protected createArm(
    side: 'left' | 'right',
    armColor: number,
    handColor: number
  ): THREE.Group {
    const arm = new THREE.Group();
    const direction = side === 'left' ? -1 : 1;
    arm.name = side === 'left' ? 'leftArmGroup' : 'rightArmGroup';

    // Upper arm (shoulder to elbow)
    const upperArmGeometry = new THREE.CapsuleGeometry(0.08, 0.25, 8, 16);
    const upperArmMaterial = createMaterial(armColor);
    const upperArm = new THREE.Mesh(upperArmGeometry, upperArmMaterial);
    upperArm.position.set(direction * 0.15, -0.15, 0);
    upperArm.name = side === 'left' ? 'leftUpperArm' : 'rightUpperArm';
    arm.add(upperArm);

    // Elbow joint (for rotation)
    const elbowJoint = new THREE.Group();
    elbowJoint.position.set(direction * 0.15, -0.3, 0);
    elbowJoint.name = side === 'left' ? 'leftElbow' : 'rightElbow';
    arm.add(elbowJoint);

    // Lower arm (elbow to wrist)
    const lowerArmGeometry = new THREE.CapsuleGeometry(0.07, 0.22, 8, 16);
    const lowerArmMaterial = createMaterial(armColor);
    const lowerArm = new THREE.Mesh(lowerArmGeometry, lowerArmMaterial);
    lowerArm.position.set(0, -0.15, 0);
    lowerArm.name = side === 'left' ? 'leftLowerArm' : 'rightLowerArm';
    elbowJoint.add(lowerArm);

    // Hand/paw
    const handGeometry = new THREE.SphereGeometry(0.09, 8, 8);
    const handMaterial = createMaterial(handColor);
    const hand = new THREE.Mesh(handGeometry, handMaterial);
    hand.position.set(0, -0.28, 0);
    hand.scale.set(1, 1.2, 0.8);
    hand.name = side === 'left' ? 'leftHand' : 'rightHand';
    elbowJoint.add(hand);

    if (side === 'left') {
      this.leftHand = hand;
    } else {
      this.rightHand = hand;
    }

    return arm;
  }

  // Create bipedal legs
  protected createLeg(
    side: 'left' | 'right',
    legColor: number,
    footColor: number
  ): THREE.Group {
    const legGroup = new THREE.Group();
    const direction = side === 'left' ? -1 : 1;
    legGroup.name = side === 'left' ? 'leftLegGroup' : 'rightLegGroup';

    // Upper leg (thigh)
    const thighGeometry = new THREE.CapsuleGeometry(0.1, 0.3, 8, 16);
    const thighMaterial = createMaterial(legColor);
    const thigh = new THREE.Mesh(thighGeometry, thighMaterial);
    thigh.position.set(direction * 0.12, -0.55, 0);
    thigh.name = side === 'left' ? 'leftThigh' : 'rightThigh';
    legGroup.add(thigh);

    // Lower leg (shin)
    const shinGeometry = new THREE.CapsuleGeometry(0.08, 0.25, 8, 16);
    const shinMaterial = createMaterial(legColor);
    const shin = new THREE.Mesh(shinGeometry, shinMaterial);
    shin.position.set(direction * 0.12, -0.82, 0);
    shin.name = side === 'left' ? 'leftShin' : 'rightShin';
    legGroup.add(shin);

    // Foot
    const footGeometry = new THREE.BoxGeometry(0.12, 0.08, 0.18);
    const footMaterial = createMaterial(footColor);
    const foot = new THREE.Mesh(footGeometry, footMaterial);
    foot.position.set(direction * 0.12, -1, 0.05);
    foot.name = side === 'left' ? 'leftFoot' : 'rightFoot';
    legGroup.add(foot);

    if (side === 'left') {
      this.leftLeg = thigh;
    } else {
      this.rightLeg = thigh;
    }

    this.add(legGroup);
    return legGroup;
  }

  holdTool(toolMesh: THREE.Object3D): void {
    // Clear existing tools
    while (this.toolHolder.children.length > 0) {
      this.toolHolder.remove(this.toolHolder.children[0]);
    }
    this.toolHolder.add(toolMesh);

    // Position tool between hands
    if (this.rightHand) {
      const handWorldPos = new THREE.Vector3();
      this.rightHand.getWorldPosition(handWorldPos);
      this.worldToLocal(handWorldPos);
      this.toolHolder.position.copy(handWorldPos);
    }
  }

  getToolHolder(): THREE.Object3D {
    return this.toolHolder;
  }

  // Animation methods
  standIdle(): void {
    this.currentAnimation = 'standIdle';
  }

  typeMotion(): void {
    this.currentAnimation = 'typeMotion';
  }

  hammerMotion(): void {
    this.currentAnimation = 'hammerMotion';
  }

  readMotion(): void {
    this.currentAnimation = 'readMotion';
  }

  writeMotion(): void {
    this.currentAnimation = 'writeMotion';
  }

  useToolWithHands(): void {
    this.currentAnimation = 'useToolWithHands';
  }

  // Walking animation for movement
  walkMotion(delta: number): void {
    this.animationTime += delta;
    this.animateWalkMotion();
  }

  animate(delta: number): void {
    this.animationTime += delta;

    switch (this.currentAnimation) {
      case 'standIdle':
        this.animateStandIdle();
        break;
      case 'typeMotion':
        this.animateTypeMotion();
        break;
      case 'hammerMotion':
        this.animateHammerMotion();
        break;
      case 'readMotion':
        this.animateReadMotion();
        break;
      case 'writeMotion':
        this.animateWriteMotion();
        break;
      case 'useToolWithHands':
        this.animateUseToolWithHands();
        break;
    }
  }

  private animateStandIdle(): void {
    // Gentle breathing motion
    if (this.torso) {
      this.torso.scale.y = 1 + Math.sin(this.animationTime * 1.5) * 0.03;
    }

    // Subtle weight shifting
    this.position.x = Math.sin(this.animationTime * 0.5) * 0.02;
    this.rotation.z = Math.sin(this.animationTime * 0.5) * 0.02;

    // Slight head tilt
    if (this.headGroup) {
      this.headGroup.rotation.z = Math.sin(this.animationTime * 0.8) * 0.05;
    }

    // Relaxed arm sway
    if (this.leftArm) {
      this.leftArm.rotation.x = Math.sin(this.animationTime * 0.8) * 0.05;
    }
    if (this.rightArm) {
      this.rightArm.rotation.x = Math.sin(this.animationTime * 0.8 + Math.PI) * 0.05;
    }
  }

  private animateTypeMotion(): void {
    // Rapid alternating hand movements (typing on keyboard)
    const typingSpeed = this.animationTime * 10;

    if (this.leftArm && this.rightArm) {
      const leftElbow = this.leftArm.getObjectByName('leftElbow') as THREE.Group;
      const rightElbow = this.rightArm.getObjectByName('rightElbow') as THREE.Group;

      if (leftElbow) {
        leftElbow.rotation.x = Math.sin(typingSpeed) * 0.15 + 0.3;
      }
      if (rightElbow) {
        rightElbow.rotation.x = Math.sin(typingSpeed + Math.PI * 0.5) * 0.15 + 0.3;
      }

      // Shoulders slightly forward
      this.leftArm.rotation.x = 0.2;
      this.rightArm.rotation.x = 0.2;
    }

    // Head focused forward
    if (this.headGroup) {
      this.headGroup.rotation.x = -0.1;
    }

    // Torso leans slightly forward
    this.rotation.x = 0.05;
  }

  private animateHammerMotion(): void {
    // Swinging motion with right arm
    const swingPhase = Math.sin(this.animationTime * 3);

    if (this.rightArm) {
      const rightElbow = this.rightArm.getObjectByName('rightElbow') as THREE.Group;

      // Arm raises and swings down
      this.rightArm.rotation.x = -0.5 + swingPhase * 0.8;
      this.rightArm.rotation.z = 0.3;

      if (rightElbow) {
        rightElbow.rotation.x = swingPhase > 0 ? -0.3 : 0.5;
      }
    }

    // Left arm stabilizes
    if (this.leftArm) {
      this.leftArm.rotation.x = 0.3;
      this.leftArm.rotation.z = -0.2;
    }

    // Body rotates with swing
    this.rotation.y = swingPhase * 0.15;

    // Head follows motion
    if (this.headGroup) {
      this.headGroup.rotation.x = swingPhase * 0.1;
    }
  }

  private animateReadMotion(): void {
    // Holding book/paper in front, looking down
    if (this.leftArm && this.rightArm) {
      // Arms up holding book
      this.leftArm.rotation.x = -0.8;
      this.leftArm.rotation.z = -0.4;
      this.rightArm.rotation.x = -0.8;
      this.rightArm.rotation.z = 0.4;

      const leftElbow = this.leftArm.getObjectByName('leftElbow') as THREE.Group;
      const rightElbow = this.rightArm.getObjectByName('rightElbow') as THREE.Group;

      if (leftElbow) {
        leftElbow.rotation.x = -1.2;
      }
      if (rightElbow) {
        rightElbow.rotation.x = -1.2;
      }
    }

    // Head tilts down to read
    if (this.headGroup) {
      this.headGroup.rotation.x = 0.3;
      // Occasional head tilt as "reading"
      this.headGroup.rotation.z = Math.sin(this.animationTime * 0.5) * 0.1;
    }

    // Slight sway while reading
    this.rotation.y = Math.sin(this.animationTime * 0.4) * 0.05;
  }

  private animateWriteMotion(): void {
    // Right hand moves in writing motion
    if (this.rightArm) {
      const rightElbow = this.rightArm.getObjectByName('rightElbow') as THREE.Group;

      // Arm positioned for writing
      this.rightArm.rotation.x = 0.3;
      this.rightArm.rotation.z = 0.5;

      if (rightElbow) {
        // Elbow bent, hand moving in writing motion
        rightElbow.rotation.x = -0.8;
        rightElbow.rotation.z = Math.sin(this.animationTime * 4) * 0.1;
      }

      if (this.rightHand) {
        // Hand makes small circular writing motions
        this.rightHand.rotation.y = Math.sin(this.animationTime * 4) * 0.15;
      }
    }

    // Left arm supports/stabilizes
    if (this.leftArm) {
      this.leftArm.rotation.x = 0.4;
      this.leftArm.rotation.z = -0.3;

      const leftElbow = this.leftArm.getObjectByName('leftElbow') as THREE.Group;
      if (leftElbow) {
        leftElbow.rotation.x = -0.5;
      }
    }

    // Head tilts down watching the writing
    if (this.headGroup) {
      this.headGroup.rotation.x = 0.4;
    }

    // Slight body lean forward
    this.rotation.x = 0.1;
  }

  private animateUseToolWithHands(): void {
    // Generic tool use animation - hands working
    const workCycle = Math.sin(this.animationTime * 2.5);

    if (this.leftArm && this.rightArm) {
      // Both arms positioned to use tool
      this.leftArm.rotation.x = -0.3 + workCycle * 0.2;
      this.rightArm.rotation.x = -0.3 - workCycle * 0.2;

      const leftElbow = this.leftArm.getObjectByName('leftElbow') as THREE.Group;
      const rightElbow = this.rightArm.getObjectByName('rightElbow') as THREE.Group;

      if (leftElbow) {
        leftElbow.rotation.x = -0.6 + workCycle * 0.3;
      }
      if (rightElbow) {
        rightElbow.rotation.x = -0.6 - workCycle * 0.3;
      }
    }

    // Head focused on tool
    if (this.headGroup) {
      this.headGroup.rotation.x = -0.15;
      this.headGroup.rotation.y = Math.sin(this.animationTime * 1.2) * 0.1;
    }

    // Slight body movement with work
    this.position.y = this.baseY + Math.abs(workCycle) * 0.05;
  }

  private animateWalkMotion(): void {
    // Walking speed multiplier for animation
    const walkSpeed = 8.0;
    const walkTime = this.animationTime * walkSpeed;

    // Alternating leg movement
    if (this.leftLeg && this.rightLeg) {
      // Left leg swings forward/back
      this.leftLeg.rotation.x = Math.sin(walkTime) * 0.4;
      // Right leg swings opposite
      this.rightLeg.rotation.x = Math.sin(walkTime + Math.PI) * 0.4;
    }

    // Alternating arm swing (opposite to legs)
    if (this.leftArm && this.rightArm) {
      this.leftArm.rotation.x = Math.sin(walkTime + Math.PI) * 0.3;
      this.rightArm.rotation.x = Math.sin(walkTime) * 0.3;
    }

    // Body bob while walking
    const bobAmount = 0.08;
    this.position.y = this.baseY + Math.abs(Math.sin(walkTime * 2)) * bobAmount;

    // Slight forward lean
    this.rotation.x = 0.1;

    // Slight side-to-side sway
    this.rotation.z = Math.sin(walkTime) * 0.05;

    // Head stays relatively level despite body movement
    if (this.headGroup) {
      this.headGroup.rotation.x = -0.08; // Slight downward tilt (looking forward)
      this.headGroup.rotation.z = -Math.sin(walkTime) * 0.03; // Counter body sway slightly
    }
  }

  // Set base Y position (called when positioning agent)
  setBaseY(y: number): void {
    this.baseY = y;
  }

  // Reset rotation (called before animation)
  resetRotation(): void {
    this.rotation.set(0, 0, 0);
    if (this.toolHolder) {
      this.toolHolder.rotation.set(0, 0, 0);
      this.toolHolder.position.set(0, 0, 0);
    }
  }
}

// 1. Wise Owl - Standing humanoid with wing-arms
export const createOwl = (): AnimalModel => {
  const owl = new AnimalModel();

  // Torso (upright body)
  const torsoGeometry = new THREE.CapsuleGeometry(0.25, 0.4, 16, 16);
  const torsoMaterial = createMaterial(0x8B4513);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.3;
  owl.torso = torso;
  owl.add(torso);

  // Head group (for rotation)
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.3;
  owl.headGroup = headGroup;
  owl.add(headGroup);

  // Head sphere
  const headGeometry = new THREE.SphereGeometry(0.35, 16, 16);
  const headMaterial = createMaterial(0xA0522D);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Big eyes
  const eyeGeometry = new THREE.CircleGeometry(0.15, 16);
  const eyeMaterial = createMaterial(0xFFFFFF);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.12, 0.05, 0.32);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.12, 0.05, 0.32);
  headGroup.add(rightEye);

  // Pupils
  const pupilGeometry = new THREE.CircleGeometry(0.06, 16);
  const pupilMaterial = createMaterial(0x000000);

  const leftPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  leftPupil.position.set(-0.12, 0.05, 0.33);
  headGroup.add(leftPupil);

  const rightPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  rightPupil.position.set(0.12, 0.05, 0.33);
  headGroup.add(rightPupil);

  // Beak
  const beakGeometry = new THREE.ConeGeometry(0.08, 0.15, 8);
  const beakMaterial = createMaterial(0xFFD700);
  const beak = new THREE.Mesh(beakGeometry, beakMaterial);
  beak.position.set(0, -0.05, 0.32);
  beak.rotation.x = Math.PI;
  headGroup.add(beak);

  // Wing-arms (act as arms)
  const leftWingArm = owl.createArm('left', 0x654321, 0x8B4513);
  leftWingArm.position.set(-0.25, 0.05, 0);
  owl.leftArm = leftWingArm;
  owl.add(leftWingArm);

  const rightWingArm = owl.createArm('right', 0x654321, 0x8B4513);
  rightWingArm.position.set(0.25, 0.05, 0);
  owl.rightArm = rightWingArm;
  owl.add(rightWingArm);

  // Legs (standing upright)
  owl.createLeg('left', 0xA0522D, 0xFFD700);
  owl.createLeg('right', 0xA0522D, 0xFFD700);

  // Position tool holder at chest level
  owl.toolHolder.position.set(0, -0.1, 0.4);

  return owl;
};

// 2. Busy Beaver - Standing with front paws as hands
export const createBeaver = (): AnimalModel => {
  const beaver = new AnimalModel();

  // Upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.28, 0.45, 16, 16);
  const torsoMaterial = createMaterial(0x8B4513);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.35;
  beaver.torso = torso;
  beaver.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.25;
  beaver.headGroup = headGroup;
  beaver.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const headMaterial = createMaterial(0xA0522D);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Eyes
  const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.12, 0.08, 0.25);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.12, 0.08, 0.25);
  headGroup.add(rightEye);

  // Big front teeth
  const toothGeometry = new THREE.BoxGeometry(0.06, 0.15, 0.05);
  const toothMaterial = createMaterial(0xFFFFFF);

  const leftTooth = new THREE.Mesh(toothGeometry, toothMaterial);
  leftTooth.position.set(-0.06, -0.08, 0.28);
  headGroup.add(leftTooth);

  const rightTooth = new THREE.Mesh(toothGeometry, toothMaterial);
  rightTooth.position.set(0.06, -0.08, 0.28);
  headGroup.add(rightTooth);

  // Small round ears
  const earGeometry = new THREE.SphereGeometry(0.1, 8, 8);
  const earMaterial = createMaterial(0x8B4513);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.22, 0.22, 0);
  leftEar.scale.z = 0.5;
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.22, 0.22, 0);
  rightEar.scale.z = 0.5;
  headGroup.add(rightEar);

  // Arms with paw-hands
  const leftArm = beaver.createArm('left', 0x8B4513, 0xA0522D);
  leftArm.position.set(-0.28, 0, 0);
  beaver.leftArm = leftArm;
  beaver.add(leftArm);

  const rightArm = beaver.createArm('right', 0x8B4513, 0xA0522D);
  rightArm.position.set(0.28, 0, 0);
  beaver.rightArm = rightArm;
  beaver.add(rightArm);

  // Legs
  beaver.createLeg('left', 0x8B4513, 0xA0522D);
  beaver.createLeg('right', 0x8B4513, 0xA0522D);

  // Flat tail (still visible when standing)
  const tailGeometry = new THREE.BoxGeometry(0.35, 0.1, 0.5);
  const tailMaterial = createMaterial(0x654321);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.7, -0.3);
  tail.rotation.x = -Math.PI / 8;
  beaver.add(tail);

  beaver.toolHolder.position.set(0, -0.15, 0.4);

  return beaver;
};

// 3. Quick Rabbit - Standing on hind legs
export const createRabbit = (): AnimalModel => {
  const rabbit = new AnimalModel();

  // Slender upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.22, 0.5, 16, 16);
  const torsoMaterial = createMaterial(0xF5F5DC);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.4;
  rabbit.torso = torso;
  rabbit.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.35;
  rabbit.headGroup = headGroup;
  rabbit.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.28, 16, 16);
  const headMaterial = createMaterial(0xFFFAF0);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Long ears
  const earGeometry = new THREE.CapsuleGeometry(0.08, 0.55, 8, 16);
  const earMaterial = createMaterial(0xF5F5DC);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.12, 0.5, 0);
  leftEar.rotation.z = -0.15;
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.12, 0.5, 0);
  rightEar.rotation.z = 0.15;
  headGroup.add(rightEar);

  // Pink inner ears
  const innerEarGeometry = new THREE.CapsuleGeometry(0.04, 0.35, 8, 16);
  const innerEarMaterial = createMaterial(0xFFB6C1);

  const leftInnerEar = new THREE.Mesh(innerEarGeometry, innerEarMaterial);
  leftInnerEar.position.set(-0.12, 0.5, 0.05);
  leftInnerEar.rotation.z = -0.15;
  headGroup.add(leftInnerEar);

  const rightInnerEar = new THREE.Mesh(innerEarGeometry, innerEarMaterial);
  rightInnerEar.position.set(0.12, 0.5, 0.05);
  rightInnerEar.rotation.z = 0.15;
  headGroup.add(rightInnerEar);

  // Eyes
  const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.1, 0.05, 0.25);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.1, 0.05, 0.25);
  headGroup.add(rightEye);

  // Cute pink nose
  const noseGeometry = new THREE.SphereGeometry(0.05, 8, 8);
  const noseMaterial = createMaterial(0xFFB6C1);
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.set(0, -0.05, 0.27);
  headGroup.add(nose);

  // Arms (front paws)
  const leftArm = rabbit.createArm('left', 0xF5F5DC, 0xFFB6C1);
  leftArm.position.set(-0.22, 0.05, 0);
  rabbit.leftArm = leftArm;
  rabbit.add(leftArm);

  const rightArm = rabbit.createArm('right', 0xF5F5DC, 0xFFB6C1);
  rightArm.position.set(0.22, 0.05, 0);
  rabbit.rightArm = rightArm;
  rabbit.add(rightArm);

  // Strong hind legs
  rabbit.createLeg('left', 0xF5F5DC, 0xFFB6C1);
  rabbit.createLeg('right', 0xF5F5DC, 0xFFB6C1);

  // Fluffy tail
  const tailGeometry = new THREE.SphereGeometry(0.12, 8, 8);
  const tailMaterial = createMaterial(0xFFFFFF);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.55, -0.15);
  rabbit.add(tail);

  rabbit.toolHolder.position.set(0, -0.1, 0.35);

  return rabbit;
};

// 4. Small Cute Dragon - Standing bipedal
export const createDragon = (): AnimalModel => {
  const dragon = new AnimalModel();

  // Upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.25, 0.4, 16, 16);
  const torsoMaterial = createMaterial(0x9370DB);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.3;
  dragon.torso = torso;
  dragon.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.3;
  dragon.headGroup = headGroup;
  dragon.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.32, 16, 16);
  const headMaterial = createMaterial(0xBA55D3);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Snout
  const snoutGeometry = new THREE.ConeGeometry(0.12, 0.22, 8);
  const snoutMaterial = createMaterial(0xBA55D3);
  const snout = new THREE.Mesh(snoutGeometry, snoutMaterial);
  snout.position.set(0, -0.05, 0.32);
  snout.rotation.x = Math.PI / 2;
  headGroup.add(snout);

  // Big cute eyes
  const eyeGeometry = new THREE.SphereGeometry(0.1, 8, 8);
  const eyeMaterial = createMaterial(0xFFD700);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.13, 0.08, 0.25);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.13, 0.08, 0.25);
  headGroup.add(rightEye);

  // Pupils
  const pupilGeometry = new THREE.SphereGeometry(0.05, 8, 8);
  const pupilMaterial = createMaterial(0x000000);

  const leftPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  leftPupil.position.set(-0.13, 0.08, 0.32);
  headGroup.add(leftPupil);

  const rightPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  rightPupil.position.set(0.13, 0.08, 0.32);
  headGroup.add(rightPupil);

  // Horns
  const hornGeometry = new THREE.ConeGeometry(0.08, 0.22, 8);
  const hornMaterial = createMaterial(0xFFD700);

  const leftHorn = new THREE.Mesh(hornGeometry, hornMaterial);
  leftHorn.position.set(-0.12, 0.3, 0);
  leftHorn.rotation.z = -0.25;
  headGroup.add(leftHorn);

  const rightHorn = new THREE.Mesh(hornGeometry, hornMaterial);
  rightHorn.position.set(0.12, 0.3, 0);
  rightHorn.rotation.z = 0.25;
  headGroup.add(rightHorn);

  // Arms with claws
  const leftArm = dragon.createArm('left', 0x9370DB, 0x8B008B);
  leftArm.position.set(-0.25, 0.05, 0);
  dragon.leftArm = leftArm;
  dragon.add(leftArm);

  const rightArm = dragon.createArm('right', 0x9370DB, 0x8B008B);
  rightArm.position.set(0.25, 0.05, 0);
  dragon.rightArm = rightArm;
  dragon.add(rightArm);

  // Wings (decorative, smaller since standing)
  const wingGeometry = new THREE.ConeGeometry(0.2, 0.35, 3);
  const wingMaterial = createMaterial(0x8B008B);

  const leftWing = new THREE.Mesh(wingGeometry, wingMaterial);
  leftWing.position.set(-0.2, -0.1, -0.15);
  leftWing.rotation.set(0, 0, Math.PI / 4);
  dragon.add(leftWing);

  const rightWing = new THREE.Mesh(wingGeometry, wingMaterial);
  rightWing.position.set(0.2, -0.1, -0.15);
  rightWing.rotation.set(0, 0, -Math.PI / 4);
  dragon.add(rightWing);

  // Legs
  dragon.createLeg('left', 0x9370DB, 0x8B008B);
  dragon.createLeg('right', 0x9370DB, 0x8B008B);

  // Tail
  const tailGeometry = new THREE.ConeGeometry(0.12, 0.65, 8);
  const tailMaterial = createMaterial(0x9370DB);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.5, -0.35);
  tail.rotation.x = Math.PI / 2.5;
  dragon.add(tail);

  // Tail tip spike
  const spikeGeometry = new THREE.ConeGeometry(0.08, 0.18, 4);
  const spikeMaterial = createMaterial(0xFFD700);
  const spike = new THREE.Mesh(spikeGeometry, spikeMaterial);
  spike.position.set(0, -0.65, -0.65);
  spike.rotation.x = Math.PI / 2.5;
  dragon.add(spike);

  dragon.toolHolder.position.set(0, -0.1, 0.4);

  return dragon;
};

// 5. Curious Fox - Standing upright
export const createFox = (): AnimalModel => {
  const fox = new AnimalModel();

  // Slender upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.23, 0.45, 16, 16);
  const torsoMaterial = createMaterial(0xFF6347);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.35;
  fox.torso = torso;
  fox.add(torso);

  // White chest patch
  const chestGeometry = new THREE.SphereGeometry(0.18, 16, 16);
  const chestMaterial = createMaterial(0xFFFAF0);
  const chest = new THREE.Mesh(chestGeometry, chestMaterial);
  chest.position.set(0, -0.3, 0.2);
  chest.scale.set(0.8, 1, 0.5);
  fox.add(chest);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.25;
  fox.headGroup = headGroup;
  fox.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.28, 16, 16);
  const headMaterial = createMaterial(0xFF7F50);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Snout
  const snoutGeometry = new THREE.ConeGeometry(0.11, 0.22, 8);
  const snoutMaterial = createMaterial(0xFFFAF0);
  const snout = new THREE.Mesh(snoutGeometry, snoutMaterial);
  snout.position.set(0, -0.08, 0.3);
  snout.rotation.x = Math.PI / 2;
  headGroup.add(snout);

  // Eyes
  const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.11, 0.08, 0.23);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.11, 0.08, 0.23);
  headGroup.add(rightEye);

  // Pointy ears
  const earGeometry = new THREE.ConeGeometry(0.11, 0.28, 8);
  const earMaterial = createMaterial(0xFF6347);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.13, 0.32, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.13, 0.32, 0);
  headGroup.add(rightEar);

  // Arms
  const leftArm = fox.createArm('left', 0xFF6347, 0xFF7F50);
  leftArm.position.set(-0.23, 0.05, 0);
  fox.leftArm = leftArm;
  fox.add(leftArm);

  const rightArm = fox.createArm('right', 0xFF6347, 0xFF7F50);
  rightArm.position.set(0.23, 0.05, 0);
  fox.rightArm = rightArm;
  fox.add(rightArm);

  // Legs
  fox.createLeg('left', 0xFF6347, 0xFF7F50);
  fox.createLeg('right', 0xFF6347, 0xFF7F50);

  // Bushy tail
  const tailGeometry = new THREE.SphereGeometry(0.22, 16, 16);
  const tailMaterial = createMaterial(0xFF6347);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.4, -0.3);
  tail.scale.set(0.7, 0.7, 1.3);
  fox.add(tail);

  // White tail tip
  const tailTipGeometry = new THREE.SphereGeometry(0.13, 8, 8);
  const tailTipMaterial = createMaterial(0xFFFFFF);
  const tailTip = new THREE.Mesh(tailTipGeometry, tailTipMaterial);
  tailTip.position.set(0, -0.4, -0.55);
  fox.add(tailTip);

  fox.toolHolder.position.set(0, -0.1, 0.38);

  return fox;
};

// 6. Happy Penguin - Already naturally bipedal
export const createPenguin = (): AnimalModel => {
  const penguin = new AnimalModel();

  // Upright egg-shaped body
  const torsoGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const torsoMaterial = createMaterial(0x000000);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.scale.set(1, 1.3, 0.85);
  torso.position.y = -0.35;
  penguin.torso = torso;
  penguin.add(torso);

  // White belly
  const bellyGeometry = new THREE.SphereGeometry(0.25, 16, 16);
  const bellyMaterial = createMaterial(0xFFFFFF);
  const belly = new THREE.Mesh(bellyGeometry, bellyMaterial);
  belly.scale.set(0.75, 1.15, 0.55);
  belly.position.set(0, -0.35, 0.18);
  penguin.add(belly);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.25;
  penguin.headGroup = headGroup;
  penguin.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.28, 16, 16);
  const headMaterial = createMaterial(0x000000);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Eyes
  const eyeGeometry = new THREE.CircleGeometry(0.1, 16);
  const eyeMaterial = createMaterial(0xFFFFFF);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.09, 0.05, 0.26);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.09, 0.05, 0.26);
  headGroup.add(rightEye);

  // Pupils
  const pupilGeometry = new THREE.CircleGeometry(0.04, 16);
  const pupilMaterial = createMaterial(0x000000);

  const leftPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  leftPupil.position.set(-0.09, 0.05, 0.27);
  headGroup.add(leftPupil);

  const rightPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  rightPupil.position.set(0.09, 0.05, 0.27);
  headGroup.add(rightPupil);

  // Orange beak
  const beakGeometry = new THREE.ConeGeometry(0.07, 0.18, 8);
  const beakMaterial = createMaterial(0xFF8C00);
  const beak = new THREE.Mesh(beakGeometry, beakMaterial);
  beak.position.set(0, -0.05, 0.3);
  beak.rotation.x = Math.PI / 2;
  headGroup.add(beak);

  // Flippers as arms
  const leftFlipper = penguin.createArm('left', 0x000000, 0x000000);
  leftFlipper.position.set(-0.3, 0, 0);
  // Scale flipper to be flatter
  leftFlipper.scale.set(0.7, 1, 0.5);
  penguin.leftArm = leftFlipper;
  penguin.add(leftFlipper);

  const rightFlipper = penguin.createArm('right', 0x000000, 0x000000);
  rightFlipper.position.set(0.3, 0, 0);
  rightFlipper.scale.set(0.7, 1, 0.5);
  penguin.rightArm = rightFlipper;
  penguin.add(rightFlipper);

  // Orange feet
  const footGeometry = new THREE.BoxGeometry(0.14, 0.06, 0.2);
  const footMaterial = createMaterial(0xFF8C00);

  const leftFoot = new THREE.Mesh(footGeometry, footMaterial);
  leftFoot.position.set(-0.12, -0.9, 0.05);
  penguin.add(leftFoot);

  const rightFoot = new THREE.Mesh(footGeometry, footMaterial);
  rightFoot.position.set(0.12, -0.9, 0.05);
  penguin.add(rightFoot);

  penguin.toolHolder.position.set(0, -0.15, 0.35);

  return penguin;
};

// 7. Sleepy Bear - Standing upright
export const createBear = (): AnimalModel => {
  const bear = new AnimalModel();

  // Large upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.32, 0.5, 16, 16);
  const torsoMaterial = createMaterial(0x8B4513);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.4;
  bear.torso = torso;
  bear.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.35;
  bear.headGroup = headGroup;
  bear.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.35, 16, 16);
  const headMaterial = createMaterial(0xA0522D);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Round ears
  const earGeometry = new THREE.SphereGeometry(0.14, 8, 8);
  const earMaterial = createMaterial(0x8B4513);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.22, 0.28, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.22, 0.28, 0);
  headGroup.add(rightEar);

  // Snout
  const snoutGeometry = new THREE.SphereGeometry(0.16, 8, 8);
  const snoutMaterial = createMaterial(0xD2B48C);
  const snout = new THREE.Mesh(snoutGeometry, snoutMaterial);
  snout.position.set(0, -0.08, 0.3);
  snout.scale.z = 0.7;
  headGroup.add(snout);

  // Sleepy eyes (small slits)
  const eyeGeometry = new THREE.BoxGeometry(0.11, 0.04, 0.05);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.11, 0.08, 0.28);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.11, 0.08, 0.28);
  headGroup.add(rightEye);

  // Nose
  const noseGeometry = new THREE.SphereGeometry(0.06, 8, 8);
  const noseMaterial = createMaterial(0x000000);
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.set(0, -0.08, 0.42);
  headGroup.add(nose);

  // Strong arms with paws
  const leftArm = bear.createArm('left', 0x8B4513, 0xA0522D);
  leftArm.position.set(-0.32, 0.05, 0);
  bear.leftArm = leftArm;
  bear.add(leftArm);

  const rightArm = bear.createArm('right', 0x8B4513, 0xA0522D);
  rightArm.position.set(0.32, 0.05, 0);
  bear.rightArm = rightArm;
  bear.add(rightArm);

  // Legs
  bear.createLeg('left', 0x8B4513, 0xA0522D);
  bear.createLeg('right', 0x8B4513, 0xA0522D);

  bear.toolHolder.position.set(0, -0.15, 0.45);

  return bear;
};

// 8. Playful Cat - Standing on hind legs
export const createCat = (): AnimalModel => {
  const cat = new AnimalModel();

  // Sleek upright torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.2, 0.45, 16, 16);
  const torsoMaterial = createMaterial(0xFF69B4);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.35;
  cat.torso = torso;
  cat.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.3;
  cat.headGroup = headGroup;
  cat.add(headGroup);

  // Head (round and cute)
  const headGeometry = new THREE.SphereGeometry(0.28, 16, 16);
  const headMaterial = createMaterial(0xFFC0CB);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Pointy ears
  const earGeometry = new THREE.ConeGeometry(0.11, 0.23, 4);
  const earMaterial = createMaterial(0xFF69B4);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.16, 0.3, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.16, 0.3, 0);
  headGroup.add(rightEar);

  // Big cute eyes
  const eyeGeometry = new THREE.SphereGeometry(0.09, 8, 8);
  const eyeMaterial = createMaterial(0x00FF00);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.1, 0.05, 0.25);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.1, 0.05, 0.25);
  headGroup.add(rightEye);

  // Pupils (vertical slits)
  const pupilGeometry = new THREE.BoxGeometry(0.03, 0.08, 0.05);
  const pupilMaterial = createMaterial(0x000000);

  const leftPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  leftPupil.position.set(-0.1, 0.05, 0.28);
  headGroup.add(leftPupil);

  const rightPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
  rightPupil.position.set(0.1, 0.05, 0.28);
  headGroup.add(rightPupil);

  // Pink nose
  const noseGeometry = new THREE.SphereGeometry(0.04, 8, 8);
  const noseMaterial = createMaterial(0xFF1493);
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.set(0, -0.08, 0.27);
  headGroup.add(nose);

  // Whiskers
  const whiskerGeometry = new THREE.CylinderGeometry(0.008, 0.008, 0.35, 4);
  const whiskerMaterial = createMaterial(0xFFFFFF);

  for (let i = 0; i < 3; i++) {
    const leftWhisker = new THREE.Mesh(whiskerGeometry, whiskerMaterial);
    leftWhisker.position.set(-0.2, -0.05 - i * 0.025, 0.25);
    leftWhisker.rotation.set(0, 0, -Math.PI / 4);
    headGroup.add(leftWhisker);

    const rightWhisker = new THREE.Mesh(whiskerGeometry, whiskerMaterial);
    rightWhisker.position.set(0.2, -0.05 - i * 0.025, 0.25);
    rightWhisker.rotation.set(0, 0, Math.PI / 4);
    headGroup.add(rightWhisker);
  }

  // Arms with paws
  const leftArm = cat.createArm('left', 0xFF69B4, 0xFFC0CB);
  leftArm.position.set(-0.2, 0.05, 0);
  cat.leftArm = leftArm;
  cat.add(leftArm);

  const rightArm = cat.createArm('right', 0xFF69B4, 0xFFC0CB);
  rightArm.position.set(0.2, 0.05, 0);
  cat.rightArm = rightArm;
  cat.add(rightArm);

  // Legs
  cat.createLeg('left', 0xFF69B4, 0xFFC0CB);
  cat.createLeg('right', 0xFF69B4, 0xFFC0CB);

  // Curled tail (higher position for standing)
  const tailGeometry = new THREE.TorusGeometry(0.2, 0.07, 8, 16, Math.PI);
  const tailMaterial = createMaterial(0xFF69B4);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.2, -0.25);
  tail.rotation.x = -Math.PI / 6;
  cat.add(tail);

  cat.toolHolder.position.set(0, -0.1, 0.35);

  return cat;
};

// 9. Cheerful Pig - Standing upright
export const createPig = (): AnimalModel => {
  const pig = new AnimalModel();

  // Round chubby torso
  const torsoGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const torsoMaterial = createMaterial(0xFFB6C1);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.scale.set(1.1, 1.2, 0.95);
  torso.position.y = -0.35;
  pig.torso = torso;
  pig.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.3;
  pig.headGroup = headGroup;
  pig.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const headMaterial = createMaterial(0xFFC0CB);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Snout (flat cylinder)
  const snoutGeometry = new THREE.CylinderGeometry(0.16, 0.16, 0.14, 16);
  const snoutMaterial = createMaterial(0xFF69B4);
  const snout = new THREE.Mesh(snoutGeometry, snoutMaterial);
  snout.position.set(0, -0.05, 0.32);
  snout.rotation.x = Math.PI / 2;
  headGroup.add(snout);

  // Nostrils
  const nostrilGeometry = new THREE.SphereGeometry(0.04, 8, 8);
  const nostrilMaterial = createMaterial(0x000000);

  const leftNostril = new THREE.Mesh(nostrilGeometry, nostrilMaterial);
  leftNostril.position.set(-0.06, -0.05, 0.39);
  headGroup.add(leftNostril);

  const rightNostril = new THREE.Mesh(nostrilGeometry, nostrilMaterial);
  rightNostril.position.set(0.06, -0.05, 0.39);
  headGroup.add(rightNostril);

  // Eyes
  const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.13, 0.08, 0.25);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.13, 0.08, 0.25);
  headGroup.add(rightEye);

  // Floppy ears
  const earGeometry = new THREE.SphereGeometry(0.13, 8, 8);
  const earMaterial = createMaterial(0xFFB6C1);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.scale.set(0.6, 1, 0.3);
  leftEar.position.set(-0.25, 0.2, 0);
  leftEar.rotation.z = -0.4;
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.scale.set(0.6, 1, 0.3);
  rightEar.position.set(0.25, 0.2, 0);
  rightEar.rotation.z = 0.4;
  headGroup.add(rightEar);

  // Arms
  const leftArm = pig.createArm('left', 0xFFB6C1, 0xFFC0CB);
  leftArm.position.set(-0.3, 0.02, 0);
  pig.leftArm = leftArm;
  pig.add(leftArm);

  const rightArm = pig.createArm('right', 0xFFB6C1, 0xFFC0CB);
  rightArm.position.set(0.3, 0.02, 0);
  pig.rightArm = rightArm;
  pig.add(rightArm);

  // Legs
  pig.createLeg('left', 0xFFB6C1, 0xFFC0CB);
  pig.createLeg('right', 0xFFB6C1, 0xFFC0CB);

  // Curly tail
  const tailGeometry = new THREE.TorusGeometry(0.08, 0.035, 8, 16);
  const tailMaterial = createMaterial(0xFFB6C1);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.2, -0.28);
  tail.rotation.y = Math.PI / 4;
  pig.add(tail);

  pig.toolHolder.position.set(0, -0.1, 0.4);

  return pig;
};

// 10. Wise Turtle - Standing with shell
export const createTurtle = (): AnimalModel => {
  const turtle = new AnimalModel();

  // Shell (on back while standing)
  const shellGeometry = new THREE.SphereGeometry(0.35, 16, 16, 0, Math.PI * 2, 0, Math.PI / 1.5);
  const shellMaterial = createMaterial(0x228B22);
  const shell = new THREE.Mesh(shellGeometry, shellMaterial);
  shell.position.set(0, -0.2, -0.15);
  shell.rotation.x = 0.3;
  turtle.add(shell);

  // Shell pattern (hexagons)
  const patternGeometry = new THREE.CircleGeometry(0.1, 6);
  const patternMaterial = createMaterial(0x006400);

  for (let i = 0; i < 5; i++) {
    const angle = (i / 5) * Math.PI * 2;
    const pattern = new THREE.Mesh(patternGeometry, patternMaterial);
    pattern.position.set(
      Math.cos(angle) * 0.18,
      -0.08,
      -0.15 + Math.sin(angle) * 0.18
    );
    pattern.rotation.x = -Math.PI / 3;
    turtle.add(pattern);
  }

  // Torso (front body visible)
  const torsoGeometry = new THREE.CapsuleGeometry(0.18, 0.3, 16, 16);
  const torsoMaterial = createMaterial(0x9ACD32);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.3;
  turtle.torso = torso;
  turtle.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.2;
  turtle.headGroup = headGroup;
  turtle.add(headGroup);

  // Head
  const headGeometry = new THREE.SphereGeometry(0.18, 16, 16);
  const headMaterial = createMaterial(0x9ACD32);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  head.scale.set(0.9, 0.8, 1.1);
  headGroup.add(head);

  // Eyes
  const eyeGeometry = new THREE.SphereGeometry(0.06, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.09, 0.05, 0.18);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.09, 0.05, 0.18);
  headGroup.add(rightEye);

  // Smile
  const smileGeometry = new THREE.TorusGeometry(0.07, 0.018, 8, 16, Math.PI);
  const smileMaterial = createMaterial(0x000000);
  const smile = new THREE.Mesh(smileGeometry, smileMaterial);
  smile.position.set(0, -0.05, 0.19);
  smile.rotation.x = Math.PI;
  headGroup.add(smile);

  // Arms
  const leftArm = turtle.createArm('left', 0x9ACD32, 0x9ACD32);
  leftArm.position.set(-0.18, -0.05, 0);
  turtle.leftArm = leftArm;
  turtle.add(leftArm);

  const rightArm = turtle.createArm('right', 0x9ACD32, 0x9ACD32);
  rightArm.position.set(0.18, -0.05, 0);
  turtle.rightArm = rightArm;
  turtle.add(rightArm);

  // Short sturdy legs
  turtle.createLeg('left', 0x9ACD32, 0x9ACD32);
  turtle.createLeg('right', 0x9ACD32, 0x9ACD32);

  // Short tail
  const tailGeometry = new THREE.ConeGeometry(0.05, 0.12, 8);
  const tailMaterial = createMaterial(0x9ACD32);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.set(0, -0.5, -0.25);
  tail.rotation.x = Math.PI / 2;
  turtle.add(tail);

  turtle.toolHolder.position.set(0, -0.1, 0.3);

  return turtle;
};

// 11. Energetic Squirrel - Standing upright with big tail
export const createSquirrel = (): AnimalModel => {
  const squirrel = new AnimalModel();

  // Small slender torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.18, 0.38, 16, 16);
  const torsoMaterial = createMaterial(0xD2691E);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.32;
  squirrel.torso = torso;
  squirrel.add(torso);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.25;
  squirrel.headGroup = headGroup;
  squirrel.add(headGroup);

  // Head (round with big eyes)
  const headGeometry = new THREE.SphereGeometry(0.23, 16, 16);
  const headMaterial = createMaterial(0xCD853F);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Big round eyes
  const eyeGeometry = new THREE.SphereGeometry(0.08, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.09, 0.05, 0.2);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.09, 0.05, 0.2);
  headGroup.add(rightEye);

  // Small ears
  const earGeometry = new THREE.ConeGeometry(0.07, 0.14, 8);
  const earMaterial = createMaterial(0xD2691E);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.13, 0.25, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.13, 0.25, 0);
  headGroup.add(rightEar);

  // Tiny nose
  const noseGeometry = new THREE.SphereGeometry(0.03, 8, 8);
  const noseMaterial = createMaterial(0x000000);
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.set(0, -0.02, 0.22);
  headGroup.add(nose);

  // Arms (for holding acorns/tools)
  const leftArm = squirrel.createArm('left', 0xD2691E, 0xCD853F);
  leftArm.position.set(-0.18, 0.02, 0);
  squirrel.leftArm = leftArm;
  squirrel.add(leftArm);

  const rightArm = squirrel.createArm('right', 0xD2691E, 0xCD853F);
  rightArm.position.set(0.18, 0.02, 0);
  squirrel.rightArm = rightArm;
  squirrel.add(rightArm);

  // Legs
  squirrel.createLeg('left', 0xD2691E, 0xCD853F);
  squirrel.createLeg('right', 0xD2691E, 0xCD853F);

  // Big bushy tail (signature feature) - arches up behind
  const tailGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const tailMaterial = createMaterial(0xD2691E);
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.scale.set(0.55, 1.4, 0.7);
  tail.position.set(0, 0, -0.3);
  tail.rotation.x = 0.6;
  squirrel.add(tail);

  squirrel.toolHolder.position.set(0, -0.08, 0.3);

  return squirrel;
};

// 12. Friendly Koala - Standing upright
export const createKoala = (): AnimalModel => {
  const koala = new AnimalModel();

  // Chubby torso
  const torsoGeometry = new THREE.CapsuleGeometry(0.28, 0.4, 16, 16);
  const torsoMaterial = createMaterial(0x808080);
  const torso = new THREE.Mesh(torsoGeometry, torsoMaterial);
  torso.position.y = -0.32;
  koala.torso = torso;
  koala.add(torso);

  // White chest patch
  const chestGeometry = new THREE.SphereGeometry(0.22, 16, 16);
  const chestMaterial = createMaterial(0xF5F5F5);
  const chest = new THREE.Mesh(chestGeometry, chestMaterial);
  chest.position.set(0, -0.28, 0.22);
  chest.scale.set(0.75, 0.95, 0.45);
  koala.add(chest);

  // Head group
  const headGroup = new THREE.Group();
  headGroup.position.y = 0.3;
  koala.headGroup = headGroup;
  koala.add(headGroup);

  // Big round head
  const headGeometry = new THREE.SphereGeometry(0.33, 16, 16);
  const headMaterial = createMaterial(0x9E9E9E);
  const head = new THREE.Mesh(headGeometry, headMaterial);
  headGroup.add(head);

  // Large fluffy ears
  const earGeometry = new THREE.SphereGeometry(0.2, 16, 16);
  const earMaterial = createMaterial(0x808080);

  const leftEar = new THREE.Mesh(earGeometry, earMaterial);
  leftEar.position.set(-0.3, 0.25, 0);
  headGroup.add(leftEar);

  const rightEar = new THREE.Mesh(earGeometry, earMaterial);
  rightEar.position.set(0.3, 0.25, 0);
  headGroup.add(rightEar);

  // Inner ear (white/light gray)
  const innerEarGeometry = new THREE.CircleGeometry(0.11, 16);
  const innerEarMaterial = createMaterial(0xE0E0E0);

  const leftInnerEar = new THREE.Mesh(innerEarGeometry, innerEarMaterial);
  leftInnerEar.position.set(-0.3, 0.25, 0.18);
  headGroup.add(leftInnerEar);

  const rightInnerEar = new THREE.Mesh(innerEarGeometry, innerEarMaterial);
  rightInnerEar.position.set(0.3, 0.25, 0.18);
  headGroup.add(rightInnerEar);

  // Big nose (signature black nose)
  const noseGeometry = new THREE.SphereGeometry(0.11, 16, 16);
  const noseMaterial = createMaterial(0x000000);
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.set(0, -0.05, 0.3);
  nose.scale.set(1.15, 0.75, 0.75);
  headGroup.add(nose);

  // Sleepy eyes
  const eyeGeometry = new THREE.SphereGeometry(0.06, 8, 8);
  const eyeMaterial = createMaterial(0x000000);

  const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  leftEye.position.set(-0.11, 0.08, 0.27);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
  rightEye.position.set(0.11, 0.08, 0.27);
  headGroup.add(rightEye);

  // Arms
  const leftArm = koala.createArm('left', 0x808080, 0x9E9E9E);
  leftArm.position.set(-0.28, 0.05, 0);
  koala.leftArm = leftArm;
  koala.add(leftArm);

  const rightArm = koala.createArm('right', 0x808080, 0x9E9E9E);
  rightArm.position.set(0.28, 0.05, 0);
  koala.rightArm = rightArm;
  koala.add(rightArm);

  // Legs
  koala.createLeg('left', 0x808080, 0x9E9E9E);
  koala.createLeg('right', 0x808080, 0x9E9E9E);

  koala.toolHolder.position.set(0, -0.1, 0.38);

  return koala;
};

// Helper function to create all animals at once
export const createAllAnimals = (): Record<string, AnimalModel> => {
  return {
    owl: createOwl(),
    beaver: createBeaver(),
    rabbit: createRabbit(),
    dragon: createDragon(),
    fox: createFox(),
    penguin: createPenguin(),
    bear: createBear(),
    cat: createCat(),
    pig: createPig(),
    turtle: createTurtle(),
    squirrel: createSquirrel(),
    koala: createKoala(),
  };
};

// Export the animal names for easy reference
export const ANIMAL_NAMES = [
  'owl',
  'beaver',
  'rabbit',
  'dragon',
  'fox',
  'penguin',
  'bear',
  'cat',
  'pig',
  'turtle',
  'squirrel',
  'koala',
] as const;

export type AnimalName = typeof ANIMAL_NAMES[number];

// Export the class for type checking
export { AnimalModel };
