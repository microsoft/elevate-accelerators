"""Build or check a design-time Silver field register against captured evidence."""

import argparse
import csv
import hashlib
import io
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook


BASE = Path(__file__).resolve().parent
WORKBOOK = BASE.parents[1] / 'data-models/Education_Analytics_Silver_Data_Model.xlsx'
OUTPUT = BASE / 'silver-field-readiness.csv'
EXPECTED_WORKBOOK_HASH = '35242165814142a4b2c737a7095a0648551942ee77252dfce5f62bdd7fc7468e'
REFERENCE_TABLES = {'Country', 'TermType', 'ContentType', 'AssessmentType',
                    'AttendanceStatus', 'SignalType', 'ActionType'}
SOURCE_GUIDES = 'canvas-official-schema.md; moodle-official-schema.md; powerschool-official-schema.md; nwea-official-schema.md'

MAPPINGS = """School.Name|NWEA|StudentBySchool.csv|SchoolName|Roster school label is not a complete authoritative school catalog.
School.SchoolCode|NWEA|StudentBySchool.csv|School_StateID|Preserve identifier type; state code is not automatically the local school code.
AcademicTerm.Name|Canvas|enrollment_terms::EnrollmentTerm|name|Join SIS term crosswalk before conformance.
AcademicTerm.StartDate|Canvas|enrollment_terms::EnrollmentTerm|start_at|Nullable source access date; verify calendar meaning and timezone.
AcademicTerm.EndDate|Canvas|enrollment_terms::EnrollmentTerm|end_at|Role overrides and inclusive/exclusive semantics require validation.
AcademicTerm.Name|NWEA|AssessmentResults.csv|TermName|Label only; does not supply a stable key or calendar dates.
Program.Name|NWEA|ProgramAssignments.csv|Program|Assigned label needs governed program definition and identifier.
Person.DisplayName|Canvas|users::User|name|Restricted identity processing; names are not join keys.
Person.GivenName|Moodle|user|firstname|Reference storage only; confirm permitted API fields or database export.
Person.Surname|Moodle|user|lastname|Reference storage only; minimize names outside restricted identity processing.
Person.BirthDate|NWEA|StudentBySchool.csv|StudentDateOfBirth|Declared String; parse approved format and restrict processing.
Person.EmailPseudonym|Moodle|user|email|Input to governed pseudonymization; never copy clear email as a pseudonym.
Person.PrimaryRole|Canvas|enrollments::Enrollment|type|Contextual enrollment role; choose primary role through policy, not source order.
Student.CurrentGradeLevel|NWEA|StudentBySchool.csv|Grade|Roster grade requires time and SIS authority reconciliation; do not assume grade at test.
Student.EnrollmentStatus|Canvas|enrollments::Enrollment|enrollment_state|Course enrollment state is not official school enrollment status.
Teacher.RoleTitle|Canvas|enrollments::Enrollment|role|Custom course role is not necessarily an official staff title.
Teacher.Department|Moodle|user|department|Free text profile field; reconcile SIS authority and visibility.
Course.Name|Canvas|courses::Course|name|LMS shell may not equal the Silver catalog course; crosswalk required.
Course.CourseCode|Canvas|courses::Course|course_code|Display code may be nonunique; do not use as global identity.
Course.Name|Moodle|course|fullname|Reference storage; shell to catalog mapping required.
Course.CourseCode|Moodle|course|shortname|Preserve idnumber separately for institutional identity.
Section.Name|Canvas|sections::Section|name|Use section crosswalk; Moodle topics are not equivalent.
Section.SectionCode|Canvas|sections::Section|sis_section_id|SIS identifier permission-dependent; distinguish code from internal ID.
Section.StartDate|Canvas|sections::Section|start_at|Course and term restrictions affect actual availability.
Section.EndDate|Canvas|sections::Section|end_at|Retain source timestamp/timezone and null semantics.
Section.DeliveryMode|Canvas|courses::Course|course_format|Course-level delivery mode must be reconciled to section.
Enrollment.EnrollmentRole|Canvas|enrollments::Enrollment|type|Map custom roles and distinguish school from section enrollment.
Enrollment.EntryDate|Canvas|enrollments::Enrollment|start_at|May be null; do not substitute creation time as enrollment start.
Enrollment.ExitDate|Canvas|enrollments::Enrollment|end_at|Do not infer absent end date from current status.
Enrollment.EntryDate|Moodle|user_enrolments|timestart|Reference storage; zero sentinel and multiple plugin enrollments require rules.
Enrollment.ExitDate|Moodle|user_enrolments|timeend|Reference storage; zero sentinel is not a 1970 date.
TeacherAssignment.RoleInSection|Canvas|enrollments::Enrollment|role|Resolve teacher or TA role in section context.
TeacherAssignment.StartDate|Canvas|enrollments::Enrollment|start_at|Teacher enrollment interval candidate; preserve historical assignments.
TeacherAssignment.EndDate|Canvas|enrollments::Enrollment|end_at|Current endpoint is not a complete change history.
LearningContent.Name|Canvas|assignments::Assignment|name|Assignment subtype only; pages/files/modules have separate identities.
LearningContent.Name|Moodle|assign|name|Assignment instance differs from course-module placement.
LearningContent.StandardCode|Canvas|assignments::Assignment|ab_guid|Optional array; use versioned many-to-many alignment, not a lossy single string.
LearningContent.AvailableFromDate|Canvas|assignments::Assignment|unlock_at|Context-dependent; preserve per-student overrides and source availability rules.
LearningContent.DueDate|Canvas|assignments::Assignment|due_at|Base/context date is not all students' effective due date.
LearningContent.MaxScore|Canvas|assignments::Assignment|points_possible|Meaningful only for validated numeric grading semantics.
LearningContent.DueDate|Moodle|assign|duedate|Reference base date; resolve overrides, group priority and extensions separately.
LearningContent.AvailableFromDate|Moodle|assign|allowsubmissionsfromdate|Zero may mean unset; do not infer universal content availability.
LearningContent.MaxScore|Moodle|assign|grade|Can encode a scale; not always a positive maximum.
Assessment.Name|NWEA|AssessmentResults.csv|TestName|Definition identifier must not be confused with TestID event identifier.
Assessment.Subject|NWEA|AssessmentResults.csv|Subject|Map vocabulary with test scale; NWEA Course is not SIS course.
Assessment.Name|Canvas|quizzes::Quiz|title|Classic Quiz definition; survey and New Quizzes are separate contracts.
Assessment.MaxScore|Canvas|quizzes::Quiz|points_possible|Classroom points candidate only; never use a RIT validity cutoff for MAP.
AssessmentResult.AssessmentDate|NWEA|AssessmentResults.csv|TestStartDate|Parse declared String; preserve TestStartTime and confirm workstation timezone.
AssessmentResult.ScoreRaw|NWEA|AssessmentResults.csv|TestRITScore|Scale score, not raw item points; preserve RIT scale and SEM separately.
AssessmentResult.ScorePercent|NWEA|AssessmentResults.csv|PercentCorrect|Adaptive-test diagnostic only, not percent mastery; never use RIT or percentile here.
AssessmentResult.ProficiencyLevel|NWEA|AssessmentResults.csv|ProjectedProficiencyLevel1|Projection requires study/season/grade context; not observed proficiency. One scalar is lossy.
AssessmentResult.GrowthMeasure|NWEA|AssessmentResults.csv|FalltoFallObservedGrowth|Only one seasonal measure; preserve pairing, eligibility, units, SE and other families separately.
AssignmentSubmission.DueDate|Canvas|assignments::AssignmentOverride|due_at|Resolve actual audience, membership and contextual base date; do not copy an arbitrary override.
AssignmentSubmission.SubmittedDate|Canvas|submissions::Submission|submitted_at|Nullable for unsubmitted work; preserve attempts and source context.
AssignmentSubmission.AttemptNumber|Canvas|submissions::Submission|attempt|Regrades can modify the same attempt; source-qualified identity required.
AssignmentSubmission.AttemptNumber|Moodle|assign_submission|attemptnumber|Reference storage starts at zero; preserve source numbering.
AssignmentSubmission.SubmissionStatus|Canvas|submissions::Submission|workflow_state|Map status without losing draft, pending review, graded and unsubmitted distinctions.
AssignmentSubmission.SubmissionStatus|Moodle|assign_submission|status|Reference storage; group/reopened/latest semantics require extraction contract.
AssignmentSubmission.ScoreRaw|Canvas|submissions::Submission|score|Retain display grade, posting, regrade and excusal state separately.
AssignmentSubmission.ScoreRaw|Moodle|assign_grades|grade|Separate grade record; join user/assignment/attempt correctly.
AssignmentSubmission.IsLate|Canvas|submissions::Submission|late|Requires assigned, visible, nonexcused population and effective date.
AssignmentSubmission.IsMissing|Canvas|submissions::Submission|missing|Source flag subject to policy; null submitted date alone is not missing work.
DigitalEngagement.EventDate|Canvas|users::PageView|created_at|Log-derived event, not complete evidence of learning or attendance.
DigitalEngagement.EventDate|Moodle|logstore_standard_log|timecreated|Reference storage Unix seconds; log access and retention not established by an API.
DigitalEngagement.EventType|Moodle|logstore_standard_log|eventname|Versioned canonical taxonomy needs component/action/target and actor rules.
DigitalEngagement.EventObject|Moodle|logstore_standard_log|objectid|Polymorphic through objecttable; not always a content identifier.
DigitalEngagement.ActivityDurationSeconds|Canvas|users::PageView|interaction_seconds|Observed interaction proxy; not verified active learning time.
DigitalEngagement.ActorRole|Canvas|enrollments::Enrollment|type|Resolve actor context on event date; summary current role is not history.
ContentUsage.IsCompleted|Moodle|course_modules_completion|completionstate|Reference state, not Boolean; account for manual/pass/fail and disabled tracking.
ContentUsage.LastAccessedDate|Moodle|user_lastaccess|timeaccess|Course-level summary only, insufficient for per-content last access without additional events.
"""

OVERRIDES = {
    'Person.AadObjectIdPseudonym': ('Unestablished optional input', 'No authoritative Entra object-ID mapping established in the four selected source contracts. Leave unavailable; do not fabricate or expand connector scope.'),
    'Attendance.AttendanceDate': ('Tenant evidence required', 'PowerSchool event schema and attendance mode must be obtained; public UI labels are not API fields.'),
    'Attendance.AttendancePeriod': ('Tenant evidence required', 'Acquire PowerSchool meeting/period schema and school schedule; preserve daily versus meeting grain.'),
    'Attendance.AttendanceMinutes': ('Derivation or tenant evidence required', 'Obtain attended versus absent time units and conversion rules; do not map minutes_absent directly to attended minutes.'),
    'Attendance.ExpectedMinutes': ('Derivation or tenant evidence required', 'Column already exists. Source scheduled opportunity requires calendar/track/bell schedule and enrollment context.'),
    'Attendance.AbsenceReason': ('Tenant evidence required', 'Acquire approved codes; avoid sensitive narrative reasons unless justified.'),
    'Attendance.IsExcused': ('Derivation or tenant evidence required', 'Use approved school code/category mapping; a label or ADA point is not enough.'),
    'AssignmentSubmission.ScorePercent': ('Derivation required', 'Use score and valid points denominator, grading scale/version, excusal and posting context. Extra credit may exceed 100.'),
    'AssignmentSubmission.IsCompleted': ('Derivation required', 'Define completion independently of submitted/graded/missing flags; include audience, attempts and exemptions.'),
    'AssessmentResult.PassIndicator': ('Policy and evidence required', 'No universal MAP pass flag. Require assessment-specific threshold and study/scale version; otherwise remain null.'),
    'Assessment.ProficiencyScale': ('Policy and evidence required', 'Govern assessment-specific scale or linking study; achievement quintile is not state proficiency.'),
    'ContentUsage.EngagementQualityScore': ('Platform derivation required', 'No native measure established; define evidence, rule version and uncertainty without treating missing telemetry as poor engagement.'),
    'ContentUsage.TimeOnTaskSeconds': ('Derivation required', 'No universal measured active duration. Use approved source-specific observation or explicitly estimated sessions with caps and coverage.'),
    'ContentUsage.CompletionPercent': ('Derivation required', 'Activity state is not percentage. Define valid required-item denominator; do not copy course progress to every content row.'),
    'ContentUsage.ViewsCount': ('Derivation required', 'Count deduplicated approved content events; require linked object identity and known observation coverage.'),
    'ContentUsage.UsageDate': ('Derivation required', 'Bucket source events by approved local date and declared student-content grain.'),
    'ContentUsage.FirstAccessedDate': ('Derivation required', 'Earliest retained content event is not necessarily first-ever access; retain historical coverage boundaries.'),
    'DigitalEngagement.ApplicationName': ('Platform metadata', 'Use governed source instance/application identifier; never infer from content names.'),
    'DigitalEngagement.AccessCount': ('Derivation required', 'Distinguish single-event weight from daily aggregate; deduplicate and preserve units/window.'),
    'DigitalEngagement.UsedIndicator': ('Derivation required', 'Observed qualifying use only; lack of an available feed is unknown, not false.'),
    'DigitalEngagement.ActivityReportPeriodDays': ('Platform metadata', 'Set from declared extraction/aggregation window; not applicable to a point event unless explicitly defined.'),
    'TeacherAssignment.IsPrimaryTeacher': ('Policy and evidence required', 'Use effective-dated authoritative staff association; do not pick the first LMS teacher.'),
    'AcademicTerm.AcademicYear': ('Policy and evidence required', 'Use approved SIS calendar and term crosswalk; names/WI are not sufficient evidence.'),
    'LearningContent.IsRequired': ('Policy and evidence required', 'Assignment visibility, audience and module completion requirements differ; no universal required flag.'),
    'LearningContent.Language': ('Tenant evidence required', 'Site/user locale does not establish content language.'),
    'LearningContent.DifficultyLevel': ('Tenant evidence required', 'No canonical difficulty measure established; require content metadata or governed assessment definition.'),
}


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def evidence_index():
    index = {}
    for row in load_csv(BASE / 'lms-field-evidence.csv'):
        if row['interface'] == 'SIS import CSV (inbound only)':
            continue
        key = (row['source'], row['entity'], row['field'])
        assert key not in index, key
        index[key] = (row['interface'], row['evidence_url'], row['version'])
    for row in load_csv(BASE / 'nwea-export-fields.csv'):
        if row['group'] == 'literal_field':
            index[('NWEA', row['file'], row['field'])] = (
                'Published export dictionary', row['evidence_url'], '2026-09-14 dictionary snapshot')
    return index


def build_rows():
    workbook_hash = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
    assert workbook_hash == EXPECTED_WORKBOOK_HASH, 'Silver workbook changed; review mappings before regenerating.'
    workbook = load_workbook(WORKBOOK, read_only=True, data_only=True)
    schema = list(workbook['Silver_Schema'].values)[1:]
    overview = {row[0]: row for row in list(workbook['Tables_Overview'].values)[1:]}
    workbook.close()
    assert len(schema) == 345 and len(overview) == 28
    targets = {f'{row[0]}.{row[1]}' for row in schema}
    assert len(targets) == len(schema)
    evidence = evidence_index()
    mappings = {}
    for target, source, entity, field, note in csv.reader(io.StringIO(MAPPINGS), delimiter='|'):
        assert target in targets, target
        assert (source, entity, field) in evidence, (source, entity, field)
        mappings.setdefault(target, []).append((source, entity, field, note))
    assert set(OVERRIDES) <= targets
    result = []
    for table, column, dtype, requirement, description in schema:
        target = f'{table}.{column}'
        disposition = 'Tenant evidence required'
        decision = 'No exact mapping selected in this register. Consult source guides and acquire permitted target-environment fields; do not infer coverage from similar names.'
        if table in {'Source', 'SourceSystemIdMapping'}:
            disposition = 'Platform metadata'
            decision = 'Connector registry or lineage crosswalk; source-qualified identity, schema/extract manifest and match evidence required.'
        elif column in {'CreatedDate', 'ModifiedDate', 'SourceSystemId', 'SourceId'}:
            disposition = 'Platform lineage policy'
            decision = 'Define source versus conformance timestamp semantics. Preserve extraction time separately; absent source time is unknown. SourceId may require a stable composite.'
        elif table in REFERENCE_TABLES:
            disposition = 'Governed reference'
            decision = 'Maintain versioned controlled values and source-code mapping; do not claim vendor-native conformed reference records.'
        elif table == 'StudentSignal':
            disposition = 'Platform derivation required'
            decision = 'Compute from validated evidence with rule/model version, time window, provenance and uncertainty. No operational source supplies this cross-source signal.'
        elif table == 'InterventionAction':
            disposition = 'Platform workflow required'
            decision = 'Capture authorized action lifecycle, actor, status and evidence; completion is not inferred from a recommendation. Structured outcome measurements need extension.'
        elif 'PK' in str(requirement):
            disposition = 'Canonical identity required'
            decision = 'Generate stable opaque Silver key from governed identity resolution, not bare source ID; preserve source record grain and namespace.'
        elif 'FK' in str(requirement):
            disposition = 'Crosswalk required'
            decision = 'Resolve to the referenced Silver entity with source instance/type and valid-time context. Unknown or ambiguous linkage must remain visible, not guessed.'
        elif column in {'IsActive', 'IsActiveInTerm', 'IsCurrent'}:
            disposition = 'Derivation required'
            decision = 'Define status and effective-date rule at a reproducible as-of time; preserve source state, permissions and absence of observations separately.'
        if target in OVERRIDES:
            disposition, decision = OVERRIDES[target]
        candidates, interfaces, urls, versions = [], [], [], []
        if target in mappings:
            disposition = 'Documented candidate; conformance required'
            notes = []
            for source, entity, field, note in mappings[target]:
                interface, url, version = evidence[(source, entity, field)]
                candidates.append(f'{source}:{entity}.{field}')
                interfaces.append(interface)
                urls.append(url)
                versions.append(version)
                notes.append(note)
            decision = ' '.join(notes)
        result.append({
            'SilverTable': table, 'SilverField': column, 'SilverType': dtype,
            'WorkbookRequirement': requirement, 'WorkbookPriority': overview[table][2],
            'WorkbookGrain': overview[table][3], 'Disposition': disposition,
            'CandidateSourceFields': '; '.join(candidates),
            'CandidateInterfaces': '; '.join(interfaces), 'EvidenceURLs': '; '.join(urls),
            'EvidenceVersions': '; '.join(versions), 'DecisionOrGap': decision,
            'TenantValidation': 'Not performed', 'SourceGuides': SOURCE_GUIDES,
            'WorkbookSHA256': workbook_hash,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate saved register without modifying files.')
    args = parser.parse_args()
    rows = build_rows()
    if args.check:
        assert load_csv(OUTPUT) == rows, 'Saved register differs from reviewed mappings/workbook.'
    else:
        with OUTPUT.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        assert load_csv(OUTPUT) == rows
    print('PASS: 345 unique Silver fields; selected references exist in official inventories; workbook hash unchanged.')
    print('Tenant records verified: 0. This is a triage register, not an approved transformation contract.')
    for disposition, count in sorted(Counter(row['Disposition'] for row in rows).items()):
        print(f'{disposition}: {count}')


if __name__ == '__main__':
    main()