# Official Schema Evidence and Analytics Readiness

Research date: **2026-09-14**. Scope: PowerSchool SIS, local open-source Canvas, Moodle, and NWEA MAP Growth. The existing Silver workbook is unchanged: **28 tables, 345 columns**.

## Executive decision

**Current scope: synthetic-only software engineering, with no institutional pilots or real-data access dependency.** Use the captured schemas and [synthetic sample package](../../../sample-data/README.md) to specify and test source-to-Silver transformations. Documented assumptions are acceptable fixture contracts, but must not be presented as verified vendor behavior.

We retrieved official schema metadata and implementation evidence, not student records. Public research can confirm a published interface, but cannot establish installed versions, permissions, populated fields, historical depth, or cross-system matches. **Live tenant records tested: 0.** The source guides' tenant requests and approvals are future compatibility considerations, not current project prerequisites.

| Source | What was actually retrieved | Strength of evidence | Future deployment verification only |
| --- | --- | --- | --- |
| Canvas | 144 official Swagger resource documents; 2,526 declared property rows; 118 fields in 17 SIS import formats; live endpoint documentation | Public REST declarations and behavior; import schemas kept separate | Local deployed-build parity, permitted responses, complete pagination, grade/override reconciliation; do not assume hosted New Quizzes is included locally |
| Moodle | v5.0.2 official source pinned to a commit: 487 tables and 4,430 fields from 83 non-test XMLDB files; selected external-function definitions | Reproducible reference storage schema and selected API contracts | Installed release/plugins, token-visible functions, generated site API docs, authorized log access and history |
| NWEA | Official export dictionary: 179 entries across six export sheets | 165 literal field entries and 14 compressed family templates; not a fixed expanded header count | Actual Comprehensive headers/options, testing windows/norms, valid-versus-all-attempt scope, entitled current API spec if used |
| PowerSchool | Current official SIS help: dictionary location, selected exact fields/import labels, contacts, calendar, section and attendance semantics | Public concepts and selected names; not a full SQL/API schema | Authorized in-product dictionary, selected export/view definitions, code/denominator metadata, sample payloads |

Counts measure **schema metadata**, not student records, unique business concepts, deployable API coverage, or the fraction of Silver populated. The 7,074 LMS rows mix three explicitly labelled interfaces and must not be added into a readiness percentage. Moodle v5.0.2 is a research reference, not a deployment recommendation.

## Read the evidence

- [canvas-official-schema.md](canvas-official-schema.md): exact REST fields and routes, inbound CSV distinction, scopes, history, assessment/standards, all 28 Silver tables and tenant checks.
- [moodle-official-schema.md](moodle-official-schema.md): pinned XMLDB versus API definitions, identifiers, completion, grades, logs, overrides, all 28 Silver tables and tenant checks.
- [powerschool-official-schema.md](powerschool-official-schema.md): exact public evidence, current dictionary access, unsuccessful routes, and administrator request package.
- [nwea-official-schema.md](nwea-official-schema.md): export types, field families, contradictory declarations, current norms guidance, API limits and administrator request package.
- [lms-field-evidence.csv](lms-field-evidence.csv): 7,074 extracted schema fields with interface, declared type, evidence URL, version and document hash. It is not a data-extraction allowlist.
- [nwea-export-fields.csv](nwea-export-fields.csv): all 179 published dictionary entries with sheet/cell references. Repeated templates remain templates.
- [silver-field-readiness.csv](silver-field-readiness.csv): one row for each of the actual workbook's 345 columns, with declared requirement/grain, selected source candidates, evidence URLs, disposition and unresolved decision.
- [build_silver_register.py](build_silver_register.py): reproducible generator and offline validator for that register. Requires Python and `openpyxl` (validated with 3.1.5); run from the accelerator folder with `python "docs/research/official-schemas/build_silver_register.py" --check`. Omit `--check` to regenerate after reviewed mapping changes. The workbook hash guard deliberately rejects an unreviewed model revision.

The source guides contain successful official URLs, checked dates, version boundaries and blocked routes. Raw vendor documents were inspected but not checked into this repository. Field inventories preserve metadata rather than entire copyrighted documentation. Source hashes identify snapshots; they cannot reconstruct a document if the vendor changes it.

### Field-level triage

The register covers every target column, **not every possible source-to-target mapping**. Candidate mappings were explicitly selected and checked against the captured field inventories; no fuzzy name matching was used. Moodle candidates labelled database XMLDB require authorized storage access or a separately verified API equivalent. PowerSchool's public UI concepts do not become invented SQL/API field paths. A candidate can require a join, pseudonymization, a grain change, or an extension and is not an approved direct copy.

| Disposition group | Columns | Meaning |
| --- | ---: | --- |
| Selected documented candidates | 56 | Official metadata contains selected related fields; transformations, authority and tenant availability still need approval |
| Canonical IDs and foreign-key crosswalks | 77 | 17 canonical keys plus 60 links require conformance; native source IDs alone do not satisfy them |
| Lineage, platform metadata and reference data | 133 | 104 lineage fields, 13 metadata fields and 16 reference fields require platform policies/configuration |
| Derived signals, metrics and workflow | 49 | 20 derivations, 15 platform derivations and 14 workflow fields need tested logic or operational capture |
| Policy, tenant or unestablished optional input | 30 | 21 tenant-evidence fields, 3 derivation-or-tenant fields, 5 policy/evidence fields and 1 unestablished optional input |
| **Total** | **345** | Classification of target columns, not measured data completeness |

All rows have `TenantValidation=Not performed`. Foreign-key and lineage classification is not evidence that their source inputs are available. Unselected mappings remain unresolved rather than being marked unsupported. For current development, specify semantic fit and source priority in the synthetic contracts and verify them against known fixture results. Institutional approval would apply only to a separately scoped live-data integration.

## Cross-source overlap and ownership

This summary preserves the useful comparisons from the retired conceptual assessment without its unsupported percentage scores or a second manually maintained coverage matrix. Use the field register and source guides for evidence details.

| Intersection | Shared concepts | Engineering rule |
| --- | --- | --- |
| Canvas and Moodle | Users, course shells, enrollment, learning content, submissions, grades, completion and activity concepts | Reuse canonical concepts, not raw schemas. Keep contextual grades, completion states and event grains distinct; Moodle topics are not classroom sections |
| PowerSchool and the LMSs | Learner identity, roster, course/class structure, enrollment and teaching assignments | Treat the proposed SIS extract as the official-roster authority within our synthetic scenario; map LMS delivery separately |
| PowerSchool and NWEA | Student/school identifiers, grade and term context; optional class/teacher roster labels | Derive links from scoped source identifiers; do not require a supplied synthetic crosswalk. NWEA class/program labels do not constitute a complete authoritative catalog |
| All four | Source identity and time context | Namespace IDs by source instance and entity type. Equal numeric IDs or similar names do not establish equivalence |
| Platform-owned | Lineage, canonical identifiers, reference mappings, derived signals, recommendations and intervention outcomes | Generate or capture these explicitly; they are not missing vendor fields |

Potential geography enrichment and governed student characteristics remain optional, use-case-driven extensions. Do not introduce real personal data or additional external connectors to fill optional fields for this synthetic build.

## Findings that change the design

| Finding | Consequence for Bronze / Silver |
| --- | --- |
| Canvas SIS `user_id` is an external provisioning identifier; REST `User.id` is internal | Separate import fixtures from REST extracts. Map `sis_user_id` explicitly; never join bare IDs across instances |
| General Canvas Submission has no declared `id`; Classic QuizSubmission does | Use source-qualified assignment/user/attempt identity for the former and the documented quiz-attempt ID for the latter |
| Canvas `include[]=read_status` can mark submissions read | Exclude this include from passive extraction. Audit other observational APIs for side effects |
| Canvas page-view documentation warns against isolated high-stakes use | Do not use clicks alone as attendance or definitive individual engagement evidence |
| Moodle `course_sections` contains topics; `user_enrolments` does not contain user roles | Do not manufacture classroom sections from topics. Join context-aware roles separately; respect source API response grain |
| Moodle logs have no universal active-time field; completion is not a percentage or proof of mastery | Keep durations unknown or explicitly estimated; derive counts/ratios with a valid denominator and coverage indicator |
| NWEA Combined does not list `TestID` or `GrowthMeasureYN`; Comprehensive does | Prefer Comprehensive for event-level joins and growth eligibility, subject to actual header validation |
| NWEA's dictionary has repeated families, type conflicts and stale 2020-norms wording; current help points to 2025 norms | Preserve raw headers and values, norms reference and score scale. Do not invent expanded columns, hard-code a norm year, or coerce all values blindly |
| NWEA valid-result exports omit some attempted/invalid-test populations | They cannot alone provide an assessment participation denominator or complete attempt history |
| PowerSchool calendar membership/conversion rules and end-exclusive class exit dates affect metrics | Acquire calendar and attendance rules; apply effective-date semantics per entity, not globally |
| The Silver model already includes source-ID mapping, teacher-assignment dates, submission DueDate and attendance ExpectedMinutes | Extend or populate existing structures; do not describe these fields as absent. The gaps are richer relationships, policy, provenance and source evidence |

## Required Silver decisions

These are **proposals, not applied workbook changes**.

| Priority | Existing target | Missing contract or representation | Analytics affected |
| --- | --- | --- | --- |
| P0 | Source / SourceSystemIdMapping | Instance-qualified IDs; mapping evidence/effective dates; extract schema/build/options/hash; source time separate from load time | All cross-source joins and reproducibility |
| P0 | School / Course / Section / Enrollment / AcademicTerm | Approved organizational, catalog, class and term crosswalks; enrollment grain and effective-interval rules | Cohorts, rosters, attribution and teacher views |
| P0 | Attendance / AttendanceStatus | Instructional calendar, track/period schedules, expected-opportunity records, code conversions and excusal policy | Attendance and chronic absence denominators |
| P0 | LearningContent / AssignmentSubmission | Audience/override/group membership, effective deadlines, excused/visible/posted states, grading policy, regrade history | Missing work, late work, scores and course grades |
| P0 | Assessment / AssessmentResult | Scale, percentile, standard error, eligibility, norms/WI, administration, paired growth observations and multiple component results | Growth, proficiency, skill-gap recommendations |
| P1 | DigitalEngagement / ContentUsage | Event versus snapshot/aggregate grain, observation coverage, duration derivation and completion rules | Engagement and content usage |
| P1 | StudentSignal / InterventionAction | Evidence/version metadata, recommendation review, status history, structured baseline/follow-up metric, dates and unit | Explainable recommendations and outcome tracking |
| P1 | LearningContent.StandardCode | Versioned many-to-many content/outcome/competency/assessment-domain alignment | Targeted remediation and content effectiveness |
| P1 | Person and student support | Governed guardian/support relationships and accommodations where actually needed | Approved outreach and contextual analysis |
| P1 | Course-grade results | Separate official grade and LMS calculated-grade snapshots, scale, term/store code and policy | Course performance; avoid mixing with MAP results |

Do not add Entra identity, a new SIS, a new assessment provider or other connectors to the hackathon scope just to fill optional fields. `Person.AadObjectIdPseudonym` has no established authoritative source in these four contracts and can remain unavailable. K-12-oriented PowerSchool/MAP coverage does not establish equivalent higher-education assessment or registrar coverage; certify each population separately.

## What can proceed now

1. Freeze selected source-shaped fixture contracts and field allowlists. Keep all four source workstreams; synthetic data is the primary strategy, not a temporary dependency on eventual school access.
2. Specify identifiers, grains, states, times, denominators and privacy boundaries using these findings; preserve original values alongside canonical mappings.
3. Start from the primary district-scale sample: 1,800 students in three schools, with 28 source tables and no precomputed shared mapping CSVs. Derive identities during transformation; obtain source-instance context from pipeline configuration. Extend the fixtures with regrades, overrides, transfers and missing test pairs as those capabilities are implemented; those cases are not all present today.
4. Implement Bronze-to-Silver transformations and calculate golden metrics from the produced Silver tables. The current sample validator checks fixtures, not a completed transformation pipeline.

## Current engineering acceptance gates

- Validate selected field names, types and explicitly documented assumptions against the captured evidence. Do not claim full vendor-schema validation for partial records.
- Derive source-qualified identity links from the source records, without precomputed crosswalk inputs. Required joins must resolve in the positive fixture; deliberately ambiguous or unmatched negative cases must be reported or quarantined.
- Preserve lineage, raw values and declared grains. Reprocessing the same batch must not duplicate logical records.
- Reconcile output counts and analytics with [the sample's expected results](../../../sample-data/README.md#cohort-and-known-answers), using the declared denominators and windows.
- Verify missing versus zero, null timestamps, score scales and completion semantics. A metric without a valid denominator is not computable.
- Keep optional/unrepresented capabilities explicit rather than filling all 28 Silver tables artificially. No private credentials, real records, tenant deployment or pilot is needed to pass these engineering gates.

### Data-quality reporting checklist

| Measure | Definition / test expectation |
| --- | --- |
| Identity resolution | Matched, unmatched and ambiguous source identities by source and school; positive fixture resolves through explicit source identifiers, with missing/duplicate identifiers rejected |
| Class and enrollment reconciliation | Validate explicit source-to-class mappings and active membership windows; do not compare different LMS courses as if their rosters must agree |
| Assessment joins | Every positive-fixture test event links to exactly one synthetic student; report unresolved identities separately |
| Attendance code mapping | Every positive-fixture code resolves through the declared policy; unknown codes become explicit exceptions |
| Referential integrity | Required foreign keys resolve; negative-test orphans are quarantined or reported according to the contract |
| Duplicate business keys | Zero unintended duplicates at the declared grain; preserve legitimate snapshots and attempts separately |
| Freshness and history | Compare event/extract time to a fixed test clock and fixture window, not today's clock for a historical dataset |
| Duration provenance | Distinguish source-observed, estimated and unavailable durations; never silently turn unavailable activity into zero |

The old percentage targets were proposals, not measured or approved gates. Prefer exact known outcomes for deterministic fixtures; define tolerances only where a test scenario explicitly requires them.

## Future tenant compatibility only

Retained as reference for a possible separately authorized integration. These requests are **not a backlog dependency for this project**, and no institutional pilot is planned.

| Evidence package | Obtain from | Required content |
| --- | --- | --- |
| PowerSchool schema and export | Authorized SIS administrator | In-product dictionary under intended read role; enabled plugin/view/export schema; attendance/calendar/code conversions; school/year scope; de-identified samples |
| Canvas deployment and extract | Local Canvas administrator | Build, features, permitted resources/includes, SIS IDs, representative REST responses and UI totals, history/retention and override cases |
| Moodle deployment and extract | Moodle administrator | Release/plugins, `core_webservice_get_site_info`, service allowlist, generated API docs, response wrappers, completion/grade configuration, approved log route |
| NWEA assessment package | Assessment coordinator or entitled integration owner | Comprehensive ZIP with optional files; actual repeated headers; Manage Terms windows/WI; norms reference; matching source reports; separate invalid-attempt report if participation is required |
| Shared linkage and governance | Data steward / education owner | Approved crosswalk, authority per field, valid populations, retention, permitted AI fields, sensitive-data access, interpretation policy |

Do not paste credentials or student records into chat or commit them. Use approved de-identification that preserves stable relationship keys. Collect metadata first, then a small authorized common cohort and overlapping term; growth needs comparable prior windows.

## Future live-data acceptance gates

- Every critical input has official evidence, an approved mapping, and an observed target-environment value or a tested derivation. Unknown is not unavailable, and neither is zero.
- Check matched, unmatched, ambiguous and excluded populations per school/source/time. Review false matches, not only a high aggregate match rate.
- Reconcile scoped source counts and reports; detect incomplete pagination, permission loss, masked data, deletions and late corrections.
- Prove correct denominators, effective deadlines, score scales, test eligibility and norms. No valid denominator means **not computable**, not zero.
- Reproduce a prior calculation from its source snapshot, mapping/rule version and evidence. A current-state API does not establish unlimited history.
- Validate intervention completion independently of recommendations. Before/after changes are associations, not causal impact.
- Approve sensitive-field use and role/school isolation before live analytics or AI prompting.

No universal percentage certifies all analytics. For a future live integration, set thresholds with owners after profiling, and approve readiness separately for roster, attendance, assignment, assessment, engagement and intervention workflows. This does not limit current synthetic contract and transformation testing.