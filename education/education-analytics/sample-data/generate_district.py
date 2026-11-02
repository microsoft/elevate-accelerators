"""Generate a synthetic middle-school district as streaming source/table CSVs."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from itertools import chain
from math import fsum
from pathlib import Path


BASE = Path(__file__).resolve().parent
OUTPUT = BASE
EVIDENCE = BASE / 'schema-evidence'
NULL = '\\N'
DISTRICT_NAME = 'Cedar Valley School District'
GIVEN_NAMES = ('Amelia', 'Oliver', 'Sophia', 'Elijah', 'Maya', 'Lucas', 'Isabella', 'Noah',
               'Aisha', 'Ethan', 'Chloe', 'Mateo', 'Zoe', 'Liam', 'Aria', 'Daniel',
               'Grace', 'Leo', 'Layla', 'Isaac', 'Nora', 'Owen', 'Priya', 'Adam',
               'Sofia', 'Julian', 'Hannah', 'Caleb', 'Leila', 'Samuel', 'Elena', 'Adrian')
STAFF_GIVEN_NAMES = ('Margaret', 'Thomas', 'Rebecca', 'Jonathan', 'Diana', 'Gregory',
                     'Teresa', 'Vincent', 'Monica', 'Raymond', 'Claudia', 'Frederick',
                     'Denise', 'Lawrence', 'Renee', 'Martin', 'Valerie', 'Philip',
                     'Judith', 'Marcus', 'Elaine', 'Russell', 'Cynthia', 'Warren')
SURNAMES = ('Bennett', 'Rivera', 'Patel', 'Kim', 'Morgan', 'Brooks', 'Nguyen', 'Carter',
            'Reed', 'Sullivan', 'Chen', 'Garcia', 'Hayes', 'Ahmed', 'Parker', 'Mitchell',
            'Turner', 'Wilson', 'Collins', 'Murphy', 'Flores', 'Shah', 'Walker', 'Ross',
            'Cooper', 'Bailey', 'Evans', 'Foster', 'Torres', 'Singh', 'Reyes', 'Hughes',
            'Ward', 'Price', 'Kelly', 'Watson', 'Gray', 'Sanders', 'Powell', 'Long',
            'Scott', 'Green', 'Adams', 'Nelson', 'Hill', 'Young', 'Allen', 'Wright',
            'King', 'Woods', 'Bell', 'Ortiz', 'James', 'Perry', 'Cole', 'Russell',
            'Stone', 'Diaz', 'West', 'Lane', 'Santos', 'Park', 'Ford', 'Walsh')
# A second learner surname pool, used only once the roster outgrows the first one (former
# learners from the prior school year do). Disjoint from both other pools.
EXTRA_SURNAMES = ('Alvarez', 'Barnes', 'Castro', 'Dixon', 'Ellis', 'Fisher', 'Gibson', 'Harper',
                  'Ibrahim', 'Jensen', 'Khan', 'Larsen', 'Mendoza', 'Nash', 'Owens', 'Pierce',
                  'Quinn', 'Ramos', 'Shaw', 'Tran', 'Vargas', 'Wade', 'Yates', 'Zamora',
                  'Austin', 'Banks', 'Chavez', 'Dunn', 'Estrada', 'Freeman', 'Grant', 'Hart',
                  'Irwin', 'Jordan', 'Kemp', 'Lowe', 'Marsh', 'Novak', 'Olsen', 'Patton',
                  'Rhodes', 'Silva', 'Tucker', 'Vance', 'Webb', 'Abbott', 'Becker', 'Cohen',
                  'Delgado', 'Erikson', 'Fleming', 'Gordon', 'Hale', 'Ingram', 'Joyce', 'Keller',
                  'Lyons', 'Moreno', 'Norris', 'Osborne', 'Pratt', 'Riley', 'Sutton', 'Tate')
# Staff draw from their own surname pool as well as their own given-name pool. Sharing the
# surnames was enough to put a teacher and a learner on screen as "Bennett" beside
# "Bennett" in the same class, which reads as one person recorded twice rather than as two
# people. Keeping both halves of the name disjoint is what makes the roles distinguishable
# wherever only part of a name is shown.
STAFF_SURNAMES = ('Abernathy', 'Blackwood', 'Castellanos', 'Dunmore', 'Eastwick', 'Fairbairn',
                  'Galloway', 'Hartley', 'Ingersoll', 'Kowalski', 'Lindqvist', 'Marchetti',
                  'Norrington', 'Oyelaran', 'Pemberton', 'Quintero', 'Rutherford', 'Stanhope',
                  'Thackeray', 'Underhill', 'Vasquez', 'Wexford', 'Yarborough', 'Zielinski',
                  'Ashworth', 'Beaumont', 'Calloway', 'Devereaux', 'Ellsworth', 'Fitzgerald',
                  'Granville', 'Holloway', 'Isakson', 'Kirkpatrick', 'Lockhart', 'Montgomery')
# Fictional schools placed at real Snohomish County, Washington localities: a real city,
# its real state and postal code, and a street that exists in that city. The street numbers
# are synthetic, so an address geocodes to the right neighbourhood for a map without
# claiming a real building. Fields are separate because a single "Everett, Washington" cell
# is not an address and cannot be filtered, joined or geocoded as one.
SCHOOL_PROFILES = (
    ('Alder Heights', '2415 Colby Avenue', 'Everett', 'WA', '98201', 'Snohomish'),
    ('Summit Harbor', '19200 44th Avenue West', 'Lynnwood', 'WA', '98036', 'Snohomish'),
    ('Rainier View', '7500 212th Street SW', 'Edmonds', 'WA', '98026', 'Snohomish'),
    ('Cascade Point', '11700 Mukilteo Speedway', 'Mukilteo', 'WA', '98275', 'Snohomish'),
    ('North Creek', '15600 Main Street', 'Mill Creek', 'WA', '98012', 'Snohomish'),
    ('Harbor Ridge', '23200 58th Avenue West', 'Mountlake Terrace', 'WA', '98043', 'Snohomish'),
)
COURSE_CODES = ('MATH', 'ELA', 'SCI', 'HIST', 'ART', 'PE')
COURSE_TITLES = ('Mathematics', 'English Language Arts', 'Integrated Science',
                 'World History', 'Visual Arts', 'Physical Education')
TASK_TOPICS = (
    ('Ratios and Proportions', 'Expressions and Equations', 'Geometry and Measurement',
     'Statistics and Probability', 'Number Systems'),
    ('Reading for Evidence', 'Narrative Writing', 'Vocabulary in Context',
     'Comparing Texts', 'Argument and Persuasion'),
    ('Scientific Investigation', 'Matter and Energy', 'Earth Systems',
     'Ecosystems', 'Forces and Motion'),
    ('Reading Historical Sources', 'Ancient Civilizations', 'Trade and Exchange',
     'Geography and Society', 'Government and Citizenship'),
    ('Line and Shape', 'Color Theory', 'Perspective Drawing',
     'Visual Storytelling', 'Art and Culture'),
    ('Movement Skills', 'Teamwork and Strategy', 'Personal Fitness',
     'Health and Wellbeing', 'Goal Setting'),
)
TASK_FORMATS = ('Practice', 'Reflection', 'Application', 'Project', 'Review', 'Assessment')

# How often each kind of task is set, aligned to TASK_FORMATS. A class sets routine practice
# far more often than it sets a project or an end-of-unit assessment, so the six formats must
# not arrive in equal sixths.
FORMAT_FREQUENCY = (0.34, 0.16, 0.21, 0.07, 0.15, 0.07)

# The totals each kind of task is marked out of, aligned to TASK_FORMATS. A piece of practice
# and an end-of-unit assessment are not marked out of the same number, which is why the
# coursework measure divides summed points by summed maxima rather than averaging per-task
# percentages: with one shared maximum the two arithmetics agree and the distinction is
# untestable.
FORMAT_MAX_SCORES = ((10, 15, 20), (20, 25, 30), (40, 50, 60),
                     (80, 100, 120), (25, 30, 40), (60, 75, 100))

# How severely each subject marks, in percentage points, aligned to COURSE_TITLES. Two
# departments marking the same piece of work do not award the same number, so a mark is
# only comparable within its own subject. Making that explicit here is what stops the
# report presenting six subjects as one scale.
SUBJECT_MARKING = (-4.0, -1.5, -2.5, 0.0, 3.5, 5.0)

# How demanding each kind of task is, aligned to TASK_FORMATS: routine practice scores
# above a project or an end-of-unit assessment.
FORMAT_DEMAND = (1.5, 0.5, -1.0, -2.5, 1.0, -3.5)

COURSEWORK_BASE = 74.0

# How many learners a class in each subject holds, aligned to COURSE_TITLES. A school does
# not teach every subject in groups of the same size: a practical or physical subject runs
# fewer and larger groups than a core written one. Every subject used to inherit the
# homeroom grid, so all six had exactly one class per homeroom and the class counts came
# out identical six times over. Sizes differ here, so the number of classes differs too.
SUBJECT_CLASS_SIZES = (24, 26, 28, 30, 34, 48)

# How much set work each subject carries, in tasks per class per year relative to the base,
# aligned to COURSE_TITLES. Mathematics sets frequent short practice; physical education
# records comparatively little written work. Without this every subject drew its task count
# from one distribution, so six very different departments published within a few tasks of
# each other and the totals only differed by rounding.
SUBJECT_TASK_LOAD = (9, 6, 3, 0, -4, -7)

# Starting RIT for Mathematics and English Language Arts, the two assessed subjects.
ASSESSMENT_BASE = (206.0, 203.0)

# How a learner's attendance moves over the year. Most learners hold a steady pattern, but a
# real register also holds learners whose attendance dips mid-year, slides gradually or
# improves. A fixture where everyone's absence rate is constant from September to June has
# nothing for a comparison of periods, a rolling rate or a follow-up to find.
ATTENDANCE_TRAJECTORIES = (('Steady', 0.70), ('Mid-year dip', 0.15),
                           ('Gradual decline', 0.08), ('Improving', 0.07))

# Early-warning rules a school applies by hand. Both are deliberately simple and visible, so a
# report can show which learners met a rule without a risk score or a prediction.
ATTENDANCE_RULE_ABSENCES = 5
ATTENDANCE_RULE_DAYS = 20
MISSING_WORK_RULE_MISSING = 3
MISSING_WORK_RULE_TASKS = 5
CHRONIC_ABSENCE_RATE = 0.10

# How far back absence reaches into a piece of work: the two school weeks before it is due.
COURSEWORK_ABSENCE_DAYS = 10

# What teachers log when a rule is met. Attendance actions escalate in this order for the
# same learner; missing-work follow-ups are logged by the teacher of that class.
ATTENDANCE_ACTIONS = ('Student check-in', 'Family contact', 'Attendance plan', 'Counselor referral')
ATTENDANCE_REASON = f'Attendance: {ATTENDANCE_RULE_ABSENCES} or more absences in {ATTENDANCE_RULE_DAYS} school days'
MISSING_WORK_ACTION = 'Missing work follow-up'
MISSING_WORK_REASON = (f'Coursework: {MISSING_WORK_RULE_MISSING} or more of the last '
                       f'{MISSING_WORK_RULE_TASKS} pieces of work missing')
MAX_WORK_FOLLOW_UPS = 3

# Not every learner who meets a rule gets an action, and not every action is followed by a
# change. Both gaps are what a real log shows, and both are needed so a before/after view
# can find learners who improved and learners who did not.
ACTION_LOGGED_SHARE = 0.75
ACTION_RESPONSE_SHARE = 0.60
ACTION_COOLDOWN_DAYS = 15
FOLLOW_UP_DAYS = 10
RESPONSE_RESIDUAL = 0.35
RESPONSE_RAMP_DAYS = 10
# A coursework follow-up is compared on the pieces of work in that class, not on days: a
# class can set nothing for two weeks, so a day window would often hold no work at all.
FOLLOW_UP_WORK_PIECES = 5
# Once the missing-work rule is met in a class, the learner keeps missing more work there until
# a follow-up they respond to. Without this, missing work is a fresh draw for every task, the
# window that met the rule is followed by an ordinary one for everybody, and a before/after
# view shows almost every learner improving whether or not anything was done.
WORK_SLUMP_FACTOR = 5.0

# The school year before the current one. The SIS keeps earlier years' enrollments apart from
# the current one, as PowerSchool's reenrollments table does, so the prior year adds school
# membership, attendance and assessment history but no class rosters or LMS coursework.
PRIOR_SCHOOL_YEAR_START = date(2024, 9, 2)
CURRENT_SCHOOL_YEAR_START = date(2025, 9, 1)
# Daily absence baselines by school in the prior year, aligned to the current year's. One
# school improves, one declines and one holds, so a year-on-year view has movement to show.
PRIOR_SCHOOL_BASELINE = (0.058, 0.057, 0.040)
CURRENT_SCHOOL_BASELINE = (0.052, 0.067, 0.038)
# How membership changes between the two years, beyond the year groups moving up.
NEW_TO_DISTRICT_SHARE = 0.06
TRANSFER_SHARE = 0.03
LEFT_DISTRICT_SHARE = 0.05
FINAL_GRADE = 8
PRIOR_RIT_OFFSET = 9.0


def school_year_label(start):
    return f'{start.year}-{start.year + 1}'


def instructional_days_from(start, count):
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def person_name(identifier, staff=False):
    index = identifier - 1
    given_names = STAFF_GIVEN_NAMES if staff else GIVEN_NAMES
    surnames = STAFF_SURNAMES if staff else SURNAMES
    capacity = len(given_names) * len(surnames)
    if not staff and index >= capacity:
        # Former learners push the roster past the first pool. A second, disjoint pool keeps
        # every name unique without renaming anyone the first pool already named.
        index -= capacity
        surnames = EXTRA_SURNAMES
    return given_names[index % len(given_names)], surnames[(index // len(given_names) + index * 17) % len(surnames)]


def full_name(identifier, staff=False):
    return ' '.join(person_name(identifier, staff))


def contact_email(identifier, staff=False):
    given, surname = person_name(identifier, staff)
    role = 'staff' if staff else 'students'
    return f'{given.lower()}.{surname.lower()}.{identifier}@{role}.cedarvalley.example'


def school_name(identifier):
    campus = (identifier - 1) // len(SCHOOL_PROFILES)
    suffix = f' Campus {campus + 1}' if campus else ''
    return f'{SCHOOL_PROFILES[(identifier - 1) % len(SCHOOL_PROFILES)][0]} Middle School{suffix}'


def school_address(identifier):
    """Street, city, state, postal code and county for one school.

    Extra campuses reuse a locality but move along its street, so two schools never share
    one address and a map does not stack them on a single pin.
    """
    campus = (identifier - 1) // len(SCHOOL_PROFILES)
    street, city, state, postal_code, county = SCHOOL_PROFILES[(identifier - 1) % len(SCHOOL_PROFILES)][1:]
    if campus:
        number, _, remainder = street.partition(' ')
        street = f'{int(number) + campus * 100} {remainder}'
    return street, city, state, postal_code, county


def stable_unit(*values):
    value = '|'.join(str(value) for value in values).encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest()[:8], 'big') / 2**64


def stable_spread(*values):
    """A repeatable deviate in [-1, 1], clustered around zero rather than flat.

    Two draws added together give a triangular distribution, so most learners sit near the
    middle and the extremes stay rare. A single uniform draw would make a learner as likely
    to be exceptional as average, which reads as noise rather than as a cohort.
    """
    return stable_unit('spread-a', *values) + stable_unit('spread-b', *values) - 1


def student_ability(student):
    """How this learner does across the board, in percentage points around the base."""
    return 9.0 * stable_spread('ability-v1', student)


def subject_aptitude(student, subject):
    """How this learner does in one subject, over and above their general standing.

    This is the term the earlier fixture lacked. Scores were `55 + (student + task +
    subject) % 46`, so `subject` only shifted a cycle: every subject averaged 77.5% across
    the district, and for one learner the subjects came out as a ramp whose direction was
    decided by their id number. A report asking "which subject should I follow up on" could
    only read that arithmetic back. Holding a per-learner, per-subject offset constant is
    what makes a learner genuinely stronger in some subjects than others.
    """
    return 9.0 * stable_spread('aptitude-v1', student, subject)


def topic_aptitude(student, subject, unit):
    """How this learner does on one unit within a subject.

    Smaller than the subject term on purpose: a learner who is broadly fine in a subject can
    still have one topic that has not landed, which is the case a teacher most wants to
    find, and it should not be large enough to swamp the subject signal above it.
    """
    return 6.0 * stable_spread('topic-v1', student, subject, unit)


def coursework_standing(student, subject):
    """This learner's overall standing in a subject, roughly -18 to +18 points."""
    return student_ability(student) + subject_aptitude(student, subject)


def coursework_percentage(student, subject, unit, activity, task, recent_absence=0.0):
    """The proportion of a task's mark scheme this learner earns, 0 to 100.

    `recent_absence` is the share of the instructional days before the due date that the
    learner missed. Work set while a learner was away is marked lower, so a period of absence
    shows up in the coursework as well as in the register.
    """
    return min(100.0, max(0.0, COURSEWORK_BASE
                          + student_ability(student)
                          + subject_aptitude(student, subject)
                          + topic_aptitude(student, subject, unit)
                          + SUBJECT_MARKING[subject]
                          + FORMAT_DEMAND[activity]
                          - 12.0 * recent_absence
                          + 4.0 * stable_spread('mark-v1', student, subject, task)))


def coursework_score(student, subject, task, unit, activity, max_score, recent_absence=0.0):
    """The mark awarded for one piece of work, out of that task's own maximum.

    A mark scheme has no room above its maximum or below zero, and the Gold contract
    asserts that a graded score sits inside it.
    """
    return round(max_score * coursework_percentage(student, subject, unit, activity, task, recent_absence) / 100.0, 1)


def missing_probability(student, subject, recent_absence):
    """How likely a piece of work is never handed in.

    Tied to standing in that subject, so the learner struggling with the marks is also the
    one with gaps in what was handed in, and to recent absence, so work set while a learner
    was away goes missing more often. Keeping them independent would produce a cohort
    where nobody's missing work, low marks and absences ever coincide.
    """
    return min(0.35, max(0.01, 0.055 - 0.0035 * coursework_standing(student, subject) + 0.30 * recent_absence))


def late_probability(student, subject, recent_absence):
    """How likely work arrives after the due date, on the same reasoning as missing work."""
    return min(0.35, max(0.02, 0.085 - 0.0045 * coursework_standing(student, subject) + 0.25 * recent_absence))


def assessment_score(student, subject, window, interval_absence=(), year=''):
    """RIT score for one test sitting.

    Built from the same ability and aptitude terms as the coursework, so a learner who is
    stronger in Mathematics than in English reads that way in both places. Growth between
    sittings shrinks with the share of days missed in between, so a learner whose attendance
    dipped in winter gains less between the Fall and Winter tests. A prior-year sitting
    (`year` set) starts a year's growth lower and draws its own sitting-to-sitting noise.
    """
    slow_growth = stable_unit('growth-v1', student) < 0.12
    growth = sum((2.0 if slow_growth else 5.0) * max(0.0, 1.0 - 2.5 * rate)
                 for rate in interval_absence[:window])
    rit = (ASSESSMENT_BASE[subject]
           + 0.85 * student_ability(student)
           + 0.75 * subject_aptitude(student, subject)
           + growth
           - (PRIOR_RIT_OFFSET if year else 0.0)
           + 1.5 * (stable_spread('rit-v1', year, student, subject, window) if year
                    else stable_spread('rit-v1', student, subject, window)))
    return round(rit)


def year_unit(seed, year, *values):
    """stable_unit for the current year (`year` empty) or with its own draw for another year."""
    return stable_unit(seed, year, *values) if year else stable_unit(seed, *values)


def attendance_trajectory(student, year=''):
    """Which of the year-long attendance patterns this learner follows in a school year.

    Each year is drawn separately, so a learner who dipped last winter need not dip again.
    """
    return ATTENDANCE_TRAJECTORIES[weighted_choice([share for _, share in ATTENDANCE_TRAJECTORIES],
                                                   year_unit('trajectory-v1', year, student))][0]


def trajectory_effect(student, index, instructional_days, year=''):
    """How much this learner's absence risk is raised or lowered on one instructional day."""
    kind = attendance_trajectory(student, year)
    progress = index / max(1, instructional_days - 1)
    if kind == 'Gradual decline':
        return 1.0 + 1.4 * progress
    if kind == 'Improving':
        return 1.6 - 0.8 * progress
    if kind == 'Mid-year dip':
        onset = 0.25 + 0.28 * year_unit('dip-onset-v1', year, student)
        peak = 2.2 + 1.6 * year_unit('dip-peak-v1', year, student)
        fade = onset + 0.30 + 0.15 * year_unit('dip-fade-v1', year, student)
        if progress < onset:
            return 1.0
        rise = min(1.0, (progress - onset) * instructional_days / 8)
        # Left alone, a dip eases a little towards the end of the year but does not vanish.
        ease = max(0.0, min(1.0, (progress - fade) * instructional_days / 20))
        return 1.0 + (peak - 1.0) * rise * (1.0 - 0.5 * ease)
    return 1.0


def attendance_risk(student):
    """How prone this learner is to absence, held from one school year to the next."""
    risk = 0.45 + stable_unit('attendance-risk', student) * 1.25
    if stable_unit('chronic-risk', student) < 0.07:
        risk += 1.35
    return risk


def case_owner_subject(student):
    """The core subject whose teacher logs this learner's attendance actions."""
    return int(stable_unit('case-owner-v1', student) * 3)


def absences_before(marks, index, span):
    """Absences on the `span` instructional days before day `index`, not counting that day."""
    return sum(marks[max(0, index - span):index])


def meets_attendance_rule(marks, index):
    """Whether the attendance rule is met on the window ending with day `index`."""
    return (index + 1 >= ATTENDANCE_RULE_DAYS
            and sum(marks[index + 1 - ATTENDANCE_RULE_DAYS:index + 1]) >= ATTENDANCE_RULE_ABSENCES)


def attendance_outcome_note(marks, index):
    """What the teacher records at the follow-up, read only from the register."""
    before = absences_before(marks, index, FOLLOW_UP_DAYS)
    after = sum(marks[index + 1:index + 1 + FOLLOW_UP_DAYS])
    return 'Fewer absences since the action' if after < before else 'Absences continue; consider next step'


def work_outcome_note(work, index):
    """What the teacher records at a missing-work follow-up.

    `work` is the learner's (due day, missing) pairs in that class, in due order.
    """
    following = [missing for due, missing in work if index < due <= index + FOLLOW_UP_DAYS]
    if not following:
        return 'No work due before the follow-up'
    return 'Next piece of work also missing' if following[0] else 'Next piece of work handed in'


def attendance_patterns(absences):
    """District counts of learners by year-long attendance pattern, read from the register.

    `absences` maps a learner to their 0/1 absence marks in instructional-day order.
    """
    chronic = flagged = rising = falling = 0
    for marks in absences.values():
        days = len(marks)
        half = days // 2
        chronic += sum(marks) / days >= CHRONIC_ABSENCE_RATE
        flagged += any(meets_attendance_rule(marks, index) for index in range(days))
        change = sum(marks[half:]) / (days - half) - sum(marks[:half]) / half
        rising += change >= 0.05
        falling += change <= -0.05
    return dict(chronically_absent_learners=chronic, learners_meeting_attendance_rule=flagged,
                learners_absence_rising_5pp=rising, learners_absence_falling_5pp=falling)


def action_follow_up(absences, actions):
    """Absences in equal windows before and after each learner's first attendance action.

    `actions` holds (learner, day index, log type). This is an observed before/after
    comparison, not evidence that an action caused a change.
    """
    first = {}
    for learner, index, kind in actions:
        if kind in ATTENDANCE_ACTIONS and index < first.get(learner, index + 1):
            first[learner] = index
    compared = fewer = before_total = after_total = 0
    for learner, index in sorted(first.items()):
        marks = absences[learner]
        if index < FOLLOW_UP_DAYS or index + FOLLOW_UP_DAYS >= len(marks):
            continue
        before = absences_before(marks, index, FOLLOW_UP_DAYS)
        after = sum(marks[index + 1:index + 1 + FOLLOW_UP_DAYS])
        compared += 1
        fewer += after < before
        before_total += before
        after_total += after
    return dict(learners_with_attendance_action=len(first), learners_compared=compared,
                fewer_absences_after=fewer, same_or_more_absences_after=compared - fewer,
                absence_rate_before=round(before_total / max(1, compared * FOLLOW_UP_DAYS), 4),
                absence_rate_after=round(after_total / max(1, compared * FOLLOW_UP_DAYS), 4))


def missing_work_by_recent_absence(records):
    """Missing-work rate for work due while the attendance rule was met, against all other work.

    `records` holds (absences in the attendance-rule window before the due date, missing).
    """
    counts = {True: [0, 0], False: [0, 0]}
    for recent, missing in records:
        tally = counts[recent >= ATTENDANCE_RULE_ABSENCES]
        tally[0] += bool(missing)
        tally[1] += 1
    return dict(after_attendance_rule_met=round(counts[True][0] / max(1, counts[True][1]), 4),
                otherwise=round(counts[False][0] / max(1, counts[False][1]), 4),
                pieces_after_attendance_rule_met=counts[True][1])


def work_window(work, index):
    """Missing flags of the pieces of work in one class due before and after day `index`.

    `work` is (due day, missing) in due order. The day of the action is in neither window,
    as for attendance, and each side holds at most FOLLOW_UP_WORK_PIECES pieces.
    """
    before = [missing for due, missing in work if due < index][-FOLLOW_UP_WORK_PIECES:]
    after = [missing for due, missing in work if due > index][:FOLLOW_UP_WORK_PIECES]
    return before, after


def coursework_follow_up(work_by_class, actions):
    """Missing work in equal windows of pieces before and after each learner's first follow-up.

    `actions` holds (learner, class, day index, log type). Observed after, not caused by.
    """
    first = {}
    for learner, section, index, kind in actions:
        if kind == MISSING_WORK_ACTION and (learner not in first or index < first[learner][1]):
            first[learner] = (section, index)
    compared = fewer = before_missing = after_missing = 0
    for learner, (section, index) in first.items():
        before, after = work_window(work_by_class[learner, section], index)
        if len(before) < FOLLOW_UP_WORK_PIECES or len(after) < FOLLOW_UP_WORK_PIECES:
            continue
        compared += 1
        fewer += sum(after) < sum(before)
        before_missing += sum(before)
        after_missing += sum(after)
    pieces = max(1, compared * FOLLOW_UP_WORK_PIECES)
    return dict(learners_with_coursework_follow_up=len(first), learners_compared=compared,
                fewer_missing_after=fewer, same_or_more_missing_after=compared - fewer,
                missing_rate_before=round(before_missing / pieces, 4),
                missing_rate_after=round(after_missing / pieces, 4))


def enrollment_changes(prior, current):
    """How membership moved between two school years.

    `prior` and `current` map a learner to (school, grade). A learner in the highest grade
    their school taught last year who is not enrolled this year completed that school.
    """
    final_grade = {}
    for school, grade in prior.values():
        final_grade[school] = max(final_grade.get(school, grade), grade)
    entry, leaving = Counter(), Counter()
    for learner, (school, _) in current.items():
        if learner not in prior:
            entry['New'] += 1
        else:
            entry['Continuing' if prior[learner][0] == school else 'Transferred in'] += 1
    for learner, (school, grade) in prior.items():
        if learner in current:
            leaving['Continuing' if current[learner][0] == school else 'Transferred out'] += 1
        else:
            leaving['Completed final grade' if grade == final_grade[school] else 'Left'] += 1
    return dict(entry=dict(sorted(entry.items())), exit=dict(sorted(leaving.items())))


def varied_school_sizes(school_count, average_students):
    spread = min(max(1, round(average_students * 0.1)), max(0, average_students - 25))
    midpoint = (school_count - 1) / 2
    sizes = [average_students + round((index - midpoint) * spread) for index in range(school_count)]
    sizes[-1] += school_count * average_students - sum(sizes)
    assert min(sizes) >= 25
    return sizes


def class_label(grade, ordinal, subject):
    return f'{COURSE_TITLES[subject]} {grade} - Group {ordinal + 1:02d}'


def class_code(school, grade, ordinal, subject):
    return f'S{school:02d}-{COURSE_CODES[subject]}{grade}-{ordinal + 1:02d}'


def weighted_choice(weights, draw):
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if draw < cumulative:
            return index
    return len(weights) - 1


SECTION_PLANS = {}

# Which subject each teaching section belongs to, filled in as the sections are formed.
# The section number used to encode it, but sections are now numbered school by school and
# subject by subject in whatever quantity each subject needs, so the subject has to be
# recorded rather than recovered by arithmetic.
SECTION_SUBJECT = {}


def section_plan(section, instructional_days):
    """What one class sets over the year: unit, format, mark scheme and due day per task.

    Every class used to set exactly thirty tasks, each marked out of one hundred, each due
    on one of the same thirty dates, with the six formats cycling so every class set exactly
    five of each. Four separate properties were therefore a single grid, and anything
    counting work by class, by format or by week could only read that grid back: no class
    was busier than another, no task was worth more than another, and no week was heavier
    than another. Each property now varies on its own seed, so the four are independent.

    How many tasks a class sets starts from its subject rather than from one shared range.
    A mathematics class sets frequent short practice and a physical education class records
    little written work, so the two are not drawn from the same distribution: doing that
    left six departments publishing within a few tasks of each other. The realized range is
    recorded in the manifest rather than asserted as a constant, because a calendar too
    short to hold that many distinct due dates caps the count at the dates available.
    """
    cached = SECTION_PLANS.get((section, instructional_days))
    if cached is not None:
        return cached
    subject = SECTION_SUBJECT[section]
    units = len(TASK_TOPICS[0])
    first = 3 + int(stable_unit('due-start-v1', section) * 7)
    last = instructional_days - 1 - int(stable_unit('due-end-v1', section) * 6)
    # One due date per task, so a class cannot set more tasks than it has days to set them on.
    count = min(18 + SUBJECT_TASK_LOAD[subject] + int(stable_unit('task-count-v2', section) * 12),
                last - first + 1)
    assert count >= 6, (section, count)
    plan = []
    occurrences = Counter()
    previous = first - 1
    for task in range(1, count + 1):
        activity = weighted_choice(FORMAT_FREQUENCY, stable_unit('format-v1', section, task))
        unit = min(units - 1, (task - 1) * units // count)
        maxima = FORMAT_MAX_SCORES[activity]
        max_score = maxima[min(len(maxima) - 1, int(stable_unit('max-score-v1', section, task) * len(maxima)))]
        target = first + round((last - first) * (task - 1) / max(1, count - 1))
        drift = round((stable_unit('due-drift-v1', section, task) - 0.5) * 5)
        # Reserve a day for each task still to come, so the dates stay strictly increasing
        # and distinct however far the drift pushes one of them.
        due = min(last - (count - task), max(previous + 1, target + drift))
        previous = due
        occurrences[unit, activity] += 1
        plan.append((unit, activity, occurrences[unit, activity], max_score, due))
    SECTION_PLANS[section, instructional_days] = plan
    return plan


def assignment_label(section, task, instructional_days):
    subject = SECTION_SUBJECT[section]
    unit, activity, occurrence, _, _ = section_plan(section, instructional_days)[task - 1]
    # A class can revisit one format within a unit, so repeats are numbered rather than
    # sharing a name with the task before them.
    suffix = f' {occurrence}' if occurrence > 1 else ''
    return f'Unit {unit + 1}: {TASK_TOPICS[subject][unit]} - {TASK_FORMATS[activity]}{suffix}'


def task_format_of(label):
    """Read the task format back out of a published assignment name."""
    trailing = label.rsplit(' - ', 1)[-1]
    head, _, tail = trailing.rpartition(' ')
    return head if tail.isdigit() and head else trailing


def utc(day):
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def generate(school_count, average_students_per_school, instructional_days):
    assert school_count > 0 and average_students_per_school >= 25 and instructional_days >= 30
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (EVIDENCE / 'lms-field-evidence.csv').open(encoding='utf-8-sig', newline='') as stream:
        lms = list(csv.DictReader(stream))
    with (EVIDENCE / 'nwea-export-fields.csv').open(encoding='utf-8-sig', newline='') as stream:
        nwea = list(csv.DictReader(stream))
    days = []
    current = date(2025, 9, 1)
    while len(days) < instructional_days:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    school_sizes = varied_school_sizes(school_count, average_students_per_school)
    school_boundaries = []
    for size in school_sizes:
        school_boundaries.append((school_boundaries[-1] if school_boundaries else 0) + size)
    students = range(1, sum(school_sizes) + 1)
    schools = range(1, school_count + 1)
    subjects = ('Mathematics', 'Reading', 'Science', 'History', 'Arts', 'Physical Education')
    source_for = lambda school: 'Moodle' if school % 3 == 1 else 'Canvas'
    school_for = lambda student: bisect_left(school_boundaries, student) + 1
    school_start = lambda school: 0 if school == 1 else school_boundaries[school - 2]
    group_for = lambda student: (student - school_start(school_for(student)) - 1) // 25
    grade_for = lambda student: 6 + group_for(student) % 3
    student_key = lambda student: f'SYN-D1-STU-{student:06d}'

    # Teaching groups are formed inside a school and year group, one set per subject, at the
    # size that subject is taught in. Every subject used to reuse the homeroom grid, so a
    # year group that fills nine mathematics classes also appeared to fill nine physical
    # education classes and all six subjects reported an identical class count. Forming them
    # per subject means a larger class size yields fewer classes, which is what a timetable
    # actually produces.
    year_rosters = defaultdict(list)
    for student in students:
        year_rosters[school_for(student), grade_for(student)].append(student)
    section_of = {}
    section_grade = {}
    section_teacher = {}
    teacher_school = {}
    teacher_subject = {}
    sections = []
    next_section = 1
    next_teacher = 1
    teacher_blocks = {}
    for school in schools:
        for subject in range(6):
            size = SUBJECT_CLASS_SIZES[subject]
            ordinal = 0
            for grade in (6, 7, 8):
                roster = year_rosters[school, grade]
                for start in range(0, len(roster), size):
                    section = next_section
                    next_section += 1
                    sections.append((school, ordinal, subject, section))
                    section_grade[section] = grade
                    SECTION_SUBJECT[section] = subject
                    for member in roster[start:start + size]:
                        section_of[member, subject] = section
                    # One teacher carries up to four classes of their own subject.
                    block = school, subject, ordinal // 4
                    teacher = teacher_blocks.get(block)
                    if teacher is None:
                        teacher = next_teacher
                        next_teacher += 1
                        teacher_blocks[block] = teacher
                        teacher_school[teacher] = school
                        teacher_subject[teacher] = subject
                    section_teacher[section] = teacher
                    ordinal += 1
    teacher_count = len(teacher_school)
    teacher_user = lambda teacher: len(students) + teacher

    # The prior school year. Learners now in grades 7 and 8 were one year group lower then,
    # unless they joined the district this year, and a few were at another of its schools.
    # This year's grade 6 arrived from elementary school. Learners who are no longer here are
    # added as former learners: last year's final grade, which moved on, and a few from the
    # younger year groups who left the district.
    prior_days = instructional_days_from(PRIOR_SCHOOL_YEAR_START, instructional_days)
    prior_year, current_year = school_year_label(prior_days[0]), school_year_label(days[0])
    prior_membership = {}
    for student in students:
        grade = grade_for(student)
        if grade == 6 or stable_unit('joined-v1', student) < NEW_TO_DISTRICT_SHARE:
            continue
        school = school_for(student)
        if school_count > 1 and stable_unit('transfer-v1', student) < TRANSFER_SHARE:
            school = school % school_count + 1
        prior_membership[student] = (school, grade - 1)
    former_learners = []
    next_former = len(students) + 1
    for school in schools:
        current_counts = Counter(grade_for(student) for student in students if school_for(student) == school)
        for grade, count in ((FINAL_GRADE, current_counts[FINAL_GRADE]),
                             (6, round(LEFT_DISTRICT_SHARE * current_counts[7])),
                             (7, round(LEFT_DISTRICT_SHARE * current_counts[8]))):
            for _ in range(count):
                prior_membership[next_former] = (school, grade)
                former_learners.append(next_former)
                next_former += 1
    current_membership = {student: (school_for(student), grade_for(student)) for student in students}
    manifest = dict(synthetic=True, generator='generate_district.py', profile='middle-school-district',
                    presentation_version=6,
                    assumptions=dict(districts=1, schools=school_count,
                                     average_students_per_school=average_students_per_school,
                                     school_student_counts=school_sizes,
                                     instructional_days=instructional_days,
                                     class_sizes_by_subject=dict(zip(COURSE_TITLES, SUBJECT_CLASS_SIZES)),
                                     homeroom_size=25,
                                     subjects_per_student=6,
                                     classes_per_subject='Varies by subject and year group; see expected_results.classes_by_subject',
                                     assignments_per_section='Varies by class; see expected_results.assignments',
                                     assessment_windows=3, assessment_subjects=2,
                                     calendar='Synthetic weekdays only; no real holidays or district calendar',
                                     lms_assignment='The first school in each three-school group uses Moodle; others use Canvas',
                                     analysis_limits='LMS assignment is not randomized; do not infer an LMS effect from school comparisons',
                                     grade_bands='Grades 6-8 assigned by homeroom; stable within a school year',
                                     names='Deterministic fictional names; student and staff given-name and surname pools are disjoint',
                                     geography='Fictional institutions at real Snohomish County, Washington localities: real city, state and postal code with synthetic street numbers, so an address geocodes to the locality without identifying a building',
                                     attendance='Seeded student/day variation with school-specific baseline rates and a year-long pattern per learner',
                                     attendance_trajectories={name: share for name, share in ATTENDANCE_TRAJECTORIES},
                                     early_warning_rules=dict(attendance=ATTENDANCE_REASON, missing_work=MISSING_WORK_REASON,
                                                              chronic_absence_rate=CHRONIC_ABSENCE_RATE),
                                     teacher_actions=('Proposed PowerSchool-style log entries. A rule met is logged in '
                                                      f'{ACTION_LOGGED_SHARE:.0%} of cases; {ACTION_RESPONSE_SHARE:.0%} of actions are '
                                                      'followed by fewer absences or less missing work. These shares are constructed '
                                                      'to give the log both outcomes; they are not evidence that an action works'),
                                     coursework_and_absence=(f'Work due after absence in the {COURSEWORK_ABSENCE_DAYS} instructional days '
                                                             'before it is more often missing or late and is marked lower'),
                                     assessment_growth='RIT growth between sittings shrinks with the share of days missed in between',
                                     school_years=('Two synthetic school years. The prior year carries SIS membership (reenrollments), '
                                                   'attendance and assessment history only; class rosters, LMS coursework and the action log '
                                                   'start in the current year'),
                                     enrollment_change=(f'Learners now in grades 7-8 were one grade lower last year, except about '
                                                        f'{NEW_TO_DISTRICT_SHARE:.0%} who joined this year; about {TRANSFER_SHARE:.0%} were at '
                                                        f'another district school. Last year\'s grade {FINAL_GRADE} moved on and about '
                                                        f'{LEFT_DISTRICT_SHARE:.0%} of grades 6-7 left the district'),
                                     prior_year_attendance='Same learner risk, a separately drawn year-long pattern and a prior baseline per school',
                                     contact_domains='Reserved .example domains; no deliverable real addresses',
                                     assessment_labels='Illustrative test labels, not official NWEA test catalog names'),
                    evidence_hashes={name: digest(EVIDENCE / name) for name in
                                     ('lms-field-evidence.csv', 'nwea-export-fields.csv')}, tables=[])

    def write(source, entity, rows, fields, interface, grain):
        if source in {'Canvas', 'Moodle'}:
            allowed = {row['field'] for row in lms if row['source'] == source
                       and row['entity'] == entity and row['interface'] == interface}
            assert set(fields) <= allowed, (entity, set(fields) - allowed)
        elif source == 'NWEA':
            allowed = {row['field'] for row in nwea if row['file'] == entity and row['group'] == 'literal_field'}
            assert set(fields) <= allowed, (entity, set(fields) - allowed)
        filename = entity.split('::')[0]
        if not filename.endswith('.csv'):
            filename += '.csv'
        path = OUTPUT / source / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n')
            writer.writerow(fields)
            for row in rows:
                assert len(row) == len(fields), entity
                writer.writerow([NULL if value is None else json.dumps(value) if isinstance(value, (bool, list))
                                 else value for value in row])
                count += 1
        manifest['tables'].append(dict(source=source, entity=entity, interface=interface, grain=grain,
                                       path=path.relative_to(OUTPUT).as_posix(), columns=fields,
                                       rows=count, sha256=digest(path)))

    proposed = 'proposed synthetic extract; not vendor verified'
    write('PowerSchool', 'districts', [(1, DISTRICT_NAME)], ['district_id', 'district_name'], proposed, 'district')
    write('PowerSchool', 'schools', ((school, 1, school_name(school), f'CV-{school:03d}', 'Middle School',
                              *school_address(school), 'en', f'https://school{school}.cedarvalley.example') for school in schools),
            ['source_school_id', 'district_id', 'school_name', 'school_code', 'school_type',
             'street_address', 'city', 'state', 'postal_code', 'county', 'language', 'website'], proposed, 'school')
    write('PowerSchool', 'students', chain(((student_key(student), school_for(student), grade_for(student),
                                            *person_name(student), contact_email(student), 'Active',
                                            f'{grade_for(student)}-{group_for(student) + 1:02d}')
                                           for student in students),
                                          ((student_key(student), *prior_membership[student], *person_name(student),
                                            contact_email(student), 'Inactive', None) for student in former_learners)),
            ['student_number', 'source_school_id', 'grade_level', 'first_name', 'last_name', 'email', 'enrollment_status', 'homeroom'],
          proposed, 'student; a former learner keeps the school and grade they were last enrolled in')
    write('PowerSchool', 'teachers', ((teacher, teacher_school[teacher],
                               full_name(teacher, True), *person_name(teacher, True), contact_email(teacher, True),
                               COURSE_TITLES[teacher_subject[teacher]], 'Classroom Teacher') for teacher in range(1, teacher_count + 1)),
            ['source_teacher_id', 'source_school_id', 'name', 'first_name', 'last_name', 'email', 'department', 'role_title'], proposed, 'teacher')
    write('PowerSchool', 'courses', ((subject + 1, title, COURSE_CODES[subject],
                             f'Middle-school {title.lower()} curriculum for grades 6-8.')
                            for subject, title in enumerate(COURSE_TITLES)),
            ['source_course_id', 'course_name', 'course_code', 'description'], proposed, 'district catalog course')
    write('PowerSchool', 'sections', ((section, school, subject + 1, section_teacher[section],
                                       section_grade[section], class_label(section_grade[section], group, subject),
                                       class_code(school, section_grade[section], group, subject))
                                      for school, group, subject, section in sections),
          ['source_section_id', 'source_school_id', 'source_course_id', 'source_teacher_id', 'grade_level', 'section_name', 'section_code'],
          proposed, 'school teaching section; one teacher for fixture year')
    write('PowerSchool', 'enrollments', ((student_key(student), school_for(student), days[0].isoformat(),
                                          (days[-1] + timedelta(days=1)).isoformat()) for student in students),
          ['student_number', 'source_school_id', 'entry_date', 'exit_date'], proposed,
          'current school-year membership; exit exclusive; year group is the student grade_level')
    write('PowerSchool', 'reenrollments', ((student_key(student), school, grade, prior_days[0].isoformat(),
                                            (prior_days[-1] + timedelta(days=1)).isoformat())
                                           for student, (school, grade) in sorted(prior_membership.items())),
          ['student_number', 'source_school_id', 'grade_level', 'entry_date', 'exit_date'], proposed,
          'earlier school-year membership with the year group then; exit exclusive')
    write('PowerSchool', 'terms', [(2400, prior_year, prior_days[0].isoformat(), prior_days[-1].isoformat()),
                                   (2500, current_year, days[0].isoformat(), days[-1].isoformat())],
          ['source_term_id', 'school_year', 'first_day', 'last_day'], proposed, 'district school year; last_day inclusive')
    write('PowerSchool', 'section_enrollments', ((student_key(student), section_of[student, subject])
                                               for student in students for subject in range(6)),
          ['student_number', 'source_section_id'], proposed, 'student section membership for full fixture year')
    write('PowerSchool', 'calendar', ((school, day.isoformat(), 360) for school in schools for day in prior_days + days),
          ['source_school_id', 'instructional_date', 'expected_minutes'], proposed, 'school instructional day')
    attendance_absences = 0

    def simulate_attendance():
        """Day-by-day absence marks for every learner, and the attendance actions teachers log.

        Simulated a day at a time because the two depend on each other: an action is logged a
        few days after the rule is met, and some learners' absences then ease. Not every
        learner who meets the rule gets an action, and not every action is followed by a
        change, so the log holds both outcomes.
        """
        absences = {}
        actions = []
        for student in students:
            school = school_for(student)
            grade = grade_for(student)
            individual_risk = attendance_risk(student)
            school_baseline = CURRENT_SCHOOL_BASELINE[(school - 1) % 3]
            grade_effect = 1 + (grade - 7) * 0.04
            owner_section = section_of[student, case_owner_subject(student)]
            marks = bytearray(instructional_days)
            residual, response_from, response_start = 1.0, 1.0, None
            logged, quiet_until, pending = 0, -1, None
            for index, day in enumerate(days):
                if index == pending:
                    pending = None
                    actions.append((index, student, owner_section, ATTENDANCE_ACTIONS[logged], ATTENDANCE_REASON))
                    if stable_unit('attendance-response-v1', student, logged) < ACTION_RESPONSE_SHARE:
                        response_from, response_start = residual, index
                    logged += 1
                    quiet_until = index + ACTION_COOLDOWN_DAYS
                if response_start is not None:
                    step = min(1.0, (index - response_start) / RESPONSE_RAMP_DAYS)
                    residual = response_from * (1.0 - (1.0 - RESPONSE_RESIDUAL) * step)
                elevation = individual_risk * trajectory_effect(student, index, instructional_days)
                if elevation > 1.0:
                    elevation = 1.0 + (elevation - 1.0) * residual
                weekday_effect = 1.12 if day.weekday() in (0, 4) else 0.94
                seasonal_effect = 1.1 if day.month in (12, 1, 2) else 1.0
                absence_probability = min(0.35, school_baseline * elevation * weekday_effect * seasonal_effect * grade_effect)
                marks[index] = stable_unit('attendance-v3', student, day.isoformat()) < absence_probability
                if (pending is None and index > quiet_until and logged < len(ATTENDANCE_ACTIONS)
                        and meets_attendance_rule(marks, index)):
                    if stable_unit('attendance-action-logged-v1', student, index) < ACTION_LOGGED_SHARE:
                        pending = index + 1 + int(stable_unit('attendance-action-lag-v1', student, index) * 4)
                    else:
                        quiet_until = index + ACTION_COOLDOWN_DAYS
            absences[student] = marks
        return absences, actions

    def simulate_coursework(absences):
        """Every learner's outcome on every task, and the missing-work follow-ups logged.

        Tasks are walked in due order for each class, so a follow-up is logged only after
        the rule is met on work already due, and some learners then miss less work in that
        class.
        """
        outcomes = {}
        actions = []
        for student in students:
            marks = absences[student]
            # One follow-up per learner per day, so "the learner's first follow-up" is never a tie.
            follow_up_days = set()
            for subject in range(6):
                section = section_of[student, subject]
                history = []
                responses = []
                followed, quiet_until = 0, -1
                struggling, clear_from = False, None
                for task, (unit, activity, _, max_score, due) in enumerate(
                        section_plan(section, instructional_days), start=1):
                    recent = (absences_before(marks, due, COURSEWORK_ABSENCE_DAYS)
                              / max(1, min(due, COURSEWORK_ABSENCE_DAYS)))
                    support = 0.5 ** sum(day <= due for day in responses)
                    if struggling and clear_from is not None and due >= clear_from:
                        struggling, clear_from = False, None
                    probability = missing_probability(student, subject, recent) * support
                    if struggling:
                        probability = min(0.6, probability * WORK_SLUMP_FACTOR)
                    missing = stable_unit('missing-v1', student, subject, task) < probability
                    late = not missing and stable_unit('late-v1', student, subject, task) < late_probability(student, subject, recent)
                    score = None if missing else coursework_score(student, subject, task, unit, activity, max_score, recent)
                    outcomes[student, subject, task] = missing, late, score
                    history.append(missing)
                    rule_met = sum(history[-MISSING_WORK_RULE_TASKS:]) >= MISSING_WORK_RULE_MISSING
                    if rule_met and clear_from is None:
                        struggling = True
                    if followed < MAX_WORK_FOLLOW_UPS and due > quiet_until and rule_met:
                        if stable_unit('work-action-logged-v1', student, subject, task) < ACTION_LOGGED_SHARE:
                            day = due + 1 + int(stable_unit('work-action-lag-v1', student, subject, task) * 3)
                            while day in follow_up_days:
                                day += 1
                            if day < instructional_days:
                                follow_up_days.add(day)
                                actions.append((day, student, section, MISSING_WORK_ACTION, MISSING_WORK_REASON))
                                if stable_unit('work-response-v1', student, subject, followed) < ACTION_RESPONSE_SHARE:
                                    responses.append(day)
                                    clear_from = day
                                followed += 1
                                quiet_until = day + ACTION_COOLDOWN_DAYS
                        else:
                            quiet_until = due + ACTION_COOLDOWN_DAYS
        return outcomes, actions

    absences, attendance_actions = simulate_attendance()
    outcomes, work_actions = simulate_coursework(absences)

    def simulate_prior_attendance():
        """The prior year's register: the same learner risk, the school's prior baseline and a
        separately drawn year-long pattern. The action log starts this year, so no follow-up."""
        marks_by_learner = {}
        for student, (school, grade) in sorted(prior_membership.items()):
            individual_risk = attendance_risk(student)
            school_baseline = PRIOR_SCHOOL_BASELINE[(school - 1) % 3]
            grade_effect = 1 + (grade - 7) * 0.04
            marks = bytearray(len(prior_days))
            for index, day in enumerate(prior_days):
                elevation = individual_risk * trajectory_effect(student, index, len(prior_days), prior_year)
                weekday_effect = 1.12 if day.weekday() in (0, 4) else 0.94
                seasonal_effect = 1.1 if day.month in (12, 1, 2) else 1.0
                absence_probability = min(0.35, school_baseline * elevation * weekday_effect * seasonal_effect * grade_effect)
                marks[index] = stable_unit('attendance-v3', student, day.isoformat()) < absence_probability
            marks_by_learner[student] = marks
        return marks_by_learner

    prior_absences = simulate_prior_attendance()

    def attendance():
        nonlocal attendance_absences
        for student, (school, _) in sorted(prior_membership.items()):
            marks = prior_absences[student]
            for index, day in enumerate(prior_days):
                absent = bool(marks[index])
                yield student_key(student), school, day.isoformat(), 'A' if absent else 'P', 360 if absent else 0
        for student in students:
            school = school_for(student)
            marks = absences[student]
            for index, day in enumerate(days):
                absent = bool(marks[index])
                attendance_absences += int(absent)
                yield student_key(student), school, day.isoformat(), 'A' if absent else 'P', 360 if absent else 0

    write('PowerSchool', 'attendance', attendance(),
          ['student_number', 'source_school_id', 'attendance_date', 'attendance_code', 'minutes_absent'],
          proposed, 'student instructional day; absence policy is synthetic')

    work_by_class = defaultdict(list)
    for (student, subject, task), (missing, _, _) in outcomes.items():
        section = section_of[student, subject]
        work_by_class[student, section].append((section_plan(section, instructional_days)[task - 1][4], missing))
    for work in work_by_class.values():
        work.sort()
    logged_actions = sorted(attendance_actions + work_actions, key=lambda action: (action[0], action[1], action[3]))

    def log_entries():
        for log_id, (index, student, section, kind, reason) in enumerate(logged_actions, start=1):
            follow_up = index + FOLLOW_UP_DAYS
            completed = follow_up < instructional_days
            if not completed:
                note = None
            elif kind in ATTENDANCE_ACTIONS:
                note = attendance_outcome_note(absences[student], index)
            else:
                note = work_outcome_note(work_by_class[student, section], index)
            # A follow-up that falls after the last instructional day stays open, dated two
            # calendar weeks on rather than on a school day the calendar does not hold.
            follow_up_date = days[follow_up] if completed else days[index] + timedelta(days=14)
            yield (log_id, student_key(student), school_for(student), section, section_teacher[section],
                   days[index].isoformat(), kind, reason, 'Completed' if completed else 'Open',
                   follow_up_date.isoformat(), days[follow_up].isoformat() if completed else None, note)

    write('PowerSchool', 'log_entries', log_entries(),
          ['log_id', 'student_number', 'source_school_id', 'source_section_id', 'source_teacher_id',
           'entry_date', 'log_type', 'reason', 'status', 'follow_up_date', 'completed_date', 'outcome_note'],
          proposed, 'teacher-logged student action; follow-up observations are descriptive, not causal')
    expected = dict(students=len(students), schools=school_count, teachers=teacher_count,
                    sections=len(sections), section_enrollments=len(students) * 6,
                    attendance_records=len(students) * instructional_days, absent_days=attendance_absences)
    expected['attendance_rate'] = 1 - attendance_absences / expected['attendance_records']
    # Read back from the same structures the CSVs were written from, through the helpers the
    # validator uses on the published files, so the two sides cannot define a figure apart.
    keyed_absences = {student_key(student): absences[student] for student in students}
    expected['attendance_patterns'] = attendance_patterns(keyed_absences)
    expected['log_entries'] = dict(
        total=len(logged_actions),
        by_type={kind: sum(action[3] == kind for action in logged_actions)
                 for kind in (*ATTENDANCE_ACTIONS, MISSING_WORK_ACTION)},
        learners=len({action[1] for action in logged_actions}),
        open=sum(action[0] + FOLLOW_UP_DAYS >= instructional_days for action in logged_actions))
    expected['attendance_action_follow_up'] = action_follow_up(
        keyed_absences, ((student_key(action[1]), action[0], action[3]) for action in logged_actions))
    expected['missing_work_by_recent_absence'] = missing_work_by_recent_absence(
        (absences_before(absences[student], section_plan(section_of[student, subject], instructional_days)[task - 1][4],
                         ATTENDANCE_RULE_DAYS),
         missing)
        for (student, subject, task), (missing, _, _) in outcomes.items())
    expected['coursework_follow_up'] = coursework_follow_up(
        work_by_class, ((action[1], action[2], action[0], action[3]) for action in logged_actions))

    # The prior school year, for year-on-year comparison. Rates are ratios of the published
    # rows; chronic absence uses the same threshold as the current year.
    def by_school(membership, marks_by_learner, length):
        totals = defaultdict(lambda: [0, 0])
        for learner, (school, _) in membership.items():
            totals[school][0] += sum(marks_by_learner[learner])
            totals[school][1] += length
        return {school_name(school): round(1 - absent / records, 4) for school, (absent, records) in sorted(totals.items())}

    prior_absent = sum(sum(marks) for marks in prior_absences.values())
    expected['school_years'] = [prior_year, current_year]
    expected['attendance_rate_by_school'] = by_school(current_membership, absences, instructional_days)
    expected['prior_year'] = dict(
        school_year=prior_year, learners=len(prior_membership), former_learners=len(former_learners),
        attendance_records=len(prior_membership) * len(prior_days), absent_days=prior_absent,
        attendance_rate=1 - prior_absent / (len(prior_membership) * len(prior_days)),
        attendance_rate_by_school=by_school(prior_membership, prior_absences, len(prior_days)),
        chronically_absent_learners=sum(sum(marks) / len(prior_days) >= CHRONIC_ABSENCE_RATE
                                        for marks in prior_absences.values()),
        assessment_results=len(prior_membership) * 6)
    expected['enrollment_changes'] = enrollment_changes(
        {student_key(learner): value for learner, value in prior_membership.items()},
        {student_key(learner): value for learner, value in current_membership.items()})

    for source in ('Canvas', 'Moodle'):
        selected = [section for section in sections if source_for(section[0]) == source]
        population = [student for student in students if source_for(school_for(student)) == source]
        teachers = sorted({section_teacher[section] for school, group, subject, section in selected})
        assignments = [(section * 100 + task, section, task, entry)
                       for school, group, subject, section in selected
                       for task, entry in enumerate(section_plan(section, instructional_days), start=1)]
        missing_count = 0
        late_count = 0

        def submissions():
            nonlocal missing_count, late_count
            for student in population:
                for subject in range(6):
                    section = section_of[student, subject]
                    for task, (unit, activity, _, max_score, due_index) in enumerate(
                            section_plan(section, instructional_days), start=1):
                        missing, late, score = outcomes[student, subject, task]
                        missing_count += int(missing)
                        late_count += int(late)
                        due = days[due_index]
                        submitted = utc(due + timedelta(days=1 if late else -1))
                        if source == 'Canvas':
                            yield section * 100 + task, student, None if missing else 1, None if missing else submitted.isoformat(), score, 'unsubmitted' if missing else 'graded', late, missing
                        else:
                            yield student * 1000 + subject * 100 + task, section * 100 + task, student, 0, 'new' if missing else 'submitted', int(utc(days[0]).timestamp()) if missing else int(submitted.timestamp()), 1

        if source == 'Canvas':
            interface = 'REST response model (Swagger)'
            users = [(student, full_name(student), student_key(student), *person_name(student), contact_email(student)) for student in population]
            users += [(teacher_user(teacher), full_name(teacher, True), f'SYN-TEACHER-{teacher}',
                     *person_name(teacher, True), contact_email(teacher, True)) for teacher in teachers]
            write(source, 'users::User', users, ['id', 'name', 'sis_user_id', 'first_name', 'last_name', 'email'], interface, 'user including teachers')
            write(source, 'courses::Course', ((section, class_label(section_grade[section], group, subject), f'SYN-SECTION-{section}', 'available',
                                     class_code(school, section_grade[section], group, subject), 'en', utc(days[0]).isoformat(),
                                     utc(days[-1] + timedelta(days=1)).isoformat())
                                             for school, group, subject, section in selected),
                ['id', 'name', 'sis_course_id', 'workflow_state', 'course_code', 'locale', 'start_at', 'end_at'], interface, 'LMS shell per teaching section; not catalog course')
            write(source, 'sections::Section', ((section, section, f'SYN-SECTION-{section}', class_label(section_grade[section], group, subject)) for school, group, subject, section in selected),
                ['id', 'course_id', 'sis_section_id', 'name'], interface, 'class section')
            enrollments = [(student * 10 + subject, student, section_of[student, subject],
                            section_of[student, subject], 'StudentEnrollment', 'active')
                           for student in population for subject in range(6)]
            enrollments += [(len(students) * 10 + section, teacher_user(section_teacher[section]), section, section, 'TeacherEnrollment', 'active')
                            for school, group, subject, section in selected]
            write(source, 'enrollments::Enrollment', enrollments, ['id', 'user_id', 'course_id', 'course_section_id', 'type', 'enrollment_state'], interface, 'user section role')
            write(source, 'assignments::Assignment', ((assignment, section, assignment_label(section, task, instructional_days), float(entry[3]),
                                         utc(days[entry[4]]).isoformat(), True, 'points', ['online_text_entry'],
                                         f'Complete {assignment_label(section, task, instructional_days).lower()} and explain your approach.')
                                                     for assignment, section, task, entry in assignments),
                ['id', 'course_id', 'name', 'points_possible', 'due_at', 'published', 'grading_type', 'submission_types', 'description'], interface, 'assignment')
            write(source, 'submissions::Submission', submissions(), ['assignment_id', 'user_id', 'attempt', 'submitted_at', 'score', 'workflow_state', 'late', 'missing'], interface, 'current student assignment snapshot')
        else:
            interface = 'database XMLDB'
            write(source, 'user', ((student, student_key(student), f'{person_name(student)[0].lower()}.{person_name(student)[1].lower()}.{student}',
                            *person_name(student), contact_email(student), 'en', school_name(school_for(student))) for student in population),
                ['id', 'idnumber', 'username', 'firstname', 'lastname', 'email', 'lang', 'institution'], interface, 'student user subset; staff role data remains in proposed SIS')
            write(source, 'course', ((section, class_label(section_grade[section], group, subject), f'SYN-SECTION-{section}',
                              f'{COURSE_TITLES[subject]} learning activities for grade {section_grade[section]}.',
                              int(utc(days[0]).timestamp()), int(utc(days[-1] + timedelta(days=1)).timestamp()))
                            for school, group, subject, section in selected),
                ['id', 'fullname', 'shortname', 'summary', 'startdate', 'enddate'], interface, 'course shell per teaching section')
            write(source, 'enrol', ((section, section, 'manual') for school, group, subject, section in selected),
                  ['id', 'courseid', 'enrol'], interface, 'enrollment plugin instance')
            write(source, 'user_enrolments', ((student * 10 + subject, student, section_of[student, subject], 0)
                                             for student in population for subject in range(6)),
                  ['id', 'userid', 'enrolid', 'status'], interface, 'user plugin enrollment')
            assignment_rows = (
                (assignment, section, assignment_label(section, task, instructional_days), entry[3],
                 int(utc(days[entry[4]]).timestamp()),
                 f'Complete {assignment_label(section, task, instructional_days).lower()} and explain your approach.')
                for assignment, section, task, entry in assignments
            )
            write(source, 'assign', assignment_rows,
                  ['id', 'course', 'name', 'grade', 'duedate', 'intro'], interface, 'assignment')
            write(source, 'assign_submission', submissions(), ['id', 'assignment', 'userid', 'attemptnumber', 'status', 'timemodified', 'latest'], interface, 'submission state; new is not an actual submitted attempt')
            write(source, 'assign_grades', ((student * 1000 + subject * 100 + task,
                                            section_of[student, subject] * 100 + task,
                                            student, 0,
                                            outcomes[student, subject, task][2])
                                           for student in population for subject in range(6)
                                           for task, entry in enumerate(
                                               section_plan(section_of[student, subject], instructional_days), start=1)
                                           if not outcomes[student, subject, task][0]),
                  ['id', 'assignment', 'userid', 'attemptnumber', 'grade'], interface, 'graded individual submission attempt')
        snapshots = sum(len(section_plan(section_of[student, subject], instructional_days))
                        for student in population for subject in range(6))
        expected[source] = dict(students=len(population), assignment_snapshots=snapshots,
                                missing=missing_count, late=late_count)

    # Pin the variation this fixture exists to provide. A change that flattened marks back
    # to one number per subject, or the assignments back to one grid, would still produce
    # valid CSVs with correct row counts and matching hashes, so the structural checks
    # above cannot catch it on their own.
    #
    # Every total below is accumulated with fsum, which is exactly rounded and therefore
    # independent of the order the terms arrive in. The generator walks learners in id
    # order while the validator reads one LMS export and then the other, so a plain running
    # sum lets the two sides differ in the last bit and an exact comparison becomes a
    # coin toss near a rounding boundary.
    subject_points = {subject: ([], []) for subject in range(6)}
    within_student_ranges = []
    for student in students:
        subject_means = []
        for subject in range(6):
            section = section_of[student, subject]
            percentages = []
            for task, (unit, activity, _, max_score, _) in enumerate(
                    section_plan(section, instructional_days), start=1):
                missing, _, score = outcomes[student, subject, task]
                if missing:
                    continue
                subject_points[subject][0].append(score)
                subject_points[subject][1].append(max_score)
                # Tasks are marked out of different totals, so a learner's standing in a
                # subject is the mean of what they earned of each scheme, not of raw marks.
                percentages.append(100.0 * score / max_score)
            if percentages:
                subject_means.append(fsum(percentages) / len(percentages))
        if len(subject_means) > 1:
            within_student_ranges.append(max(subject_means) - min(subject_means))
    expected['coursework_score_by_subject'] = {
        COURSE_TITLES[subject]: round(fsum(earned) / fsum(possible), 4)
        for subject, (earned, possible) in sorted(subject_points.items())
    }
    expected['mean_within_student_subject_range'] = round(
        fsum(within_student_ranges) / len(within_student_ranges), 2)

    plans = [section_plan(section, instructional_days) for school, group, subject, section in sections]
    format_counts = Counter(TASK_FORMATS[entry[1]] for plan in plans for entry in plan)
    max_score_counts = Counter(entry[3] for plan in plans for entry in plan)
    classes_by_subject = Counter(subject for school, group, subject, section in sections)
    assignments_by_subject = Counter()
    for school, group, subject, section in sections:
        assignments_by_subject[subject] += len(section_plan(section, instructional_days))
    expected['classes_by_subject'] = {COURSE_TITLES[subject]: classes_by_subject[subject] for subject in range(6)}
    expected['assignments_by_subject'] = {COURSE_TITLES[subject]: assignments_by_subject[subject] for subject in range(6)}
    expected['assignments'] = dict(
        total=sum(len(plan) for plan in plans),
        min_per_section=min(len(plan) for plan in plans),
        max_per_section=max(len(plan) for plan in plans),
        distinct_due_date_calendars=len({tuple(days[entry[4]].isoformat() for entry in plan) for plan in plans}),
        by_format={name: format_counts[name] for name in TASK_FORMATS},
        by_max_score={str(score): count for score, count in sorted(max_score_counts.items())},
    )

    window_indices = [instructional_days // 6, instructional_days // 2, instructional_days - 1]
    window_dates = [days[index] for index in window_indices]

    prior_window_dates = [prior_days[index] for index in window_indices]

    def interval_absence(marks):
        """Share of instructional days missed between consecutive test sittings."""
        return [sum(marks[start:end]) / (end - start) for start, end in zip(window_indices, window_indices[1:])]
    terms = tuple(f'{season} {current_year}' for season in ('Fall', 'Winter', 'Spring'))
    prior_terms = tuple(f'{season} {prior_year}' for season in ('Fall', 'Winter', 'Spring'))
    prior_roster = sorted(prior_membership.items())
    write('NWEA', 'StudentBySchool.csv', chain(
        ((term, student_key(student), f'SYN-SCHOOL-{school}', str(grade), *person_name(student),
          school_name(school), DISTRICT_NAME, 'SYN-DISTRICT-1')
         for term in prior_terms for student, (school, grade) in prior_roster),
        ((term, student_key(student), f'SYN-SCHOOL-{school_for(student)}',
                            str(grade_for(student)), *person_name(student),
                            school_name(school_for(student)), DISTRICT_NAME, 'SYN-DISTRICT-1')
                              for term in terms for student in students)),
           ['TermName', 'StudentID', 'School_StateID', 'Grade', 'StudentFirstName', 'StudentLastName',
            'SchoolName', 'DistrictName', 'District_StateID'], 'selected literal export fields', 'student school term roster')
    # Prior-year sittings use test ids ending 5-7 so they never collide with this year's 0-2.
    write('NWEA', 'AssessmentResults.csv', chain(
        ((student * 100 + subject * 10 + 5 + window, student_key(student), term,
          f'SYN-SCHOOL-{school}', subjects[subject], day.isoformat(),
          assessment_score(student, subject, window, interval_absence(prior_absences[student]), prior_year), 3.0,
          f'{subjects[subject]} Growth Assessment - Grades 6-8', school_name(school), DISTRICT_NAME)
         for student, (school, _) in prior_roster for subject in (0, 1)
         for window, (term, day) in enumerate(zip(prior_terms, prior_window_dates))),
        ((student * 100 + subject * 10 + window, student_key(student), term,
                                             f'SYN-SCHOOL-{school_for(student)}', subjects[subject], day.isoformat(),
                                             assessment_score(student, subject, window, interval_absence(absences[student])), 3.0,
                                             f'{subjects[subject]} Growth Assessment - Grades 6-8',
                                             school_name(school_for(student)), DISTRICT_NAME)
                                            for student in students for subject in (0, 1)
                                            for window, (term, day) in enumerate(zip(terms, window_dates)))),
          ['TestID', 'StudentID', 'TermName', 'School_StateID', 'Subject', 'TestStartDate', 'TestRITScore', 'TestStandardError',
           'TestName', 'SchoolName', 'DistrictName'],
          'selected literal export fields', 'synthetic assessment event; no norms or vendor growth projections')
    expected['assessment_results'] = len(students) * 6
    manifest['expected_results'] = expected
    manifest['csv_encoding'] = dict(encoding='UTF-8', null=NULL, boolean='true/false', arrays='JSON within CSV cell')
    (OUTPUT / 'manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    return manifest


def derive_student_links(roster_rows, source_users, enrolled_users):
    roster = {}
    for row in roster_rows:
        external_id = row['student_number']
        assert external_id and external_id != NULL and external_id not in roster, 'Missing or duplicate SIS identifier.'
        roster[external_id] = row
    links = {}
    for source, identifier_field in (('Canvas', 'sis_user_id'), ('Moodle', 'idnumber')):
        seen_users = set()
        seen_external = set()
        for row in source_users[source]:
            user_id = row['id']
            assert user_id and user_id != NULL and user_id not in seen_users, (source, 'Invalid or duplicate user ID')
            seen_users.add(user_id)
            if user_id not in enrolled_users[source]:
                continue
            external_id = row.get(identifier_field)
            assert external_id in roster, (source, user_id, 'Unresolved SIS identifier')
            assert external_id not in seen_external, (source, external_id, 'Ambiguous student mapping')
            seen_external.add(external_id)
            links[source, user_id] = roster[external_id]
        assert enrolled_users[source] <= seen_users, (source, 'Enrolled user missing from users')
    return links


def check(manifest):
    assert manifest['profile'] == 'middle-school-district'
    assert all(table['source'] in {'PowerSchool', 'Canvas', 'Moodle', 'NWEA'} for table in manifest['tables']), 'Only source datasets belong in the sample manifest.'
    expected_paths = {table['path'] for table in manifest['tables']}
    assert len(expected_paths) == len(manifest['tables']), 'Duplicate table paths in manifest.'
    actual_paths = {path.relative_to(OUTPUT).as_posix()
                    for source in ('PowerSchool', 'Canvas', 'Moodle', 'NWEA', 'Shared')
                    for path in (OUTPUT / source).glob('*.csv')}
    assert actual_paths == expected_paths, ('Missing or stale table files', expected_paths - actual_paths, actual_paths - expected_paths)

    def read(source, filename):
        with (OUTPUT / source / filename).open(encoding='utf-8', newline='') as stream:
            yield from csv.DictReader(stream)

    for table in manifest['tables']:
        path = OUTPUT / table['path']
        assert digest(path) == table['sha256'], path
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == table['columns']
            assert sum(1 for row in reader) == table['rows'], path
    expected = manifest['expected_results']
    assumptions = manifest['assumptions']
    assert expected['students'] == sum(assumptions['school_student_counts'])
    assert expected['attendance_records'] == expected['students'] * assumptions['instructional_days']
    school_rows = list(read('PowerSchool', 'schools.csv'))
    schools = {row['source_school_id'] for row in school_rows}
    roster_rows = list(read('PowerSchool', 'students.csv'))
    roster = {row['student_number']: row for row in roster_rows}
    assert {row['enrollment_status'] for row in roster_rows} <= {'Active', 'Inactive'}
    active = {student: row for student, row in roster.items() if row['enrollment_status'] == 'Active'}
    teachers = {row['source_teacher_id']: row for row in read('PowerSchool', 'teachers.csv')}
    sections = {row['source_section_id']: row for row in read('PowerSchool', 'sections.csv')}
    assert len(active) == expected['students'] and len(schools) == expected['schools']
    assert len(roster) - len(active) == expected['prior_year']['former_learners']
    assert len(teachers) == expected['teachers'] and len(sections) == expected['sections']
    student_names = {(row['first_name'], row['last_name']) for row in roster_rows}
    teacher_names = {(row['first_name'], row['last_name']) for row in teachers.values()}
    student_name_capacity = len(GIVEN_NAMES) * (len(SURNAMES) + len(EXTRA_SURNAMES))
    teacher_name_capacity = len(STAFF_GIVEN_NAMES) * len(STAFF_SURNAMES)
    if len(roster_rows) <= student_name_capacity:
        assert len(student_names) == len(roster_rows), 'Student display names must be unique when the name pool permits it.'
    if len(teachers) <= teacher_name_capacity:
        assert len(teacher_names) == len(teachers), 'Teacher display names must be unique when the name pool permits it.'
    assert student_names.isdisjoint(teacher_names), 'Student and teacher display names must not overlap.'
    # Full names alone are not enough. Sharing a surname pool put a teacher and a learner on
    # screen as the same "Bennett" wherever only part of a name is shown, so both halves of
    # the name have to come from separate pools.
    assert {given for given, _ in student_names}.isdisjoint({given for given, _ in teacher_names}), \
        'Student and teacher given names must not overlap.'
    assert {surname for _, surname in student_names}.isdisjoint({surname for _, surname in teacher_names}), \
        'Student and teacher surnames must not overlap.'
    # A school has to sit somewhere a map can find. Locality, state and postal code are
    # checked against the real Washington places the profile declares, and each school needs
    # its own street line so two campuses do not land on one pin.
    known_places = {(city, state, postal_code) for _, _, city, state, postal_code, _ in SCHOOL_PROFILES}
    addresses = set()
    for row in school_rows:
        place = row['city'], row['state'], row['postal_code']
        assert place in known_places, ('School locality is not one of the declared real places.', place)
        assert row['county'] == 'Snohomish', row['county']
        assert row['street_address'].split(' ', 1)[0].isdigit(), row['street_address']
        address = row['street_address'], *place
        assert address not in addresses, ('Two schools share one address.', address)
        addresses.add(address)
    school_sizes = {school: sum(row['source_school_id'] == school for row in active.values()) for school in schools}
    if len(schools) > 1 and max(assumptions['school_student_counts']) > min(assumptions['school_student_counts']):
        assert len(set(school_sizes.values())) > 1, 'School populations must not all be equal.'
    for section in sections.values():
        assert section['source_school_id'] in schools
        assert teachers[section['source_teacher_id']]['source_school_id'] == section['source_school_id']
    source_users = {'Canvas': list(read('Canvas', 'users.csv')), 'Moodle': list(read('Moodle', 'user.csv'))}
    enrolled_users = {
        'Canvas': {row['user_id'] for row in read('Canvas', 'enrollments.csv') if row['type'] == 'StudentEnrollment'},
        'Moodle': {row['userid'] for row in read('Moodle', 'user_enrolments.csv')},
    }
    crosswalk = derive_student_links(roster_rows, source_users, enrolled_users)
    assert len(crosswalk) == len(active)
    assert {row['student_number'] for row in crosswalk.values()} == set(active)

    # School years. The current year's membership is enrollments.csv with the year group from
    # students.csv; earlier years are reenrollments.csv, which carries its own year group.
    terms = sorted(read('PowerSchool', 'terms.csv'), key=lambda row: row['first_day'])
    assert [row['school_year'] for row in terms] == expected['school_years'], terms
    for earlier, later in zip(terms, terms[1:]):
        assert earlier['last_day'] < later['first_day'], 'School years overlap.'
    prior_term, current_term = terms[-2], terms[-1]
    in_term = lambda term, day: term['first_day'] <= day <= term['last_day']
    stints = defaultdict(list)
    current_membership, prior_membership = {}, {}
    for row in read('PowerSchool', 'enrollments.csv'):
        assert row['student_number'] in active, ('Current enrollment for an inactive learner.', row['student_number'])
        grade = roster[row['student_number']]['grade_level']
        stints[row['student_number']].append((row['source_school_id'], row['entry_date'], row['exit_date']))
        assert in_term(current_term, row['entry_date'])
        current_membership[row['student_number']] = (row['source_school_id'], int(grade))
    for row in read('PowerSchool', 'reenrollments.csv'):
        assert row['student_number'] in roster
        assert row['exit_date'] <= current_term['first_day'], 'A reenrollment overlaps the current year.'
        stints[row['student_number']].append((row['source_school_id'], row['entry_date'], row['exit_date']))
        if in_term(prior_term, row['entry_date']):
            prior_membership[row['student_number']] = (row['source_school_id'], int(row['grade_level']))
    assert set(current_membership) == set(active)
    for student, row in roster.items():
        if student not in active:
            assert student in prior_membership, ('A former learner has no earlier enrollment.', student)
            assert (row['source_school_id'], int(row['grade_level'])) == prior_membership[student], student
    # The schools reported for a former learner, and the prior-year roster, are pinned exactly.
    changes = enrollment_changes(prior_membership, current_membership)
    assert changes == expected['enrollment_changes'], (changes, expected['enrollment_changes'])

    calendar = {(row['source_school_id'], row['instructional_date']) for row in read('PowerSchool', 'calendar.csv')}
    seen = set()
    absent = prior_records = prior_absent = 0
    attendance_by_school = {school: [0, 0] for school in schools}
    prior_by_school = {school: [0, 0] for school in schools}
    prior_absence_days = Counter()
    absence_days_by_student = {student: 0 for student in active}
    absence_dates_by_student = {student: [] for student in active}
    for row in read('PowerSchool', 'attendance.csv'):
        key = row['student_number'], row['attendance_date']
        assert key not in seen
        seen.add(key)
        assert any(school == row['source_school_id'] and entry <= row['attendance_date'] < exit_
                   for school, entry, exit_ in stints[row['student_number']]), ('Attendance outside membership.', key)
        assert (row['source_school_id'], row['attendance_date']) in calendar
        assert row['minutes_absent'] == ('360' if row['attendance_code'] == 'A' else '0')
        is_absent = row['attendance_code'] == 'A'
        if not in_term(current_term, row['attendance_date']):
            assert in_term(prior_term, row['attendance_date'])
            prior_records += 1
            prior_absent += is_absent
            prior_by_school[row['source_school_id']][0] += 1
            prior_by_school[row['source_school_id']][1] += is_absent
            prior_absence_days[row['student_number']] += is_absent
            continue
        absent += is_absent
        attendance_by_school[row['source_school_id']][0] += 1
        if is_absent:
            attendance_by_school[row['source_school_id']][1] += 1
            absence_days_by_student[row['student_number']] += 1
            absence_dates_by_student[row['student_number']].append(row['attendance_date'])
    current_records = len(seen) - prior_records
    assert current_records == expected['attendance_records']
    assert absent == expected['absent_days']
    assert 1 - absent / current_records == expected['attendance_rate']
    prior = expected['prior_year']
    prior_days = sum(1 for school, day in calendar if school == next(iter(schools)) and in_term(prior_term, day))
    assert prior_records == prior['attendance_records'] == len(prior_membership) * prior_days
    assert prior_absent == prior['absent_days'] and 1 - prior_absent / prior_records == prior['attendance_rate']
    assert len(prior_membership) == prior['learners']
    assert sum(prior_absence_days[student] / prior_days >= CHRONIC_ABSENCE_RATE
               for student in prior_membership) == prior['chronically_absent_learners']
    school_label = {row['source_school_id']: row['school_name'] for row in school_rows}
    for label, totals, key in (('current', attendance_by_school, expected['attendance_rate_by_school']),
                               ('prior', prior_by_school, prior['attendance_rate_by_school'])):
        rates = {school_label[school]: round(1 - absences / records, 4)
                 for school, (records, absences) in sorted(totals.items(), key=lambda item: int(item[0]))}
        assert rates == key, (label, rates, key)
    # Year on year has to move: a fixture where every school's rate is the same in both
    # years gives a comparison nothing to show.
    if len(schools) > 1 and assumptions['instructional_days'] >= 90:
        moves = [expected['attendance_rate_by_school'][name] - prior['attendance_rate_by_school'][name]
                 for name in expected['attendance_rate_by_school']]
        assert max(moves) > 0.003 and min(moves) < -0.003, ('Schools must both improve and decline.', moves)
    school_attendance_rates = {
        school: 1 - absences / records for school, (records, absences) in attendance_by_school.items()
    }
    if len(schools) > 1 and assumptions['instructional_days'] >= 90:
        assert len({round(rate, 5) for rate in school_attendance_rates.values()}) > 1, 'School attendance rates must vary.'
    if assumptions['instructional_days'] >= 90 and len(active) >= 100:
        assert len(set(absence_days_by_student.values())) >= 10, 'Student attendance histories are insufficiently varied.'
        distinct_attendance_histories = {tuple(dates) for dates in absence_dates_by_student.values()}
        assert len(distinct_attendance_histories) >= len(active) * 0.95, 'Too many students share an identical attendance history.'
    instructional_dates = sorted({day for _, day in calendar if in_term(current_term, day)})
    day_index = {instructional_date: index for index, instructional_date in enumerate(instructional_dates)}
    absence_marks = {}
    for student_number, dates in absence_dates_by_student.items():
        marks = bytearray(len(instructional_dates))
        for absence_date in dates:
            marks[day_index[absence_date]] = 1
        absence_marks[student_number] = marks
    membership = set()
    for row in read('PowerSchool', 'section_enrollments.csv'):
        key = row['student_number'], row['source_section_id']
        assert key not in membership
        membership.add(key)
        assert roster[key[0]]['source_school_id'] == sections[key[1]]['source_school_id']
    assert len(membership) == expected['section_enrollments']
    # A class belongs to one year group, so everyone in it must be in that year group. The
    # teaching groups are formed per subject now rather than inherited from the homeroom
    # grid, and a grouping that crossed a year boundary would put two year groups in one
    # class while still producing the right number of rows.
    for student_number, section_id in membership:
        assert roster[student_number]['grade_level'] == sections[section_id]['grade_level'], \
            ('A class holds more than one year group.', section_id)
    # Read the class counts back per subject. Every subject used to inherit the homeroom
    # grid and so reported an identical count; a change that restored that would still
    # produce valid files with correct totals, which is why it is asserted from the
    # published rows rather than trusted.
    published_classes = Counter(section['source_course_id'] for section in sections.values())
    assert len(set(published_classes.values())) > 1, \
        ('Every subject has the same number of classes.', dict(published_classes))
    assert max(published_classes.values()) >= min(published_classes.values()) * 1.3, \
        ('Subjects barely differ in how many classes they run.', dict(published_classes))
    class_sizes = Counter(section_id for _, section_id in membership)
    sizes_by_subject = defaultdict(set)
    for section_id, size in class_sizes.items():
        sizes_by_subject[sections[section_id]['source_course_id']].add(size)
    assert len({max(sizes) for sizes in sizes_by_subject.values()}) > 1, \
        'Every subject is taught in the same size of class.'
    # Marks read back from the Canvas CSVs, so the variation is proven from the published
    # files rather than from the generator's own arithmetic.
    marks_by_subject = {subject: ([], []) for subject in range(6)}
    marks_by_student = defaultdict(list)
    tasks_by_section = Counter()
    formats_set = Counter()
    maxima_set = Counter()
    due_dates_by_section = defaultdict(list)
    due_index_of = {}
    work_by_class = defaultdict(list)
    for source in ('Canvas', 'Moodle'):
        canvas = source == 'Canvas'
        assignments = {row['id']: row for row in read(source, 'assignments.csv' if canvas else 'assign.csv')}
        users = {row['id'] for row in read(source, 'users.csv' if canvas else 'user.csv')}
        for row in assignments.values():
            section = row['course_id' if canvas else 'course']
            tasks_by_section[section] += 1
            formats_set[task_format_of(row['name'])] += 1
            maxima_set[float(row['points_possible' if canvas else 'grade'])] += 1
            # Canvas publishes an ISO instant and Moodle an epoch second, so both are read
            # back as the calendar date they mean before the two sources are compared.
            due = (datetime.fromisoformat(row['due_at']) if canvas
                   else datetime.fromtimestamp(int(row['duedate']), timezone.utc))
            due_dates_by_section[section].append(due.date().isoformat())
            due_index_of[row['id']] = day_index[due.date().isoformat()]
        seen = set()
        missing_count = 0
        late_count = 0
        for row in read(source, 'submissions.csv' if canvas else 'assign_submission.csv'):
            user = row['user_id' if canvas else 'userid']
            assignment_id = row['assignment_id' if canvas else 'assignment']
            key = user, assignment_id
            assert key not in seen
            seen.add(key)
            assert user in users and (source, user) in crosswalk
            assignment = assignments[assignment_id]
            assert (crosswalk[source, user]['student_number'], assignment['course_id' if canvas else 'course']) in membership
            if canvas:
                missing = row['missing'] == 'true'
                assert missing == (row['submitted_at'] == NULL) == (row['score'] == NULL)
                late = not missing and datetime.fromisoformat(row['submitted_at']) > datetime.fromisoformat(assignment['due_at'])
                assert late == (row['late'] == 'true')
                if not missing:
                    assert 0 <= float(row['score']) <= float(assignment['points_possible'])
                    subject = int(sections[assignment['course_id']]['source_course_id']) - 1
                    maximum = float(assignment['points_possible'])
                    marks_by_subject[subject][0].append(float(row['score']))
                    marks_by_subject[subject][1].append(maximum)
                    marks_by_student[user, subject].append(100.0 * float(row['score']) / maximum)
            else:
                missing = row['status'] == 'new'
                late = not missing and int(row['timemodified']) > int(assignment['duedate'])
            missing_count += missing
            late_count += late
            work_by_class[crosswalk[source, user]['student_number'], assignment['course_id' if canvas else 'course']].append(
                (due_index_of[assignment_id], missing))
        assert len(seen) == expected[source]['assignment_snapshots']
        assert missing_count == expected[source]['missing'] and late_count == expected[source]['late']
        if not canvas:
            graded = set()
            for row in read(source, 'assign_grades.csv'):
                key = row['userid'], row['assignment']
                assert key in seen and key not in graded
                graded.add(key)
                maximum = float(assignments[row['assignment']]['grade'])
                assert 0 <= float(row['grade']) <= maximum
                subject = int(sections[assignments[row['assignment']]['course']]['source_course_id']) - 1
                marks_by_subject[subject][0].append(float(row['grade']))
                marks_by_subject[subject][1].append(maximum)
                marks_by_student[row['userid'], subject].append(100.0 * float(row['grade']) / maximum)
            assert len(graded) == len(seen) - missing_count

    # Assignments must not arrive as a grid. Counts, mark schemes, formats and due dates are
    # four separate properties, and if any one of them is constant across the district then
    # a report counting work by class, by weighting, by format or by week is reading the
    # generator rather than the fixture.
    published_assignments = dict(
        total=sum(tasks_by_section.values()),
        min_per_section=min(tasks_by_section.values()),
        max_per_section=max(tasks_by_section.values()),
        distinct_due_date_calendars=len({tuple(dates) for dates in due_dates_by_section.values()}),
        by_format={name: formats_set[name] for name in TASK_FORMATS},
        by_max_score={str(int(score)): count for score, count in sorted(maxima_set.items())},
    )
    assert published_assignments == expected['assignments'], (published_assignments, expected['assignments'])
    assert set(formats_set) <= set(TASK_FORMATS), \
        ('Unrecognised task format in an assignment name.', set(formats_set) - set(TASK_FORMATS))
    assert published_assignments['min_per_section'] < published_assignments['max_per_section'], \
        'Every class sets the same number of tasks.'
    assert len(maxima_set) > 1, 'Every task is marked out of the same total.'
    assert max(formats_set.values()) > 2 * min(formats_set.values()), \
        ('Task formats are split evenly across the six kinds.', dict(formats_set))
    if assumptions['instructional_days'] >= 90:
        # Only meaningful once the year is long enough to hold distinct calendars. A short
        # volume-test run leaves classes setting almost as many tasks as there are days, so
        # they are forced onto the same dates and a floor would be testing the calendar
        # length rather than the fixture.
        assert published_assignments['distinct_due_date_calendars'] >= len(due_dates_by_section) * 0.95, \
            'Classes share one due-date calendar.'
    seen = set()
    pairs = set()
    for row in read('NWEA', 'AssessmentResults.csv'):
        assert row['TestID'] not in seen
        seen.add(row['TestID'])
        assert any('SYN-SCHOOL-' + school == row['School_StateID'] and entry <= row['TestStartDate'] < exit_
                   for school, entry, exit_ in stints[row['StudentID']]), ('Test sat outside membership.', row['TestID'])
        assert row['TermName'].endswith(current_term['school_year']) == in_term(current_term, row['TestStartDate'])
        key = row['StudentID'], row['Subject'], row['TermName']
        assert key not in pairs
        pairs.add(key)
    assert expected['assessment_results'] == len(active) * 6
    assert len(seen) == expected['assessment_results'] + prior['assessment_results'] == (len(active) + len(prior_membership)) * 6

    # Subjects must not all land on the same number, and one learner must be genuinely
    # stronger in some subjects than others. Without both, a report asking "where is this
    # student falling behind" can only read the generator's arithmetic back.
    published = {COURSE_TITLES[subject]: round(fsum(earned) / fsum(possible), 4)
                 for subject, (earned, possible) in sorted(marks_by_subject.items())}
    assert published == expected['coursework_score_by_subject'], (published, expected['coursework_score_by_subject'])
    assert len(set(published.values())) == len(published), ('Every subject scores the same.', published)
    assert max(published.values()) - min(published.values()) > 0.03, ('Subjects barely differ.', published)

    ranges = []
    for student in {student for student, _ in marks_by_student}:
        means = [fsum(marks) / len(marks) for subject in range(6)
                 if (marks := marks_by_student.get((student, subject)))]
        if len(means) > 1:
            ranges.append(max(means) - min(means))
    assert ranges, 'No per-student subject means could be read back.'
    within_student_range = round(fsum(ranges) / len(ranges), 2)
    # Recomputed from the CSVs and compared exactly, so the recorded figure cannot drift
    # away from the published data while a threshold alone still passes. The threshold
    # stays as well: equality proves the manifest describes these files, and the floor
    # proves the files carry variation worth reporting on.
    assert within_student_range == expected['mean_within_student_subject_range'], (
        within_student_range, expected['mean_within_student_subject_range'])
    assert within_student_range > 3.0, (
        'A learner must be meaningfully stronger in some subjects than others.',
        within_student_range)

    # The year must move. A register where every learner keeps one absence rate from
    # September to June gives a period comparison, a rolling rate or a follow-up nothing to
    # find, so the patterns are read back from the published register and pinned.
    patterns = attendance_patterns(absence_marks)
    assert patterns == expected['attendance_patterns'], (patterns, expected['attendance_patterns'])
    if assumptions['instructional_days'] >= 90 and len(active) >= 100:
        assert patterns['learners_absence_rising_5pp'] >= len(active) * 0.02, ('Too few learners whose attendance worsens.', patterns)
        assert patterns['learners_absence_falling_5pp'] >= len(active) * 0.02, ('Too few learners whose attendance improves.', patterns)

    # Every logged action must be explainable from the published data: the learner, class
    # and teacher must belong together, the rule it cites must have been met in the days
    # before it was logged, and the outcome note must say what the records show.
    for work in work_by_class.values():
        work.sort()
    log_rows = list(read('PowerSchool', 'log_entries.csv'))
    log_ids = set()
    logged = []
    logged_work = []
    same_day = set()
    for row in log_rows:
        assert row['log_id'] not in log_ids, ('Duplicate log entry.', row['log_id'])
        log_ids.add(row['log_id'])
        student_number, section_id = row['student_number'], row['source_section_id']
        assert roster[student_number]['source_school_id'] == row['source_school_id']
        assert (student_number, section_id) in membership, ('Action logged for a class the learner is not in.', row['log_id'])
        assert sections[section_id]['source_teacher_id'] == row['source_teacher_id'], ('Action logged by a teacher who does not teach that class.', row['log_id'])
        assert row['entry_date'] in day_index, ('Action logged on a day that is not an instructional day.', row['log_id'])
        assert row['follow_up_date'] > row['entry_date']
        index = day_index[row['entry_date']]
        completed = row['status'] == 'Completed'
        assert row['status'] in {'Completed', 'Open'}
        assert completed == (row['completed_date'] != NULL) == (row['outcome_note'] != NULL), row['log_id']
        assert completed == (index + FOLLOW_UP_DAYS < len(instructional_dates)), row['log_id']
        if completed:
            assert row['completed_date'] == row['follow_up_date'] == instructional_dates[index + FOLLOW_UP_DAYS]
        marks = absence_marks[student_number]
        if row['log_type'] in ATTENDANCE_ACTIONS:
            assert row['reason'] == ATTENDANCE_REASON
            assert any(meets_attendance_rule(marks, trigger) for trigger in range(max(0, index - 4), index)), \
                ('Attendance action logged without the rule being met.', row['log_id'])
            if completed:
                assert row['outcome_note'] == attendance_outcome_note(marks, index), row['log_id']
        else:
            assert row['log_type'] == MISSING_WORK_ACTION and row['reason'] == MISSING_WORK_REASON, row['log_id']
            work = work_by_class[student_number, section_id]
            assert any(index - 3 <= due < index
                       and sum(missing for _, missing in work[max(0, position + 1 - MISSING_WORK_RULE_TASKS):position + 1])
                       >= MISSING_WORK_RULE_MISSING
                       for position, (due, _) in enumerate(work)), \
                ('Missing-work follow-up logged without the rule being met.', row['log_id'])
            if completed:
                assert row['outcome_note'] == work_outcome_note(work, index), row['log_id']
        logged.append((student_number, index, row['log_type']))
        logged_work.append((student_number, section_id, index, row['log_type']))
        category = 'Attendance' if row['log_type'] in ATTENDANCE_ACTIONS else 'Coursework'
        # "A learner's first action" must never be a tie, or the report and this check could
        # pick different ones.
        assert (student_number, category, row['entry_date']) not in same_day, ('Two same-kind actions on one day.', row['log_id'])
        same_day.add((student_number, category, row['entry_date']))
    published_log = dict(
        total=len(log_rows),
        by_type={kind: sum(row['log_type'] == kind for row in log_rows)
                 for kind in (*ATTENDANCE_ACTIONS, MISSING_WORK_ACTION)},
        learners=len({row['student_number'] for row in log_rows}),
        open=sum(row['status'] == 'Open' for row in log_rows))
    assert published_log == expected['log_entries'], (published_log, expected['log_entries'])
    follow_up = action_follow_up(absence_marks, logged)
    assert follow_up == expected['attendance_action_follow_up'], (follow_up, expected['attendance_action_follow_up'])
    work_follow_up = coursework_follow_up(work_by_class, logged_work)
    assert work_follow_up == expected['coursework_follow_up'], (work_follow_up, expected['coursework_follow_up'])

    # Absence must reach the coursework: work due after a run of absences goes missing more
    # often than the rest.
    by_absence = missing_work_by_recent_absence(
        (absences_before(absence_marks[student_number], due, ATTENDANCE_RULE_DAYS), missing)
        for (student_number, _), work in work_by_class.items() for due, missing in work)
    assert by_absence == expected['missing_work_by_recent_absence'], (by_absence, expected['missing_work_by_recent_absence'])
    # Floors only hold once the year and the cohort are large enough for the rules to fire
    # often; a short volume-test run can legitimately log no escalations at all.
    if assumptions['instructional_days'] >= 90 and len(active) >= 100:
        assert all(published_log['by_type'].values()), ('Every action type must appear in the log.', published_log)
        assert work_follow_up['fewer_missing_after'] > 0 and work_follow_up['same_or_more_missing_after'] > 0, work_follow_up
        assert all(changes['entry'].get(kind) for kind in ('New', 'Continuing', 'Transferred in')), changes
        assert all(changes['exit'].get(kind) for kind in ('Continuing', 'Transferred out', 'Completed final grade', 'Left')), changes
        # Both outcomes must be present: a log where every action is followed by improvement
        # would read as proof that actions work, and one where none is would give a follow-up
        # view nothing to show.
        assert follow_up['fewer_absences_after'] > 0 and follow_up['same_or_more_absences_after'] > 0, follow_up
        assert follow_up['learners_with_attendance_action'] < patterns['learners_meeting_attendance_rule'], \
            'Every learner who met the attendance rule has an action; the log must also show gaps.'
        assert by_absence['after_attendance_rule_met'] > by_absence['otherwise'], by_absence

    print(f'PASS: {len(manifest["tables"])} table files; counts, hashes, unique keys, school joins, '
          f'workload metrics, subject variation, attendance patterns, logged actions and both school years checked.')
    print(json.dumps(expected, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schools', type=int, default=3)
    parser.add_argument('--average-students-per-school', '--students-per-school', dest='average_students_per_school',
                        type=int, default=600,
                        help='Average school population; individual school sizes vary around this value (default: 600).')
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--check', action='store_true', help='Check existing files without regeneration.')
    args = parser.parse_args()
    if args.check:
        manifest = json.loads((OUTPUT / 'manifest.json').read_text(encoding='utf-8'))
    else:
        manifest = generate(args.schools, args.average_students_per_school, args.days)
    check(manifest)


if __name__ == '__main__':
    main()