<template>
  <div class="game-logs-container">
    <!-- Quest Log Panel -->
    <div class="quest-log-panel">
      <!-- Parchment Header -->
      <div class="quest-header">
        <div class="header-decoration left"></div>
        <h2 class="quest-title">
          <span class="quest-icon">📜</span>
          Quest Log
          <span class="quest-icon">✨</span>
        </h2>
        <div class="header-decoration right"></div>
      </div>

      <!-- Log Entries Container -->
      <div class="logs-scroll-area">
        <TransitionGroup name="log-entry" tag="div" class="logs-list">
          <div
            v-for="(entry, index) in visibleLogs"
            :key="entry.id || `${entry.session_id}-${entry.timestamp}-${index}`"
            class="log-entry"
            :class="getLogEntryClass(entry)"
            :style="getLogEntryStyle(entry)"
          >
            <!-- Speech Bubble -->
            <div class="speech-bubble" :style="getSpeechBubbleStyle(entry)">
              <div class="bubble-content">
                <!-- Animal Emoji Avatar -->
                <div class="avatar">
                  {{ getAnimalEmoji(entry) }}
                </div>

                <!-- Log Content -->
                <div class="log-content">
                  <div class="log-header">
                    <span class="agent-name" :style="getAgentNameStyle(entry)">
                      {{ getAgentName(entry) }}
                    </span>
                    <span class="timestamp">{{ formatTime(entry.timestamp) }}</span>
                  </div>
                  <div class="log-action">
                    {{ getActionText(entry) }}
                  </div>
                </div>
              </div>

              <!-- Speech Bubble Tail -->
              <div class="bubble-tail" :style="getBubbleTailStyle(entry)"></div>
            </div>
          </div>
        </TransitionGroup>

        <!-- Empty State -->
        <div v-if="visibleLogs.length === 0" class="empty-state">
          <div class="empty-icon">🌙</div>
          <p class="empty-text">No recent quests...</p>
          <p class="empty-subtext">Waiting for adventures to begin!</p>
        </div>
      </div>

      <!-- Parchment Footer -->
      <div class="quest-footer">
        <div class="footer-decoration"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { HookEvent } from '../types';
import { useEventColors } from '../composables/useEventColors';
import { useEventEmojis } from '../composables/useEventEmojis';

interface Props {
  events: HookEvent[];
  maxVisible?: number;
}

const props = withDefaults(defineProps<Props>(), {
  maxVisible: 10,
});

const { getColorForSession, getHexColorForSession } = useEventColors();
const { getEmojiForEventType, getEmojiForToolName } = useEventEmojis();

// Animal emojis for different event types
const animalEmojiMap: Record<string, string> = {
  'SessionStart': '🦊',
  'SessionEnd': '🦉',
  'PreToolUse': '🐻',
  'PostToolUse': '🐰',
  'PostToolUseFailure': '🐼',
  'SubagentStart': '🐱',
  'SubagentStop': '🐶',
  'UserPromptSubmit': '🐸',
  'PermissionRequest': '🦝',
  'Notification': '🐦',
  'Stop': '🐢',
  'PreCompact': '🐿️',
  'default': '🐹',
};

// Keep track of visible logs with fade-out timer
const visibleLogs = computed(() => {
  // Take the most recent events
  const recent = [...props.events]
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
    .slice(0, props.maxVisible);

  return recent;
});

const getAnimalEmoji = (event: HookEvent): string => {
  return animalEmojiMap[event.hook_event_type] || animalEmojiMap.default;
};

const getAgentName = (event: HookEvent): string => {
  // Extract agent name from source_app or use source_app directly
  const name = event.source_app || 'Unknown Agent';
  return name.length > 20 ? name.substring(0, 20) + '...' : name;
};

const getActionText = (event: HookEvent): string => {
  const eventType = event.hook_event_type;
  const emoji = getEmojiForEventType(eventType);

  // Get tool name if available
  const toolName = event.payload?.tool_name;
  const toolEmoji = toolName ? getEmojiForToolName(toolName) : '';

  // Create friendly action text
  switch (eventType) {
    case 'SessionStart':
      return `${emoji} Started a new session`;
    case 'SessionEnd':
      return `${emoji} Session ended`;
    case 'PreToolUse':
      return toolName ? `${emoji}${toolEmoji} Using ${toolName}` : `${emoji} Using a tool`;
    case 'PostToolUse':
      return toolName ? `${emoji} Completed ${toolName}` : `${emoji} Tool completed`;
    case 'PostToolUseFailure':
      return toolName ? `${emoji} ${toolName} failed` : `${emoji} Tool failed`;
    case 'SubagentStart':
      return `${emoji} Summoned helper`;
    case 'SubagentStop':
      return `${emoji} Helper finished`;
    case 'UserPromptSubmit':
      return `${emoji} Received message`;
    case 'PermissionRequest':
      return `${emoji} Requesting permission`;
    case 'Notification':
      return `${emoji} ${event.summary || 'Notification'}`;
    case 'Stop':
      return `${emoji} Task complete`;
    case 'PreCompact':
      return `${emoji} Organizing thoughts`;
    default:
      return `${emoji} ${eventType}`;
  }
};

const formatTime = (timestamp?: number): string => {
  if (!timestamp) return '';

  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 1000) return 'just now';
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

  return new Date(timestamp).toLocaleTimeString();
};

const getLogEntryClass = (event: HookEvent): string => {
  const classes = [];

  // Add priority class for important events
  if (['SessionStart', 'SessionEnd', 'PermissionRequest'].includes(event.hook_event_type)) {
    classes.push('priority-high');
  }

  return classes.join(' ');
};

const getLogEntryStyle = (event: HookEvent) => {
  return {
    '--entry-delay': `${Math.random() * 0.3}s`,
  };
};

const getSpeechBubbleStyle = (event: HookEvent) => {
  const hexColor = getHexColorForSession(event.session_id);

  return {
    '--bubble-color': hexColor,
    '--bubble-shadow': `${hexColor}40`,
  };
};

const getBubbleTailStyle = (event: HookEvent) => {
  const hexColor = getHexColorForSession(event.session_id);

  return {
    borderTopColor: hexColor,
  };
};

const getAgentNameStyle = (event: HookEvent) => {
  const hexColor = getHexColorForSession(event.session_id);

  return {
    color: hexColor,
  };
};
</script>

<style scoped>
.game-logs-container {
  width: 100%;
  height: 100%;
  padding: 1rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.quest-log-panel {
  width: 100%;
  max-width: 800px;
  background: linear-gradient(135deg, #fef5e7 0%, #f9e4c8 100%);
  border-radius: 20px;
  box-shadow:
    0 10px 40px rgba(139, 90, 43, 0.3),
    inset 0 2px 4px rgba(255, 255, 255, 0.8),
    inset 0 -2px 4px rgba(139, 90, 43, 0.2);
  border: 4px solid #d4a574;
  position: relative;
  overflow: hidden;
}

/* Parchment texture effect */
.quest-log-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(139, 90, 43, 0.03) 2px,
      rgba(139, 90, 43, 0.03) 4px
    );
  pointer-events: none;
  opacity: 0.5;
}

.quest-header {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 2rem 1rem 2rem;
  position: relative;
  border-bottom: 3px solid #d4a574;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.5) 0%, transparent 100%);
}

.header-decoration {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, transparent, #d4a574, transparent);
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.header-decoration.left {
  left: 1rem;
}

.header-decoration.right {
  right: 1rem;
}

.quest-title {
  font-family: 'Georgia', 'Palatino', serif;
  font-size: 1.75rem;
  font-weight: 700;
  color: #8b5a2b;
  text-shadow:
    0 1px 0 rgba(255, 255, 255, 0.8),
    0 2px 4px rgba(139, 90, 43, 0.3);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  letter-spacing: 0.5px;
}

.quest-icon {
  font-size: 1.5rem;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-5px);
  }
}

.logs-scroll-area {
  padding: 1.5rem;
  max-height: 600px;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

/* Custom scrollbar */
.logs-scroll-area::-webkit-scrollbar {
  width: 8px;
}

.logs-scroll-area::-webkit-scrollbar-track {
  background: rgba(212, 165, 116, 0.2);
  border-radius: 4px;
}

.logs-scroll-area::-webkit-scrollbar-thumb {
  background: #d4a574;
  border-radius: 4px;
}

.logs-scroll-area::-webkit-scrollbar-thumb:hover {
  background: #c49563;
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.log-entry {
  animation: slideIn 0.5s ease-out var(--entry-delay, 0s) both;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* TransitionGroup animations */
.log-entry-enter-active {
  animation: slideIn 0.5s ease-out;
}

.log-entry-leave-active {
  animation: fadeOut 0.4s ease-in;
}

.log-entry-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

@keyframes fadeOut {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(-20px);
  }
}

.speech-bubble {
  background: white;
  border-radius: 16px;
  padding: 1rem 1.25rem;
  box-shadow:
    0 4px 12px var(--bubble-shadow, rgba(0, 0, 0, 0.15)),
    0 0 0 3px var(--bubble-color, #3B82F6);
  position: relative;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.speech-bubble:hover {
  transform: translateY(-2px);
  box-shadow:
    0 6px 16px var(--bubble-shadow, rgba(0, 0, 0, 0.2)),
    0 0 0 3px var(--bubble-color, #3B82F6);
}

.bubble-tail {
  position: absolute;
  left: 2rem;
  bottom: -8px;
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid var(--bubble-color, #3B82F6);
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.1));
}

.bubble-content {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.avatar {
  font-size: 2rem;
  line-height: 1;
  flex-shrink: 0;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

.log-content {
  flex: 1;
  min-width: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  gap: 0.5rem;
}

.agent-name {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--bubble-color, #3B82F6);
  font-family: 'Georgia', serif;
  letter-spacing: 0.3px;
}

.timestamp {
  font-size: 0.75rem;
  color: #9ca3af;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.log-action {
  font-size: 0.9rem;
  color: #4b5563;
  line-height: 1.4;
  word-wrap: break-word;
}

.priority-high .speech-bubble {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow:
      0 4px 12px var(--bubble-shadow, rgba(0, 0, 0, 0.15)),
      0 0 0 3px var(--bubble-color, #3B82F6);
  }
  50% {
    box-shadow:
      0 4px 16px var(--bubble-shadow, rgba(0, 0, 0, 0.25)),
      0 0 0 5px var(--bubble-color, #3B82F6),
      0 0 20px var(--bubble-shadow, rgba(0, 0, 0, 0.1));
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.7;
  animation: float 3s ease-in-out infinite;
}

.empty-text {
  font-family: 'Georgia', serif;
  font-size: 1.25rem;
  font-weight: 600;
  color: #8b5a2b;
  margin-bottom: 0.5rem;
}

.empty-subtext {
  font-size: 0.95rem;
  color: #a0826d;
  font-style: italic;
}

.quest-footer {
  padding: 1rem 2rem;
  border-top: 3px solid #d4a574;
  background: linear-gradient(0deg, rgba(255, 255, 255, 0.5) 0%, transparent 100%);
  display: flex;
  justify-content: center;
}

.footer-decoration {
  width: 100px;
  height: 3px;
  background: linear-gradient(90deg, transparent, #d4a574, transparent);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .quest-log-panel {
    background: linear-gradient(135deg, #3a2f28 0%, #2d231d 100%);
    border-color: #6b5742;
  }

  .quest-title {
    color: #d4a574;
    text-shadow:
      0 1px 0 rgba(0, 0, 0, 0.5),
      0 2px 4px rgba(212, 165, 116, 0.3);
  }

  .quest-header {
    border-bottom-color: #6b5742;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.3) 0%, transparent 100%);
  }

  .quest-footer {
    border-top-color: #6b5742;
    background: linear-gradient(0deg, rgba(0, 0, 0, 0.3) 0%, transparent 100%);
  }

  .header-decoration,
  .footer-decoration {
    background: linear-gradient(90deg, transparent, #6b5742, transparent);
  }

  .speech-bubble {
    background: #2d231d;
    color: #e8dcc8;
  }

  .log-action {
    color: #c4b5a0;
  }

  .timestamp {
    color: #8b7355;
  }

  .empty-text {
    color: #d4a574;
  }

  .empty-subtext {
    color: #a0826d;
  }

  .logs-scroll-area::-webkit-scrollbar-track {
    background: rgba(107, 87, 66, 0.2);
  }

  .logs-scroll-area::-webkit-scrollbar-thumb {
    background: #6b5742;
  }

  .logs-scroll-area::-webkit-scrollbar-thumb:hover {
    background: #8b7355;
  }
}
</style>
