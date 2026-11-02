# Silver Data Model Creation Specification

## Purpose

Define the deployable Microsoft Fabric artifacts required to create the Silver Lakehouse and its empty, typed Delta tables from the authoritative CSV model definitions. This specification covers Lakehouse creation and physical table definitions only. Bronze-to-Silver transformation and data population are separate work.

## Authoritative inputs

| Input | Role |
| --- | --- |
| [Silver schema notebook](../../src/fabric/notebooks/EDU_SL_CreateSchema.ipynb) | Deployable source of truth for 24 physical tables, 158 ordered columns, types, logical nullability, primary keys and foreign keys |
| [Silver_Data_Model.csv](../data-models/Silver_Data_Model.csv) | Repository design evidence with grains, purposes, Bronze dependencies and source rules; not deployed to Fabric |
| [Model_Relationships.csv](../data-models/Model_Relationships.csv) | Repository relationship design evidence; not deployed to Fabric |
| [Bronze schema notebook](../../src/fabric/notebooks/EDU_BR_CreateSchema.ipynb) | Creates or verifies the 28 source-qualified Bronze tables and two control tables |
| [Bronze ingestion notebook](../../src/fabric/notebooks/EDU_BR_Ingestion.ipynb) | Validates and loads source rows into pre-created Bronze tables |

The notebook embeds the compact physical schema required by workload users. Repository validation must mechanically compare that literal to the two design CSVs so changes cannot drift silently. Fabric execution has no runtime dependency on those CSVs.

## Target artifacts

The installation script creates or reuses these Fabric items in the selected workspace:

| Artifact | Default name | Responsibility |
| --- | --- | --- |
| Shared configuration notebook | `EDU_Config` | Future common artifact names, Lakehouse references and reusable helpers |
| Bronze Lakehouse | `EDU_BR` | Raw source tables and landing files |
| Bronze schema notebook | `EDU_BR_CreateSchema` | Create or verify Bronze source and control tables |
| Bronze ingestion notebook | `EDU_BR_Ingestion` | Validated Bronze ingestion |
| Silver Lakehouse | `EDU_SL` | Dedicated home for the 24 retained Silver Delta tables |
| Silver schema notebook | `EDU_SL_CreateSchema` | Validate model contracts and create/verify empty physical tables |

The Silver notebook uses `EDU_SL` as its default Lakehouse. A dedicated Silver Lakehouse makes an additional `silver` schema redundant; tables use the default Lakehouse namespace.

## Artifact naming convention

Follow the established Nonprofit Data Solutions pattern:

```text
<solution>_<layer>_<action-or-flow>
```

| Token | Meaning | Examples |
| --- | --- | --- |
| `EDU` | Education Analytics solution prefix | `EDU_Config` |
| `BR` | Bronze layer | `EDU_BR`, `EDU_BR_CreateSchema`, `EDU_BR_Ingestion` |
| `SL` | Silver layer | `EDU_SL`, `EDU_SL_CreateSchema` |
| `GD` | Gold layer | `EDU_GD`, `EDU_GD_CreateSchema` |
| `BR_SL` | Bronze-to-Silver flow | `EDU_BR_SL_Transform` |
| `SL_GD` | Silver-to-Gold flow | `EDU_SL_GD_Enrichment` |

Repository notebook filenames use the same artifact name with an `.ipynb` extension, for example `EDU_SL_CreateSchema.ipynb`. Fabric item names omit the extension.

The `EDU_Bronze` Lakehouse predates this convention and remains in place to preserve its Fabric item ID and data. Bronze schema creation and ingestion use the convention-aligned `EDU_BR_CreateSchema` and `EDU_BR_Ingestion` names.

Any future Lakehouse rename to `EDU_BR` must be a controlled migration that preserves the Fabric item ID and does not recreate or reload unchanged Bronze tables.

## Notebook parameters

The notebook parameters default to:

```python
allow_destructive_changes = False
exit_notebook_on_success = True
```

## Installer changes

Extend `deploy/Install-IntoWorkspace.ps1` without duplicating its Fabric CLI helpers.

1. Add `SilverLakehouseBaseName`, defaulting to `SL`.
2. Add `SilverNotebookBaseName`, defaulting to `SL_CreateSchema`.
3. Create or reuse `${Prefix}${SilverLakehouseBaseName}` after the Bronze Lakehouse step.
4. Prepare a temporary copy of the Silver notebook and inject the Silver workspace/Lakehouse ID and name into its Fabric dependency metadata.
5. Import the notebook with `fab import --force`, preserving the existing item ID on reruns.
6. Optionally execute it synchronously with `fab job run`.
7. Include both Silver artifacts in the installation summary.

The existing `RunNotebook` behavior must remain backward compatible for Bronze. Add an explicit `RunSilverCreateSchemaNotebook` switch; a later orchestration change can introduce a single `RunAll` option.

`PlanOnly` must parse both notebook definitions, generate both prepared notebook definitions, and make no Fabric changes. Repository tests separately compare the embedded Silver contract with the design CSVs.

## Notebook responsibilities

The Silver model notebook performs these stages in order:

1. Validate that a default Silver Lakehouse is attached.
2. Load the embedded ordered physical-schema dictionary.
3. Require exactly 24 distinct tables, 158 columns and 34 foreign-key relationships.
4. Reject duplicate table/column definitions, duplicate primary keys, unsupported data types, invalid boolean flags and malformed `Table.column` foreign-key references.
5. Require every table to have exactly one primary key and every declared foreign key to resolve to a declared table/column.
6. Topologically validate table dependencies and fail on cycles.
7. Build a PySpark `StructType` for every table in embedded tuple order.
8. Create missing empty Delta tables in dependency order.
9. Compare existing tables to the contract and skip exact matches without producing new Delta versions.
10. Fail on missing, extra, reordered, mistyped or logical-contract metadata drift unless destructive changes are explicitly enabled.
11. Return a compact JSON result for pipeline orchestration.

This notebook does not read Bronze data, derive canonical keys, populate rows, enforce business relationships or calculate metrics.

## Type mapping

Only types present in the current Silver model are allowed:

| Model type | PySpark type |
| --- | --- |
| `STRING` | `StringType()` |
| `DATE` | `DateType()` |
| `TIMESTAMP` | `TimestampType()` |
| `INT` | `IntegerType()` |
| `DOUBLE` | `DoubleType()` |
| `BOOLEAN` | `BooleanType()` |

Unknown or parameterized types fail validation. Type expansion requires an approved model CSV change and a notebook test.

## Table inventory

| Creation group | Table | Columns | Primary key | Grain |
| ---: | --- | ---: | --- | --- |
| 1 | `District` | 3 | `district_id` | District |
| 1 | `Student` | 5 | `student_id` | Student |
| 1 | `Course` | 5 | `course_id` | catalog course |
| 1 | `AcademicTerm` | 3 | `term_id` | school year from the SIS terms extract |
| 1 | `AssessmentInstrument` | 5 | `assessment_id` | source test label and subject within the input package |
| 1 | `AssessmentWindow` | 6 | `window_id` | instrument window label |
| 1 | `ActionType` | 3 | `action_type_id` | governed teacher action type |
| 2 | `School` | 9 | `school_id` | School |
| 3 | `SchoolAddress` | 7 | `school_id` | school postal address; the key is also the reference to `School` |
| 3 | `Teacher` | 6 | `teacher_id` | Teacher |
| 3 | `Section` | 8 | `section_id` | Section |
| 3 | `SchoolEnrollment` | 7 | `enrollment_id` | student-school effective interval |
| 3 | `SourceIdentity` | 5 | `mapping_id` | source instance/entity/user |
| 3 | `CalendarDay` | 5 | `calendar_id` | school-instructional day |
| 3 | `AssessmentResult` | 9 | `result_id` | source test event |
| 4 | `SectionEnrollment` | 6 | `enrollment_id` | student-section interval |
| 4 | `TeacherAssignment` | 6 | `assignment_id` | teacher-section interval |
| 4 | `InterventionAction` | 14 | `action_id` | teacher-logged learner action; `section_id` is an optional foreign key |
| 4 | `LmsSection` | 5 | `mapping_id` | source instance/LMS class |
| 4 | `Attendance` | 7 | `attendance_id` | student-school-day observation |
| 4 | `LearningContent` | 8 | `content_id` | LMS assignment |
| 5 | `Obligation` | 7 | `obligation_id` | learner-content base audience interval |
| 6 | `SubmissionState` | 7 | `state_id` | student-task observed snapshot |
| 6 | `Submission` | 12 | `submission_id` | student-task-source attempt |

Creation groups are dependency levels, not transformation execution groups. Tables within a group may be created in parallel after all earlier groups succeed.

## Delta metadata and constraints

For each column, preserve the compact logical contract metadata in the Spark schema:

```json
{
  "primaryKey": true,
  "declaredNullable": false,
  "foreignKey": null
}
```

Fabric Delta normalizes columns created by an empty DataFrame to physically nullable fields. The notebook therefore preserves the CSV model's requiredness as `declaredNullable` field metadata and validates that logical declaration on reruns; it does not claim that the Delta physical schema enforces `NOT NULL`.

Delta tables created through Spark also do not enforce the CSV model's primary-key and foreign-key semantics. The notebook records those declarations as metadata and validates their definitions, but required-value, uniqueness and referential-integrity checks belong to the later transformation/data-quality notebook.

Rich table purposes, column descriptions, Bronze mappings and use-case notes remain in `Silver_Data_Model.csv` for repository review; they are intentionally omitted from the compact runtime schema literal. Do not add ingestion columns such as `LoadBatchId` to the 24 business tables unless they are first approved in the design model and embedded contract. Snapshot or load metadata should use a separately approved operational table rather than silently changing every business schema.

## Idempotency and drift policy

The model-creation notebook is idempotent:

- Missing table: create an empty Delta table.
- Existing exact schema: report `SKIPPED_MATCHING` and perform no write.
- Existing compatible table with data: leave data and schema unchanged.
- Existing schema drift: fail with an exact table/column/type/logical-metadata difference.
- Contract removes or renames a table/column: fail; never drop automatically.
- `allow_destructive_changes = True`: reserved for controlled development rebuilds and must not be the deployment default.

The notebook must not overwrite populated Silver tables merely to reapply a matching schema.

## Pipeline result

Return JSON with at least:

```json
{
  "status": "SUCCEEDED",
  "tablesExpected": 21,
  "tablesCreated": 0,
  "tablesSkipped": 21,
  "tablesFailed": 0,
  "columnsValidated": 134,
  "relationshipsValidated": 28,
  "schemaContractHash": "<sha256>"
}
```

Any validation or table-creation failure must fail the notebook job and prevent a successful pipeline result.

## Acceptance criteria

1. Installer `PlanOnly` validates and prepares the Silver notebook without contacting Fabric.
2. Installer creates or reuses `EDU_SL` and imports `EDU_SL_CreateSchema` with the correct default Lakehouse metadata.
3. First notebook run creates exactly the 24 contract-defined empty Delta tables with 158 columns in total.
4. Every physical table schema matches CSV column order and type; logical nullability, primary keys and foreign keys match field metadata.
5. Every declared primary key and all 28 logical Silver relationships resolve to physical columns.
6. Second run creates no table versions and reports 24 `SKIPPED_MATCHING` tables.
7. Adding an unsupported type, duplicate column, broken foreign key or dependency cycle causes a clear validation failure before table creation.
8. Existing populated tables are never truncated or overwritten by the model-creation notebook.
9. The installer remains safe to rerun and preserves Fabric item IDs.
10. Bronze deployment and its existing `RunNotebook` behavior remain unchanged.
11. A repository parity check proves that the embedded physical schema matches all 134 rows and 28 foreign keys in the design CSVs.

## Deferred work

- Bronze-to-Silver transformation logic and canonical key derivation.
- Data population ordering, incremental processing and snapshot publication.
- Primary-key uniqueness, foreign-key integrity and business-rule checks over populated data.
- Silver operational audit-table design.
- Gold Lakehouse and model creation.
- Pipeline orchestration across Bronze ingestion, Silver model creation and Silver transformation.
