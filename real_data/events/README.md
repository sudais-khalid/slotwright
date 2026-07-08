# Semester event plan

The list of events the department/societies want scheduled this semester —
the agent decides the day, time slot, and venue for each one.

## CSV template (`event_plan_template.csv`)

| column | meaning | example |
|---|---|---|
| name | event name | AI Career Fair 2026 |
| category | workshop / seminar / hackathon / career_fair / guest_lecture / society_meeting | career_fair |
| expected_audience | rough head count | 250 |
| priority | 1 (minor) – 3 (major) | 3 |
| target_semesters | which semesters it's for, `;`-separated, or `all` | 6;7;8 |
| preferred_week | semester week 1–16 the organizer wants (the agent may defer it) | 5 |
| duration_hours | how long it runs | 3 |
| organizer | society/department | AI Innovation Society |

Also useful (optional): the academic calendar — exam weeks and holiday dates
for the semester — as a note in any file here, e.g.
`calendar.txt`: "midterms week 8, finals week 16, Eid holidays weeks 11–12".
