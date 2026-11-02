# NWEA MAP Growth Research and Development Environment Guide

## Role in the hackathon

NWEA MAP Growth is the selected assessment source. It should provide assessment definitions, test events, RIT scores, percentiles, proficiency levels, and growth indicators.

## Development environment feasibility

NWEA MAP Growth should be treated as access-gated.

No public self-service sandbox was confirmed. Real source data access normally requires:

- A licensed MAP Growth environment.
- A district or school assessment coordinator.
- Access to Data Export Scheduler.
- A NWEA system account or partner access for Data API usage.

Unlike Canvas or Moodle, the team should not plan to load fabricated assessment results into NWEA. For the hackathon, the practical development environment is usually an export fixture: a ZIP/CSV package shaped like NWEA exports.

## What data is stored there

| Area | Example data |
| --- | --- |
| Organizations | districts, schools, school metadata |
| Students | student identifiers, demographics, school relationships |
| Test results | test events, subject, test date, grade, RIT score, percentile |
| Growth | projected growth, observed growth, growth percentile where available |
| Proficiency | achievement level, proficiency band, norm group |
| Instructional areas | domain/strand-level strengths and weaknesses where available |

## How to create the development environment

### Option A: licensed MAP Growth environment

1. Request access from a district or school assessment coordinator.
2. Confirm that the environment contains de-identified or approved test data.
3. Ask the coordinator to enable or create a Data Export Scheduler export.
4. Choose Comprehensive or Combined export format.
5. Retrieve the generated ZIP/CSV package.
6. Use the package as the source fixture for connector development.

### Option B: NWEA Data API access

1. Request or confirm a NWEA system account.
2. Confirm organizations, students, and test results API access.
3. Use HTTPS REST calls to retrieve accessible district/school/student/test-result data.
4. Store raw JSON responses as connector fixtures.

### Option C: synthetic export fixture

Use this if no MAP Growth environment or API credentials are available.

1. Create `nwea_assessments.csv`.
2. Create `nwea_assessment_results.csv`.
3. Create `nwea_proficiency_bands.csv`.
4. Create `nwea_growth_targets.csv`.
5. Ensure `source_student_id` matches the shared synthetic SIS student IDs.
6. Include at least fall and winter/spring windows to support growth analysis.

## How to load sample source data

For NWEA, the recommended hackathon pattern is not to load synthetic records into the MAP Growth product. Instead:

- If a licensed environment exists, generate exports from real approved/de-identified data.
- If API access exists, retrieve accessible test result data through the NWEA Data API.
- If neither exists, create export-shaped synthetic files outside NWEA and treat them as the source-system extract.

## Connector and extract options

| Option | Use when | Notes |
| --- | --- | --- |
| Data Export Scheduler | Assessment coordinator access exists | Exports Comprehensive or Combined CSV ZIP packages. |
| Automated retrieval script | Scheduler export is configured | NWEA docs describe retrieving scheduled exports by script. |
| NWEA Data API | System account/partner access exists | REST API includes organizations, students, and test results. |
| Synthetic export fixture | No access | Recommended Day 1 fallback. |

## Synthetic fallback

| File | Grain |
| --- | --- |
| `nwea_assessments.csv` | One row per assessment/test definition |
| `nwea_assessment_results.csv` | One row per student/test/window |
| `nwea_proficiency_bands.csv` | One row per subject/grade/score band |
| `nwea_growth_targets.csv` | One row per student/subject/window |

Minimum demo volume: 300 students, two subjects, two test windows, 1,200 result rows, and proficiency-band reference data.

## References

- NWEA Data Export Scheduler: https://teach.mapnwea.org/contents/help/Content/ContextSensitiveHelp/UsingReportsandInstructionalResources/DataExportScheduler.htm
- How to export MAP Growth data: https://teach.mapnwea.org/impl/maphelp/Content/Data/DataExportHowto.htm
- Automated retrieval of data export files: https://teach.mapnwea.org/impl/maphelp/Content/Data/AutomatedRetrieval_DataExportFiles.htm
- NWEA Data API overview: https://developers.nwea.org/data-api-overview
- Example community ETL pattern for scheduled exports: https://github.com/xmarcosx/nwea-map-etl
