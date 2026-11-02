# PowerSchool SIS: Official Schema Evidence

> **Project scope:** synthetic-only development; no real-data access or institutional pilot is required. Administrator requests, permissions and approval checks below are future compatibility reference, not current blockers. See [current engineering gates](README.md#current-engineering-acceptance-gates).

Checked: **2026-09-14**. Product: **PowerSchool SIS**, not PowerSchool Enrollment, eSchoolPlus, Schoology, Schoolnet, Special Programs, or another PowerSchool product. **No tenant access; 0 live data records verified.** No vendor database dump, complete API schema, or authorized export was obtained.

## Findings and Evidence Boundaries

Public official SIS documentation confirms database concepts, selected exact fields, import contracts, export behavior, and permissions. It does **not** expose a complete current database dictionary or SIS Views API contract at the URLs checked. Earlier synthetic filenames such as `powerschool_students.csv` are project proposals, not official vendor export schemas.

The current [Data Dictionary help](https://ps.powerschool-docs.com/pssis-admin/latest/data-dictionary) states that the dictionary was previously in Community and is now integrated into SIS: **System Management > Data > Data Dictionary**. It exposes tables/views, fields, SQL types/lengths, validation minimum/maximum lengths, validation-required status, descriptions, field introduction versions, and indexes with uniqueness. Results depend on the logged-in user's export permissions and the particular SIS instance. The public page explains the tool; it does not contain those tenant table definitions.

The [Import and Export page](https://ps.powerschool-docs.com/pssis-admin/latest/import-and-export) still links to a legacy SIS Views dictionary route that returned **404**. It describes SIS Views as predefined SQL queries providing metrics that can be joined and filtered. This confirms the concept, not view names, column lists, API paths, or refresh guarantees. No current public SIS Views API schema was recovered from the official sitemap or the checked legacy routes. Do not infer endpoint spelling or JSON properties from SQL fields.

## Source-Specific Evidence

SQL types, physical nullability, foreign keys, and defaults are **not declared in the public evidence below**, unless explicitly noted. UI validation and import requirements are not database constraints.

| Requested area | Confirmed public evidence and short definition | Contract boundary / missing evidence |
| --- | --- | --- |
| Schools / district | [School Information](https://ps.powerschool-docs.com/pssis-admin/latest/school-information) describes school name, abbreviation, address, grade range, category and School Number. The latter allows up to nine digits and cannot be altered after creation. | These are UI labels, not a published `Schools` column list. District hierarchy, internal school key versus school number, SQL types and state extensions require tenant metadata. Do not infer a district table from a UI page. |
| Students | [Import and Export](https://ps.powerschool-docs.com/pssis-admin/latest/import-and-export) explicitly identifies `student_number` and `Students.EnrollmentID`. [Quick Import](https://ps.powerschool-docs.com/pssis-admin/latest/quick-import) distinguishes the internal student `ID` from `student_number` in its meal-transaction option. | Preserve internal IDs and business identifiers separately. `student_number` is an important import/export match key, not proof that every database foreign key references it or that it is a universal cross-district key. |
| Current school enrollment / reenrollment | The import page explicitly identifies `Students.EnrollmentID` and `ReEnrollments.ID`. On current Students updates, omitting EnrollmentID preserves the existing value; a new record can receive a generated ID. ReEnrollments does not support updates through the described import workflow. | Obtain school history separately from section enrollment. Blank or zero identifiers can regenerate enrollment IDs; these import behaviors are not permission to mutate tenant data. Exact date/status columns and key relations remain unverified. |
| Staff / teachers | [DDE](https://ps.powerschool-docs.com/pssis-admin/latest/direct-database-export) explicitly uses `Teachers` and the export expression `[teachers]lastfirst`. Quick Import describes matching teacher updates by teacher number. | Teacher number is a documented matching concept, not an exact column spelling in that passage. Obtain staff identity, school associations and teaching-role metadata; do not equate all staff with teachers. |
| Terms | [Years and Terms](https://ps.powerschool-docs.com/pssis-admin/latest/years-and-terms) distinguishes scheduling terms from grading terms. UI labels include Name of Term, Abbreviation, First Day of Term, Last Day of Term and Import File Term #. | `TermID` is explicitly listed in the CC import contract, where it uses the import-file term value. Do not equate that import value with a physical database primary key without verification. Calendar dates and term hierarchy require tenant metadata. |
| Calendar | [Automated Calendar Setup](https://ps.powerschool-docs.com/pssis-admin/latest/automated-calendar-setup) documents cycle day, bell schedule, school/track in-session flags, membership value, membership type and note. | These are UI concepts, not verified `Calendar_Day` fields. Obtain instructional day, track, period and bell-schedule definitions and attendance conversions; a term date range alone is not an attendance denominator. |
| Attendance / codes | [Attendance Codes](https://ps.powerschool-docs.com/pssis-admin/latest/attendance-codes-school-level) documents school-specific Code, Code Categories, Points, teacher-assignability, administrator locking, ADA inclusion and ADM membership. Quick Import has an Attendance target and an overwrite option. | Exact attendance event columns and SQL types are not public here. Meeting, Daily and Time semantics differ. Code points are not minutes absent. Presence status and conversion rules determine ADA; ADM flag applies to Daily mode. Do not classify excused absence from a code label alone. |
| CC / section enrollment | [Quick Import](https://ps.powerschool-docs.com/pssis-admin/latest/quick-import) identifies **Student Schedules (CC table)** and explicitly lists the required input labels below. | This is a documented import contract, not a full CC database schema. DDE calls CC "current grades" in an example, but that does not make it the StoredGrades academic-history entity. |
| Courses / sections | Quick Import names `Courses` and `Sections`; section imports require valid schedule expressions. [DDE](https://ps.powerschool-docs.com/pssis-admin/latest/direct-database-export) explicitly demonstrates `[Courses.CoursesCoreFields]Alt_Course_Number` while exporting Sections. | This is an extension-aware export expression, not proof that `Alt_Course_Number` is a core Courses column. Obtain course/section internal keys, course numbers, term and school associations, teachers, meeting patterns and extension definitions. |
| Stored grades | [Transfer Stored Grades](https://ps.powerschool-docs.com/pssis-admin/latest/transfer-stored-grades-direct-enrollment-only) explicitly identifies the `StoredGrades` table and `SchoolID`, `SchoolName` fields. Quick Import describes Historical Grades matching by term/store code and course identifiers. | The cited transfer operation mutates data and was **not performed**. Obtain store-code, mark, credit, grading-term, student/course/section keys and GPA configuration metadata. Historical course grades are not standardized assessment scores or individual submission attempts. |
| Contacts | [Contacts](https://ps.powerschool-docs.com/pssis-admin/latest/contacts) is an independent entity shared across students. [Export Contacts](https://ps.powerschool-docs.com/pssis-admin/latest/export-contacts) documents the **Contacts** and **Student Legacy Contacts** PowerSchool Data Sets, repeated identity fields and child-record output. | A flat contact export can have multiple rows per contact and sparse repeated values; it is not one row per guardian. Obtain the selected export mapping and related child schemas, not only legacy student contact fields. |
| Accommodation / support plans | No core SIS accommodation table, field contract or export was verified in the checked public SIS pages or indexed accommodation routes. | This is an unresolved access/configuration question, **not proof that SIS cannot hold accommodations**. Ask whether the district uses SIS extensions, state fields or a separately licensed support product. Do not substitute Special Programs documentation as a SIS schema. |

### Exact CC Import Labels

The seven required inputs as spelled on the Quick Import page are:

````text
Student_Number
Course Number
Section Number
DateEnrolled
Dateleft
TermID
SchoolID
````

`Dropped` is separately documented as optional; `True` imports a dropped enrollment. The page describes both required SchoolID and Normal Mode behavior when SchoolID is omitted. Preserve that documentation nuance and test the chosen import mode in an approved non-production tenant; do not claim unconditional database NOT NULL constraints. This investigation performed no imports.

### Status and Contact Semantics

The import page's enrollment status values are: <= -2 inactive, -1 preregistered, 0 active, 1 inactive, 2 transferred out, 3 graduated, 4 imported as historical, >= 5 inactive. It labels this "Enroll Status Field"; the exact physical spelling/type should be obtained from the tenant field list. Keep raw values and use an explicit conformed mapping.

[Contact Information DATs](https://ps.powerschool-docs.com/pssis-admin/latest/contact-information-dats) documents `*contact_info`, including relationship values `custody`, `dataaccess`, `emergency`, `enddate`, `liveswith`, `receivesmail`, `relationship`, `schoolpickup`, `startdate`, and demographic `personid`. These are **DAT object selectors**, not verified SQL column names or API JSON fields. The default relationship view is effective on the day of execution; `asof-pers` supports temporal selection. Field-level denial can return `*****`, while no matching value returns an empty string. Masking, missingness and a real literal value must remain distinguishable.

The Contacts export can produce repeated ID/DCID/name values and separate child rows; unrelated phone/email/student positions must not be treated as inherently paired relationships. Export actual relationship identifiers and effective dates where authorized.

### Additional Academic Structure Evidence

- [Quick Staff Export](https://ps.powerschool-docs.com/pssis-admin/latest/quick-staff-export) confirms that the **Fields** picker exposes the selectable staff fields. Ask for that actual list and export mapping; the public instructions do not enumerate it.
- [Courses](https://ps.powerschool-docs.com/pssis-admin/latest/courses) confirms course availability and active status by **school and year**, credit hours, credit type, subject, grade scale, GPA exclusions and course archives. These are UI concepts here, not a physical column inventory. A single Silver `Course.IsActive` needs a scoped availability rule rather than a district-wide assumption.
- [Sections](https://ps.powerschool-docs.com/pssis-admin/latest/sections) explicitly mentions database fields `Users.Homeroom` (fallback when section Room is blank) and `Sections.Max_Load_Status` (teacher-load classification). It describes section numbers as unique within the same course and school year, not globally unique. Section teacher associations have role, allocation, Start Date and End Date. Multiple leads can cover different dates, with at most one lead on any day; additional staff can coexist. Allocation totals need not equal 100. Preserve this history instead of overwriting it with one primary teacher. Section deletion can also remove associated past/current enrollments, reinforcing the need for reconciliation or verified deletion events.
- [Edit an Enrollment Record](https://ps.powerschool-docs.com/pssis-admin/latest/edit-an-enrollment-record) defines class **Enroll Date** as the first effective day and **Exit Date** as the first day enrollment is no longer effective. Treat this documented class interval as start-inclusive/end-exclusive; do not silently apply the rule to every other date pair or to contact relationships. These labels are UI semantics, not new asserted database column names.

## Extraction, Permissions and Privacy

| Route | What is documented | Integration consequence |
| --- | --- | --- |
| Direct Database Export (DDE) | Selected tables/fields, related-table expressions, selectable delimiter/quoting/header/sort options, school filtering when `SchoolID` exists; restricted extension fields may be masked | Record selected table, field expressions, filters, school scope, encoding and format. DDE is not a fixed vendor CSV schema and not an API pagination contract. Do not use DDA modification functions. |
| [Data Export Manager](https://ps.powerschool-docs.com/pssis-admin/latest/export-data-using-the-data-export-manager) | Tables, extensions, approved data sets and third-party PowerQueries; school/district and student/staff selection; sources require access to their required tables/fields | Pin the exact data source and export mapping. A PowerQuery or dataset alias is not a physical table. A shaded/unavailable source or masked field is not absence of the business data. Do not use Edit All Filtered Records. |
| [Global API and SIF Settings](https://ps.powerschool-docs.com/pssis-admin/latest/configure-global-api-and-sif-settings) | Configurable data-event generation and per-plugin request throttling | Public existence of notifications does not prove delivery, replay, deletion events or subscriptions are enabled. Respect tenant limits and retry guidance; do not invent a numeric rate limit. |
| SIS Views / REST / plugin API | Conceptual SIS Views evidence; developer portal login; no complete current public contract recovered | Request authorized API specification, installed plugin/PowerQuery definitions, granted table/field access and version. Database, view and API names/types may differ. |

**Pagination and watermarks:** no SIS API page size, cursor, ordering, modified-since filter, deletion feed or watermark guarantees were verified. Require the exact contract before implementation. If using file snapshots, scope them by school/year/table and record extraction time, row counts, hashes and filters. Verify joins with counts and orphan checks. Student exit dates, term IDs and grade-store dates are not reliable modification watermarks. Historical corrections and deletions require re-extraction/reconciliation or a verified change-feed contract. SIS Views may need refresh/consistency metadata before mixing them with base-table snapshots.

Use a least-privilege read-only integration identity and an approved de-identified sample or headers-only exports. Minimize student names, birth dates, addresses, guardian contacts and support-plan data. Encrypt extracts, restrict access, set retention/deletion rules and keep credentials out of artifacts. Do not interpret masked fields as source nulls. No automated login or authentication bypass was attempted.

## Precise Admin Evidence Request

1. **Version and scope:** SIS build/version, enabled state/province package, extensions, plugins/PowerQueries, school list, extraction role and field/table export restrictions. Capture metadata under the intended integration role, not merely an unrestricted administrator.
2. **Dictionary evidence:** from System Management > Data > Data Dictionary, provide a read-only export if supported, otherwise approved screenshots/copied metadata for tables/views, columns, SQL type/length, validation-required/min/max, descriptions, version, indexes/uniqueness, and relationships where available. Do not assume the dictionary UI has a downloadable whole-schema export.
3. **Identity and academic metadata:** resolve `Schools`, `Students`, `Teachers` and any staff/user or school-staff association structures; `Terms`, `Courses`, `Sections`, `CC`, `ReEnrollments`, `StoredGrades`. These are lookup targets, not an assertion that each is an API resource. Include internal ID/DCID versus student/teacher/course/school business numbers, referenced keys and deletion semantics.
4. **Attendance denominator:** provide dictionary metadata and approved header-only/sample exports for the tenant's attendance events, code/category associations, instructional calendar, membership/track flags, bell schedules/periods and conversions. Search `Attendance`, `Attendance_Code`, `Calendar_Day` and relevant schedule structures as **candidate names to confirm**, not already-verified column contracts. Include mode, timezone, units, presence/absence, excused mapping, ADA/ADM and historical code validity.
5. **Contacts:** Data Export Manager > PowerSchool Data Sets > Contacts, plus selected-column mapping and approved relationship/child records. Include contact identifiers, student links, relationship type, priority, effective dates, custody/emergency/pickup/data-access flags only as permitted, and IDs for phone/email/address child records. Request Student Legacy Contacts only when needed for reconciliation; do not use it as a complete modern contact model.
6. **Accommodations:** identify the actual owning module/extension and approved coded fields, student/plan identifiers, effective dates, assignment versus delivery semantics and lookup values. Request no clinical/free-text material unless explicitly necessary and authorized.
7. **Export fixtures:** one headers-only file and, where permitted, a small de-identified sample per requested entity, with exact export definitions, delimiters, encoding, school/year filters, timezone, sample counts and generation time. Include past enrollment/grade/calendar examples, dropped section enrollments, multiple teachers/contacts and masked/null cases.
8. **API/Views contract:** obtain official version-specific SIS Views API/REST documentation through the entitled portal or admin, enabled view names/SQL definitions or output schemas, endpoints, response envelope and JSON fields/types, authorization scopes, pagination, stable ordering, throttling, change-event/deletion behavior, watermark support and consistency/refresh rules. Provide sanitized request/response examples without keys/tokens.

## Read-Only Silver Comparison

Inspected [Education_Analytics_Silver_Data_Model.xlsx](../../data-models/Education_Analytics_Silver_Data_Model.xlsx), `Silver_Schema`: **28 tables, 345 populated column definitions**. SHA-256: `35242165814142a4b2c737a7095a0648551942ee77252dfce5f62bdd7fc7468e`. No workbook changes were made. These are design gaps, not a verified field-to-field tenant mapping.

| Silver area | Supported concept and unresolved gap |
| --- | --- |
| `School`, `Person`, `Student`, `Teacher` | SIS identity and organization concepts align. Preserve business/internal/state identifiers through governed `SourceSystemIdMapping`; the workbook does not provide an effective-dated multi-identifier registry. All staff should not become Teacher records automatically. |
| `AcademicTerm`, `Course`, `Section`, `TeacherAssignment` | Broad structural alignment; scheduling term versus grading term must remain distinct. TeacherAssignment has effective dates and roles; populate from actual teacher associations, not just one display name. |
| `Enrollment` | Has school, course, section, program and term keys plus EntryDate/ExitDate. It needs a documented grain distinguishing current school membership, reenrollment history and CC section enrollment; combining them without type/scope risks duplicates. |
| `Attendance`, `AttendanceStatus` | Attendance already has `AttendancePeriod`, `AttendanceMinutes`, `ExpectedMinutes`, `AbsenceReason`, `IsExcused`. The gap is not absence of those columns; it is source rules, instructional-calendar/track/period entities, and richer effective-dated code/conversion metadata. AttendanceStatus currently has only a name plus key/lineage fields. |
| Historical course grades | No dedicated course-grade entity. `AssessmentResult` is not a lossless home for store code, credits and GPA/grade-scale semantics; `AssignmentSubmission` represents attempts rather than final historical grades. |
| Contacts and accommodations | No dedicated contact relationship or accommodation/plan entity. Person alone cannot represent relationship permissions, multiple child contacts, effective dates or support assignment versus delivery. |
| Lineage and extraction | Silver CreatedDate/ModifiedDate are load/conformance fields, not verified source watermarks. SourceSystemIdMapping has LoadBatchId but no complete export-schema/version/scope manifest. Signals, intervention workflows and cross-source conformance remain platform-owned. |

## Live URL Audit

All successful official page links used above were retrieved on **2026-09-14**. Public HTML documentation is evidence, not live tenant validation. Official discovery also used [the PowerSchool portal](https://ps.powerschool-docs.com/?l=en) and [its XML sitemap](https://ps.powerschool-docs.com/sitemap.xml), including its 14 child sitemaps; no current SIS Views API or accommodation-specific SIS schema page was located there. Sitemap absence alone does not prove a feature is unavailable.

| Checked URL | Observed result |
| --- | --- |
| https://docs.powerschool.com/ | Redirect to `https://ps.powerschool-docs.com/?l=en`; portal, not schema |
| https://docs.powerschool.com/sitemap.xml | Redirect to that same HTML portal, not XML |
| https://docs.powerschool.com/pssis-data-dictionary/latest/ | Redirect to that same portal, not dictionary content |
| https://ps.powerschool-docs.com/pssis-data-dictionary/latest/ | HTTP 404 |
| https://ps.powerschool-docs.com/pssis-data-dictionary/latest/powerschool-sis-views | HTTP 404; this is still linked by the successful Import and Export page |
| https://ps.powerschool-docs.com/pssis-data-dictionary/latest/sis-views-api | HTTP 404 |
| https://ps.powerschool-docs.com/pssis-data-dictionary/23.12/powerschool-sis-views | HTTP 404 |
| https://docs.powerschool.com/PSDD/latest | HTTP 404 |
| https://ps.powerschool-docs.com/pssis-admin/latest/sis-views | HTTP 404 |
| https://ps.powerschool-docs.com/pssis-admin/latest/powerschool-sis-views | HTTP 404 |
| https://ps.powerschool-docs.com/pssis-admin/latest/data-access-tags-dats | HTTP 404; the working contact-specific DAT page is linked above |
| https://support.powerschool.com/developer/ | HTTP 200 after redirect to `https://support.powerschool.com/login.action`; PowerSource login, not developer schema; authentication/entitlement required |

## Checks and Remaining Blockers

- Live official help retrieval and XML sitemap inspection; product boundary checked against the SIS admin documentation space.
- Read-only openpyxl inspection of the actual Silver workbook, including table/column counts and specific target fields.
- Cross-checked CC input labels against Quick Import and enrollment ID semantics against Import and Export.
- **Blockers:** authorized instance-specific dictionary, current SIS Views/API specifications, granted extract scope, exact accommodations owner, samples, join keys/types, and incremental/deletion guarantees. Public documentation resolves useful concepts and selected names, but not a production-ready tenant contract.