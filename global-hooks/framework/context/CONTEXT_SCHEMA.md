# Rolling Context Manager - Schema Documentation

**Version**: 1.0
**Purpose**: Consistent multi-tier memory system for proactive context management

---

## Overview

The rolling context manager prevents context overflow by proactively compressing "cold" segments (completed tasks, old topics) before hitting limits.

**3-Tier Architecture**:
- **L1 (Hot)**: Raw conversation, active topics (0-60% context)
- **L2 (Warm)**: Compressed segments in knowledge-db (searchable, persistent)
- **L3 (Cold)**: Archived session logs (pruned after 30 days)

---

## Triggers

| Condition | Action | Tier |
|-----------|--------|------|
| Context > 60% + cold segments exist | Queue for compression | L1 → L2 |
| Context > 80% + very old segments | Archive to cold storage | L2 → L3 |
| Archive age > 30 days | Prune (keep summary only) | L3 → DELETE |

**Cold Segment Definition**:
- Not mentioned in 20+ turns
- Task marked as completed
- Has substantial content (5+ messages)

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ L1: Hot Context (Raw Conversation)                          │
│ - Active topics, ongoing tasks                              │
│ - 0-60% context usage                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │ Every 10 turns: Check for cold segments
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Compression Queue                                            │
│ .claude/data/context_queue/{session_id}_pending.json        │
│ - segment_id, topic, turn range, message count              │
└─────────────────┬───────────────────────────────────────────┘
                  │ Claude sees system reminder
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Claude Compresses Segments                                   │
│ - Read queued segments from conversation history            │
│ - Compress intelligently (preserve key decisions/outcomes)  │
│ - Save to L2 storage                                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ L2: Warm Storage (Knowledge DB)                             │
│ data/knowledge-db/compressed_context/                       │
│ - Compressed segments with metadata                         │
│ - Searchable via knowledge-db skill                         │
│ - Preserved indefinitely (until archived to L3)             │
└─────────────────┬───────────────────────────────────────────┘
                  │ Context > 80% + segment age > 50 turns
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ L3: Cold Storage (Session Archives)                         │
│ .claude/data/sessions/{session_id}/archived_context/        │
│ - Very old compressed segments                              │
│ - Rarely accessed, pruned after 30 days                     │
└─────────────────────────────────────────────────────────────┘
```

---

## File Formats

### Compression Queue Format

**Location**: `.claude/data/context_queue/{session_id}_pending.json`

```json
{
  "pending": [
    {
      "segment_id": "seg_42_0",
      "topic": "Implement OAuth2 authentication",
      "start_turn": 15,
      "end_turn": 35,
      "message_count": 12,
      "turns_since_mention": 25,
      "queued_at_turn": 60,
      "timestamp": "2026-02-16T15:30:00"
    }
  ],
  "compressed": [
    {
      "segment_id": "seg_42_0",
      "topic": "Implement OAuth2 authentication",
      "compressed_at_turn": 65,
      "original_tokens": 2400,
      "compressed_tokens": 380,
      "compression_ratio": 6.3,
      "storage_location": "data/knowledge-db/compressed_context/seg_42_0.json",
      "timestamp": "2026-02-16T15:32:00"
    }
  ],
  "last_check_turn": 60
}
```

---

### L2 Storage Format (Knowledge DB)

**Location**: `data/knowledge-db/compressed_context/{segment_id}.json`

```json
{
  "segment_id": "seg_42_0",
  "topic": "Implement OAuth2 authentication",
  "session_id": "abc-123-def-456",
  "start_turn": 15,
  "end_turn": 35,
  "original_tokens": 2400,
  "compressed_tokens": 380,
  "compression_ratio": 6.3,
  "compressed_at": "2026-02-16T15:32:00",
  "last_accessed": "2026-02-16T15:32:00",
  "access_count": 0,
  "relevance_score": 0.85,
  "compressed_content": "Implemented OAuth2 authentication system with...",
  "key_decisions": [
    "Used JWT tokens with 1-hour expiry",
    "Stored refresh tokens in httpOnly cookies",
    "Implemented PKCE flow for public clients"
  ],
  "key_files": [
    "src/auth/oauth2.ts",
    "src/middleware/auth.ts"
  ],
  "metadata": {
    "contains_code": true,
    "contains_errors": false,
    "task_completed": true
  }
}
```

---

### L3 Archive Format

**Location**: `.claude/data/sessions/{session_id}/archived_context/{segment_id}.json`

Same format as L2, but:
- Only accessed if explicitly searched
- Pruned after 30 days (keeps only `compressed_content` summary)

---

## Compression Guidelines (for Claude)

When you see a system reminder about pending compression:

### 1. Read Pending Queue

```bash
cat ~/.claude/data/context_queue/{session_id}_pending.json
```

### 2. Extract Segments from Conversation

For each pending segment:
- Locate messages in turn range (start_turn → end_turn)
- Read full context of that segment

### 3. Compress Intelligently

**Preserve**:
- ✅ Key decisions made
- ✅ Important file paths/changes
- ✅ Error resolutions
- ✅ Critical outcomes
- ✅ User preferences stated

**Discard**:
- ❌ Verbose tool outputs
- ❌ Intermediate debugging steps
- ❌ Repetitive back-and-forth
- ❌ Boilerplate responses

**Target**: 80-90% token reduction (2,400 tokens → 300-400 tokens)

### 4. Save to L2 Storage

```json
{
  "segment_id": "{from queue}",
  "topic": "{from queue}",
  "compressed_content": "{your intelligent summary}",
  "key_decisions": ["{bullet points}"],
  "key_files": ["{files modified}"],
  ...
}
```

Save to: `data/knowledge-db/compressed_context/{segment_id}.json`

### 5. Update Queue

Move segment from `pending` to `compressed` in queue file.

### 6. Report

```
✅ Compressed 3 segments (6,200 tokens → 980 tokens)
Saved to knowledge-db (L2 storage)
Context freed: ~5,220 tokens
```

---

## Hook Configuration

**Hook**: `PostToolUse` (runs after every tool execution)

**Frequency**: Check every ~10 turns

**Triggers**:
- Context > 60% → Queue cold segments
- Context > 80% → Archive to L3
- Every 50 turns → Prune old archives

**Non-blocking**: Always exits 0, never blocks workflow

---

## Retrieval and Search

Compressed segments are searchable via knowledge-db skill:

```bash
/knowledge-db search "OAuth2 authentication implementation"
```

Returns relevant compressed segments from L2 storage, even if they're no longer in active context.

---

## Maintenance

### Manual Compression Trigger

```bash
# Force compression check (bypass 10-turn wait)
FORCE_COMPRESSION_CHECK=1 uv run .../auto_context_manager.py
```

### View Compression Queue

```bash
cat ~/.claude/data/context_queue/{session_id}_pending.json | jq
```

### Clear Archive

```bash
rm -rf ~/.claude/data/sessions/{session_id}/archived_context/
```

### Check L2 Storage

```bash
ls -lh data/knowledge-db/compressed_context/
```

---

## Performance Impact

| Operation | Frequency | Overhead | Impact |
|-----------|-----------|----------|--------|
| Queue check | Every 10 turns | <50ms | Negligible |
| Compression (Claude) | When needed | ~5-10s | User-visible, but valuable |
| Archive pruning | Every 50 turns | <100ms | Negligible |
| L2 search | On demand | ~200ms | Negligible |

**Net Benefit**:
- Prevents expensive full-context compaction (15-30s)
- Maintains ~40% more working context
- Preserves searchable history indefinitely

---

## Migration and Compatibility

**Backward Compatible**: Does not interfere with default Claude Code compaction

**Fallback**: If auto-compaction fails, default system compaction still works

**Opt-out**: Set `DISABLE_AUTO_CONTEXT_MANAGER=1` to disable hook

---

## Troubleshooting

### Hook not triggering

Check turn count:
```bash
# View session JSON
cat ~/.claude/data/sessions/{session_id}.json | jq '.messages | length'
```

### Queue file not created

Check permissions:
```bash
ls -la ~/.claude/data/context_queue/
```

### Compression not happening

Check if Claude sees system reminders in stderr output.

---

## Summary

This system provides **proactive, intelligent context management** that:
- ✅ Prevents context overflow before it happens
- ✅ Uses your current Claude session (no external API costs)
- ✅ Maintains searchable history in knowledge-db
- ✅ Self-cleans old archives
- ✅ Fully automated, non-blocking
- ✅ Consistent schema for reliable operation

**User never hits full compaction wall. Context stays fresh and working.**
