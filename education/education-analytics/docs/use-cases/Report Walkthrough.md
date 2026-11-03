# Report walkthrough: from a district figure to one learner, and back

A 15-minute script for the Education Analytics report on the default sample data. It uses four pages: **District**, **School briefing**, **Class review** and **Student review**. It moves from the district to a school, a class and one learner, then back up to the district, the way a head of district, a head of school and a teacher would read the report. Every figure below comes from the default sample data and was checked against the deployed semantic model. If you regenerate the data with other settings, the names and numbers change.

The accelerator does not depend on this script. It only shows where to click and what the data contains.

## Before you start

1. Deploy the accelerator, run `EDU_BR_GD_Processing`, and refresh the semantic model. Keep the default reporting period (`2024-09-01` to `2026-05-09`) so both school years reach Gold.
2. Every page is filtered to the latest school year (2025-2026). Comparisons with 2024-2025 use the same dates a year earlier.
3. The school map on the District page needs Azure Maps to be allowed in the Power BI tenant settings.
4. Open the report in reading view and clear all slicers. Optionally save a bookmark for each scene.
5. Optional (scene 6): create a Fabric data agent over the semantic model with the instructions in [Data agent set-up](#data-agent-set-up).

## People and records used

| Role | Name in the data | Where |
| --- | --- | --- |
| Head of district | (you) | Cedar Valley School District: 3 middle schools, 1,800 learners this year, 1,753 last year |
| Head of school | (you) | **Summit Harbor Middle School**, 19200 44th Avenue West, Lynnwood, 600 learners |
| Teacher | **Martin Rutherford**, English Language Arts | *English Language Arts 6 - Group 07*, 26 learners |
| Learner (attendance) | **Isaac Patel** (`SYN-D1-STU-001012`), grade 6 | Summit Harbor |
| Learner (coursework) | **Nora Murphy** (`SYN-D1-STU-001013`), grade 6 | Same class |
| Counter-example | **Liam Diaz** (`SYN-D1-STU-000910`), grade 8 | Summit Harbor |
| A gap | **Mateo Torres** (`SYN-D1-STU-000044`), grade 7 | Alder Heights |

## The story in one sentence

The district is doing better than last year, but one school is not. In that school we can see which learners met a rule, what teachers did about it, and what happened next, down to one learner's week-by-week record.

## Scene 1 - The district this year and last (head of district, 3 min)

**Page:** District. No slicers.

**Show:**
- First card: district attendance **93.0%**, up **0.6** points on last year (**92.4%**). Chronic absence fell from **24.6%** to **23.1%** of learners.
- Second card: **1,800** learners enrolled against **1,753** last year (**+47**): **691** new, **45** transferred in from another district school, **59** left the district, and **585** completed their final grade last year.
- *Attendance rate by school, this school year and last*: Alder Heights **93.0%** (last year **91.3%**), Rainier View **94.7%** (**94.0%**), Summit Harbor **91.1%** (**91.7%**).
- *Attendance by month, this school year against last*: both years dip through winter. This year falls from **93.8%** in September to **92.0%** in January and recovers to **93.6%** in April.
- The map: three schools in Lynnwood, Everett and Edmonds, sized by learners enrolled. Hover **Summit Harbor**: **600** learners against **592**, and attendance down on last year.

**Say:** "The district improved this year. Two schools went up. Summit Harbor went down, and it is two points below the others. Coverage is close to 100%, so this is not missing data. That is where we look next."

The page compares schools on the same year group and period. It does not rank them. A year group holds a different cohort each year, so a change on last year describes the school, not the same learners.

## Scene 2 - One school: who met a rule, and what we did (head of school, 3 min)

**Page:** School briefing. **School** = Summit Harbor. Thresholds at their defaults (10% and 5 absences in 20 school days).

**Show:**
- *Early warning and actions logged*: **40.5%** of learners missed at least 10% of their known days, and **326** met the attendance rule on at least one day. Teachers logged **729** actions for **353** learners; **32** are still open.
- Move **Chronic absence threshold (%)** to 15, then back to 10. The share changes: "the rule is ours, and it is visible".
- *Attendance rate by year group*: the share meeting the attendance rule, side by side with attendance.
- *Actions logged by month and type*: actions peak in January (**152**). Check-ins come first, then family contacts and attendance plans.
- *After a first attendance action*: **282** learners at this school compared over 10 school days either side. Absence fell from about **29%** to about **13%**, and **223** had fewer absences.

**Say:** "These are not risk scores. A learner appears here because they met a rule we can all read, and the threshold is a slicer. We can also see that teachers acted, when, and what happened next."

## Scene 3 - One class (teacher, 2 min)

**Page:** Class review. **Class teacher** = Martin Rutherford, **Class** = English Language Arts 6 - Group 07 (Summit Harbor Middle School).

**Show:**
- *Selected classes at a glance*: **26** learners, class attendance **91.7%**, **10** learners met the attendance rule, **27** actions logged.
- The students table. Sort by attendance:
  - **Isaac Patel** has the lowest attendance in the class (**83.3%**), met the attendance rule, and has the most actions (**4**).
  - **Nora Murphy** has good attendance (**92.2%**) and did not meet the attendance rule, but has the most unsubmitted work (**11** pieces) and **3** actions.

**Say:** "Two learners, two different problems. One is not in school. The other is in school, but the work is not coming in."

**Do:** right-click **Isaac Patel** and choose **Drill through > Student review**.

## Scene 4 - Attendance for one learner (teacher, 2 min)

**Page:** Student review, for Isaac Patel.

**Show:**
- The three cards at the top:
  - *Attendance this school year*: **83.3%**, **30** absent days. *Last year* is blank, because he is in grade 6 and new to the school.
  - *Marked work*: **72%**, level with the rest of his classes. The absences have not shown up in his marks yet.
  - *Actions teachers logged*: **4**, none still open.
- *Attendance rate by week, with the actions teachers logged*: steady in autumn, a sharp drop in December and February, and back up in March. The columns mark each logged action on the same timeline.
- *Actions logged for this student*:

| Date | Action | Logged by | Outcome note |
| --- | --- | --- | --- |
| 2025-12-11 | Student check-in | Martin Rutherford | Fewer absences since the action |
| 2026-01-05 | Family contact | Martin Rutherford | Fewer absences since the action |
| 2026-01-19 | Missing work follow-up (World History) | Jonathan Fairbairn | Next piece of work handed in |
| 2026-02-16 | Attendance plan | Martin Rutherford | Fewer absences since the action |

- *Recorded assignments*: his missing work clusters in December (3 pieces) and January (4 pieces).
- *Marked work by subject*: English Language Arts **71.5%**, about the same as the rest of the class.
- *Test results by window*: Reading RIT **203 > 206 > 210** across Fall, Winter and Spring.

**Say:** "The rule fired on 5 December. Mr Rutherford checked in six days later, and the school followed up. The point is not that the check-in worked. The point is that we saw it early, wrote down what we did, and can look back honestly."

## Scene 5 - Coursework for one learner (teacher, 2 min)

**Page:** Student review. **Student** = Nora Murphy.

**Show** the actions table with the work columns (5 pieces of work due before and after each follow-up):

| Date | Action | Logged by | Work missing before / after |
| --- | --- | --- | --- |
| 2025-10-15 | Missing work follow-up (English) | Martin Rutherford | 3 / 1 |
| 2026-02-20 | Missing work follow-up (English) | Martin Rutherford | 4 / 0 |
| 2026-04-13 | Missing work follow-up (World History) | Jonathan Fairbairn | 3 / 2 |

- *Marked work*: **71%**, about **1** point below the rest of her classes. *Where to follow up: marked work by topic* shows where she sits furthest below the class in English: *Unit 3: Vocabulary in Context*, **6.7** points below.

**Say:** "Nora met the missing-work rule again in early January, but the next follow-up came in late February. The data shows the gap as clearly as it shows the follow-up."

**Optional - ask the data agent:** "Summarize Nora Murphy's English work since December and list three questions for a conversation with her." A good answer quotes the missing pieces and the dates, and predicts nothing.

## Scene 6 - Not every follow-up is followed by a change (head of school, 1 min)

**Do:** on **Student review**, choose **Liam Diaz** in the Student slicer.

**Show:** the attendance card, **83.3%** against **82.7%** last year. A check-in in October and an attendance plan in February are both followed by *Absences continue; consider next step*. Only the family contact in January was followed by fewer absences.

**Optional:** choose **Mateo Torres** (Alder Heights). His attendance fell from **95.0%** last year to **89.4%**. He met the attendance rule in late March, and the actions card and list are empty.

**Say:** "The report shows the actions that were not followed by a change, and the learners we missed. That is what makes it credible to teachers."

## Scene 7 - Back to the district (head of district, 2 min)

**Page:** School briefing. Clear the School slicer.

**Show** the two follow-up cards:
- *After a first attendance action*: **536** learners compared over 10 school days either side. Absence **28.99%** before and **11.94%** after; **432** had fewer absences and **104** the same or more.
- *After a first missing-work follow-up*: **310** learners compared over 5 pieces of work either side. Missing work **61.0%** before and **21.5%** after; **273** missed less and **37** the same or more.

**Say:** "This is observed after, not caused by. A rule fires on an unusually bad run, so some of the fall would have happened anyway. What this gives us is an honest picture of where follow-up happens, and where it does not."

**Close:** "From one district figure to one learner's week, and back. Same data, same rules, for every role."

## Data agent set-up

Create a Fabric data agent over the `EducationAnalytics` semantic model. Suggested instructions:

> You help teachers and school leaders read attendance, coursework, enrollment and logged actions. Quote figures and their coverage exactly as the model returns them. Never predict an outcome, score or rank a learner or a school, or say that an action caused a change; use "observed after". Always state the threshold in use for chronic absence and the attendance rule, and the school year. When asked for next steps, suggest questions for a conversation, not decisions.

Example questions:
- District: "How did attendance and enrollment at each school change since last school year?"
- School: "How many learners at Summit Harbor met the attendance rule, and how many have an open action?"
- Teacher: "Summarize Isaac Patel's attendance and English work since December, and list three questions for a check-in."

## Questions you may get

| Question | Answer |
| --- | --- |
| Is this real data? | No. It is synthetic, generated by `sample-data/generate_district.py`. The patterns are built to behave like real records and are documented in the sample data README. |
| Does the follow-up work? | The data cannot say. Before/after figures describe what happened next. Part of any fall is regression to the mean, and how often an action is followed by improvement was set by the generator. |
| Where does the action log come from? | A proposed PowerSchool-style log extract (`log_entries.csv`). In a real district, map it from your SIS log, case-management tool or a Teams or Planner list. |
| Why is last year's coursework missing? | The sample keeps only SIS membership, attendance and tests for earlier years, as many districts do once LMS courses are archived. |
| Can we change the rules? | The thresholds are slicers on the School briefing page. The 20-day, 10-day and 5-piece windows are constants in `EDU_Config`. |
| Is anyone scored? | No. Nothing predicts, scores or ranks a learner. A learner appears because they met a visible rule. |

## Reset afterwards

Clear all slicers, set both thresholds back to their defaults (10% and 5), and return to the District page.
