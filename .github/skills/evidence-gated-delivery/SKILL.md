---
name: evidence-gated-delivery
description: Use when implementing, testing, reviewing or preparing changes with reproducible evidence.
---
Inspect project instructions, manifests, lockfiles and CI. Make isolated changes. Run applicable checks in an authorized environment and record commands, runtime versions, exit codes and evidence. Keep failures and missing evidence visible. Merge or deploy only after required independent review and verification.

The `portfolio-verifier` remains read-only: it inspects files and existing evidence without modifying files, running commands or deploying. For required checks without runtime evidence, it reports the missing evidence and lists the commands and prerequisites in its handoff to a maintainer or CI job authorized to run them. The executor returns the tested revision, commands, runtime versions, exit codes and results. The verifier labels its static observations separately from runtime results supplied by the executor and leaves any required check without results unverified.
