---
name: Performance Profiler
version: 0.1.0
description: "This skill should be used when the user asks about performance, slow code, profiling, optimization, latency, memory usage, or benchmarking. It profiles and optimizes code performance, identifies bottlenecks, and suggests improvements."
---

# Performance Profiler Skill

Identify performance bottlenecks, measure execution time, analyze memory usage, and suggest targeted optimizations.

## When to Use

- User reports: "slow", "takes too long", "performance issue", "optimize"
- High latency in API endpoints or scripts
- Memory usage concerns
- Before/after performance comparison needed
- Hook execution timeout issues

## Workflow

### Step 1: Identify the Performance Target

Determine what to profile:
- **Specific function/endpoint**: Targeted profiling
- **Entire application**: Broad profiling first, then drill down
- **Build/compilation**: Build tool profiling
- **Hook execution**: Claude Code hook timing

### Step 2: Measure Current Performance

**Python:**
```bash
# Quick timing
python3 -c "import time; start = time.perf_counter(); ... ; print(f'Elapsed: {time.perf_counter() - start:.4f}s')"

# cProfile for detailed breakdown
python3 -m cProfile -s cumulative script.py 2>&1 | head -30
```

**JavaScript/Node.js:**
```bash
node --prof script.js
node --prof-process isolate-*.log > profile.txt
```

**Shell/Hooks:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"echo test"}}' | time uv run /path/to/hook.py
```

### Step 3: Analyze Results

Key metrics to extract:
1. **Total execution time**
2. **Top 5 time-consuming functions**
3. **Memory peak usage**
4. **I/O operations** (file reads, network calls)
5. **CPU-bound vs I/O-bound** classification

### Step 4: Identify Bottlenecks

Common bottleneck patterns:

| Pattern | Symptom | Fix |
|---------|---------|-----|
| N+1 queries | Linear DB calls in loop | Batch query, join |
| Unbounded iteration | Growing list/dict in loop | Generator, streaming |
| Synchronous I/O | Blocking calls in async | Use async/await |
| Repeated computation | Same result computed multiple times | Caching, memoization |
| Large file reads | Reading entire file into memory | Streaming, chunked |
| String concatenation | Building strings in loop | Join, StringBuilder |
| Import overhead | Heavy imports at module level | Lazy imports |

### Step 5: Suggest Optimizations

Prioritize by impact:
1. **Algorithm changes** (O(n^2) to O(n log n))
2. **I/O reduction** (caching, batching, connection pooling)
3. **Concurrency** (parallel processing, async I/O)
4. **Data structure changes** (list to set for lookups)
5. **Micro-optimizations** (last resort, only if measurable)

### Step 6: Generate Report

```markdown
## Performance Analysis

### Target
[What was profiled]

### Current Performance
- Execution time: [X]ms
- Memory usage: [X]MB
- Key bottleneck: [description]

### Bottlenecks Found
1. **[Location]**: [description] - [X]% of total time

### Recommendations
1. [High impact fix] - Expected improvement: [X]%
2. [Medium impact fix] - Expected improvement: [X]%

### Before/After
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time   | Xms    | Yms   | Z%          |
```

## Hook Performance Guidelines

Claude Code hooks have strict timeouts (5-10s default):

1. **Pattern matching hooks** (damage-control): Target < 50ms
2. **Logging hooks** (observability): Target < 100ms
3. **Validation hooks** (framework): Target < 5s
4. **Circuit breaker wrapper**: Adds ~20ms overhead

## Examples

### Example 1: Slow Python Script
User: "This script takes 30 seconds to run"
1. Profile with cProfile, identify top functions
2. Look for I/O-bound operations
3. Suggest caching/batching/async improvements

### Example 2: Hook Timeout
User: "My PreToolUse hook keeps timing out"
1. Time the hook with test input
2. Check YAML loading (cache config), regex compilation (pre-compile)
3. Suggest moving heavy work to PostToolUse
