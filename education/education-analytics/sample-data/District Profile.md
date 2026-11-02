# District-scale synthetic data

## Purpose and assumptions

One district can own several schools in one PowerSchool instance. Canvas accounts or Moodle sites can also serve more than one school, and each school need not use both LMSs. Source-instance identity is distinct from school identity. Multiple independent districts would require separate instance-qualified keys, not just different school names.

This profile models **one fictional middle-school district**, not a measured average school or a real institutional calendar. Defaults are configurable engineering assumptions:

| Parameter | Default |
| --- | ---: |
| Schools | 3 |
| Students per school | 540 / 600 / 660 |
| Total students | 1,800 |
| Homerooms per school | 22 / 24 / 27, maximum 25 learners each |
| Grade levels | 6-8, assigned by homeroom |
| Subjects per learner | 6 |
| Teaching sections | 386, distinct from 6 district catalog courses; count varies by subject because class size does |
| Teachers | 103; each covers up to four sections of one subject |
| School years | Two: 2024-2025 from September 2, 2024 and 2025-2026 from September 1, 2025 |
| Instructional days | 180 synthetic weekdays per school year |
| Assignments per section | 20-34 over the fixture year, varying by class |
| Assessment windows / subjects | 3 / 2 |
| Attendance patterns | 70% steady, 15% mid-year dip, 8% gradual decline, 7% improving |
| Early-warning rules | 5+ absences in 20 school days; 3+ of the last 5 pieces of work missing in a class |
| Teacher actions | Logged for about 75% of rules met; about 60% followed by improvement; current year only |
| Membership change between years | About 6% of grades 7-8 new this year, 3% transferred between schools, 5% of grades 6-7 left; last year's grade 8 moved on |

The calendar excludes weekends only, not real holidays or vacations. No teacher timetable, room schedule, staffing standard or realistic resource allocation is claimed. Fall/Winter/Spring labels are fixed synthetic labels; `--days` changes spacing for volume tests, not an official school calendar. A class needs one instructional day per task it sets, so a short `--days` volume run caps the count below 20; the realized range is recorded in the manifest rather than assumed. Membership changes between the two school years (new learners, transfers between the district's schools, leavers and the final year group moving on) are implemented; mid-year enrollment changes, transfers to other districts' records, repeated IDs across instances, overrides and historical revisions are not.

School 1 uses Moodle; schools 2 and 3 use Canvas. The first school in each three-school group uses Moodle for larger runs. All schools use proposed PowerSchool extracts and NWEA-shaped results. Each selected source has one synthetic instance for the district. The generator's allocation is documented in the manifest; it does not generate shared mapping/configuration CSVs. Source-instance registration belongs to future pipeline configuration.

## Organization and system hierarchy

**Education structure:** District -> School -> Teaching section (class). Students join classes through enrollments; teachers join them through assignments. A student can attend several classes. A catalog course, such as Mathematics, can be taught by many sections across schools.

**System structure is separate:** a source instance is a particular PowerSchool installation, Canvas deployment/account scope, Moodle site, or NWEA integration scope. It can serve multiple schools, and one school can use several source systems. Do not equate district, school and source instance IDs.

| Source | How the organization can be represented | Important distinction |
| --- | --- | --- |
| PowerSchool | District containing multiple schools | Multi-school operation is documented; our district/school CSVs remain proposed extracts, not a verified vendor schema |
| Canvas | Root account -> subaccounts -> courses -> sections | A district may use a root account and schools may use subaccounts, but subaccounts can also represent other units |
| Moodle | Site -> course categories -> courses; users enroll in courses | Categories require an explicit school mapping and are not isolated tenants. Moodle topic sections are content containers, not classroom sections |
| NWEA | District -> schools -> rostered students and assessment results | Native district/school context exists, but assessment groups do not automatically equal SIS teaching sections |

**Our fixture:** one district, three schools and one synthetic instance per source. School 1 uses Moodle, schools 2-3 use Canvas, and all three have PowerSchool-shaped and NWEA-shaped data. Population, LMS, and attendance ordering deliberately differ, but one three-school fixture still cannot support causal LMS comparisons. These choices are a valid test scenario, not a requirement or claimed standard deployment for every institution.

Organization relationships are carried in the proposed SIS extracts and source identifiers; cross-source mappings must be derived during transformation rather than supplied as additional Bronze tables. Native Canvas account/subaccount records and Moodle category-to-school mappings are **not yet generated**. Source-qualified keys remain necessary even when source numeric IDs happen to match.

See the official evidence guides for [PowerSchool](../docs/research/official-schemas/powerschool-official-schema.md), [Canvas](../docs/research/official-schemas/canvas-official-schema.md), [Moodle](../docs/research/official-schemas/moodle-official-schema.md), and [NWEA](../docs/research/official-schemas/nwea-official-schema.md). The distinction above is organizational; it does not require real data or institutional access for our synthetic tests.

## Generate and check

### Fictional names and descriptive fields

The district profile uses deterministic fictional names instead of numbered placeholder labels. The default district is **Cedar Valley School District**, with the fictional **Alder Heights**, **Summit Harbor**, and **Rainier View Middle School**. Each school carries a full address — street line, city, state, postal code and county — at a real Snohomish County, Washington locality: Everett 98201, Lynnwood 98036 and Edmonds 98026, on streets that exist in those cities. Street numbers are synthetic, so an address geocodes to the right neighbourhood for a map without naming a real building, and extra campuses move along the same street rather than stacking on one pin. A single `city` cell reading `Everett, Washington` was not an address and could not be filtered, joined or geocoded as one. No records were obtained from a school.

- Learner first/last names agree across PowerSchool, the assigned LMS and NWEA. Canvas teacher names agree with the proposed SIS teacher records. Student and staff draw from **separate given-name and separate surname pools**, and the default fixture validates uniqueness within each role. Sharing the surnames was enough to put a teacher and a learner on screen as the same "Bennett" in one class, which reads as one person recorded twice wherever only part of a name is shown; the fixture now validates that full names, given names and surnames are all disjoint across the two roles.
- Contact emails and school websites use reserved `.example` domains and must not be used for outbound communication. School street numbers are synthetic and no personal addresses, birth dates or sensitive learner characteristics are introduced.
- Schools include readable codes, type labels and a geocodable address; proposed SIS teachers include department and role. Classes include subject/grade/group names, and proposed SIS and Canvas classes have readable codes.
- Assignments use subject-specific unit topics and activity labels, such as `Unit 1: Ratios and Proportions - Practice`, with short descriptions. A format repeated within one unit is numbered so two tasks in a class never share a name. This is illustrative content, not an official curriculum or standards alignment.
- NWEA rosters include fictional learner, school and district names. Assessment names are illustrative, not verified NWEA product catalog entries.

Attendance is reproducible but no longer periodic: a stable hash supplies student/day draws, while school baselines, individual risk, weekday, season, grade and a year-long pattern per learner influence absence probability. Most learners keep a steady pattern; others dip mid-year, decline gradually or improve. Absence also reaches the coursework and the tests, and teachers log actions when a transparent rule is met; see [Change over the year and teacher actions](README.md#change-over-the-year-and-teacher-actions). The fixture validates that school rates differ, that learners have at least ten distinct annual absence totals, and that both rising and falling attendance are present.

Assignments are no longer a grid. How many tasks a class sets, which format each one is, what total it is marked out of and when it is due are four independent seeded properties rather than one cycle. How many tasks a class sets starts from its subject: mathematics sets frequent short practice and physical education records little written work, so a class sets **11 to 38** tasks depending on which department it belongs to rather than every subject drawing from one range and publishing within a few tasks of the next. Formats are weighted so routine practice arrives far more often than a project or an end-of-unit assessment instead of each format landing an equal number of times; mark schemes run from 10 to 120 points by format; and each class has its own due-date calendar rather than the district sharing thirty dates. Because tasks are marked out of different totals, the coursework measure must divide summed points by summed maxima — with one shared maximum that is indistinguishable from averaging per-task percentages, and the distinction is untestable.

Classes are formed inside a school and year group, one set per subject, at the size that subject is taught in: 24 for mathematics through to 48 for physical education. Every subject used to reuse the homeroom grid, so a year group that filled nine mathematics classes appeared to fill nine physical education classes too and all six subjects reported an identical class count. Forming them per subject means a larger class yields fewer classes, which is what a timetable produces.

| Subject | Class size | Classes | Assignments set |
| --- | --- | --- | --- |
| Mathematics | 24 | 80 | 2,620 |
| English Language Arts | 26 | 73 | 2,181 |
| Integrated Science | 28 | 71 | 1,855 |
| World History | 30 | 63 | 1,497 |
| Visual Arts | 34 | 57 | 1,108 |
| Physical Education | 48 | 42 | 708 |

Marks are built the same way and are no longer a single arithmetic cycle. A mark is a learner's general standing, plus a **per-learner per-subject aptitude**, plus a per-topic offset within that subject, plus how severely the subject marks and how demanding the task format is, plus a small per-task draw, scaled to that task's own mark scheme. Missing and late work are drawn against that same per-subject standing, so gaps in what was handed in fall where the marks are weakest. RIT scores are built from the same standing and aptitude terms, so a learner stronger in Mathematics than in English reads that way in both coursework and assessment.

The point is that a learner has real strengths and weaknesses to find. The fixture validates that no two subjects score the same, that the strongest and weakest subject differ by more than three points across the district, and that a learner's own best and worst subjects differ by more than three points on average — currently a mean of 13.35. Which subject a learner is weakest in is close to evenly spread across the six, so no subject is systematically the weak one. Achievement scores remain constructed and should not be interpreted as statistically realistic. The manifest records `presentation_version=6` and these assumptions.

```powershell
python "sample-data/generate.py"
python "sample-data/generate.py" --check
```

For a custom size:

```powershell
python "sample-data/generate_district.py" --schools 3 --average-students-per-school 600 --days 180
```

Requires Python 3.11+ and the two captured official evidence CSVs, with no additional packages, Docker, tenants or real data. Both generator commands stream to the primary `sample-data/<source>/<table>.csv` folders, not the retired `generated/district/` location. Regeneration overwrites this profile's files; there is no automatic cleanup of unrelated files. Check mode reads the saved manifest, ignores sizing flags and rejects missing or extra primary CSV tables. The old 30-student package and small-only completion tables are removed; Git history retains them.

**Primary outputs are no longer under an ignored directory:** they replace the version-controlled source samples. Only legacy files under `generated/` remain ignored and must not be loaded. The primary manifest includes counts, interface/grain metadata, evidence hashes, file hashes and expected results. CSVs use UTF-8, LF, JSON Boolean values and `\N` for null. Source string identifiers must remain strings. This manifest lists column names, not complete vendor types/nullability.

## Browse generated tables

Use [the primary table index](README.md#table-index) to browse every source table. [PowerSchool attendance](PowerSchool/attendance.csv), [Canvas enrollments](Canvas/enrollments.csv), [NWEA student rosters](NWEA/StudentBySchool.csv) and [the manifest](manifest.json) now refer directly to district-scale data.

## Default expected results

| Measure | Expected |
| --- | ---: |
| School membership records | 1,800 |
| Student-section memberships | 10,800 |
| Daily attendance records | 324,000 |
| Absent student-days | 22,675 |
| Attendance rate | 93.00% |
| Chronically absent learners (10% or more of days) | 416 |
| Learners meeting the attendance rule at least once | 629 |
| Learners whose absence rises / falls by 5+ points between halves of the year | 210 / 173 |
| Teacher action log entries / learners | 1,486 / 787 |
| Absence rate before / after a first attendance action (536 learners, 10-day windows) | 28.99% / 11.94% |
| Missing work before / after a first missing-work follow-up (310 learners, 5 pieces) | 61.03% / 21.48% |
| Assignments set | 9,969 across 386 classes, 11 to 38 each |
| Canvas student-assignment snapshots | 187,336 |
| Canvas missing / late | 14,619 / 17,483 |
| Moodle student-assignment states | 80,757 |
| Moodle missing / late | 6,393 / 7,434 |
| Moodle actual grade rows | 74,364 |
| Missing work: due while the attendance rule was met / otherwise | 15.12% / 7.61% |
| NWEA test events | 10,800 |
| Marks by subject | 68.38% Mathematics to 77.49% Physical Education |
| Mean best-to-worst subject spread within a learner | 13.35 points |
| Previous school year: learners / former learners | 1,753 / 644 |
| Previous school year: absent student-days / attendance rate | 24,000 / 92.39% |
| Previous school year: chronically absent learners | 437 |
| This year's learners: continuing / transferred in / new | 1,064 / 45 / 691 |
| Last year's learners: continuing / transferred out / completed grade 8 / left | 1,064 / 45 / 585 / 59 |

Each generated snapshot represents expected work at the end of the simulation, not necessarily an actual submission. Missing Canvas work has null submitted date/attempt/score; missing Moodle work uses synthetic `new` state and has no grade. Moodle `timemodified` is deliberately set to the simulated submission time only for this fixture; it is not generally a submission timestamp in Moodle. Dates for late work may follow the last instructional day. Scores are constructed, bounded points or RIT values, not scientifically realistic outcomes. No norms, projected growth or proficiency are invented. Teacher actions and the share followed by improvement are constructed so that both outcomes appear; they are not evidence that an action works, and part of any before/after drop is regression to the mean.

## Contract and validation boundaries

PowerSchool files are proposed project extracts. Canvas files select REST fields; Moodle files select reference XMLDB fields, not actual database dump rows or API responses. NWEA selects literal export fields, not a complete Comprehensive ZIP. All source field-name selections except proposed PowerSchool fields are checked against the captured evidence. User records and school counts do not demonstrate compatibility with a real deployment.

Validation checks the exact 28-table primary CSV set, file hashes, headers and row counts, unique student-day/submission/test-event keys, teacher-school relationships, student-school/class relationships, identities derived from source fields, assignment references, missing/late counts, score bounds, per-subject and within-learner mark variation, attendance aggregates and year-long patterns, every logged teacher action against the records it cites, school addresses against the declared real localities, disjoint student and staff name pools, and assignment variation across count, mark scheme, format mix and due-date calendar. The per-subject scores, the mean within-learner spread, the assignment totals, the attendance patterns, the action-log counts, the before/after follow-up figures and the absence-to-missing-work link are recomputed from the CSVs and compared exactly with the manifest, so a recorded figure cannot drift away from the published data, and are then held to a floor so the data cannot lose its variation. Missing or ambiguous student links fail rather than falling back to a supplied crosswalk. These are the primary fixture's expected results. No Silver transformation or Fabric performance test has been run.