# Bronze to Silver Transformation

## Purpose

`EDU_BR_SL_Transform` converts one source instance from Bronze Delta tables into the 24-table Silver model in `EDU_SL`.

The notebook handles transformation, validation, publication, and unchanged-run detection. `EDU_SL_CreateSchema` remains responsible for the physical Silver tables.

The transformation reads Bronze tables only. It does not read CSV files, manifests, repository model files, or Bronze ingestion-audit records at runtime.

## Required run order

Run the Fabric assets in this order:

1. `EDU_BR_CreateSchema` creates or verifies the 25 Bronze source tables and two control tables.
2. `EDU_BR_Ingestion` validates and loads the source snapshot into those tables.
3. `EDU_SL_CreateSchema` creates or confirms the 24 Silver tables.
4. `EDU_BR_SL_Transform` validates Bronze and publishes Silver data.
5. Gold or reporting refreshes start only after transformation succeeds.

The transformation can run independently after Bronze and the Silver schema already exist.

## Prerequisites

Before running, confirm:

- The Bronze and Silver Lakehouses are attached to the notebook.
- All required Bronze tables exist as Delta tables.
- Every required Bronze table has rows for the selected `SourceInstanceId`.
- `EDU_SL_CreateSchema` has created all 24 Silver business tables.
- Source identifiers follow the conventions expected by the current mapping.

The notebook uses 24 of the 25 ingested Bronze tables. `canvas_courses` is intentionally unused because PowerSchool supplies canonical courses and sections.

## Parameters

Cell 2 contains:

```python
bronze_lakehouse_name = "EDU_Bronze"
source_instance_id = "synthetic-district-v2"
force_reload = False
exit_notebook_on_success = True
```

- `bronze_lakehouse_name` identifies Bronze. The installer injects the deployed name.
- `source_instance_id` selects one source snapshot. Different source instances are never mixed.
- `force_reload` rebuilds all targets. Leave it `False` for normal runs.
- `exit_notebook_on_success` returns JSON to a calling pipeline. Set it to `False` only for interactive investigation.

## Transformation scope

| Group | Silver tables |
| --- | --- |
| Organization and people | `District`, `School`, `Student`, `Teacher` |
| Academic structure | `Course`, `AcademicTerm`, `Section`, `CalendarDay` |
| Membership | `SchoolEnrollment`, `SectionEnrollment`, `TeacherAssignment` |
| Source mappings | `SourceIdentity`, `LmsSection` |
| Participation and content | `Attendance`, `LearningContent`, `Obligation` |
| Student work | `SubmissionState`, `Submission` |
| Assessment | `AssessmentInstrument`, `AssessmentWindow`, `AssessmentResult` |

PowerSchool is authoritative for schools, people, courses, sections, and memberships. Canvas and Moodle contribute LMS content and student work. NWEA contributes assessments. Users are linked through institutional identifiers, never names or email addresses.

Silver identifiers are deterministic: the same source instance and native identifiers produce the same Silver keys on every run.

### School years and earlier membership

`powerschool_terms` gives one `AcademicTerm` per school year (`valid_to` is the day after `last_day`); overlapping years stop the run. The current term is the one holding the current enrollments, and every section in the extract belongs to it. `SchoolEnrollment` unions the current year's `powerschool_enrollments` (year group from the student record) with earlier years' `powerschool_reenrollments` (year group on the row). Class rosters resolve against current membership only, so a learner with an earlier enrollment at the same school is never doubled into a class. `SchoolAddress` carries each school's postal address from `powerschool_schools`, so `School` keeps its existing schema.

### Teacher-logged actions

`powerschool_log_entries` feeds two tables. `ActionType` is the distinct `log_type` list. `InterventionAction` resolves the learner, school, teacher and optional class to their Silver keys, casts the dates, lower-cases `status` (anything other than `open` or `completed` stops the run) and derives `reason_category` from the recorded reason up to its first colon (`Attendance`, `Coursework`, otherwise `Other`). A class is optional, so the foreign-key gate skips null references rather than reporting them as unresolved. Gold enrichment then asserts that each action lies inside the learner's school membership and, when it names a class, inside both the class membership and the teacher's assignment on that date. Nothing here scores, predicts or interprets the outcome note.

## Current identifier conventions

The sample package uses:

- Canvas `sis_section_id`: `SYN-SECTION-<number>`
- Moodle course `shortname`: `SYN-SECTION-<number>`
- NWEA `School_StateID`: `SYN-SCHOOL-<number>`

The notebook fails on unsupported values instead of silently dropping records. Before onboarding a real district, replace these parsing rules with governed district identifiers and test the mappings before publication.

## Quality gate

All changed target datasets are checked before the first Silver business-table write. Publication is blocked when validation fails.

The notebook verifies:

1. Output columns and types match the existing Silver schema.
2. Required Silver fields are populated.
3. Primary keys are unique.
4. Declared foreign keys resolve to parent tables.
5. Required Bronze tables contain data for the selected source instance.
6. LMS and NWEA identifiers use supported formats.
7. Assessment windows have an unambiguous chronological order.
8. Each Silver target preserves the expected grain derived from its current Bronze inputs, so unresolved joins cannot silently discard rows.

Attendance and assessments must resolve during school membership. Obligations must resolve to a student, section, content item, and active membership. Moodle grades are matched by assignment, user, and attempt. Submitted Moodle work remains in Silver when no grade is available, with `score` left null.

These completeness checks calculate expectations from the current Bronze snapshot. They are not fixed thresholds. Synthetic row counts remain sample-package acceptance evidence, not production runtime gates.

## Incremental behavior

Each target fingerprint uses:

- Delta versions of that target's Bronze dependencies.
- The target Silver schema.
- The notebook transformation-contract version.

When the latest successful fingerprint matches, the target is `SKIPPED_UNCHANGED` and gets no new Silver Delta version. A Bronze change rebuilds only dependent targets.

Use `force_reload = True` only for an intentional full rebuild, then return it to `False`.

## Operational tables

The notebook maintains:

- `transform_audit`: target fingerprint, status, row count, and timestamps.
- `transform_diagnostic`: coarse execution stages used for troubleshooting.

These are operational tables, not part of the 24-table Silver business model.

## Deployment directions

Validate preparation without changing Fabric:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EDUCATION-ANALYTICS" `
    -PlanOnly `
    -SkipBronzeDataUpload
```

Deploy code without re-uploading Bronze files:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EDUCATION-ANALYTICS" `
    -SkipLocalValidation `
    -SkipBronzeDataUpload
```

Create the Silver schema and run transformation during installation:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EDUCATION-ANALYTICS" `
    -SkipBronzeDataUpload `
    -RunSilverCreateSchemaNotebook `
    -RunSilverTransformNotebook
```

Do not use `-SkipLocalValidation` for a release unless the same inputs already passed `-PlanOnly` or equivalent validation.

## Failure and recovery directions

When a run fails:

1. Retrieve Fabric job status and available API details before changing code.
2. Check `transform_diagnostic` for the last completed stage.
3. Check `transform_audit` for prior successful targets.
4. Correct the Bronze data, mapping, Silver schema, or notebook code.
5. Rerun normally; use `force_reload` only when a full rebuild is required.
6. Keep Gold and report refreshes blocked until success.

Delta writes are atomic per table, not across all 24 tables. A publication failure can leave a mixed state; a successful rerun reconverges it.

## Successful result

The notebook returns the run ID, source instance, Bronze fingerprint, targets written or skipped, rows published, and quality-error count.

An unchanged rerun should report:

- `tablesWritten = 0`
- `tablesSkipped = 21`
- No new Delta version on any Silver business table

## Verified acceptance

As of September 17, 2026:

- Full transformation completed successfully in Fabric.
- All 21 Silver business tables were published.
- The Spark `due_at` ambiguity was removed through explicit column naming.
- A second unchanged Fabric run completed successfully.
- All 21 Silver business tables remained at Delta version 1 after that rerun.
- Runtime code has no CSV, manifest, ingestion-audit, or fixed mock-count dependency.

## Out of scope

- Live connector extraction or API paging.
- Name- or email-based identity matching.
- Historical submission-state reconstruction.
- Gold, semantic-model, or report refresh implementation.
- Assessment proficiency, intervention-effect, or growth claims.
- Cross-table transactional snapshots or Silver history retention.
