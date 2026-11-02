# NWEA MAP Growth: Official Schema Evidence

> **Project scope:** synthetic-only development; no real-data access or institutional pilot is required. Administrator requests, permissions and approval checks below are future compatibility reference, not current blockers. See [current engineering gates](README.md#current-engineering-acceptance-gates).

Checked: **2026-09-14**. Scope: public official documentation and export dictionary only. **0 live tenant records verified; no tenant access.** This is an export schema investigation, not a verified Data API contract. Proposed synthetic CSV names in earlier research are not vendor schemas.

## Confirmed Export Structure

The official [export overview](https://teach.mapnwea.org/impl/maphelp/Content/Data/AboutExportingTestResultData.htm) describes ZIP-packaged CSV exports:

| Export | Contents |
| --- | --- |
| Comprehensive | `StudentBySchool.csv` and `AssessmentResults.csv`; optional `ClassAssignments.csv`, `ProgramAssignments.csv`, and `AccommodationAssignment.csv`, depending on export choices |
| Combined | `ComboStudentAssessment.csv`, combining student-to-school context and valid assessment results for the selected term |

The overview also lists an Odyssey-specific format. It is not a seventh worksheet in the MAP field dictionary and is not established here as a general-purpose integration schema.

The official [field dictionary](https://teach.mapnwea.org/assist/doc/MAP_Export_Field_Descriptions.xlsx) was downloaded to OS temporary storage, not the repository. Each export worksheet is transposed: row 2 contains literal field labels, row 3 definitions, row 4 types, and row 5 size/format declarations. Count populated row-2 labels, not worksheet width, repeated field-number labels, or example records. Repeated-family labels must not be represented as verified expanded CSV headers.

## Dictionary Provenance and Counts

| Property | Observed value |
| --- | --- |
| Exact successful download URL | https://teach.mapnwea.org/assist/doc/MAP_Export_Field_Descriptions.xlsx |
| Retrieval | HTTP 200 on 2026-09-14; no redirect on workbook download |
| Bytes | 50,415 |
| SHA-256 | `2841d68b5e008269df00e6db4fe18585483b1ee72f82e2ca73ca2e34115e2994` |
| HTTP Last-Modified | `Fri, 21 Aug 2026 04:25:46 GMT` |
| HTTP ETag | `"66e534ff"` |
| Workbook metadata modified | `2023-12-04 18:43:12`; not an assurance that all definitions are current |
| AboutThisDoc revision | Changes effective December 2023; removal of the 2015 norms option |
| Parser | Python with openpyxl 3.1.5; every worksheet inspected, including AboutThisDoc |

The HTTP modification date and internal revision date differ. Neither establishes a tenant schema version. The hash identifies exactly the bytes inspected; a later download may differ.

| Worksheet / vendor export file | Populated row-2 entries | Literal fields | Repeated-family entries | Prior count independently checked |
| --- | ---: | ---: | ---: | --- |
| `ComboStudentAssessment.csv` | 75 | 68 | 7 | Confirmed as dictionary entries, not 75 actual headers |
| `AssessmentResults.csv` | 66 | 59 | 7 | Confirmed as dictionary entries, not 66 actual headers |
| `StudentBySchool.csv` | 16 | 16 | 0 | Confirmed |
| `AccommodationAssignment.csv` | 6 | 6 | 0 | Confirmed |
| `ClassAssignments.csv` | 11 | 11 | 0 | Confirmed |
| `ProgramAssignments.csv` | 5 | 5 | 0 | Confirmed |
| **Total** | **179** | **165** | **14** | Across six export sheets |

`AboutThisDoc` is the seventh worksheet, not another export schema. It uses the plural spelling `AccommodationAssignments.csv`; the actual export worksheet and current export overview use **`AccommodationAssignment.csv`**. Prefer the latter for this inventory and verify the delivered filename with an administrator.

[nwea-export-fields.csv](nwea-export-fields.csv) contains **all 179 dictionary entries**, with `file`, `group`, `field`, `type_declared`, `format_declared`, `source_cell`, and `evidence_url`. `group` classifies `literal_field` versus `repeated_family`; it is analytical metadata, not a vendor field. Literal spelling, capitalization, ellipsis and declared type/format text are retained. The CSV intentionally contains no example student records and no full vendor definition prose. Definitions are paraphrased below. There is no formal required/nullability row in the workbook; field absence/nullability must not be inferred from its example rows.

### Repeated Families and Ambiguities

| Family | Literal row-2 evidence and interpretation |
| --- | --- |
| Seasonal growth | Five grouped labels per result sheet: `FalltoWinter: . . .`, `FalltoSpring: . . .`, `WintertoWinter: . . .`, `WintertoSpring: . . .`, `SpringtoSpring: . . .`. Each refers to the seven explicit Fall-to-Fall measures: projected growth, observed growth, observed-growth SE, met projection, conditional index, conditional percentile, quintile. Row 3 also lists seven member names for each season family. Its introductory "six fields" wording is inconsistent with those seven names and row 4's reference to seven columns. |
| Instructional areas | Literal `Goal2-8: Name, RitScore, StdErr, Range, Adjective` references seven further five-field areas after the explicit `Goal1Name`, `Goal1RitScore`, `Goal1StdErr`, `Goal1Range`, `Goal1Adjective`. This is a compressed family definition, not a header named Goal2-8. Preserve the actual area names and test version; positional goal numbers are not cross-test standard identifiers. |
| Proficiency projections | Three explicit `ProjectedProficiencyStudy1` / `ProjectedProficiencyLevel1` pairs through number 3, followed by literal `ProjectedProficiency…4 to 10`. Additional applicable projections appear at the end. The workbook does not enumerate those later literal headers or definitively define their delivered order/width. Do not manufacture them or a fixed expanded header count. |

The CSV records the groups exactly as published rather than expanding templates. Row-3 member-name examples and row-2 headers also differ in capitalization (`FallToFallProjectedGrowth`, `FalltoFallObservedGrowth`, `FallToFallGrowthQuintile`); do not silently normalize the Bronze header contract. No total expanded-column count is asserted for either result file.

## Field Semantics and Optionality

These are short paraphrases of row-3 definitions, supported by each CSV entry's worksheet and cell coordinate. Types are vendor declarations, not inferred SQL types. The report groups related fields for explanation; the CSV retains the exact individual labels.

| Fields / concept | Definition and relevant limitations |
| --- | --- |
| `TermName` | Term selected for export, not a stable cross-system term key or a timestamp. |
| `DistrictName`, `District_StateID`, `SchoolName`, `School_StateID` | District/school preferences and state codes; SchoolName is School of Record when multiple schools apply. These do not establish an independent full organization dimension or historical school membership. |
| `StudentLastName`, `StudentFirstName`, `StudentMI`, `StudentDateOfBirth` | Profile identity data; MI can be a middle initial or name. Date of birth is declared String, not Date. Minimize PII outside an approved identity process. |
| `StudentID`, `Student_StateID` | District-provided profile identifier versus state identifier. Preserve as strings and scope by district/source; neither is automatically the API `studentBid`. |
| `StudentEthnicGroup`, `NWEAStandard_EthnicGroup` | Local preference label and corresponding standard label. Standard label is not a separate measured characteristic. |
| `StudentGender`, `Grade`, `NWEAStandard_Grade` | Profile gender values are M/F/X; local grade and corresponding standard grade are strings. Grade is roster-assigned; do not assume the exported value is a historical grade-at-test attribute for every use. |
| `ClassName`, `TeacherName`, `TeacherID`, `Teacher_StateID` | Roster class label and instructor identity, district/school teacher ID and state teacher ID. **No `ClassID` or class/teacher assignment effective dates appear in this dictionary.** TeacherName is declared String, 303 characters. |
| `Program`, `NWEAStandard_Program` | Assigned local program and mapped standard program label. No stable program key, begin/end dates or full program definition appears in this export sheet. |
| `Subject`, `Course`, `TestType`, `TestName` | Broad content area, specific content/RIT scale, test-type label, and full test name. Course is assessment content, not proof of an SIS catalog-course/section relationship. TestType describes Survey with Goals or Survey. |
| `TestID` | Integer test-event identifier, present in AssessmentResults and AccommodationAssignment. **Not listed in Combined.** Preserve as a source event identifier, not an assessment-definition ID. |
| `GrowthMeasureYN` | String in AssessmentResults indicating whether the result counts toward growth. Other valid repeats can be FALSE. **Not listed in Combined.** Do not conflate it with general test validity or presume it is physically Boolean. |
| `TestStartDate`, `TestStartTime`, `TestDurationMinutes` | Workstation-recorded start date, time in hh:mm:ss, and total testing minutes. Date/time are Strings; timezone is not declared. The Student Profile help says reported minutes exclude interruptions; do not equate testing minutes with elapsed wall-clock or general LMS engagement. |
| `TestRITScore`, `TestStandardError` | Whole-number overall RIT score and numeric uncertainty. RIT is a scale score, not percent correct. Keep score scale and uncertainty separate. |
| `TestPercentile`, `AchievementQuintile` | Norm-referenced achievement ranking and Low/LoAvg/Avg/HiAvg/High grouping at the 20/40/60/80 boundaries. Quintile is blank when percentile is blank. Neither is a state proficiency category. |
| `PercentCorrect` | Scored correct items divided by scored items, multiplied by 100; excludes unscored items. Diagnostic context for score confidence, not an alternative RIT scale or an automatic pass threshold. The dictionary's approximately 40-60% discussion is guidance, not a hard validity rule. |
| `RapidGuessingPercentage` | Numeric percentage of questions answered unusually quickly. It does not establish a universal disqualification threshold. Do not infer zero from missing data. |
| `NormsReferenceData` | Norm study/reference used in calculations; the definition permits `USER` and blank where no norms apply. Combined declares String; AssessmentResults declares Integer despite that text. Preserve raw values as text in staging and flag the type contradiction. |
| `WISelectedAYFall`, `WISelectedAYWinter`, `WISelectedAYSpring`, `WIPreviousAYFall`, `WIPreviousAYWinter`, `WIPreviousAYSpring` | Integer weeks of instruction before testing from Manage Terms, for selected academic year and prior year. Blank when the student lacks a valid event for that season. These are not start/end calendar dates. |
| Seven seasonal growth measures | Projected/observed RIT growth, uncertainty of observed growth, met-projection indicator, norm-conditioned index/percentile, and growth quintile. Availability depends on selected ending season, valid comparable events and norms. The explicit Fall-to-Fall definitions suppress these values for Survey tests. Other families refer back to these definitions. |
| `FalltoFallMetProjectedGrowth` | String Yes/No, with an asterisk qualification when observed-growth uncertainty may change the conclusion. Retain the qualification rather than coercing the whole field to Boolean. |
| `FalltoFallConditionalGrowthIndex` / `FalltoFallConditionalGrowthPercentile` | Growth relative to comparable students and its percentile. Index zero means typical/projected growth. Percentile is declared **Integer in Combined, Number in AssessmentResults**; retain both dictionary declarations. |
| `TypicalFallToFallGrowth`, `TypicalFallToWinterGrowth`, `TypicalFallToSpringGrowth`, `TypicalWintertoWinterGrowth`, `TypicalWintertoSpringGrowth`, `TypicalSpringToSpringGrowth` | Forward projections from the selected term into the relevant future term. These differ from backward-looking comparison measures whose ending term is selected. Depend on applicable norms and starting season; blank for Survey. |
| `LexileScore`, `LexileMin`, `LexileMax` | Reading-only correlated reading measure and range; Strings, not RIT or percentages. |
| `QuantileScore`, `QuantileMin`, `QuantileMax` | Math K-12 correlated mathematics measure and range; Strings. Do not force all scale labels into a single numeric type. |
| Goal name / RIT / SE / range / adjective | Instructional-area name, rounded integer RIT, numeric SE, string range, norm-relative descriptor. Survey goal names are blank. An asterisk descriptor or unavailable range marker means not computed, not zero or low proficiency. Preserve the raw marker. |
| `ProjectedProficiencyStudy1..3`, `ProjectedProficiencyLevel1..3` | Each study label identifies a linking study and its estimated external-assessment proficiency category. Additional studies are conditional. Survey study values are blank. These are **projections**, not observed state results or a universal proficiency-band lookup. |
| `AccommodationCategory`, `Accommodation` | Separate Comprehensive assignment rows for categories/choices associated with a TestID. Choices are recorded by the proctor; the system does **not** track whether the accommodation was actually performed. |
| `AccommodationCategories`, `Accommodations` | Combined concatenated category/choice strings, declared String with Unlimited format. The dictionary does not specify an escaping/separator contract or guarantee positional pairing; do not split into paired rows by assumption. |

## Validity, Windows and Season Pairing

[Invalid Tests and Unofficial RIT Scores](https://teach.mapnwea.org/impl/maphelp/Content/Data/DataMissingWrong_Invalid.htm) separates no test data, invalid tests with no score, unofficial valid RIT results not used for growth, and official valid results used for growth. The export overview says valid results are included; it is **not** a complete inventory of attempted/invalid tests.

The live validity page lists these invalidity rules: duration under 6 minutes for MAP Growth, or under 3 minutes for Screening and Sciences; SEM above 5.5 for MAP Growth or above 7.6 for Screening; SEM below 1.0; overall RIT below 100, above 320 for Reading, or above 350 for other tests; and exhaustion of suitable items. These are documented reporting criteria, **not an `Assessment.MaxScore` definition**, and should not be used to fabricate missing test statuses. Preserve test family/version and vendor eligibility, with local checks treated as diagnostics.

Official growth eligibility additionally depends on the test **start date** falling within the configured window; completion after the window can still qualify. For repeated same-test results in a term, the page selects the lowest SEM; it describes equal-SEM resolution as most recent or highest RIT without a deterministic precedence. Do not reimplement that tie-break by guessing. Screening results are not growth measures. The help page misspells the export flag `GrowthMeausreYN`; the workbook's exact header is **`GrowthMeasureYN`**.

| Comparison family | Beginning and ending seasons relative to selected export term |
| --- | --- |
| Fall to Fall | Previous academic-year fall to selected fall |
| Fall to Winter | Fall to selected winter in the same academic year |
| Fall to Spring | Fall to selected spring in the same academic year |
| Winter to Winter | Previous academic-year winter to selected winter |
| Winter to Spring | Winter to selected spring in the same academic year |
| Spring to Spring | Previous academic-year spring to selected spring |

The five compressed families refer to the Fall-to-Fall definitions with the season substitution; this table explains that comparison meaning, not an expanded-header contract. In contrast, the `Typical...` fields start at the selected season and project forward: same-season annual comparisons target the next academic year, while Fall-to-Winter, Fall-to-Spring and Winter-to-Spring target the next occurrence of that later season. Missing/unsupported pairs must remain missing, not zero growth. The dictionary does not define summer growth families.

[Student Growth Summary](https://teach.mapnwea.org/impl/maphelp/Content/Data/SampleReports/StudentGrowthSummaryReport.htm) requires the test window to be marked complete, excludes summer comparisons, and counts students with valid growth events in both terms; available-projection counts can be smaller. Cross-year comparisons follow the same students across grade changes. These are **report** constraints, not proof that every CSV has the same row filter or school-level aggregate schema.

[Achievement Status and Growth](https://teach.mapnwea.org/impl/maphelp/Content/Data/SampleReports/AchievementStatus_Growth.htm) distinguishes rostered term from tested term, and observed growth from projected growth and conditional growth. Its spreadsheet is a **different report output**, with such documented labels as `ASGType`, `WIStartTerm`, `WIEndTerm`, `StartTestDuration`, `EndTestDuration`; it is not part of the six-sheet dictionary and is not included in the 179-entry CSV. Request it separately when validating beginning/ending events.

## Norms and Proficiency Corrections

The December-2023 dictionary says most tests use 2020 norms and that 2015 was removed. That is **stale explanatory text**, not a safe 2026 default. The live [Growth and Norms page](https://teach.mapnwea.org/impl/maphelp/Content/Data/GrowthInsights.htm) points to the [2025 Norms Toolkit](https://connection.nwea.org/s/norms-toolkit) and labels 2020 resources historical. Student Growth Summary explicitly discusses **2025 school-level norms**.

The toolkit confirms that the RIT scale is unchanged but the national reference sample and growth expectations changed. Its national norms update does not cover USER-norm tests such as Spanish Reading, Algebra, Geometry, Integrated Mathematics, and grades 9-12 Biology/Life Science. Do not force `NormsReferenceData` to 2020 or 2025, assume all assessments have norms, or equate student norms to school-level norms.

The Growth and Norms page illustrates Fall/Winter/Spring weeks of instruction as **4/20/32**, while tenant settings can differ; workbook example values are not defaults. The [Student Profile report](https://teach.mapnwea.org/impl/maphelp/Content/Data/SampleReports/StudentProfile.htm) explains that grade, prior RIT and configured weeks influence growth comparisons. Preserve exported WI values, actual testing windows, norms reference and test version together. Do not silently recalculate historical percentiles with a different norm study.

Linking-study proficiency is separate from achievement and growth norms. The 2025 toolkit describes updated fall/winter cut scores and EISA-related math changes. The Student Profile report has no summer projections and conditions projections on study, subject, grade and district alignment. [Troubleshoot Report Data](https://teach.mapnwea.org/impl/maphelp/Content/Data/StubDataFix.htm) contains older report-specific fall/spring-only advice; do **not** use it as a blanket prohibition on winter projections given the more current toolkit. Resolve applicability with the actual report/study and tenant output.

RIT is not percentage mastery: [RIT Scores](https://teach.mapnwea.org/impl/maphelp/Content/AboutMAP/WhatRITMeans.htm) describes a comparable scale across grades and notes that instructional-area definitions can change with test versions. A norms refresh or a new goal-area label is not evidence that the student's raw achievement changed.

## Access and Extraction

The [scheduler instructions](https://teach.mapnwea.org/impl/maphelp/Content/Data/DataExportHowto.htm) require District Assessment Coordinator or School Assessment Coordinator. One-time exports allow a past ending term; daily and weekly exports use the current ending term. Same-day administrative changes do not appear until nightly processing. The latest downloadable package replaces the previous package.

The [automated retrieval instructions](https://teach.mapnwea.org/impl/maphelp/Content/Data/AutomatedRetrieval_DataExportFiles.htm) describe authenticated retrieval of an already scheduled export, up to daily, and only one export type per user at a time. The retrieval kit is available inside the authorized scheduler. These are whole-file exports, not a documented paginated change-data API. No row-level modification watermark or deletion feed has been verified.

Archive approved packages with retrieval time, selected term, scope, export options, and a content hash. Reconcile complete scoped snapshots and re-extract affected historical terms when permitted; a test date alone is not a safe incremental-update watermark. Keep credentials outside research artifacts and ingestion logs.

### Public Data API Evidence Is Separate

The [Data API Overview](https://developers.nwea.org/data-api-overview) is public and describes organizations, students and test results. It distinguishes `studentBid` from district/SIS identifiers such as `studentId` or `districtStudentId`, requires an entitled system account, and notes that the individual student-test-results API was retired after July 2021. Do not recommend that deprecated route merely because old docs mention it.

The successfully retrieved [Retrieving Test Results guide](https://developers.nwea.org/retrieving-test-results), reached from `https://developers.nwea.org/pulling-student-test-results`, documents:

- `GET https://api.nwea.org/organizations/v1/schools` to enumerate authorized schools; example properties `schoolBid`, `name`, `districtBid`.
- `GET https://api.nwea.org/test-results/v1/growth?school-bid={schoolBid}` for bulk results. These paths were **read in documentation, not called against a tenant**.
- API key plus OAuth2 bearer authorization; schools must have current-term rostered students and an applicable data-sharing agreement.
- **At most one selected result per subject/student from the last year**, chosen by NWEA business logic. This legacy guide is not a promise of complete longitudinal history or all valid attempts.
- Page size **1,000** in this guide. Follow `pagination.hasNextPage` and pass `pagination.nextPage` as `next-page`, retaining school scope. Stop when hasNextPage is false. Confirm the current entitled specification before implementing; do not infer other APIs' limits from this example.
- Example response names include `testResultBid`, `studentBid`, `schoolBid`, `termBid`, `subjectArea`, `grade`, `testName`, `testKey`, `testType`, `growthEventYn`, `duration`, `status`, `rit`, `standardError`, `ritScoreHigh`, `ritScoreLow`, `items` (`shown`, `correct`, `total`), `responseDisengagedPercentage`, `impactOfDisengagement`, `administrationStartDateTime`, `administrationEndDateTime`, `norms` (`percentile`, `reference`, `type`), `modifiedDateTime`, and `instructionalAreas` (`instructionalAreaBid`, `instructionalAreaName`, `score`, `standardError`, `scoreLow`, `scoreHigh`). These are **documented example properties**, not a complete current schema with declared requiredness. Do not infer `duration` units or map API identifiers to CSV TestID without the contract.

[Retrieving students](https://developers.nwea.org/retrieving-students) documents `/enrollments/v1/student-school-associations` with a perspective and school context, and example fields `studentSchoolAssociationBid`, `perspectiveBid`, `schoolBid`, `studentBid`, `districtStudentId`, `grade`, `beginDate`, `endDate`, `modifiedDateTime`, `firstName`, `middleName`, `lastName`, `dateOfBirth`. The example includes a pagination object. It does not establish a historical, unfiltered SIS enrollment feed or database schema.

**Watermark limitation:** an example `modifiedDateTime` property does not prove a supported modified-since filter, monotonic cursor, deletion/tombstone feed or retroactive-correction guarantees. Those remain unverified. Archive scoped snapshots and recheck selected results when their source changes; a one-result selection can replace a prior result without exposing a complete history.

The current API Specifications link leads to a Stoplight sign-in page; the legacy bulk-spec URL redirects to a generic Stoplight homepage. Neither supplied a machine-readable schema. Public tutorial examples have older dates and visible syntax issues; do not treat them as validated request/response fixtures or use any example credentials.

## Read-Only Silver Comparison

Inspected [Education_Analytics_Silver_Data_Model.xlsx](../../data-models/Education_Analytics_Silver_Data_Model.xlsx), `Silver_Schema`: **28 tables and 345 columns**; SHA-256 `35242165814142a4b2c737a7095a0648551942ee77252dfce5f62bdd7fc7468e`. No workbook changes. This is structural comparison, not verified tenant mapping or a recalculated coverage percentage.

| Silver target | What can align and what is missing |
| --- | --- |
| `School`, `Person`, `Student` | School labels/state codes, profile identity and grade contribute. No independent school catalog, conformed identity crosswalk, coordinates, AAD identity or historical demographics are established by these exports. Govern matching on scoped district IDs, not names. |
| `AcademicTerm` | TermName and WI do not supply StartDate/EndDate, a term key or a testing-window entity. Request Manage Terms configuration. |
| `Teacher`, `Section`, `TeacherAssignment`, `Enrollment` | Optional ClassAssignments can link student/class/teacher labels and teacher IDs, but no ClassID, course-section key, roles or effective dates is published. NWEA Course is test content, not SIS course identity. These mappings are partial. |
| `Program` / program enrollment | Local/standard assignment labels are available, but no canonical program ID, complete program entity or effective interval is published. Do not turn every distinct label into an authoritative program without conformance. |
| `Assessment` | Test name/type/subject contribute to a definition, but TestID belongs to an event. `MaxScore` should not be filled with a RIT validity cutoff; RIT has no conventional test-point maximum. |
| `AssessmentResult` | Has ScoreRaw, ScorePercent, ProficiencyLevel, GrowthMeasure and PassIndicator, but lacks dedicated RIT scale, percentile, SEM, growth-eligibility, start/end event pairing, norms reference, WI and multiple growth metrics. Never assign RIT to ScorePercent; PercentCorrect is a separate adaptive-test diagnostic, not comparable mastery. One GrowthMeasure cannot preserve the published family. |
| Assessment event / components | No dedicated AssessmentAdministration or AssessmentResultComponent table. Preserve TestID, timing, test version, eligibility, goal scores/errors/ranges and multiple linking-study projections in a future design, without adding them now. |
| Accommodations | No assignment entity; separate restricted records are needed for test-linked choices. Do not create a delivered-service flag from a proctor selection. |
| `DigitalEngagement` | Duration and rapid guessing offer testing context, not a login/content-usage history. Keep them typed as assessment diagnostics. |
| Lineage / platform | SourceSystemIdMapping can preserve scoped source IDs but has no complete norms/schema/extract manifest. Silver CreatedDate/ModifiedDate are not proof of source watermarks. Signals and intervention outcomes are not supplied by this export dictionary. |

## Precise Admin Evidence Request

1. With District or School Assessment Coordinator access, generate **Comprehensive**, selecting all three optional files, and provide an approved ZIP or headers-only versions of every delivered CSV plus selected-column/export settings. Include district/school scope, selected term, filename list, generation time, encoding/delimiters and whether data is de-identified.
2. Request exports ending in fall, winter and spring plus needed prior-year same-season terms to verify annual growth. Retain a real approved header for both result formats to settle family expansion, capitalization, additional proficiency study columns, Combined delimiters and whether the deployed schema has evolved beyond this public workbook.
3. Provide Manage Terms testing-window start/end dates, weeks-of-instruction values, school/year/season associations and completion status. Record rostered versus tested term and the timezone/workstation timestamp policy. Do not modify windows merely to make a research extract appear complete.
4. Supply de-identified examples covering official/unofficial repeats, Survey versus Survey with Goals, absent norms, `USER` or current norms, missing seasonal comparisons, goal markers, qualified met-growth values, multiple accommodations and linking studies. Request operational invalid-test/completion reports separately; valid-score exports cannot establish all attempted events.
5. Confirm current norms and linking-study/test/EISA versions. Supply a matching Achievement Status and Growth report and Student Growth Summary for reconciliation with export results; do not equate aggregate school norms to individual conditional percentiles.
6. For an API path, obtain the current entitled OpenAPI/specification and system-account/data-sharing scope, identifier crosswalks, selection/history behavior, auth/token lifecycle, pagination and limits, modified-since support if any, deletion behavior and nightly processing guarantees. Request the authorized automated retrieval kit separately if using scheduled files. Do not send credentials in research artifacts.

## Reproducibility and Validation

The CSV was generated mechanically with openpyxl and Python's CSV writer, then read back and compared **entry by entry** against the original worksheet labels, row-4 types, row-5 formats and coordinates. All 179 entries matched; no ambiguous family was expanded. The only openpyxl warning concerned an unparseable print header/footer, not worksheet cell values; no vendor workbook was rewritten.

The following read-only Python check downloads the current public dictionary in memory, prints its hash, inspects all sheets and emits the same CSV inventory to standard output. Run from an environment with openpyxl; the expected hash/counts describe this research snapshot, not an invariant vendor promise.

````python
import csv
import hashlib
import io
import sys
import urllib.request
import openpyxl

url = "https://teach.mapnwea.org/assist/doc/MAP_Export_Field_Descriptions.xlsx"
with urllib.request.urlopen(url, timeout=60) as response:
	payload = response.read()
print(hashlib.sha256(payload).hexdigest(), file=sys.stderr)
workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
writer = csv.writer(sys.stdout, lineterminator="\n")
writer.writerow(["file", "group", "field", "type_declared",
				 "format_declared", "source_cell", "evidence_url"])
for sheet in workbook:
	if sheet.title == "AboutThisDoc":
		print(sheet.title, list(sheet.values), file=sys.stderr)
		continue
	count = 0
	for cell in sheet[2]:
		if cell.value is None:
			continue
		label = str(cell.value)
		family = (": . . ." in label or label.startswith("Goal2-8:")
				  or label.startswith("ProjectedProficiency\u2026"))
		writer.writerow([sheet.title,
						 "repeated_family" if family else "literal_field",
						 label, sheet.cell(4, cell.column).value or "",
						 sheet.cell(5, cell.column).value or "",
						 cell.coordinate, url])
		count += 1
	print(sheet.title, count, file=sys.stderr)
````

## Evidence Status

All official content pages linked as supporting evidence above and the dictionary URL were successfully retrieved live on **2026-09-14**. Additional successful discovery pages were [Report Basics](https://teach.mapnwea.org/impl/maphelp/Content/Data/OverviewReports.htm), [MAP Help Center](https://teach.mapnwea.org/impl/maphelp/Content/MAPHelpCenter.htm), [MAP Report Details](https://teach.mapnwea.org/impl/maphelp/Content/Data/MAPReportsSummary.htm), and the [legacy Data Export Scheduler help](https://teach.mapnwea.org/contents/help/Content/ContextSensitiveHelp/UsingReportsandInstructionalResources/DataExportScheduler.htm). The report-details summary mentions only two optional files; the current dedicated export overview and six-sheet dictionary establish the additional optional accommodation file. Prefer the dedicated evidence over a stale summary.

| Unsuccessful / redirected URL checked | Observed result on 2026-09-14 |
| --- | --- |
| https://teach.mapnwea.org/impl/maphelp/Content/ContextSensitiveHelp/MAPReports/StudentGrowthSummaryReport.htm | Fetch extraction failed; direct urllib confirmed HTTP 404. Working report URL is linked above. |
| https://teach.mapnwea.org/impl/maphelp/Content/ContextSensitiveHelp/MAPReports/StudentProfileReport.htm | Fetch extraction failed; direct urllib confirmed HTTP 404. Working StudentProfile URL is linked above. |
| https://teach.mapnwea.org/impl/maphelp/Content/Data/SampleReports/StudentGrowthSummary.htm | HTTP 404; actual filename includes Report |
| https://teach.mapnwea.org/impl/maphelp/Content/ContextSensitiveHelp/MAPReports/ReportsOverview.htm | HTTP 404 |
| https://developers.nwea.org/pulling-student-test-results | HTTP 200 after redirect to `https://developers.nwea.org/retrieving-test-results`; useful tutorial, not a live API response |
| https://connection.nwea.org/s/norms-toolkit | HTTP 200 after redirect to `https://connection.nwea.org/s/norms-toolkit?language=en_US`; official 2025 norms content successfully retrieved |
| https://nwea-icp-api.docs.stoplight.io/bulk-test-results | HTTP 200 after redirect to `https://stoplight.io/`; generic homepage, no API specification recovered |
| https://nwea-apis.stoplight.io/auth | Sign-in page offering HMH Okta/email; no public machine-readable schema retrieved |

**Remaining blockers:** current tenant headers/sample contents, permission/consent scope, actual testing windows and norms, ambiguous family expansion, current API specification and change/history guarantees. Public documentation does not establish tenant availability, complete rosters, actual selected options, or consent to process student information. Names, birth dates, state identifiers, demographic attributes, programs, and accommodations require purpose-limited access, encryption, retention controls, small-group disclosure controls, and approved identity mapping. **0 live tenant records verified.**