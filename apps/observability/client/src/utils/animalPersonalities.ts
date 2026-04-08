/**
 * Animal personality traits for varied movement and behavior
 */

export interface AnimalPersonality {
  walkSpeed: number;
  walkStyle: 'normal' | 'hop' | 'waddle' | 'strut' | 'scurry' | 'lumber';
  bobIntensity: number;
  energyLevel: 'calm' | 'moderate' | 'hyper';
}

export const ANIMAL_PERSONALITIES: Record<string, AnimalPersonality> = {
  // Fast, energetic animals
  rabbit: {
    walkSpeed: 3.5,
    walkStyle: 'hop',
    bobIntensity: 0.25,
    energyLevel: 'hyper'
  },
  squirrel: {
    walkSpeed: 3.2,
    walkStyle: 'scurry',
    bobIntensity: 0.2,
    energyLevel: 'hyper'
  },
  mouse: {
    walkSpeed: 3.0,
    walkStyle: 'scurry',
    bobIntensity: 0.15,
    energyLevel: 'hyper'
  },

  // Medium speed animals
  cat: {
    walkSpeed: 2.3,
    walkStyle: 'strut',
    bobIntensity: 0.12,
    energyLevel: 'moderate'
  },
  fox: {
    walkSpeed: 2.5,
    walkStyle: 'strut',
    bobIntensity: 0.15,
    energyLevel: 'moderate'
  },
  raccoon: {
    walkSpeed: 2.2,
    walkStyle: 'waddle',
    bobIntensity: 0.18,
    energyLevel: 'moderate'
  },
  dog: {
    walkSpeed: 2.4,
    walkStyle: 'normal',
    bobIntensity: 0.15,
    energyLevel: 'moderate'
  },
  beaver: {
    walkSpeed: 1.8,
    walkStyle: 'waddle',
    bobIntensity: 0.2,
    energyLevel: 'moderate'
  },

  // Slow, steady animals
  bear: {
    walkSpeed: 1.6,
    walkStyle: 'lumber',
    bobIntensity: 0.22,
    energyLevel: 'calm'
  },
  penguin: {
    walkSpeed: 1.4,
    walkStyle: 'waddle',
    bobIntensity: 0.25,
    energyLevel: 'calm'
  },
  turtle: {
    walkSpeed: 1.2,
    walkStyle: 'lumber',
    bobIntensity: 0.1,
    energyLevel: 'calm'
  },
  pig: {
    walkSpeed: 1.7,
    walkStyle: 'waddle',
    bobIntensity: 0.18,
    energyLevel: 'calm'
  },
  koala: {
    walkSpeed: 1.5,
    walkStyle: 'lumber',
    bobIntensity: 0.12,
    energyLevel: 'calm'
  },

  // Flying/magical (medium-fast but smooth)
  owl: {
    walkSpeed: 2.0,
    walkStyle: 'normal',
    bobIntensity: 0.08,
    energyLevel: 'calm'
  },
  dragon: {
    walkSpeed: 2.2,
    walkStyle: 'strut',
    bobIntensity: 0.1,
    energyLevel: 'moderate'
  }
};

export function getWalkSpeed(animalType: string): number {
  const personality = ANIMAL_PERSONALITIES[animalType.toLowerCase()];
  return personality ? personality.walkSpeed : 2.0;
}

export function getBobIntensity(animalType: string): number {
  const personality = ANIMAL_PERSONALITIES[animalType.toLowerCase()];
  return personality ? personality.bobIntensity : 0.15;
}

export function getWalkStyle(animalType: string): string {
  const personality = ANIMAL_PERSONALITIES[animalType.toLowerCase()];
  return personality ? personality.walkStyle : 'normal';
}
