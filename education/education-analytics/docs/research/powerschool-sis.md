# PowerSchool SIS Research and Development Environment Guide

## Role in the hackathon

PowerSchool SIS is the primary Student Information System source for school, student, teacher, enrollment, demographic, course, section, and attendance data.

## Development environment feasibility

PowerSchool is not a practical self-service development environment for the hackathon. A real test environment normally requires one of:

- A district/customer non-production PowerSchool SIS environment.
- A PowerSchool partner or developer account.
- A vendor-provided sandbox/demo tenant.
- A backup/test server managed by a school district.

The public PowerSchool support/developer portal is access controlled through PowerSource, so official API and developer materials should be treated as gated until the team has credentials.

## What data is stored there

| Area | Example data |
| --- | --- |
| Organization | districts, schools, terms, calendars |
| People | students, staff, teachers, guardians |
| Student record | student number, names, grade level, demographics, enrollment status |
| Enrollment | school enrollment, reenrollment, course enrollment, section membership |
| Courses and sections | course catalog, sections, teachers, schedules |
| Attendance | daily attendance, period attendance, attendance codes, absences, tardies |
| Grades/academic history | marks, stored grades, credits, GPA-style calculated values where configured |

PowerSchool documentation emphasizes that `student_number` is essential for moving student data and should be included in exports/imports that need to match student records.

## How to create the development environment

1. Request a non-production PowerSchool SIS environment from a district admin, PowerSchool partner contact, or PowerSchool support.
2. Confirm the environment is isolated from production and approved for synthetic/de-identified data.
3. Request admin permissions for:
   - Import/export tools.
   - Field list access.
   - Attendance and enrollment setup.
   - API/plugin access if available.
4. Confirm the source data dictionary and field names before creating import files. PowerSchool imports require exact field names.
5. Confirm whether API credentials are available. If not, plan to use manual export/import first.

## How to load sample source data

Use PowerSchool's import functions only in a non-production environment.

Recommended load sequence:

1. Configure or confirm demo schools, terms, calendars, and attendance codes.
2. Import staff/teacher records if the environment allows staff imports.
3. Import student records into the Students table.
4. Create or import courses and sections.
5. Enroll students into schools/courses/sections.
6. Load attendance rows for several school days.
7. Export each dataset back out and compare the exported field names with the planned Bronze contract.

PowerSchool import/export documentation notes:

- Use Quick Import or AutoComm for student information imports.
- Include `student_number` when exporting or importing student-linked data.
- Field names must be spelled exactly as PowerSchool expects.
- Test import behavior in a test or backup server before production-like workflows.

## Connector and extract options

| Option | Use when | Notes |
| --- | --- | --- |
| Manual export | No API access yet | Export CSVs from the admin interface and land them as source-shaped Bronze files later. |
| Quick Import / AutoComm | Need to load sample source data | Good for creating a test dataset inside PowerSchool. |
| PowerSchool API/plugin | Partner/developer credentials exist | Likely best long-term connector path, but documentation/access is gated. |
| SIS Views / data dictionary | Admin has access | Useful for stable reporting-style extracts where configured. |

## Synthetic fallback

If no PowerSchool environment is available, do not block Day 1. Create source-shaped CSV files directly:

| File | Grain |
| --- | --- |
| `powerschool_schools.csv` | One row per school |
| `powerschool_people.csv` | One row per person |
| `powerschool_students.csv` | One row per student |
| `powerschool_teachers.csv` | One row per teacher |
| `powerschool_terms.csv` | One row per term |
| `powerschool_courses.csv` | One row per course |
| `powerschool_sections.csv` | One row per course section |
| `powerschool_enrollments.csv` | One row per student enrollment |
| `powerschool_attendance.csv` | One row per student/date or student/period attendance event |

Minimum demo volume: 3 schools, 30 teachers, 300 students, 20 courses, 60 sections, and 20 school days of attendance.

## References

- PowerSchool import/export documentation: https://ps.powerschool-docs.com/pssis-admin/latest/import-and-export
- PowerSource developer portal, login required: https://support.powerschool.com/developer/
