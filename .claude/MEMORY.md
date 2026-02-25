# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-02-24 (14:58 UTC)
**Commit:** docs: update memory system diagrams to reflect on-demand episodic memory (5e7363b)
**Changed:**
  README.md                   |   21 +-
  docs/MEMORY_ARCHITECTURE.md |  150 +++---
  docs/memory-system.html     | 1132 +++++++++++++++++++++++++++----------------
  scripts/generate_docs.py    |   21 +-
  4 files changed, 819 insertions(+), 505 deletions(-)

## 2026-02-24 (14:58 UTC)
**Commit:** docs: update memory system diagrams to reflect on-demand episodic memory (5e7363b)
**Changed:**
  README.md                   |   21 +-
  docs/MEMORY_ARCHITECTURE.md |  150 +++---
  docs/memory-system.html     | 1132 +++++++++++++++++++++++++++----------------
  scripts/generate_docs.py    |   21 +-
  4 files changed, 819 insertions(+), 505 deletions(-)

## 2026-02-24 (15:05 UTC) · @Tom Kwon
**Commit:** feat(memory): add team author tagging + fix Korean HTML layout (a78ff62) by Tom Kwon
**Changed:**
  docs/memory-system-ko.html                         | 969 +++++++++++++++++++++
  .../framework/facts/auto_fact_extractor.py         |  26 +-
  global-hooks/framework/facts/fact_manager.py       |   7 +-
  .../framework/memory/auto_memory_writer.py         |  17 +-
  4 files changed, 1014 insertions(+), 5 deletions(-)

## 2026-02-24 (15:27 UTC) · @Tom Kwon
**Commit:** docs: add multi-page HTML documentation system (0f5c3e9) by Tom Kwon
**Changed:**
  docs/agents.html           | 372 ++++++++++++++++++++++++++++++++
  docs/caddy.html            | 310 +++++++++++++++++++++++++++
  docs/hooks.html            | 304 ++++++++++++++++++++++++++
  docs/index.html            | 520 +++++++++++++++++++++++++++++++++++++++++++++
  docs/memory-system-ko.html |  10 +
  docs/memory-system.html    |  10 +
  docs/shared.css            | 231 ++++++++++++++++++++
  docs/skills.html           | 260 +++++++++++++++++++++++
  8 files changed, 2017 insertions(+)

## 2026-02-24 (15:45 UTC) · @Tom Kwon
**Commit:** docs: translate all HTML pages to Korean, fix memory-system colors (d89e2e0) by Tom Kwon
**Changed:**
  docs/agents.html        | 226 ++++++++++++------------
  docs/caddy.html         | 228 ++++++++++++------------
  docs/hooks.html         | 160 ++++++++---------
  docs/index.html         | 222 ++++++++++++------------
  docs/memory-system.html | 452 ++++++++++++++++++++++++------------------------
  docs/skills.html        | 146 ++++++++--------
  6 files changed, 717 insertions(+), 717 deletions(-)

## 2026-02-24 (15:46 UTC) · @Tom Kwon
**Commit:** docs: translate all HTML pages to Korean, fix memory-system colors (d89e2e0) by Tom Kwon
**Changed:**
  docs/agents.html        | 226 ++++++++++++------------
  docs/caddy.html         | 228 ++++++++++++------------
  docs/hooks.html         | 160 ++++++++---------
  docs/index.html         | 222 ++++++++++++------------
  docs/memory-system.html | 452 ++++++++++++++++++++++++------------------------
  docs/skills.html        | 146 ++++++++--------
  6 files changed, 717 insertions(+), 717 deletions(-)

## 2026-02-24 (15:46 UTC) · @Tom Kwon
**Commit:** docs: translate all HTML pages to Korean, fix memory-system colors (d89e2e0) by Tom Kwon
**Changed:**
  docs/agents.html        | 226 ++++++++++++------------
  docs/caddy.html         | 228 ++++++++++++------------
  docs/hooks.html         | 160 ++++++++---------
  docs/index.html         | 222 ++++++++++++------------
  docs/memory-system.html | 452 ++++++++++++++++++++++++------------------------
  docs/skills.html        | 146 ++++++++--------
  6 files changed, 717 insertions(+), 717 deletions(-)

## 2026-02-24 (15:48 UTC) · @Tom Kwon
**Commit:** fix(docs): translate memory-system-ko.html top nav to Korean (97b487c) by Tom Kwon
**Changed:**
  docs/memory-system-ko.html | 12 ++++++------
  1 file changed, 6 insertions(+), 6 deletions(-)

## 2026-02-24 (15:51 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:51 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:52 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:52 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:55 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:56 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:57 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (15:58 UTC) · @Tom Kwon
**Commit:** docs: remove English memory page, update all nav links to KO version (605e4bc) by Tom Kwon
**Changed:**
  docs/agents.html           |    2 +-
  docs/caddy.html            |    2 +-
  docs/hooks.html            |    4 +-
  docs/index.html            |   22 +-
  docs/memory-system-ko.html |    3 +-
  docs/memory-system.html    | 1450 --------------------------------------------
  docs/skills.html           |    2 +-
  7 files changed, 10 insertions(+), 1475 deletions(-)

## 2026-02-24 (16:00 UTC) · @Tom Kwon
**Commit:** chore: clean up root folder structure (fb6383b) by Tom Kwon
**Changed:**
  .gitignore                                                            | 3 ---
  ai_docs/README.md                                                     | 4 ----
  {global-output-styles => docs/output-styles}/bullet-points.md         | 0
  {global-output-styles => docs/output-styles}/genui.md                 | 0
  {global-output-styles => docs/output-styles}/html-structured.md       | 0
  {global-output-styles => docs/output-styles}/markdown-focused.md      | 0
  .../output-styles}/observable-tools-diffs-tts.md                      | 0
  .../output-styles}/observable-tools-diffs.md                          | 0
  {global-output-styles => docs/output-styles}/table-based.md           | 0
  {global-output-styles => docs/output-styles}/tts-summary-base.md      | 0
  ... and 3 more files

## 2026-02-24 (16:03 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:04 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:06 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:09 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:10 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:11 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-24 (16:12 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (06:55 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (06:56 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (07:04 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (07:06 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (07:06 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (07:07 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)
