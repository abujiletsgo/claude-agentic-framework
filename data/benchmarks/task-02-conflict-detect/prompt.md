# Benchmark Task 02 — Add glob conflict detection to register-domain

Improve the `register-domain` subcommand in `bin/orch-shared` to detect
overlapping glob patterns at registration time.

When a lead tries to register a glob that overlaps with one already claimed
by a different lead, the command should:
1. Print a CONFLICT warning to stderr for each overlap
2. Write entries to shared/discoveries.jsonl (topic: "domain-conflict")
3. Exit with code 1 (do not write the conflicting domains)

Overlap detection: use fnmatch. Two globs overlap if
fnmatch.fnmatch(existing_glob, new_glob) OR fnmatch.fnmatch(new_glob, existing_glob).

Same-lead re-registration should always succeed (idempotent).
Non-overlapping globs should always succeed.
