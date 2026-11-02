# Source System Research

This folder contains the source-system research and development-environment setup guidance for the four selected external hackathon sources: PowerSchool SIS, Canvas LMS, Moodle LMS, and NWEA MAP Growth. Use this research before touching Fabric. The goal is to understand how each source can be stood up, populated with sample data, extracted through a connector or export, and simulated when real access is unavailable.

## Official schema evidence

Start with [Official Schemas/README.md](official-schemas/README.md) for the official-source investigation checked on 2026-09-14, consolidated source comparisons, field inventories and complete 345-column Silver triage register. **Current work is synthetic-only engineering, with no institutional pilot or real-data access dependency.** Use [the existing sample package](../../sample-data/README.md) for file-based development. Tenant acquisition and approval checklists are future compatibility reference only. Public schema evidence is not tenant-data verification. The setup guides below describe optional local environments or future access paths; their synthetic filenames are proposed project contracts, not official vendor schemas.

## Source readiness summary

| Source | Can create development environment? | Can load sample source data into it? | Best Day 1 path |
| --- | --- | --- | --- |
| PowerSchool SIS | Not self-service; requires district/customer, partner, or vendor sandbox/test access. | Yes only with sandbox/test admin access, usually through import/export tools such as Quick Import or AutoComm. | Treat as access-gated; prepare synthetic SIS extracts unless a test environment is already available. |
| Canvas LMS | Yes. Use only a local open-source Canvas instance through the official automated Docker setup path. | Yes. Use Canvas SIS CSV imports for roster/course setup, then local UI/API for assignments and submissions. | Strong local real connector candidate. Use local Canvas SIS CSV plus REST API where possible. |
| Moodle LMS | Yes. Use Moodle Docker, local Moodle install, or hosted MoodleCloud-style environment. | Yes. Use admin CSV upload paths, Moodle UI, plugins, or web services depending on setup. | Strong local development candidate. Use local/hosted test instance plus synthetic fallback. |
| NWEA MAP Growth | No public self-service sandbox confirmed; requires licensed MAP Growth environment or partner/system account. | Generally no for fabricated assessment results; use authorized export data or simulated export files. | Treat as export/API gated; create vendor-export-shaped synthetic files. |

## Recommended research-to-implementation flow

1. Read each source guide in this folder.
2. Decide whether a real development environment is available.
3. If real access is available, load the minimum source data into the source system first.
4. If real access is unavailable, create synthetic source-shaped export files instead.
5. Draft Bronze contracts from the researched source/export shape.
6. Confirm all four sources have usable sample extracts or synthetic files and drafted contracts; only then start Fabric setup.

## Files

| File | Purpose |
| --- | --- |
| `powerschool-sis.md` | Research and development-environment guide for PowerSchool SIS. |
| `canvas-lms.md` | Research and development-environment guide for Canvas LMS. |
| `moodle-lms.md` | Research and development-environment guide for Moodle LMS. |
| `nwea-map-growth.md` | Research and export-fixture guide for NWEA MAP Growth. |

## Shared synthetic data rules

- Do not use real student, teacher, guardian, school, or district data.
- Use stable source IDs so records can join across systems.
- Keep a single synthetic identity map for students and teachers across PowerSchool, Canvas, Moodle, and NWEA sources.
- Include enough time history for Day 1-5 demo scenarios:
  - 20 school days of attendance.
  - 14 days of Canvas and Moodle engagement.
  - At least two assessment windows for growth analysis.
- Generate both risk and non-risk cohorts so dashboards show realistic variation.
