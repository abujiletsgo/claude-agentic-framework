/**
 * Animal Mapping Configuration
 *
 * Cute and whimsical mappings for agents to animals and tools to 3D objects.
 * Organized by model tier (Opus/Sonnet/Haiku) with consistent color schemes.
 */

// ============================================================================
// Type Definitions
// ============================================================================

export interface AnimalConfig {
  animal: string;
  emoji: string;
  color: string;
  gradient: string;
  hexColor: string;
  tier: 'opus' | 'sonnet' | 'haiku';
  description: string;
}

export interface ToolConfig {
  object: string;
  emoji: string;
  color: string;
  description: string;
}

export interface ColorScheme {
  primary: string;
  secondary: string;
  gradient: string;
  hex: string;
}

// ============================================================================
// Agent to Animal Mapping (All 33 Agents)
// ============================================================================

export const AGENT_ANIMAL_MAP: Record<string, AnimalConfig> = {
  // -------------------------------------------------------------------------
  // OPUS TIER - Wise and Powerful Animals (12% of agents)
  // -------------------------------------------------------------------------

  // Root Agents
  'orchestrator': {
    animal: 'owl',
    emoji: '🦉',
    color: 'bg-indigo-500',
    gradient: 'from-indigo-500 to-indigo-600',
    hexColor: '#6366F1',
    tier: 'opus',
    description: 'Wise orchestrator who sees the big picture'
  },

  'project-architect': {
    animal: 'dragon',
    emoji: '🐉',
    color: 'bg-purple-500',
    gradient: 'from-purple-500 to-purple-600',
    hexColor: '#A855F7',
    tier: 'opus',
    description: 'Powerful architect who designs grand systems'
  },

  'critical-analyst': {
    animal: 'phoenix',
    emoji: '🔥',
    color: 'bg-orange-500',
    gradient: 'from-orange-500 to-orange-600',
    hexColor: '#F97316',
    tier: 'opus',
    description: 'Critical thinker who rises from ashes with insights'
  },

  'rlm-root': {
    animal: 'fox',
    emoji: '🦊',
    color: 'bg-red-500',
    gradient: 'from-red-500 to-red-600',
    hexColor: '#EF4444',
    tier: 'opus',
    description: 'Clever fox who adapts and iterates'
  },

  // -------------------------------------------------------------------------
  // SONNET TIER - Busy and Productive Animals (50% of agents)
  // -------------------------------------------------------------------------

  // Team Agents
  'builder': {
    animal: 'beaver',
    emoji: '🦫',
    color: 'bg-amber-600',
    gradient: 'from-amber-600 to-amber-700',
    hexColor: '#D97706',
    tier: 'sonnet',
    description: 'Industrious builder who constructs with care'
  },

  'project-skill-generator': {
    animal: 'cat',
    emoji: '🐱',
    color: 'bg-pink-500',
    gradient: 'from-pink-500 to-pink-600',
    hexColor: '#EC4899',
    tier: 'sonnet',
    description: 'Clever cat who crafts custom tools'
  },

  'caddy-assistant': {
    animal: 'dog',
    emoji: '🐕',
    color: 'bg-yellow-600',
    gradient: 'from-yellow-600 to-yellow-700',
    hexColor: '#CA8A04',
    tier: 'sonnet',
    description: 'Loyal assistant who supports and helps'
  },

  // Root Agents (Sonnet)
  'researcher': {
    animal: 'raccoon',
    emoji: '🦝',
    color: 'bg-slate-600',
    gradient: 'from-slate-600 to-slate-700',
    hexColor: '#475569',
    tier: 'sonnet',
    description: 'Curious raccoon who digs through information'
  },

  'meta-agent': {
    animal: 'squirrel',
    emoji: '🐿️',
    color: 'bg-orange-600',
    gradient: 'from-orange-600 to-orange-700',
    hexColor: '#EA580C',
    tier: 'sonnet',
    description: 'Busy squirrel who organizes and coordinates'
  },

  'debug-agent': {
    animal: 'otter',
    emoji: '🦦',
    color: 'bg-cyan-600',
    gradient: 'from-cyan-600 to-cyan-700',
    hexColor: '#0891B2',
    tier: 'sonnet',
    description: 'Playful otter who finds issues in the flow'
  },

  'refiner': {
    animal: 'panda',
    emoji: '🐼',
    color: 'bg-gray-600',
    gradient: 'from-gray-600 to-gray-700',
    hexColor: '#4B5563',
    tier: 'sonnet',
    description: 'Careful panda who polishes and perfects'
  },

  'rlm-worker': {
    animal: 'wolf',
    emoji: '🐺',
    color: 'bg-slate-700',
    gradient: 'from-slate-700 to-slate-800',
    hexColor: '#334155',
    tier: 'sonnet',
    description: 'Persistent wolf who iterates until success'
  },

  'fusion-coordinator': {
    animal: 'parrot',
    emoji: '🦜',
    color: 'bg-green-600',
    gradient: 'from-green-600 to-green-700',
    hexColor: '#16A34A',
    tier: 'sonnet',
    description: 'Colorful parrot who harmonizes multiple voices'
  },

  'fusion-synthesizer': {
    animal: 'peacock',
    emoji: '🦚',
    color: 'bg-teal-600',
    gradient: 'from-teal-600 to-teal-700',
    hexColor: '#0D9488',
    tier: 'sonnet',
    description: 'Elegant peacock who combines ideas beautifully'
  },

  'plan-agent': {
    animal: 'elephant',
    emoji: '🐘',
    color: 'bg-blue-600',
    gradient: 'from-blue-600 to-blue-700',
    hexColor: '#2563EB',
    tier: 'sonnet',
    description: 'Thoughtful elephant who never forgets the plan'
  },

  'sentient-agent': {
    animal: 'dolphin',
    emoji: '🐬',
    color: 'bg-sky-500',
    gradient: 'from-sky-500 to-sky-600',
    hexColor: '#0EA5E9',
    tier: 'sonnet',
    description: 'Intelligent dolphin with deep reasoning'
  },

  'question-agent': {
    animal: 'lemur',
    emoji: '🐒',
    color: 'bg-violet-500',
    gradient: 'from-violet-500 to-violet-600',
    hexColor: '#8B5CF6',
    tier: 'sonnet',
    description: 'Inquisitive lemur who asks all the questions'
  },

  'fusion-worker': {
    animal: 'hamster',
    emoji: '🐹',
    color: 'bg-rose-500',
    gradient: 'from-rose-500 to-rose-600',
    hexColor: '#F43F5E',
    tier: 'sonnet',
    description: 'Energetic hamster who works in parallel'
  },

  'code-review-agent': {
    animal: 'meerkat',
    emoji: '🦡',
    color: 'bg-amber-500',
    gradient: 'from-amber-500 to-amber-600',
    hexColor: '#F59E0B',
    tier: 'sonnet',
    description: 'Watchful meerkat who guards code quality'
  },

  'general-purpose': {
    animal: 'bear',
    emoji: '🐻',
    color: 'bg-brown-600',
    gradient: 'from-stone-600 to-stone-700',
    hexColor: '#57534E',
    tier: 'sonnet',
    description: 'Versatile bear who handles any task'
  },

  // -------------------------------------------------------------------------
  // HAIKU TIER - Quick and Small Animals (38% of agents)
  // -------------------------------------------------------------------------

  // Team Agents
  'validator': {
    animal: 'rabbit',
    emoji: '🐰',
    color: 'bg-emerald-500',
    gradient: 'from-emerald-500 to-emerald-600',
    hexColor: '#10B981',
    tier: 'haiku',
    description: 'Quick rabbit who verifies everything'
  },

  // Root Agents (Haiku)
  'docs-scraper': {
    animal: 'mouse',
    emoji: '🐭',
    color: 'bg-gray-500',
    gradient: 'from-gray-500 to-gray-600',
    hexColor: '#6B7280',
    tier: 'haiku',
    description: 'Nimble mouse who gathers documentation'
  },

  'hello-world': {
    animal: 'bird',
    emoji: '🐦',
    color: 'bg-sky-400',
    gradient: 'from-sky-400 to-sky-500',
    hexColor: '#38BDF8',
    tier: 'haiku',
    description: 'Cheerful bird who greets and explores'
  },

  'create-worktree-subagent': {
    animal: 'bee',
    emoji: '🐝',
    color: 'bg-yellow-500',
    gradient: 'from-yellow-500 to-yellow-600',
    hexColor: '#EAB308',
    tier: 'haiku',
    description: 'Busy bee who creates new workspaces'
  },

  'context-manager': {
    animal: 'chipmunk',
    emoji: '🐿️',
    color: 'bg-orange-400',
    gradient: 'from-orange-400 to-orange-500',
    hexColor: '#FB923C',
    tier: 'haiku',
    description: 'Organized chipmunk who manages context'
  },

  // Guardrail Agents (all Haiku)
  'context-guardrail': {
    animal: 'sparrow',
    emoji: '🦜',
    color: 'bg-lime-500',
    gradient: 'from-lime-500 to-lime-600',
    hexColor: '#84CC16',
    tier: 'haiku',
    description: 'Alert sparrow who watches context limits'
  },

  'lthread-progress-checker': {
    animal: 'hummingbird',
    emoji: '🐦',
    color: 'bg-fuchsia-500',
    gradient: 'from-fuchsia-500 to-fuchsia-600',
    hexColor: '#D946EF',
    tier: 'haiku',
    description: 'Swift hummingbird who monitors progress'
  },

  'tool-use-guardian': {
    animal: 'gecko',
    emoji: '🦎',
    color: 'bg-green-500',
    gradient: 'from-green-500 to-green-600',
    hexColor: '#22C55E',
    tier: 'haiku',
    description: 'Vigilant gecko who oversees tool usage'
  },

  'token-guardian': {
    animal: 'ant',
    emoji: '🐜',
    color: 'bg-red-400',
    gradient: 'from-red-400 to-red-500',
    hexColor: '#F87171',
    tier: 'haiku',
    description: 'Careful ant who counts every token'
  },

  'error-analyzer': {
    animal: 'ladybug',
    emoji: '🐞',
    color: 'bg-red-500',
    gradient: 'from-red-500 to-red-600',
    hexColor: '#EF4444',
    tier: 'haiku',
    description: 'Helpful ladybug who debugs errors'
  },

  'permission-checker': {
    animal: 'turtle',
    emoji: '🐢',
    color: 'bg-teal-500',
    gradient: 'from-teal-500 to-teal-600',
    hexColor: '#14B8A6',
    tier: 'haiku',
    description: 'Cautious turtle who verifies permissions'
  },

  'skill-integrity-verifier': {
    animal: 'butterfly',
    emoji: '🦋',
    color: 'bg-purple-400',
    gradient: 'from-purple-400 to-purple-500',
    hexColor: '#C084FC',
    tier: 'haiku',
    description: 'Delicate butterfly who checks skill integrity'
  },

  'loop-detector': {
    animal: 'snail',
    emoji: '🐌',
    color: 'bg-amber-400',
    gradient: 'from-amber-400 to-amber-500',
    hexColor: '#FBBF24',
    tier: 'haiku',
    description: 'Observant snail who detects infinite loops'
  },
};

// ============================================================================
// Tool to 3D Object Mapping
// ============================================================================

export const TOOL_OBJECT_MAP: Record<string, ToolConfig> = {
  // Core Tools
  'Bash': {
    object: 'terminal',
    emoji: '💻',
    color: 'bg-slate-700',
    description: 'Terminal screen with glowing green text'
  },

  'Read': {
    object: 'book',
    emoji: '📖',
    color: 'bg-blue-600',
    description: 'Open book with flipping pages'
  },

  'Write': {
    object: 'pencil',
    emoji: '✏️',
    color: 'bg-yellow-500',
    description: 'Animated pencil writing on paper'
  },

  'Edit': {
    object: 'eraser',
    emoji: '🖍️',
    color: 'bg-pink-500',
    description: 'Eraser with editing marks'
  },

  'Glob': {
    object: 'magnifying-glass',
    emoji: '🔍',
    color: 'bg-purple-500',
    description: 'Magnifying glass searching files'
  },

  'Grep': {
    object: 'telescope',
    emoji: '🔭',
    color: 'bg-indigo-500',
    description: 'Telescope finding text patterns'
  },

  'WebSearch': {
    object: 'globe',
    emoji: '🌐',
    color: 'bg-blue-500',
    description: 'Spinning globe with search beam'
  },

  'WebFetch': {
    object: 'satellite',
    emoji: '📡',
    color: 'bg-cyan-500',
    description: 'Satellite dish fetching data'
  },

  // Skill Tools
  'code-review': {
    object: 'magnifying-glass',
    emoji: '🔎',
    color: 'bg-amber-600',
    description: 'Magnifying glass inspecting code'
  },

  'build': {
    object: 'hammer',
    emoji: '🔨',
    color: 'bg-orange-600',
    description: 'Hammer building and constructing'
  },

  'test': {
    object: 'flask',
    emoji: '🧪',
    color: 'bg-green-600',
    description: 'Science flask with bubbling liquid'
  },

  'refactor': {
    object: 'wrench',
    emoji: '🔧',
    color: 'bg-gray-600',
    description: 'Wrench adjusting and fixing'
  },

  'debug': {
    object: 'flashlight',
    emoji: '🔦',
    color: 'bg-yellow-600',
    description: 'Flashlight illuminating bugs'
  },

  'security-scan': {
    object: 'shield',
    emoji: '🛡️',
    color: 'bg-red-600',
    description: 'Shield protecting code'
  },

  'deploy': {
    object: 'rocket',
    emoji: '🚀',
    color: 'bg-purple-600',
    description: 'Rocket launching to production'
  },

  'git': {
    object: 'tree',
    emoji: '🌳',
    color: 'bg-green-700',
    description: 'Git tree with branches'
  },

  'database': {
    object: 'filing-cabinet',
    emoji: '🗄️',
    color: 'bg-blue-700',
    description: 'Filing cabinet with data drawers'
  },

  'api': {
    object: 'plug',
    emoji: '🔌',
    color: 'bg-teal-600',
    description: 'Power plug connecting services'
  },

  'documentation': {
    object: 'scroll',
    emoji: '📜',
    color: 'bg-amber-700',
    description: 'Ancient scroll with documentation'
  },

  'package': {
    object: 'box',
    emoji: '📦',
    color: 'bg-brown-600',
    description: 'Cardboard box with package'
  },

  'lint': {
    object: 'broom',
    emoji: '🧹',
    color: 'bg-lime-600',
    description: 'Broom sweeping up code issues'
  },

  'benchmark': {
    object: 'stopwatch',
    emoji: '⏱️',
    color: 'bg-red-500',
    description: 'Stopwatch measuring performance'
  },

  'monitor': {
    object: 'radar',
    emoji: '📊',
    color: 'bg-green-500',
    description: 'Radar screen monitoring systems'
  },
};

// ============================================================================
// Color Utilities
// ============================================================================

/**
 * Get color scheme for an animal
 */
export function getAnimalColorScheme(agentName: string): ColorScheme {
  // Try exact match first
  let config = AGENT_ANIMAL_MAP[agentName];

  // Try removing instance number (e.g., "builder-2" -> "builder")
  if (!config) {
    const baseAgentName = agentName.replace(/-\d+$/, '');
    config = AGENT_ANIMAL_MAP[baseAgentName];
  }

  if (!config) {
    return {
      primary: 'bg-gray-500',
      secondary: 'bg-gray-600',
      gradient: 'from-gray-500 to-gray-600',
      hex: '#6B7280'
    };
  }

  return {
    primary: config.color,
    secondary: config.color.replace('-500', '-600').replace('-400', '-500').replace('-600', '-700'),
    gradient: config.gradient,
    hex: config.hexColor
  };
}

/**
 * Get all agents by tier
 */
export function getAgentsByTier(tier: 'opus' | 'sonnet' | 'haiku'): string[] {
  return Object.entries(AGENT_ANIMAL_MAP)
    .filter(([_, config]) => config.tier === tier)
    .map(([agentName, _]) => agentName);
}

/**
 * Get tier statistics
 */
export function getTierStats(): Record<string, number> {
  const stats = {
    opus: 0,
    sonnet: 0,
    haiku: 0,
    total: 0
  };

  Object.values(AGENT_ANIMAL_MAP).forEach(config => {
    stats[config.tier]++;
    stats.total++;
  });

  return stats;
}

/**
 * Get animal config for agent
 * Returns a default beaver config for unknown agents so all agents appear
 */
export function getAgentAnimal(agentName: string): AnimalConfig | null {
  // Try exact match first
  if (AGENT_ANIMAL_MAP[agentName]) {
    return AGENT_ANIMAL_MAP[agentName];
  }

  // Try removing instance number (e.g., "builder-2" -> "builder")
  const baseAgentName = agentName.replace(/-\d+$/, '');
  if (AGENT_ANIMAL_MAP[baseAgentName]) {
    return AGENT_ANIMAL_MAP[baseAgentName];
  }

  // Fallback: return a default beaver config for unknown agents
  return {
    animal: 'beaver',
    emoji: '🦫',
    color: 'bg-amber-500',
    gradient: 'from-amber-500 to-amber-600',
    hexColor: '#F59E0B',
    tier: 'sonnet',
    description: 'Busy worker'
  };
}

/**
 * Get tool object config
 */
export function getToolObject(toolName: string): ToolConfig | null {
  return TOOL_OBJECT_MAP[toolName] || null;
}

/**
 * Check if agent exists
 */
export function isValidAgent(agentName: string): boolean {
  return agentName in AGENT_ANIMAL_MAP;
}

/**
 * Check if tool exists
 */
export function isValidTool(toolName: string): boolean {
  return toolName in TOOL_OBJECT_MAP;
}

/**
 * Get random animal from tier
 */
export function getRandomAnimalFromTier(tier: 'opus' | 'sonnet' | 'haiku'): AnimalConfig {
  const agents = getAgentsByTier(tier);
  const randomAgent = agents[Math.floor(Math.random() * agents.length)];
  return AGENT_ANIMAL_MAP[randomAgent];
}

// ============================================================================
// Export All
// ============================================================================

export default {
  AGENT_ANIMAL_MAP,
  TOOL_OBJECT_MAP,
  getAnimalColorScheme,
  getAgentsByTier,
  getTierStats,
  getAgentAnimal,
  getToolObject,
  isValidAgent,
  isValidTool,
  getRandomAnimalFromTier
};
