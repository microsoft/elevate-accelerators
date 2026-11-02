# Canvas LMS Research and Development Environment Guide

## Role in the hackathon

Canvas LMS is the primary LMS target for United States education scenarios. It should provide course, section, user, enrollment, assignment, submission, grade, and LMS engagement data.

## Development environment feasibility

Canvas is a strong local real-connector candidate because:

- Canvas LMS is open source.
- Canvas has public REST API documentation.
- Canvas supports SIS CSV imports for roster/course setup.

Use only a local open-source Canvas instance for the hackathon development environment. Do not plan around hosted, institutional, or Free-for-Teacher Canvas environments because admin-level SIS import, account-wide data, and connector permissions can vary and may not be available.

Canvas local setup is heavier than Moodle, so keep a synthetic fallback ready. However, the only real Canvas development path for this project should be the local open-source instance.

## What data is stored there

| Area | Example data |
| --- | --- |
| Users | users, login IDs, SIS IDs, names, emails, roles |
| Courses | courses, terms, dates, workflow state, teachers |
| Sections | sections, SIS section IDs, course relationships |
| Enrollments | student/teacher enrollments, enrollment state, last activity, scores where permitted |
| Assignments | due dates, points, submission types, grading type |
| Submissions | submitted time, workflow state, score, grade, late/missing status |
| Activity | activity stream, last activity, course progress, event-like engagement signals where available |

Canvas API responses are JSON, timestamps use ISO 8601, and API authentication uses OAuth2/access tokens.

## How to create the development environment

### Local open-source Canvas with automated Docker setup

Use the official Canvas LMS repository and its automated Docker development setup script.

GitHub links:

- Canvas LMS repository: https://github.com/instructure/canvas-lms
- Automated setup script: https://github.com/instructure/canvas-lms/blob/master/script/docker_dev_setup.sh
- Docker development docs: https://github.com/instructure/canvas-lms/blob/master/doc/docker/developing_with_docker.md
- Quick Start wiki raw page: https://raw.githubusercontent.com/wiki/instructure/canvas-lms/Quick-Start.md

Official notes from the Quick Start:

- The quick-start environment is for development only and is not production-ready.
- The automated setup script targets macOS or Ubuntu.
- Recommended machine size is at least 150 GB free disk, 8 GB RAM, and a quad-core CPU.
- On Windows, use WSL2 Ubuntu with Docker Desktop rather than trying to run the script directly in Windows PowerShell.

Automated setup steps:

```bash
git clone https://github.com/instructure/canvas-lms.git canvas-lms
cd canvas-lms
git checkout prod
./script/docker_dev_setup.sh
```

If the script fails with a Docker file permission issue, the Quick Start notes that some systems may need:

```bash
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
./script/docker_dev_setup.sh
```

When the setup script finishes:

```bash
docker compose up -d
docker compose ps
```

Then open the local Canvas instance. The Docker docs use:

```text
http://canvas.docker/
```

Pay attention to any `Next Steps` printed by `docker_dev_setup.sh`; the script may ask for additional commands after image build, asset build, or database setup.

After Canvas is running:

1. Complete the admin account setup if prompted.
2. Sign in as the Canvas admin.
3. Confirm the root account ID, usually account `1` in a fresh local instance.
4. Create an API access token or OAuth2 developer key for connector testing.
5. Verify access to SIS import functionality.
6. Load the sample SIS CSV ZIP package.

## How to load sample source data

Canvas supports SIS CSV imports. Build a ZIP package with UTF-8 CSV files and load it through the UI or the SIS Imports API.

Recommended load sequence:

1. `terms.csv`
2. `users.csv`
3. `courses.csv`
4. `sections.csv`
5. `enrollments.csv`
6. Optional groups or additional SIS import files if needed.

After the roster is loaded:

1. Create assignments through the Canvas UI or Assignments API.
2. Enroll test student users.
3. Submit assignment attempts as students or create submission records where API permissions allow.
4. Grade submissions as a teacher/admin.
5. Pull data through REST API endpoints for users, courses, sections, enrollments, assignments, submissions, and activity-like data.

Example SIS import API shape for the local Canvas instance:

```bash
curl \
  -H "Authorization: Bearer <CANVAS_ACCESS_TOKEN>" \
  -F "attachment=@canvas_sis_seed.zip" \
  "http://canvas.docker/api/v1/accounts/1/sis_imports.json?import_type=instructure_csv"
```

Adjust the account ID, host name, and token based on the local setup.

## Connector and extract options

| Option | Use when | Notes |
| --- | --- | --- |
| Local open-source Canvas REST API | Local Docker Canvas is running and an access token is available | Preferred real connector path. |
| Local Canvas SIS CSV import workflow | Need to seed Canvas with roster, course, section, and enrollment data | Required setup path for users, courses, sections, and enrollments. |
| Local Canvas UI/API setup | Need assignments, submissions, and grading events | Use after SIS CSV import creates users/courses/enrollments. |
| Synthetic files | No Canvas environment | Keep Canvas-shaped files aligned to API/SIS fields. |

## Synthetic fallback

If a Canvas environment is not available, generate:

| File | Grain |
| --- | --- |
| `canvas_courses.csv` | One row per course |
| `canvas_sections.csv` | One row per section |
| `canvas_enrollments.csv` | One row per user/course/section enrollment |
| `canvas_assignments.csv` | One row per assignment |
| `canvas_submissions.csv` | One row per student/assignment submission |
| `canvas_activity.csv` | One row per user/course/day engagement event |

Minimum demo volume: 12 courses, 36 sections, 300 students, 80 assignments, 4,000 submissions, and 14 days of activity.

## References

- Canvas API documentation: https://canvas.instructure.com/doc/api/
- Canvas SIS CSV import format: https://canvas.instructure.com/doc/api/file.sis_csv.html
- Canvas SIS Imports API: https://canvas.instructure.com/doc/api/sis_imports.html
- Canvas open-source repository: https://github.com/instructure/canvas-lms
- Canvas automated Docker setup script: https://github.com/instructure/canvas-lms/blob/master/script/docker_dev_setup.sh
- Canvas Docker development docs: https://github.com/instructure/canvas-lms/blob/master/doc/docker/developing_with_docker.md
- Canvas Quick Start wiki raw page: https://raw.githubusercontent.com/wiki/instructure/canvas-lms/Quick-Start.md
