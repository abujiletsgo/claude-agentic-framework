# CAF Hooks Benchmark: Python vs Rust

## Environment
- Binary size: 2.0M
- Iterations per test: 10
- Generated: 2026-04-08T08:28:43.400573Z

## Per-Hook Results (All Complexities)

| Hook | Complexity | Python Mean (ms) | Rust Mean (ms) | Speedup | Python Min-Max | Rust Min-Max |
|------|-----------|-----------------|---------------|---------|--------|--------|
| post-compact-verify | SIMPLE | 90.4 | 12.1 | 7.47x | 85.8-92.9 | 6.5-14.5 |
| post-compact-verify | MEDIUM | 90.0 | 13.8 | 6.52x | 82.7-93.1 | 13.5-14.4 |
| file-watcher | SIMPLE | 90.5 | 13.9 | 6.53x | 82.1-92.8 | 13.4-14.4 |
| file-watcher | MEDIUM | 89.3 | 13.8 | 6.45x | 78.3-93.1 | 13.5-14.7 |
| voice-done | SIMPLE | 90.8 | 10.6 | 8.58x | 86.1-93.0 | 6.6-13.7 |
| voice-done | MEDIUM | 106.1 | 9.0 | 11.76x | 79.6-151.5 | 6.7-14.3 |
| stop-failure-recovery | SIMPLE | 89.9 | 13.9 | 6.49x | 85.4-92.8 | 13.5-14.4 |
| stop-failure-recovery | MEDIUM | 89.8 | 12.4 | 7.27x | 84.3-93.1 | 6.5-14.4 |
| task-quality-gate | SIMPLE | 86.9 | 13.9 | 6.26x | 50.0-92.6 | 13.5-14.9 |
| task-quality-gate | MEDIUM | 91.0 | 8.0 | 11.44x | 49.0-149.8 | 6.2-14.3 |
| enforce-orchestrate | SIMPLE | 89.9 | 12.4 | 7.23x | 82.8-92.1 | 6.6-14.3 |
| enforce-orchestrate | MEDIUM | 91.0 | 10.8 | 8.41x | 86.9-92.7 | 5.9-14.2 |
| epistemic-guard | SIMPLE | 431.7 | 13.4 | 32.30x | 85.3-1363.7 | 8.2-14.5 |
| epistemic-guard | MEDIUM | 100.1 | 20.9 | 4.80x | 84.0-149.6 | 12.9-33.9 |
| auto-refine | SIMPLE | 98.0 | 13.6 | 7.21x | 89.0-145.7 | 13.3-14.1 |
| auto-refine | MEDIUM | 85.1 | 20.5 | 4.14x | 48.5-94.5 | 13.4-30.8 |
| auto-error-analyzer | SIMPLE | 151.2 | 14.7 | 10.26x | 145.3-154.2 | 13.7-16.4 |
| auto-error-analyzer | MEDIUM | 97.7 | 14.0 | 6.99x | 90.4-149.7 | 13.4-15.2 |
| context-bundle-logger | SIMPLE | 152.2 | 13.3 | 11.43x | 147.6-153.7 | 12.9-14.0 |
| context-bundle-logger | MEDIUM | 152.3 | 14.0 | 10.90x | 147.1-154.3 | 13.1-14.9 |
| damage-control | SIMPLE | 149.5 | 14.1 | 10.61x | 142.4-155.1 | 13.5-15.4 |
| damage-control | MEDIUM | 150.7 | 26.1 | 5.78x | 143.5-152.6 | 25.4-27.0 |
| auto-memory-writer | SIMPLE | 205.7 | 147.0 | 1.40x | 189.4-213.1 | 142.7-151.0 |
| auto-memory-writer | MEDIUM | 196.5 | 151.4 | 1.30x | 149.5-211.0 | 143.5-188.6 |

## Summary Statistics

- **Overall Speedup**: 5.90x (average across all hooks)
- **Average Speedup**: 9.65x
- **Average Python time**: 143.9 ms
- **Average Rust time**: 24.4 ms
- **Hooks tested**: 12
- **Net savings per hook invocation**: 119.5 ms

## Projection (100 tool calls per session)

- Python total overhead: 14391 ms (14.39s)
- Rust total overhead: 2440 ms (2.44s)
- Session savings: 11950 ms (11.95s)

## Key Findings

- **Fastest relative speedup**: epistemic-guard (32.30x)
- **Slowest relative speedup**: auto-memory-writer (1.40x)
- **Slowest Rust hook**: auto-memory-writer (147.0ms, complexity=SIMPLE)
- **All hooks faster in Rust**: YES ✓
