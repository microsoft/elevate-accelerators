# Gold Data Model Creation Specification

## Purpose

Define the deployable Microsoft Fabric artifacts required to create the Gold Lakehouse, its typed Delta tables, and the Silver-to-Gold transformation that populates them for the six current use cases. This specification covers Gold table creation, the transformation contract and the published calculation contract. Bronze ingestion and Bronze-to-Silver transformation are separate work.

The scope is **17 Gold targets plus the `GoldPublication` control table**. It covers every currently tagged Gold business column and all eight active calculations. Untagged legacy, planning and growth designs in the CSVs are design evidence, not additional requirements.

## Authoritative inputs

| Input | Role |
| --- | --- |
| [Shared configuration notebook](../../src/fabric/notebooks/EDU_Config.ipynb) | Lakehouse names, table-resolution helpers, data-quality functions, `BaseDataModel`, and the Gold writer and publisher |
| [Gold schema notebook](../../src/fabric/notebooks/EDU_GD_CreateSchema.ipynb) | Deployable source of truth for the physical Gold tables; declares `EducationGoldModel` and creates the Delta tables |
| [Silver-to-Gold enrichment notebook](../../src/fabric/notebooks/EDU_SL_GD_Enrichment.ipynb) | Deployable source of truth for the transformation; validates inputs, builds each target, validates outputs and publishes |
| [Processing pipeline](../../src/fabric/pipelines/EDU_BR_GD_Processing.DataPipeline/pipeline-content.json) | End-to-end orchestration from Bronze ingestion through Gold publication |
| [Gold_Data_Model.csv](../data-models/Gold_Data_Model.csv) | Repository design evidence with grains, purposes and use-case tags; not deployed to Fabric |
| [Silver_Data_Model.csv](../data-models/Silver_Data_Model.csv) | Input contract for the seventeen Silver tables this transformation reads; not deployed to Fabric |
| [Model_Relationships.csv](../data-models/Model_Relationships.csv) | Repository relationship design evidence; not deployed to Fabric |
| [Model_Calculations.csv](../data-models/Model_Calculations.csv) | Authoritative `MetricId` values for the semantic calculations below |
| [Silver Data Model Creation](Silver%20Data%20Model%20Creation.md) | Upstream specification; Gold consumes the tables it defines and never modifies them |
| [Use cases](../use-cases/README.md) | The six current use cases that scope every Gold column and calculation |

The notebooks embed the physical Gold schema so workload users receive self-contained artifacts. Fabric execution has no runtime dependency on the design CSVs.

**The deployed schema is the column contract.** `EDU_GD_CreateSchema` deliberately materialises only the use-case-backed columns, which is narrower than `Gold_Data_Model.csv` describes. Anything built on top of Gold must read the deployed schema, not the CSV.

## Target artifacts

The installation script creates or reuses these Fabric items in the selected workspace:

| Artifact | Default name | Responsibility |
| --- | --- | --- |
| Shared configuration notebook | `EDU_Config` | Lakehouse names, table helpers, data-quality assertions, `BaseDataModel`, Gold writer and publisher |
| Silver Lakehouse | `EDU_SL` | Existing transformation source; read-only to Gold |
| Gold Lakehouse | `EDU_GD` | Dedicated home for the 17 Gold targets and `GoldPublication` |
| Gold schema notebook | `EDU_GD_CreateSchema` | Create and verify the physical Gold Delta tables |
| Silver-to-Gold enrichment notebook | `EDU_SL_GD_Enrichment` | Validate Silver, build every target, validate outputs, publish |
| Silver-to-Gold enrichment pipeline | `EDU_SL_GD_Enrichment` | Ordered execution with concurrency 1 |

The Gold schema notebook uses `EDU_GD` as its default Lakehouse; the enrichment notebook binds Gold as default with Silver as an additional known Lakehouse. A dedicated Gold Lakehouse makes an additional `gold` schema redundant, so table references use the default Lakehouse namespace. The table helper still emits three-part names when a schema is supplied, which is required when the target Lakehouse is schema-enabled.

Notebook and pipeline item types distinguish identical base names, so the enrichment notebook and pipeline may share one name.

## Artifact naming convention

Follow the same convention as the Silver specification:

```text
<solution>_<layer>_<action-or-flow>
```

| Token | Meaning | Examples |
| --- | --- | --- |
| `EDU` | Education Analytics solution prefix | `EDU_Config` |
| `BR` | Bronze layer | `EDU_BR`, `EDU_BR_CreateSchema`, `EDU_BR_Ingestion` |
| `SL` | Silver layer | `EDU_SL`, `EDU_SL_CreateSchema` |
| `GD` | Gold layer | `EDU_GD`, `EDU_GD_CreateSchema` |
| `SL_GD` | Silver-to-Gold flow | `EDU_SL_GD_Enrichment` |

Repository notebook filenames use the same artifact name with an `.ipynb` extension. Fabric item names omit the extension. Repository artifacts follow the plain `.ipynb` and `.DataPipeline` layout, not a second package-installer tree.

`EDU_GD` is the canonical Gold Lakehouse. A pre-convention `EDU_Gold` Lakehouse existed alongside it, schema-enabled under `dbo`, and was deleted once `EDU_GD` was confirmed to hold the published snapshot: the two carried identical row counts in all fifteen data tables, but `EDU_Gold` was a refresh behind and lacked the coursework achievement columns. Nothing in the solution now reads it.

## Reference pattern

The notebooks follow the Nonprofit Data Solutions Fundraising package pattern:

| Reference artifact | Education adaptation |
| --- | --- |
| Configuration notebook | Shared Lakehouse names, table-resolution helpers, explicit model schemas and processing-state helpers |
| Gold schema notebook | Gold-attached creation notebook; `BaseDataModel` / `get_entities` pattern; nondestructive Delta creation |
| Silver-to-Gold enrichment notebook | Grouped target builders, typed projections, lookups and explicit write rules |
| Enrichment pipeline | Notebook activities with concurrency 1; downstream work starts only on success |

Preserve education names and key types; do not copy fundraising entities, integer surrogates or US-holiday calendars. Reference primary-key metadata is descriptive, not an enforced relational constraint, so the enrichment notebook validates uniqueness and relationships explicitly.

## Notebook parameters

`EDU_GD_CreateSchema` parameters default to:

```python
enable_delete_tables = False
enable_create_tables = True
```

`EDU_SL_GD_Enrichment` parameters carry the reporting period, substituted at install time:

```python
period_start = "{PERIOD_START}"
period_end   = "{PERIOD_END}"
```

`period_end` is exclusive. The period decides which enrolled instructional days become attendance opportunities, so it must never be defaulted: a guessed period silently changes every attendance denominator. The notebook refuses to run when either value is empty or still holds an unsubstituted placeholder, and names the installer flags in the failure message.

`EDU_Config` carries `{SILVER_LAKEHOUSE_NAME}`, `{SILVER_SCHEMA_NAME}`, `{GOLD_LAKEHOUSE_NAME}` and `{GOLD_SCHEMA_NAME}`. Both entry notebooks start with `%run <EDU_Config>`. The installer substitutes every placeholder in temporary copies only; checked-in definitions keep the placeholders. Workspace, Lakehouse and notebook IDs are deployment parameters, and destructive options default to off.

## Installer changes

Extend [`Install-IntoWorkspace.ps1`](../../deploy/Install-IntoWorkspace.ps1) without duplicating its Fabric CLI helpers, and do not add a second installer. Gold is installed with Bronze and Silver in one sequential pass. See the [installation README](../../deploy/README.md) for the supported switches and offline preview instructions.

1. Add `GoldLakehouseBaseName`, defaulting to `GD`. Refuse a target that resolves to the Bronze or Silver Lakehouse.
2. Add `ConfigNotebookBaseName`, `GoldNotebookBaseName`, `EnrichmentNotebookBaseName` and `ProcessingPipelineBaseName`, defaulting to the prefixed `Config`, `GD_CreateSchema`, `SL_GD_Enrichment` and `BR_GD_Processing` names.
3. Reuse the existing `SilverLakehouseBaseName`; it also names the enrichment source. Gold never creates or repopulates Silver.
4. Create or reuse `${Prefix}${GoldLakehouseBaseName}` after the Silver Lakehouse step, then resolve its actual ID.
5. Reuse the shared `New-PreparedNotebook` helper, extended to accept a source path, item name, default-Lakehouse binding, additional known Lakehouses and placeholder replacements. Import the shared configuration first.
6. Import each notebook with `fab import --force`, preserving item IDs on reruns.
7. Import the pipeline with the resolved workspace and notebook IDs substituted; never assume a filename is an item ID.
8. Add `RunGoldCreateSchemaNotebook` and `RunEndToEndPipeline` switches. Keep `RunNotebook` scoped to Bronze.
9. Preserve a reporting period that is already configured. Every install re-imports the enrichment notebook, so substituting the placeholders with nothing would erase a working period and break a scheduled pipeline. Explicit `PeriodStart` and `PeriodEnd` win; otherwise the deployed values are read back and reused.
10. Do not replace the shared configuration notebook when it already exists unless `OverwriteSharedConfigNotebook` is supplied. It may carry local edits, whereas the other notebooks are generated artifacts.
11. Include every Gold artifact in the installation summary, distinguishing created from reused and requested from completed.

`RunEndToEndPipeline` requires `PeriodStart` and `PeriodEnd`; supplying it without them is an error. The period is otherwise optional at install time: without it the enrichment notebook is still imported, with its period left unset, so a deployment-only install needs no Gold-specific parameter. An install without run switches reports execution as **not requested**, not completed.

`PlanOnly` must validate the local notebook and pipeline definitions, generate every prepared definition, confirm no Lakehouse placeholder survives substitution, and make no Fabric changes or job submissions.

Job submission, or a zero Fabric CLI exit code, is **not** proof of execution success. Poll the specific job to a terminal state; failure, cancellation and timeout must fail the installation command. Reruns update only the intended artifacts and must not create duplicate notebooks, pipelines or fact rows.

## Notebook responsibilities

`EDU_GD_CreateSchema` performs these stages in order:

1. Validate that a default Gold Lakehouse is attached.
2. Declare `EducationGoldModel(BaseDataModel)` with one explicit `StructType` getter per table.
3. Return `(schema, table_name, enableChangeDataFeed)` tuples from `get_entities()`.
4. Create missing empty Delta tables through `create_entities()`; append with `mergeSchema` so reviewed additive nullable columns are kept.
5. Never drop, truncate or silently change an existing schema. Parallel creation is acceptable only if every failure reaches orchestration.

`EDU_SL_GD_Enrichment` performs these stages in order:

1. Validate the reporting period and fail before any read when it is unset.
2. Discard any candidate snapshot left behind by an interrupted run.
3. Pin every Silver input to its current Delta version, exposing each as a view, and derive `snapshot_id` from those versions plus the transformation version and reporting period. Every later read goes through the pinned views, so one run sees a single consistent set of input versions.
4. Verify the Silver input contracts: required tables, required values, unique keys, foreign keys, membership intervals, and recognized attendance status codes including an explicit rejection of null status.
5. Stop before the first Gold write when any input contract is broken, so Gold is never built on an incomplete or inconsistent load.
6. Append every target as a candidate snapshot in dependency order, stamping one `snapshot_id` and one `as_of` on every row.
7. Validate the candidate through scoped views: declared grain, required values, key uniqueness, referential matches and attendance arithmetic.
8. Append one `GoldPublication` row only after every target passes, then retire the superseded snapshot and assert that only the published one remains.

Neither notebook modifies Silver. Reporting dates are business filters, not source-observation timestamps.

## Type mapping

Only these types appear in the Gold model:

| Model type | PySpark type | Use |
| --- | --- | --- |
| `STRING` | `StringType()` | Keys, names, codes, snapshot identity |
| `DATE` | `DateType()` | Business dates and interval bounds |
| `TIMESTAMP` | `TimestampType()` | Run cutoffs and source event timestamps |
| `INT` | `IntegerType()` | Attempt ordinals |
| `LONG` | `LongType()` | Additive counts |
| `DOUBLE` | `DoubleType()` | Observed scores and standard errors |
| `BOOLEAN` | `BooleanType()` | Native source flags |

The notation `column:TYPE?` below means nullable; without `?` the column is required. Type expansion requires an approved model change and a notebook test.

## Table inventory

Every target additionally carries the two technical columns defined under [Common technical columns](#common-technical-columns).

| Creation group | Table | Business columns | Primary key | Grain |
| ---: | --- | ---: | --- | --- |
| 1 | `DimSchool` | 8 | `school_id` | School |
| 1 | `DimStudent` | 2 | `student_id` | Learner |
| 1 | `DimTeacher` | 2 | `teacher_id` | Teacher |
| 1 | `DimAssessment` | 4 | `assessment_id` | Label and subject catalog |
| 1 | `DimWindow` | 2 | `window_id` | Assessment window |
| 1 | `DimDate` | 1 | `date` | Contiguous calendar date |
| 2 | `DimSection` | 6 | `section_id` | Section |
| 3 | `DimContent` | 7 | `content_id` | Assignment |
| 3 | `BridgeStudentSection` | 5 | `enrollment_id` | Learner-section interval |
| 3 | `BridgeTeacherSection` | 5 | `assignment_id` | Teacher-section interval |
| 4 | `FactAttendanceDay` | 13 | `attendance_day_id` | Learner-school-day |
| 4 | `FactAssessment` | 10 | `result_id` | Administration |
| 4 | `FactSubmissionState` | 8 | `state_id` | Recorded learner-task state |
| 4 | `FactSubmission` | 14 | `submission_id` | Submitted attempt |
| 5 | `FactStudentAction` | 32 | `action_id` | Teacher-logged learner action |
| 5 | `FactEnrollment` | 16 | `enrollment_term_id` | School membership per school year |
| 5 | `AggSchoolAttendance` | 10 | `aggregate_id` | School-grade-period |
| 6 | `GoldPublication` | control table | `snapshot_id` | One appended row per successful refresh |

This is **145 business columns plus 34 common technical columns**. Creation groups are dependency levels; tables within a group may be created in parallel after all earlier groups succeed.

Primary keys are unique **within one snapshot**. If snapshots ever share a physical table, the physical key also includes `snapshot_id`.

## Common technical columns

Supplied by the Gold run, never fabricated from a source record:

| Common column | Definition |
| --- | --- |
| `snapshot_id:STRING` | Fingerprint of what produced the refresh: the transformation version, the reporting period, and the exact Delta version of every Silver input. Identical across the published bundle, and identical again for a retry over unchanged inputs. The run cutoff is deliberately excluded, because hashing the clock described none of the inputs and made every retry a new identity. |
| `as_of:TIMESTAMP` | UTC input-selection and run cutoff, fixed for the bundle. It is not the unavailable historical source-observation cutoff, and it is not part of the snapshot fingerprint. |

## Source mapping

"Copy" preserves Silver keys and types; validate join cardinality. Every target is rebuilt on each run, so a change anywhere in its inputs is reflected.

| Target | Business columns | Source mapping |
| --- | --- | --- |
| `DimSchool` | `school_id:STRING`, `district_id:STRING`, `name:STRING`, `street_address:STRING?`, `city:STRING?`, `state:STRING?`, `postal_code:STRING?`, `county:STRING?` | Same-named `School` columns, left joined to `SchoolAddress` for the postal address; `city` falls back to `School.city`. District key is descriptive context; no new district dimension is required. |
| `DimStudent` | `student_id:STRING`, `display_name:STRING` | `Student.student_id`; display name = `given_name` + one space + `surname`. Not a matching or authorization key. |
| `DimTeacher` | `teacher_id:STRING`, `name:STRING` | Same-named `Teacher` columns. |
| `DimSection` | `section_id:STRING`, `school_id:STRING`, `course_id:STRING`, `subject:STRING`, `grade:STRING`, `name:STRING` | Same-named `Section` columns; `subject=Course.name` through `Section.course_id=Course.course_id`. |
| `DimContent` | `content_id:STRING`, `section_id:STRING`, `name:STRING`, `source_name:STRING`, `description:STRING`, `due_at:TIMESTAMP?`, `max_score:DOUBLE?` | Same-named `LearningContent` columns. |
| `DimAssessment` | `assessment_id:STRING`, `subject:STRING`, `unit:STRING`, `name:STRING` | Same-named `AssessmentInstrument` columns; `version` is unavailable and omitted. |
| `DimWindow` | `window_id:STRING`, `name:STRING` | Same-named `AssessmentWindow` columns. |
| `DimDate` | `date:DATE` | Every calendar date in the supported range, including noninstructional days. |
| `BridgeStudentSection` | `enrollment_id:STRING`, `student_id:STRING`, `section_id:STRING`, `valid_from:DATE`, `valid_to:DATE` | Same-named `SectionEnrollment` columns. |
| `BridgeTeacherSection` | `assignment_id:STRING`, `teacher_id:STRING`, `section_id:STRING`, `valid_from:DATE`, `valid_to:DATE` | Same-named `TeacherAssignment` columns. |
| `FactAttendanceDay` | `attendance_day_id:STRING`, `school_id:STRING`, `student_id:STRING`, `date:DATE`, `grade:STRING`, `expected_days:LONG`, `known_days:LONG`, `present_days:LONG`, `absent_days:LONG`, `unknown_days:LONG`, `rolling_expected_days:LONG?`, `rolling_absent_days:LONG?`, `rolling_window_complete:BOOLEAN?` | `CalendarDay` and effective `SchoolEnrollment`, left joined to `Attendance`. Flag rules below. The rolling columns sum `expected_days` and `absent_days` over the learner's last `ATTENDANCE_RULE_WINDOW_DAYS` (20) rows in that school and school year, ordered by date and ending with the row; `rolling_window_complete` is `rolling_expected_days = 20`. Declared nullable only because they are appended to an existing table; enrichment asserts they are never null. |
| `FactAssessment` | `result_id:STRING`, `school_id:STRING`, `student_id:STRING`, `date:DATE`, `grade:STRING`, `assessment_id:STRING`, `window_id:STRING`, `score:DOUBLE?`, `standard_error:DOUBLE?`, `is_scored:BOOLEAN` | `AssessmentResult` keys and scores; `date=assessment_date`; grade from the unique school enrollment containing that date. `is_scored` is `score IS NOT NULL`. |
| `FactSubmissionState` | `state_id:STRING`, `obligation_id:STRING`, `student_id:STRING`, `content_id:STRING`, `section_id:STRING`, `state:STRING`, `source_missing:BOOLEAN?`, `source_late:BOOLEAN?` | Copy `SubmissionState` key, obligation, state and native flags; resolve learner, content and section from the uniquely matching `Obligation`. |
| `FactSubmission` | `submission_id:STRING`, `obligation_id:STRING`, `student_id:STRING`, `content_id:STRING`, `section_id:STRING`, `attempt:INT`, `submitted_at:TIMESTAMP`, `score:DOUBLE?`, `state:STRING`, `points_possible:DOUBLE?`, `is_graded:BOOLEAN`, `is_late:BOOLEAN?`, `is_latest_attempt:BOOLEAN`, `subject:STRING` | Copy `Submission` key, attempt, time, score and state; resolve learner, content and section from the uniquely matching `Obligation`, requiring the submission's own learner and content to match it. `points_possible` is `LearningContent.max_score` for that obligation's content where it is positive, else null. `is_graded` is `score IS NOT NULL AND COALESCE(max_score, 0) > 0`. `is_late` is `Submission.source_late` unchanged. `is_latest_attempt` is `attempt = MAX(attempt) OVER (PARTITION BY obligation_id)`. `subject` resolves `Obligation.section_id -> Section.course_id -> Course.name`. |
| `FactStudentAction` | `action_id:STRING`, `student_id:STRING`, `school_id:STRING`, `section_id:STRING?`, `teacher_id:STRING`, `date:DATE`, `grade:STRING`, `class_name:STRING?`, `subject:STRING?`, `action_type:STRING`, `reason:STRING`, `reason_category:STRING`, `status:STRING`, `follow_up_date:DATE?`, `completed_date:DATE?`, `outcome_note:STRING?`, `is_completed:BOOLEAN`, `is_first_in_category:BOOLEAN`, `window_days:LONG`, `before_expected_days:LONG`, `before_known_days:LONG`, `before_absent_days:LONG`, `after_expected_days:LONG`, `after_known_days:LONG`, `after_absent_days:LONG`, `is_comparable:BOOLEAN`, `work_window_pieces:LONG?`, `before_work_due:LONG?`, `before_work_missing:LONG?`, `after_work_due:LONG?`, `after_work_missing:LONG?`, `is_work_comparable:BOOLEAN?` | `InterventionAction` in the reporting period, with `ActionType.name`, grade from the `SchoolEnrollment` containing `action_date`, and class name and subject through the optional `Section` and `Course`. The action is anchored on the learner's first `FactAttendanceDay` row on or after `action_date`; the before window is the `FOLLOW_UP_WINDOW_DAYS` (10) rows before it and the after window the 10 rows after it, the anchor day in neither. `is_comparable` requires both windows to hold 10 expected days. `is_first_in_category` is row 1 per learner, `reason_category` and school year ordered by `action_date, action_id`, and both attendance windows stay inside the action's school year. The work columns take the learner's obligations in the action's class with a due date: the `FOLLOW_UP_WORK_PIECES` (5) due before the action and the 5 due after it, nearest first, the action date in neither; a piece is missing when its obligation has no `Submission` row. `is_work_comparable` requires 5 on both sides. |
| `FactEnrollment` | `enrollment_term_id:STRING`, `enrollment_id:STRING`, `student_id:STRING`, `school_id:STRING`, `grade:STRING`, `term_id:STRING`, `school_year:STRING`, `term_start:DATE`, `term_end:DATE`, `valid_from:DATE`, `valid_to:DATE`, `entry_type:STRING`, `exit_type:STRING`, `is_final_grade:BOOLEAN`, `joined_mid_year:BOOLEAN`, `left_mid_year:BOOLEAN` | One row per `SchoolEnrollment` per `AcademicTerm` it overlaps, for terms that touch the reporting period. `entry_type` compares with the previous term: same school `Continuing`, other school `Transferred in`, none `New`, no previous term `First year in data`. `exit_type` compares with the next term: `Continuing`, `Transferred out`, `Completed final grade` when the grade is the school's highest numeric grade that term, otherwise `Left`, and `Latest year in data` when there is no next term. `school_year` is the calendar year, or both years when the term crosses New Year. |
| `AggSchoolAttendance` | `aggregate_id:STRING`, `school_id:STRING`, `grade:STRING`, `period_start:DATE`, `period_end:DATE`, `students:LONG`, `present_days:LONG`, `known_days:LONG`, `expected_days:LONG`, `unknown_days:LONG` | Selected-period aggregation of `FactAttendanceDay`; `period_end` is exclusive. |

For membership, use `valid_from <= business_date < valid_to`; reject ambiguous overlaps and unresolved required relationships. Do not join multiple class memberships into attendance rows; resolve class and teacher selections through date-qualified bridges.

Preserve one row per `content_id`, `state_id` or `submission_id`. Do not flatten attempts into state records, or co-teachers into assignment records. Assessment records retain nullable score and standard error; a matching label does not prove version equivalence or growth eligibility. Keep output snapshot identity separate from stable business keys, and never use row order as a surrogate.

## Keys, joins and dates

- Reuse Silver keys unchanged. For generated keys, use lowercase SHA-256 of a canonical UTF-8 JSON array with no insignificant whitespace: `attendance_day_id` uses `["AttendanceDay",student_id,school_id,date]`; `aggregate_id` uses `["SchoolAttendance",school_id,grade,period_start,period_end]`. Dates use ISO `YYYY-MM-DD`, and neither key includes a mutable row number or the snapshot.
- Mandatory joins must find exactly one compatible row. Duplicate keys, conflicting enrollment intervals, missing referenced entities and invalid types block publication rather than silently dropping rows.
- `DimDate` spans the earliest through latest of calendar dates, nonnull base due dates and assessment dates, as a contiguous sequence rather than the sparse set of observed dates. UTC is the documented synthetic timestamp convention; preserve native `DATE` values. A different school-local conversion requires an explicit source timezone contract, not the machine's timezone.
- Record the fully available calendar period in the run manifest. A padded `DimDate` range is not proof of attendance coverage, and out-of-range trend requests must not silently truncate their window.
- Schedule filters use `DimContent.due_at`; null means undated, not overdue. A date-only schedule filter is derived from this timestamp in the report projection; never use submission time as the assignment due date.
- Record views must state **provided source snapshot; observation time unavailable**. A filtered historical due or test date is not historical submission-state knowledge. Preserve Moodle attempt zero and native states; `new` is not proven overdue.

## Relationship and filter contract

Use these many-to-one relationships within the **same snapshot**, with single-direction dimension-to-fact filtering:

- `DimSection.school_id -> DimSchool.school_id`; `DimContent.section_id -> DimSection.section_id`.
- `BridgeStudentSection.student_id -> DimStudent.student_id` and `.section_id -> DimSection.section_id`; `BridgeTeacherSection.teacher_id -> DimTeacher.teacher_id` and `.section_id -> DimSection.section_id`.
- `FactAttendanceDay` and `FactAssessment`: `school_id -> DimSchool`, `student_id -> DimStudent`, `date -> DimDate`, using each dimension's same-named key.
- `FactAssessment.assessment_id -> DimAssessment.assessment_id`; `.window_id -> DimWindow.window_id`; `AggSchoolAttendance.school_id -> DimSchool.school_id`.
- Work facts: `student_id -> DimStudent.student_id`, `content_id -> DimContent.content_id`. Keep `section_id` as a validated class key, but do not activate a second section filter path alongside `DimSection -> DimContent -> work fact`. `obligation_id` is source lineage, not a join to a nonexistent Gold obligation table.

Class and teacher selection does not automatically cross a one-way bridge. For each business day, resolve the teacher assignments and student-section intervals valid on that day, intersect the class, school and learner selections, then filter the original attendance or assessment fact with that distinct learner set. Preserve existing filters and authorization; never join bridge rows into the fact or enable unrestricted bidirectional filtering.

Assessments use the administration date for class membership; work uses its explicit class and obligation association with the captured membership interval. A later submission may occur after the base due date or after enrollment exit; keep the source record rather than fabricating current membership.

Teacher titles and assignments are not permissions. The district use case receives only approved school, grade and period aggregates, never `DimStudent` or the detailed facts.

## Idempotency and refresh policy

Each target is built from the pinned Silver versions and **appended as a candidate snapshot**, then validated, then published. Overwriting each target in turn left the model mixed whenever a later target failed: earlier tables already held the new snapshot while later ones still held the previous one, and the newest publication row no longer described a complete physical dataset.

The sequence is:

1. Discard any candidate left behind by an interrupted run, keeping only the published snapshot.
2. Pin every Silver input to its current Delta version and derive `snapshot_id` from those versions.
3. Append each target's rows stamped with the candidate `snapshot_id`; a retry of the same snapshot replaces its own rows and nothing else.
4. Validate through views scoped to the candidate, so the published snapshot is never mixed into the checks.
5. Append the `GoldPublication` row, which moves the published pointer.
6. Retire the superseded snapshot, then assert that every table holds only the published one.

Until step 5 runs, the previously published snapshot is complete and still named by the newest publication row, so a failure at any earlier point leaves a consistent published dataset. In steady state each table holds exactly one snapshot.

- Missing table: the schema notebook creates an empty Delta table.
- Existing table: reuse it; append with `mergeSchema` for reviewed additive nullable columns. Delta appends a new column at the end of the table and makes it nullable whatever the `StructType` declares, so a column that must never be null is declared nullable here and asserted in the enrichment, where it can actually be checked against data.
- Nothing about that evolution is silent. The Gold writer compares its DataFrame columns against the physical table before every write and stops on any difference in either direction, so a `mergeSchema` that did not take effect fails the next run instead of quietly producing a table without the new columns.
- Existing schema drift: fail with an exact table, column and type difference rather than dropping.
- Contract removes or renames a table or column: fail; never drop automatically.
- Retry over unchanged inputs: deterministic, because `snapshot_id` is a fingerprint of the inputs rather than the clock, so the retry reuses the same identity and replaces its own partial rows.

Rebuilding every target keeps corrected dimensions, changed memberships and deleted source rows consistent, which a single-table incremental feed would miss. Every row carries one `snapshot_id` and one `as_of`, so a partially rewritten model is visible rather than silent.

`GoldPublication` is append-only, so it accumulates one row per successful refresh while the data tables carry only the published snapshot. The newest row is the published pointer.

Change Data Feed is not used. A single-table feed would still require every derived fact to be recomputed whenever a lookup changes, and it depends on feed retention being guaranteed on each source table. The reference configuration notebook's `CdfTable` and `ProcessCdfTable` helpers remain available should incremental processing be adopted later.

## Gold calculations

For every instructional `CalendarDay` row, select `SchoolEnrollment` where the school matches and `valid_from <= instructional_date < valid_to`. Create one learner-school-day opportunity and left join `Attendance` on learner, school and day. `date` is the calendar date and `grade` is the matched membership grade. A fact is not created outside an eligible instructional opportunity.

| Output | Calculation |
| --- | --- |
| `expected_days` | 1 for every eligible opportunity, whether or not an observation exists. |
| `known_days` | 1 for a recognized `present`, `absent` or explicitly mapped `excused`; 0 for missing or `unknown`. |
| `present_days` | 1 only for `present`; otherwise 0. |
| `absent_days` | 1 for `absent` or explicitly mapped `excused`; otherwise 0. |
| `unknown_days` | `expected_days - known_days`; missing attendance is not absence. |
| `FactAssessment.grade` | The unique `SchoolEnrollment.grade` for the same learner and school on `assessment_date`; never the current roster grade. |
| `AggSchoolAttendance` counts | Group dates in `[period_start,period_end)` by school and grade. Sum `present_days`, `known_days`, `expected_days` and `unknown_days`; `students=COUNT(DISTINCT student_id)` over eligible fact rows. Do not cross-join to work or assessment facts first. |

The fixture's source policy maps P to `present` and A to `absent`. `excused` is supported only when an approved mapping supplies it; never invent it. Unrecognized status codes are validation failures, not presumed known attendance.

Require `expected_days = known_days + unknown_days` and `known_days = present_days + absent_days` at every scope. No attendance rate is stored in atomic Silver or repeated as an additive Gold percentage. An empty eligible cohort yields no aggregate row; distinct cohort sizes are not additive across dates, grades, classes or snapshots.

Copy submission states, flags and scores. Do not derive completion, effective eligibility, grade-posting history, or missing and late classifications for unsupported sources. Keep null scores distinct from zero. Keep score scales separate, and do not create cross-window growth, proficiency, risk or intervention-effect outputs.

### Early warning and follow-up

Gold stores window components only; it flags nobody. A rule such as "5 or more absences in 20 school days" is `rolling_window_complete AND rolling_absent_days >= threshold`, with the threshold chosen in the semantic model. A follow-up figure is a ratio of sums over actions where `reason_category = 'Attendance' AND is_first_in_category AND is_comparable`, for example `SUM(after_absent_days) / SUM(after_known_days)`. It describes what was observed after an action, not its effect: a rule that fires on a run of absences selects an unusually high window, so part of any fall is regression to the mean.

### Coursework achievement

`FactSubmission` carries the operands a teacher needs to review recorded achievement. They are operands, never rates: the ratio is taken in the semantic layer so it responds to the selection.

| Output | Calculation |
| --- | --- |
| `points_possible` | `LearningContent.max_score` for the obligation's content, **only where it is positive**. A zero or absent maximum is not a denominator, so it stays null rather than producing a division by zero or a 0/0 that would read as failure. |
| `is_graded` | `score IS NOT NULL AND COALESCE(max_score, 0) > 0`. `COALESCE` is required: in SQL a comparison with null is null and `true AND null` is null, which would leave the flag null on exactly the rows that have no mark scheme. Those rows are not graded, so they must read false. |
| `is_late` | `Submission.source_late` unchanged, including its nulls. Nothing is derived from the due date, because per-learner extensions are not in the data. |
| `is_latest_attempt` | `attempt = MAX(attempt) OVER (PARTITION BY obligation_id)`. The Silver contract asserts `(obligation_id, attempt)` is unique, so a tie fails the run instead of being resolved arbitrarily. |
| `subject` | `Obligation.section_id -> Section.course_id -> Course.name`, resolved once here so per-subject achievement does not need a two-hop join in every query. |
| `FactAssessment.is_scored` | `score IS NOT NULL`. Symmetry with `is_graded`, so no measure has to decide what a null score means. |

Every lookup is to an asserted unique key, so none can multiply a submission; the row count against Silver proves it. Learner, content and section all resolve from the uniquely matching `Obligation`, and the mark scheme is looked up by that obligation's content, so every derived column hangs off one validated row rather than a mixture of the submission's own keys and the obligation's. The input contract asserts, with null-safe equality, that a submission's learner and content are the obligation's, so this is the same result on valid input and refuses to publish a hybrid fact on invalid input. Unmarked work is excluded from both operands rather than scored zero, and a missing score is never read as a failure. Achievement is recorded attainment on marked work: it is not ability, growth, a norm comparison or a prediction, and nothing here ranks a learner.

## Semantic calculations

The `MetricId` values below match [Model_Calculations.csv](../data-models/Model_Calculations.csv); the display names are proposed labels, not additional metric IDs. All measures use one published snapshot and the filter contract above. Ratios use sums of Gold components, never averages of precomputed class or school percentages.

| MetricId / display name | Definition | Missingness and filters |
| --- | --- | --- |
| `attendance_rate` / Attendance rate | `DIVIDE(SUM('FactAttendanceDay'[present_days]), SUM('FactAttendanceDay'[known_days]))` | Blank for zero known days. Show coverage beside it; format as a percentage. |
| `attendance_coverage` / Attendance coverage | `DIVIDE(SUM('FactAttendanceDay'[known_days]), SUM('FactAttendanceDay'[expected_days]))` | Blank for no opportunities; zero known out of positive expected days is valid zero coverage. |
| `selected_cohort_students` / Students in selected cohort | Distinct `FactAttendanceDay.student_id` after date-qualified membership filtering across the entire selection. | Zero for an empty but valid covered cohort. Do not sum daily distincts or count current `DimStudent` rows. |
| `rolling_attendance` / Rolling attendance rate | Apply `attendance_rate` over `[D-N+1,D+1)`, where D is the selected ending date and N is a positive user-selected number of calendar days. | Use expected opportunities inside that window; weekends are not absent days. Blank if the requested period falls outside declared calendar coverage or no known days exist. |
| `attendance_comparison` / Attendance change | For selected `[A,B)`, let L be its calendar-day length; subtract the rate for `[A-L,A)` from the rate for `[A,B)`. | Same cohort rules and snapshot, with effective membership evaluated in each period. Blank if either period is unsupported or has no known days. The result is a difference in percentage points, not relative growth. |
| `assessment_administrations` / Recorded assessment administrations | Distinct `FactAssessment.result_id` in the selected school, class, label, subject, window and date context. | Zero for an empty but valid event selection. This is not test participation or distinct learners. Retain captured events with null scores; no invented failed test. |
| `coursework_score_ratio` / Coursework score | `DIVIDE(CALCULATE(SUM('FactSubmission'[score]), 'FactSubmission'[is_graded], 'FactSubmission'[is_latest_attempt]), CALCULATE(SUM('FactSubmission'[points_possible]), 'FactSubmission'[is_graded], 'FactSubmission'[is_latest_attempt]))` | A ratio of sums, never an average of per-task percentages, so a large task cannot be outweighed by a small one. `is_latest_attempt` filters both operands so a resubmission is not counted twice. Blank when the selection holds no graded latest attempt; unmarked work is excluded rather than scored zero. Show `graded_work_coverage` beside it, and do not present subjects with different mark schemes as one comparable scale. |
| `graded_work_coverage` / Graded work coverage | `DIVIDE(CALCULATE(COUNTROWS('FactSubmission'), 'FactSubmission'[is_graded], 'FactSubmission'[is_latest_attempt]), CALCULATE(COUNTROWS('FactSubmission'), 'FactSubmission'[is_latest_attempt]))` | Blank when the selection holds no latest attempt. A low value means recorded work carries no score yet, not that it was failed or missing. It is the base that makes `coursework_score_ratio` readable: a high ratio over a small marked share is not high achievement. |

Dated detailed attendance is the source for arbitrary date, class and teacher filters. `AggSchoolAttendance` is usable only when its stored period and grade exactly match the request; for school totals sum its day components, but calculate cross-cell distinct learners from the detail unless disjointness is established. Never expose detailed learner rows to a district consumer to enable this calculation.

The same filters apply to numerator, denominator and coverage. Snapshot `as_of` must not substitute for business date, test date or source observation time. These formulas are specifications; native DAX expressions and filter behavior require runtime tests during implementation.

## Pipeline result

`GoldPublication` records at least:

```json
{
  "snapshot_id": "<sha256>",
  "as_of": "<utc timestamp>",
  "period_start": "<YYYY-MM-DD>",
  "period_end": "<YYYY-MM-DD>",
  "silver_lakehouse_name": "EDU_SL",
  "table_row_counts": "{\"FactAttendanceDay\": 0, \"...\": 0}",
  "published_at": "<utc timestamp>"
}
```

Any validation or write failure must fail the notebook job and prevent publication, so an interrupted refresh never produces a publication row.

## Acceptance criteria

1. Installer `PlanOnly` validates and prepares every Gold notebook and the pipeline without contacting Fabric, and proves no Lakehouse placeholder survives substitution.
2. Installer creates or reuses `EDU_GD` and imports the shared configuration, both notebooks and the pipeline with correct default-Lakehouse metadata and resolved item IDs.
3. The schema notebook creates exactly the 17 contract-defined tables plus `GoldPublication`, with 145 business columns and 34 common technical columns.
4. Every physical schema matches the declared column order and type; declared keys resolve to physical columns.
5. A rerun creates no unintended table versions and never drops or truncates an existing table.
6. Enrichment fails before the first Gold write when a Silver input contract is broken, when a required value is null, when an attendance status is null or unmapped, and when the reporting period is unset.
7. Each target has one row per declared grain, unique keys, no null required values, resolved foreign keys, and membership and date bounds inside the declared period.
8. Attendance arithmetic holds at every scope: `expected_days = known_days + unknown_days` and `known_days = present_days + absent_days`.
9. `AggSchoolAttendance` component sums equal the corresponding `FactAttendanceDay` sums for the same scope, and distinct learner counts are never summed across cells.
10. Null scores are preserved as null; no zero-filling occurs anywhere in the transformation path.
11. Exactly one `snapshot_id` and one `as_of` appear across the published bundle, and the newest `GoldPublication` row names that snapshot.
12. A refresh that fails partway leaves the previously published snapshot complete and still named by the newest publication row; the abandoned candidate is cleared by the next run.
13. A retry over unchanged Silver versions and an unchanged transformation produces the same `snapshot_id` and replaces its own candidate rows rather than duplicating facts.
14. Reinstalling without `PeriodStart` preserves the configured reporting period, and reinstalling without `OverwriteSharedConfigNotebook` leaves an existing shared configuration notebook untouched.
15. Row counts reconcile to their Silver sources, including the fixture reconciliation for the current school year: **324,000 expected days; 301,325 present; 22,675 absent; 93.00 per cent**, with unknown coverage preserved separately; **10,800 assessment administrations**; state and attempt counts reconciled independently, because state counts are not attempt counts.
16. Tests cover missing and zero scores, unknown attendance, zero versus blank denominators, multiple classes and co-teachers, exact rolling and prior-window boundaries, and per-day teacher and class scope.
17. Direct calculations agree with aggregates and semantic measures at school, class, learner and period scope, including out-of-range dates, late and early enrollment and nonadditive distinct counts.
18. Replay, a failed target write and a failed publication all recover without duplicate facts or advanced failure watermarks.
19. Student-level outputs stay restricted; the district use case consumes school, grade and period aggregates only.
20. Coursework achievement is additive and non-breaking: every pre-existing column keeps its values, `is_graded` equals `score IS NOT NULL AND COALESCE(points_possible, 0) > 0` exactly in both directions, a graded score sits within `[0, points_possible]`, exactly one `is_latest_attempt` is true per obligation, `subject` matches the section's course on every row, `is_scored` equals `score IS NOT NULL` exactly, and `is_late` equals `Submission.source_late` including its nulls.

21. Teacher actions: every Silver action in the period appears once in `FactStudentAction`; each lies inside the learner's school membership and, when it names a class, inside both the learner's class membership and the teacher's assignment on that date; window components satisfy `absent <= known <= expected <= window_days`; exactly one `is_first_in_category` per learner and category; and the fixture reconciles to **1,486 actions for 787 learners, 81 open, 629 learners meeting the 5-in-20 rule, 416 chronically absent at 10%, and 536 learners compared with absence 28.99% before and 11.94% after their first attendance action**. Coursework follow-ups reconcile to **310 learners compared, 61.03% missing before and 21.48% after**.
22. Two school years: the previous year reconciles to **315,540 expected days, 24,000 absent, 92.39 per cent**, and attendance by school to the manifest; `FactEnrollment` holds one row per membership per overlapping school year, uses only the documented categories, and reconciles to **1,064 continuing, 45 transferred in and 691 new learners this year, and 1,064 continuing, 45 transferred out, 585 completed final grade and 59 left from last year**; and every school carries a postal address on `DimSchool`.

These figures were reproduced by running the notebook SQL on local Spark against the sample CSVs (actions 1,486 for 787 learners, 81 open).

Real service verification still requires an approved Fabric integration run; local validation alone does not establish it.

## Deferred work

- Incremental processing through Change Data Feed, including source-side feed retention guarantees.
- A present, absent and excused split in `FactAttendanceDay`, which requires a reviewed widening of the Gold contract.
- Attended-minutes measures, assessment instrument version and assessment window sequence, none of which are available in the current Gold contract.
- Growth, proficiency, norm-referenced, risk and intervention-effect outputs.
- Effective-obligation and expected-work rates, which need eligibility inputs that Gold does not carry.
- `FactTaskSnapshot` and `AggSchoolWork`.
