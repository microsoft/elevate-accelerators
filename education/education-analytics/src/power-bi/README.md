# Education Analytics — Power BI report

A working, editable Power BI report and semantic model over the **Gold** layer of the
Education Analytics solution. It is built as a **PBIP** project, so the semantic model
(TMDL) and the report (PBIR) are plain text and reviewable in git.

| | |
|---|---|
| Open with | `EducationAnalytics.pbip` in Power BI Desktop |
| Semantic model | `EducationAnalytics.SemanticModel` — 21 tables, 193 columns, 106 measures, 28 relationships, plus 24 hidden automatic date tables ([why](#editing-it-in-power-bi-desktop)) |
| Report | `EducationAnalytics.Report` — 6 pages, 78 visuals |
| Storage mode | Import, via the Gold Lakehouse SQL analytics endpoint |
| Source | `EDU_GD` lakehouse |
| Theme | The supplied template `d365_Fundraising_Intelligence.pbit` (*Tema TSI*), applied as the report theme |

Field and measure descriptions are written in plain language and appear as tooltips in the
field list, so a reader can hover any figure to see what it means.

## Connecting it to your environment

The model reads three parameters. Change them in Power BI Desktop under
**Transform data → Edit parameters**; nothing else is environment-specific.

| Parameter | Meaning |
|---|---|
| `GoldSqlEndpoint` | Fully qualified SQL analytics endpoint of the Gold Lakehouse. **Ships empty on purpose** so no environment is baked into source control — set it before the first refresh. |
| `GoldDatabase` | Lakehouse name exposed through that endpoint (default `EDU_GD`) |
| `GoldSnapshotId` | Snapshot every Gold table loads. Empty — the default — means each table resolves the newest published snapshot on its own. The installer sets it for the duration of its refresh, then clears it again. |

`GoldSnapshotId` exists because each Gold table resolves its own snapshot. Fourteen
independent `SELECT TOP 1 snapshot_id FROM dbo.GoldPublication` lookups agree only while
nothing publishes; a publication that lands mid-refresh leaves tables loaded before it on
the old snapshot and tables loaded after it on the new one, which breaks relationships and
every measure built on them. Resolving the snapshot once and pinning it makes one refresh
load one bundle. Leave it empty for a scheduled refresh so the model keeps following the
published pointer — the superseded snapshot is retired after publication, so a stale pin
would load nothing.

To find the endpoint: open the **EDU_GD** lakehouse in Fabric, switch to the SQL analytics
endpoint, and copy its connection string. The endpoint host is shared by every item in the
workspace, so `GoldDatabase` is what selects the Gold Lakehouse.

A Lakehouse SQL analytics endpoint is expected to expose tables under the `dbo` schema
whether or not the Lakehouse itself uses Delta schemas, so each table's M query still
navigates `Schema = "dbo"` and was left unchanged by the move from a schema-enabled
Lakehouse to this one. That has not yet been exercised against `EDU_GD` — the first
refresh after setting `GoldSqlEndpoint` is the check. If a table fails to resolve, the
fix is the `Schema` value in that table's partition query, nothing else.

## Pages

Ordered from the widest view down to the narrowest: district, then school, then class,
then the individual student. New measures live on these pages rather than on pages of
their own: year-on-year and enrollment on District, early warning and follow-up on School
briefing, the attendance rule and actions per learner on Class review, and the actions
timeline, last year's attendance and marked work by subject and topic on Student review.

| Page | Use case | Audience | What it answers |
|---|---|---|---|
| District | UC5, UC8 | Head of district | School-level attendance for the same year group and period, against the same dates last school year; enrollment against last year with arrivals and leavers; the schools on a map; and marked work read one subject at a time, without ranking. Also the landing page: with a single district, the overview and the cross-school comparison are the same view |
| School briefing | UC3, UC7 | Head of school | Attendance and coverage for a chosen period; chronic absence and the attendance rule with thresholds you choose; actions logged by month and type; absence and missing work before and after a learner's first action; a records appendix by source and date |
| Assignment schedule | UC4 | Head of school | Assignment titles and due dates across classes for a chosen period, for coordinating workload |
| Class review | UC1, UC7 | Teacher | What was set, what students recorded against it, and what assessments were administered; per student, attendance, whether they met the attendance rule and how many actions were logged |
| Student review | UC2, UC6, UC7, UC8 | Teacher | One student on one page: attendance against last year, the actions logged for them on the same weekly timeline and in a list with what was observed before and after, their recorded assignments, test results, and where their marked work sits against the rest of the class by subject and by topic. Also the drillthrough target from the class pages |
| Definitions | — | All | Every metric definition, the reporting period, data freshness and the known limits |

Every page is filtered to the **latest school year** through a page filter on
`DimDate[School year scope]`. Change it in the Filters pane to read an earlier year. The
year-on-year measures shift the selected dates back 12 months themselves, so they still find
the previous year under that filter. The previous year holds membership, attendance and test
history only; class, coursework and action pages show the latest year.

The school map on *District* is an Azure Maps visual placed by
`DimSchool[Full address]`. It needs Azure Maps to be allowed in the Power BI tenant settings;
without it the visual shows a message and the rest of the page still works.

`Student review` is a drillthrough page bound to the student. Right-click a student on a
class page and choose **Drill through**.

Its Date slicer filters attendance, actions and tests. Marked work has no relationship to
`DimDate`, because a hand-in already carries its own timestamp and the class due date lives
on the assignment, so the marked-work card says *whole reporting period*. The Class slicer
also sets who the student is compared against. Select a subject in the subject chart to
narrow the topic table to it.

Every categorical slicer is a dropdown with a search box, so long lists stay usable. Date
slicers keep a range picker, where a dropdown of every date would be worse.

`District` carries a Subject slicer alongside School, Year group, Month and Period, and its
marked-work chart groups by subject with one bar per school inside each group. Marked work
is only comparable within one subject — subjects mark to their own schemes and set very
different amounts of work, so a school's subject mix would otherwise move a pooled bar on
its own. Grouping by subject first means the bars a reader naturally compares, the ones
sitting next to each other, are always the same subject. The Subject slicer narrows the
marked-work figures on that page; attendance carries no section, so it is unaffected.

Columns are named for the reader — `Source name`, `Due date`, `Class teacher` — while the
semantic model keeps the physical Gold column in `sourceColumn`, so the mapping to the
Gold contract is unchanged.

## Coverage matrix

| UC | Audience | Gold tables | Key fields | Measures | Page | Where AI could help |
|---|---|---|---|---|---|---|
| **UC1** Prepare a class review | Teacher | `DimSection`, `DimContent`, `FactSubmissionState`, `FactSubmission`, `DimStudent`, `FactAssessment`, `DimAssessment`, `DimWindow`, `BridgeTeacherSection`, `BridgeStudentSection` | `name`, `description`, `max_score`, `due_at`, `state`, `source_late`, `source_missing`, `score` | Classes, Students in Selected Classes, Attendance Rate / Coverage (Selected Classes), Assignments, Recorded Work States, Graded / Submitted / Unsubmitted / New States, Source-Flagged Late & Missing, Mean Recorded Score, Assessment Administrations, Students Assessed, Administrations with a Score, Mean Score (Selected Instrument) | Class review | Summarise what the class recorded and propose questions for the review. Must cite the figures shown and must not infer causes. |
| **UC2** Review a student's attendance and work | Teacher | `FactAttendanceDay`, `DimDate`, `DimStudent`, `FactSubmissionState`, `FactSubmission`, `DimContent`, `FactAssessment` | `present_days`, `known_days`, `expected_days`, `unknown_days`, `state`, `score`, `submitted_at` | Attendance Rate, Attendance Coverage, Attendance Rate (Prior Year), Present / Absent / Unknown Student-Days, Actions Logged, Recorded Submissions, Scored Submissions, Latest Recorded Submission, Mean Score / Standard Error | Student review | Draft factual observations and discussion questions for a teacher to review. Never a risk score or a prediction. |
| **UC3** School attendance and records briefing | Head of school | `FactAttendanceDay`, `DimDate`, `DimSchool`, `FactSubmissionState`, `FactAssessment`, `Rolling Window` | `present_days`, `known_days`, `expected_days`, `grade`, `date`, `state` | Attendance Rate, Rolling Attendance Rate, Attendance Change (pp), Attendance Coverage, Students in Selection, Recorded Work States, Assessment Administrations | School briefing | Organise the briefing and list questions to investigate, quoting period, coverage and cohort size. |
| **UC4** Assignment schedules across classes | Head of school | `DimSection`, `DimContent`, `BridgeTeacherSection`, `DimTeacher`, `DimSchool` | `subject`, `grade`, `Teacher`, `name`, `due_at`, `max_score` | Classes, Teachers, Subjects, Assignments, Assignments with a Due Date, Mean Assignment Max Score | Assignment schedule | Point out dates where several classes set work at once, as scheduling observations only. |
| **UC5** Cross-school attendance briefing | Head of district | `FactAttendanceDay`, `DimSchool`, `DimDate` | `present_days`, `known_days`, `expected_days`, `student_id`, `grade` | Students in Selection, Attendance Rate, Attendance Coverage, Present / Known / Expected Student-Days | District | Describe attendance patterns and questions for school leaders. Must not rank schools or claim causes. |
| **UC6** Review a student's performance | Teacher | `FactSubmission`, `DimContent`, `FactSubmissionState`, `DimStudent`, `DimSection`, `FactAssessment`, `DimAssessment`, `DimWindow` | `score`, `points_possible`, `is_graded`, `is_late`, `is_latest_attempt`, `subject`, `name`, `is_scored` | Marked Work Score, Cohort Marked Work Score, Difference from Cohort (pp), Marked Work Coverage, Marks Earned / Available, Pieces of Work, Marked / Unmarked Pieces, Late-Flagged Hand-Ins, Assessment Score Coverage, Mean Score (Selected Instrument), Mean Standard Error | Student review | Name the topics where the student sits furthest below the class and suggest materials for them. Must quote the coverage beside the score and must not infer ability, predict an outcome or rank students. |

| **UC7** Plan and follow up a learner check-in | Head of school, teacher | `FactAttendanceDay`, `FactStudentAction`, `DimStudent`, `DimTeacher`, `DimSchool`, `DimDate` | `rolling_absent_days`, `rolling_window_complete`, `action_type`, `reason_category`, `status`, `outcome_note`, `before_*_days`, `after_*_days`, `is_first_in_category`, `is_comparable`, `before_work_*`, `after_work_*`, `is_work_comparable` | Chronically Absent Learners, Chronic Absence Share, Learners Meeting Attendance Rule, Share Meeting Attendance Rule, Actions Logged, Learners with an Action, Attendance Actions, Coursework Follow-ups, Open / Completed Actions, Learners Compared After First Attendance Action, Absence Rate Before / After Action, Absence Change After Action (pp), Learners with Fewer / Same or More Absences After, Learners Compared After First Coursework Follow-up, Work Missing Before / After Follow-up, Missing Work Change After Follow-up (pp), Learners with Less / Same or More Missing Work After, Learners Meeting Attendance Rule (Selected Classes), Actions Logged (Selected Classes) | School briefing, Class review, Student review | Summarise who met a rule and what was logged, and draft check-in questions. Must say "observed after, not caused by", must not predict, score or rank learners, and must quote the threshold in use. |
| **UC8** Compare school years | Head of district | `FactEnrollment`, `FactAttendanceDay`, `DimSchool`, `DimDate` | `school_year`, `entry_type`, `exit_type`, `valid_from`, `valid_to`, `street_address`, `city`, `state`, `postal_code` | Learners Enrolled, Learners Enrolled (Prior Year), Enrollment Change, Enrollment Change %, New Learners, Continuing Learners, Transferred In / Out, Completed Final Grade, Learners Who Left, Attendance Rate (Prior Year), Attendance Change vs Prior Year (pp), Chronic Absence Share (Prior Year), Chronic Absence Change vs Prior Year (pp) | District, Student review | Describe how enrollment and attendance moved since last year and where to look next. Must say a year group holds a different cohort each year and must not give reasons for arrivals or departures. |

Every measure in the model is either placed on a visual (98) or used inside another
measure's DAX (8). None is decorative.

## How metrics are defined

Gold stores additive numerators and denominators; the semantic model turns them into
ratios so that filter context is respected. This is the split the Gold calculation
contract specifies, not a re-definition.

| Gold contract metric | Implemented as |
|---|---|
| `attendance_rate` | `Attendance Rate` = present ÷ known |
| `attendance_coverage` | `Attendance Coverage` = known ÷ expected |
| `selected_cohort_students` | `Students in Selection` — filter-dependent distinct count |
| `rolling_attendance` | `Rolling Attendance Rate` — trailing window from the Rolling Window slicer |
| `attendance_comparison` | `Attendance Change (pp)` — equal-length prior period, in percentage points |
| `assessment_administrations` | `Assessment Administrations` — distinct captured events |
| `coursework_score_ratio` | `Marked Work Score` = marks earned ÷ marks available |
| `graded_work_coverage` | `Marked Work Coverage` = marked pieces ÷ pieces of work |

### What each figure means

The same wording appears on the report's **Definitions** page, so a reader meets these
definitions in context rather than having to find this file. Keep the two in step.

| Figure | Meaning |
|---|---|
| **Attendance Rate** | Days present divided by the days that have a record. Blank when nothing was recorded, because no record does not mean nobody came in. |
| **Attendance Coverage** | How much of the expected attendance was actually recorded. Always read the rate next to it. |
| **Unknown Day Share** | The share of expected days with no record. The opposite of coverage, shown so gaps stay visible. |
| **Students in Selection** | How many different students are in what you selected. Never add these up across schools, year groups or periods. |
| **Rolling Attendance Rate** | Attendance over the last few days, using the window you choose on the School briefing page. |
| **Attendance Change (pp)** | How far attendance moved against the period just before, in percentage points. Blank if either period has no records. |
| **Assessment Administrations** | How many tests were sat and recorded. It counts sittings, not students, and does not say how many pupils took part. |
| **Mean Score (Selected Instrument)** | Average score for one test. Blank on purpose for more than one test, because different tests use different scales. |
| **Recorded Work States** | How many pieces of set work have a status recorded: one row per student per assignment. |
| **Source-Flagged Late / Missing** | Counts of work the school system itself flagged. Shown as counts, not percentages, because the data holds no extensions or excuses to measure against. |
| **Marked Work Score** | The share of the available marks the student earned, on work that has been marked, counting the newest attempt only. The two totals are added up first and then divided, so a big assignment is not given the same weight as a small one. Blank when nothing in the selection is marked. Compare it within one subject, not across subjects. |
| **Cohort Marked Work Score** | The same figure for everyone else in the selection, so one student can be read against the class. The learner in view is excluded, so they are not part of the figure they are measured against. |
| **Difference from Cohort (pp)** | How far one student sits above or below the rest of the selection, on the same subject or topic, in percentage points. The figure to read for where to follow up, because both sides were marked to the same scheme. Blank when either side has no marked work. |
| **Marked Work Coverage** | The share of handed-in work that has actually been marked. A low figure means the marks are not in yet, not that the work was failed. Never read the score without it. |
| **Topic** | Read from the part of the assignment title before the dash, so "Unit 3: Fractions - Practice" and "Unit 3: Fractions - Review" group together. A reading of the title, not a curriculum field. |
| **Students in View** | How many different students the figures on screen cover, counted by identifier rather than name. One means a single learner; more means a combined total that describes nobody in particular. |
| **Assessment Score Coverage** | The share of recorded test sittings that carry a score. A gap is a result not entered yet, never a failed test. |

A blank `Mean Score (Selected Instrument)` is a deliberate refusal to average two
different scales, not a gap in the data. The **Definitions** page states this; the Class
review page no longer carries a card repeating it.

Rules the model enforces rather than merely documents:

- **Ratios of sums, never averages of averages.** Rates divide summed numerators by
  summed denominators, so class size cannot distort a school or district figure.
- **Unknown is not absence.** Days with no observation stay in `unknown_days` and are
  reported through coverage. They never count against a student.
- **A missing score is missing.** Null scores stay null and are never read as zero or as
  a failure.
- **Unmarked work is not a zero.** `Marked Work Score` counts only rows where a mark
  and a usable total are both present, so work that is handed in but not yet marked is left
  out of both operands instead of dragging the score down. What was left out is visible as
  `Unmarked Pieces` and as `Marked Work Coverage`.
- **Subjects are not compared on one scale.** Each subject marks to its own scheme, so the
  page compares a student against the rest of the selection *within* a subject or topic
  rather than ranking subjects against each other. That is what `Difference from Cohort (pp)`
  is for, and it is the figure the page leads with. The Gold calculation contract requires
  this: *"Do not present subjects with different mark schemes as one comparable scale."*
- **A resubmission is counted once.** Every marked-work figure filters to the newest attempt
  for each piece of set work, so a second attempt replaces the first rather than adding to
  it.
- **Distinct counts are not summed.** `Students in Selection` is recalculated for the
  current selection.
- **Incomparable things stay incomparable.** `Mean Score (Selected Instrument)` returns
  blank when more than one instrument or unit is selected, because RIT scales from
  different instruments cannot be averaged together.
- **A missing comparison is blank, not zero.** `Attendance Change (pp)` is blank when
  either period lacks observations, so an absent comparison never reads as "no change".

## What the sample data shows

The sample data is generated, not observed, but it is built to behave like a real
district's records, so every page has something to find:

- **Schools differ.** Each school has its own attendance baseline, so school rates and
  year groups are not identical.
- **The year moves.** Most learners keep a steady pattern; others dip mid-year, decline
  gradually or improve, so a period comparison, a rolling rate and the follow-up windows
  have real changes to show.
- **Subjects and learners differ.** Each learner has their own strength per subject and
  topic, so a weakest subject is a real feature of the data.
- **Absence reaches the work.** Work due after recent absence is more often missing and
  marked lower.
- **Two school years.** The previous year has its own attendance, tests and membership,
  with learners who joined, transferred, left or moved on after their final year group.
- **Teachers log actions.** When a visible rule is met, a teacher logs a check-in, family
  contact, plan, referral or missing-work follow-up, and records a follow-up note. Some
  learners improve afterwards and some do not; some meet a rule and get no action.

These are constructed features of the fixture: they show that the report can find a
difference, never that a school or a child needs help. See
[Change over the year and teacher actions](../../sample-data/README.md#change-over-the-year-and-teacher-actions)
for the generator's assumptions and the reconciled figures.

**If the student page shows district-wide figures, no student is selected.** `Student review`
is a drillthrough target, so reaching it from the page
navigator rather than by drilling through leaves the student filter unset. The
`Student in View` banner names the student, or says plainly how many are being combined.

## Modelling notes

- **`Teacher` on `DimSection` is a calculated column.** `DimTeacher` and `DimSection` both
  sit on the one side of `BridgeTeacherSection`, so a teacher slicer cannot filter classes
  through a relationship without bidirectional filtering, which this model avoids. The
  column resolves the teacher through the bridge and lists every teacher where a section
  has had more than one.
- **`Class` on `DimSection` is a calculated column too, and it carries the school.** A
  class name is unique inside a school and nowhere else: all three schools in the sample
  run a class called `English Language Arts 6 - Group 01`, on section IDs 25, 144 and 275.
  A label of just the name makes one slicer entry and one chart bar out of three unrelated
  classes, and the class pages have no school slicer to disambiguate them. `Class` is
  therefore `name (school)`, with the raw name kept as the hidden `Class name`. Every page
  that shows a class picks this up, not just the class page.
- **Class-scoped attendance walks the bridge in DAX** for the same reason, using
  `TREATAS` over the date-qualified student roster.
- **`DimSection` has no direct relationship to the work facts.** It reaches them through
  `DimContent`; a second path would make the model ambiguous.
- **A submission hangs off its obligation.** `FactSubmissionState` (one row per obligation,
  `obligation_id` unique) is the parent of `FactSubmission` (the attempt). Without that
  relationship the two facts are unrelated and a visual showing an assignment, its recorded
  state and the attempt's score together fails with "Can't determine relationships between
  the fields". `DimStudent` and `DimContent` therefore reach `FactSubmission` through
  `FactSubmissionState` rather than directly, which keeps a single unambiguous path.
- **`GoldPublication.snapshot_id` is not a key.** That table is append-only — one row per
  successful refresh — while `snapshot_id` is a fingerprint of the inputs that deliberately
  excludes the clock (`get_snapshot_id` in `EDU_Config`). A refresh that finds Silver
  unchanged therefore republishes the same id, and a second row appears carrying it. Marking
  the column as a key made the refresh fail with *"contains a duplicate value … not allowed
  for columns … used as the primary key of a table"*. Nothing needs it to be unique: the
  table has no relationships, and `Published Snapshot` and `Reporting Period` already pick
  the newest row with `TOPN` over `Published at`. Every other `isKey` column in the model is
  the declared primary key of a business table, each asserted unique by
  `assert_unique_key` in the enrichment notebook and holding exactly one published snapshot.
- **Column display names are aliased in visuals** where two physical columns share a name
  (`DimAssessment.name` and `DimWindow.name` both being `name` breaks a visual). The model
  keeps the physical Gold names, so the 1:1 mapping to the Gold contract is intact.
- **`Subject` exists on both `DimSection` and `FactSubmission`.** Gold carries the subject
  on the submission as well, so per-subject achievement does not need a two-hop join, and
  the model keeps both. `Flagged late` likewise sits on both `FactSubmissionState` and
  `FactSubmission`, once per obligation and once per attempt. No visual projects either
  pair together: the class pages read `DimSection.Subject`, and the marked-work visuals on
  Student review read the `FactSubmission` columns.
- **The cohort excludes the learner being measured.** `Cohort Marked Work Score` removes the
  `DimStudent` filter and then puts back a filter excluding the student ids that were in
  view, so every other filter — subject, topic, class — still applies and the comparison
  stays like-for-like. Leaving the learner in their own cohort has them contribute to the
  figure they are measured against, which biases the gap towards zero by exactly `1/n` of
  its true size for a cohort of `n`. That is 0.08% across all 1,260 Canvas learners but 3.3%
  in a class of 30 — worst precisely when the Class slicer is narrowed, which is when the
  comparison is most worth trusting. With no student filtered at all the cohort is empty and
  the measure is blank, because there is then no "everyone else" to compare with.
- **A student page states who it is showing.** `Marked Work Score` is deliberately plain
  arithmetic, because it is also the cohort figure — it cannot blank itself when several
  students are in context without breaking `Cohort Marked Work Score`. The guard is
  therefore separate: `Student in View` names the learner or reports how many are being
  combined, `Difference from Cohort (pp)` blanks unless exactly one student is in view, and
  the student slicer is single-select. Without this, opening a drillthrough page from the
  page navigator silently shows the whole district, and a combined total still looks like a
  perfectly ordinary number.
- **The guard counts identifiers, not names.** `Students in View` is a distinct count of
  `student_id`. Counting `display_name` would let two learners who share a name pass as one
  and produce a combined figure with no warning — and that is a live path rather than a
  hypothetical, because the student page is drillthrough-bound to `display_name`, which
  is what the class pages show. `DimStudent` holds no other human-readable field to bind to.
  With the count on `student_id` the collision is surfaced instead: the banner names the
  count and the shared name, and `Difference from Cohort (pp)` stays blank. The sample data
  never triggers it, because the generator asserts display names are unique while the name
  pool allows.
- **`Topic` is a calculated column on `DimContent`**, not a Gold field. See the limits table
  for what that does and does not support.
- **Marked work has no relationship to `DimDate`.** `FactSubmission` and
  `FactSubmissionState` are not joined to the date table, so the date slicers filter
  attendance, actions and assessments only. That is why the marked-work visuals on
  Student review say *whole reporting period*. `Submitted at` keeps its own automatic date
  hierarchy if a hand-in date is needed on a visual.

## Editing it in Power BI Desktop

This is an ordinary PBIP project, so opening and saving it in Desktop is expected. Two
things follow from a Desktop save, and both are visible in the committed files.

**Automatic date/time is on.** Desktop's default adds a hidden date table behind every
date column — `DateTableTemplate_…` plus one `LocalDateTable_…` per column, with a
relationship each. They are committed because `model.tmdl` references them, and a model
that names a table it does not ship will not open. They do not affect any figure in this
report: every visual uses `DimDate`, and the 17 authored relationships are untouched.

They are, however, redundant here, because `DimDate` already is the date table. To drop
them, turn off **File → Options → Options → Current File → Data Load → Time
intelligence → Auto date/time**, then save. The 24 tables and 23 relationships disappear
with it.

**Local files are not committed.** Desktop writes a `.pbi/` folder next to each item
holding editor preferences, a signature bound to the current Windows user, and
`cache.abf` — a cache of the imported data. `.gitignore` excludes the folder, so no
cached student data or user-bound signature can reach the repository.

Saving in Desktop also rewrites the whole project: `$schema` URLs move to the version
Desktop ships, positions gain sub-pixel precision, role order changes and empty filter
entries appear. That churn is cosmetic — expect a large diff from a small edit.

## Rebuilding

The PBIP was first generated by a deterministic Node script kept outside the repository.
It has since been edited in Power BI Desktop, so **the committed PBIP is now the source of
truth** — regenerating from the script would discard any later Desktop edit. Treat the
script as a starting point for a rebuild from scratch, not as a way to reproduce the
current files.
