# Moodle LMS Research and Development Environment Guide

## Role in the hackathon

Moodle LMS is the global LMS/content reference source. It should provide courses, users, enrollments, content, activity, completion, grades, and usage logs.

## Development environment feasibility

Moodle is a strong local development candidate because:

- Moodle can be downloaded and run locally.
- Moodle provides Docker configuration for developers and testers through `moodle-docker`.
- Moodle has a web service framework for external systems.
- Moodle can also be hosted through MoodleCloud-style environments when available.

## What data is stored there

| Area | Example data |
| --- | --- |
| Users | users, roles, authentication state |
| Courses | courses, categories, course sections/topics |
| Enrollments | course enrollments, cohorts, groups |
| Content/resources | pages, files, URLs, books, lessons, resources |
| Activities | assignments, quizzes, forums, activities, grade items |
| Completion/progress | activity completion, course completion, gradebook values |
| Logs | user activity events, access times, module interaction events |

## How to create the development environment

### Option A: Moodle Docker for local development

This is the preferred reproducible local development path.

1. Install Docker and Docker Compose.
2. Clone Moodle and Moodle Docker repositories.
3. Set `MOODLE_DOCKER_WWWROOT` to the Moodle source folder.
4. Choose a database, for example PostgreSQL.
5. Copy the Docker config template into the Moodle source folder.
6. Start containers.
7. Initialize the Moodle database for manual testing.
8. Sign in as the admin user.

The official `moodle-docker` documentation provides the exact commands. It also notes that the manual testing site listens on `http://localhost:8000/` and the default admin username is `admin`.

### Option B: hosted Moodle

1. Create a MoodleCloud-style hosted site or use an existing test Moodle site.
2. Request administrator access.
3. Enable web services if API extraction is needed.
4. Load sample users, courses, activities, and content through the UI or CSV upload features.

## How to load sample source data

Recommended load sequence:

1. Create course categories.
2. Create courses and course sections.
3. Create users for teachers and students.
4. Enroll users into courses with teacher/student roles.
5. Add resources: pages, files, URLs, and course content.
6. Add graded activities: assignments and quizzes.
7. Sign in as students and complete realistic interactions.
8. Generate activity logs by viewing resources, submitting work, and completing activities.

For file-based workflows, Moodle web services support file upload through `/webservice/upload.php` with a service token, and file download through `/webservice/pluginfile.php`.

## Connector and extract options

| Option | Use when | Notes |
| --- | --- | --- |
| Moodle Web Services | External API access is enabled | Preferred production-style extraction. |
| Local database queries | Local Docker/test instance only | Useful for hackathon exploration, not a production connector pattern. |
| Admin CSV upload/UI setup | Need to seed test data quickly | Good for users, courses, and enrollments. |
| Synthetic files | No Moodle environment | Keep files aligned to Moodle course/content/usage concepts. |

To use Moodle Web Services:

1. Enable web services in site administration.
2. Enable the REST protocol.
3. Create an external service with required functions.
4. Create a token for a test integration user.
5. Use the live site's API documentation under Site administration > Server > Web services > API Documentation.

## Synthetic fallback

If Moodle is not available, generate:

| File | Grain |
| --- | --- |
| `moodle_courses.csv` | One row per course |
| `moodle_enrollments.csv` | One row per user/course enrollment |
| `moodle_content.csv` | One row per content/resource item |
| `moodle_content_usage.csv` | One row per student/content/day |
| `moodle_activity.csv` | One row per activity event/day |
| `moodle_grades.csv` | One row per graded item/student |

Minimum demo volume: 10 courses, 250 students, 100 content items, 5,000 usage rows, and 2,000 activity rows.

## References

- Moodle Docker for developers and testers: https://github.com/moodlehq/moodle-docker
- Moodle developer tools overview: https://moodledev.io/general/development/tools
- Moodle external services documentation: https://moodledev.io/docs/apis/subsystems/external
- Moodle file upload/download web service documentation: https://moodledev.io/docs/apis/subsystems/external/files
- Moodle downloads: https://download.moodle.org/
