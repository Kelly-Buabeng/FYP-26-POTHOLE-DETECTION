# 03 · Personas & User Stories

> Owner: Seth Akoto · Status: DRAFT started by the team lead for Seth to take over · Becomes the SRS (deliverable 10) in week 3

Priorities use MoSCoW: **M** = must have for the 6-month pilot, **S** = should have, **C** = could have if time allows, **W** = won't have this time.

## Personas

| Persona | Who | Goals | Constraints |
|---|---|---|---|
| **Ama, student commuter** | UG student who walks and takes trotro around Legon and Madina | Report hazards quickly; know they were fixed | Low-end Android phone, limited data bundle, patchy signal |
| **Kwame, commercial driver** | Taxi or trotro driver on busy Accra roads | Avoid damaged roads; report dangers without stopping long | Driving most of the day; cannot type much |
| **Officer Mensah, authority officer** | Staff at a road authority, MTTD or the UG estates office | See hazards in their area, prioritise and record fixes | Office PC; little time; needs reliable, non-duplicate reports |
| **Moderator** | Project team member during the pilot | Remove spam and fix wrong categories quickly | Checks the queue a few times a day |
| **Admin** | Team lead | Manage authorities, areas and categories | — |

## User stories

### Citizen: account

| ID | Story | Priority |
|---|---|---|
| C-01 | As a citizen, I sign in with my phone number and a one-time SMS code, so I don't need a password. | M |
| C-02 | As a citizen, I can see and delete my account and my data. | M |

### Citizen: reporting

| ID | Story | Priority |
|---|---|---|
| C-10 | As a citizen, I take a photo of a pothole in the app, and my exact GPS location is attached automatically. | M |
| C-11 | As a citizen, I can move the pin if the GPS position is slightly wrong. | M |
| C-12 | As a citizen, I report a faulty traffic light by choosing the junction on a map and picking the fault: all out, stuck on red, flashing, or damaged pole. | M |
| C-13 | As a citizen, I report another hazard (broken-down vehicle, accident, flooding, fallen tree, missing drain or manhole cover, damaged sign, pedestrian danger) by choosing its type. | M |
| C-14 | As a citizen, I can add a short description. | S |
| C-15 | As a citizen with no signal, my report is saved and sent automatically when I'm back online. | M |
| C-16 | As a citizen, I'm told straight away whether the AI saw a pothole, so I can retake a bad photo. | S |
| C-17 | As a citizen near an existing report, I can tap "still there" or "fixed" instead of making a new report. | S |

### Citizen: follow-up and map

| ID | Story | Priority |
|---|---|---|
| C-20 | As a citizen, I see a list of my reports and the status of each one. | M |
| C-21 | As a citizen, I get a notification when my report is confirmed, assigned and fixed. | S |
| C-22 | As a citizen, I see a map of active hazards around me, filtered by type. | M |
| C-23 | As a road user, I get an alert when I'm near a serious hazard. | W (later phase) |

### Authority officer

| ID | Story | Priority |
|---|---|---|
| A-01 | As an officer, I sign in to a web dashboard with email, password and a second factor. | M |
| A-02 | As an officer, I see only incidents in my authority's area, on a map and in a list. | M |
| A-03 | As an officer, I sort and filter incidents by type, severity, status and number of reports. | M |
| A-04 | As an officer, I open an incident and see its photos (blurred), location, history and reports. | M |
| A-05 | As an officer, I change an incident's status (assigned, in progress, fixed) and add a note. | M |
| A-06 | As an officer, I export incidents to CSV for my own reports. | S |
| A-07 | As an officer, I see simple statistics: open incidents, time to fix, hotspots. | C |

### Moderator and admin

| ID | Story | Priority |
|---|---|---|
| M-01 | As a moderator, I see a queue of reports the AI wasn't sure about and approve, reject or merge them. | M |
| M-02 | As a moderator, I can block an account that sends spam. | S |
| M-03 | As an admin, I create authorities, draw their areas on a map and invite their officers. | M |
| M-04 | As an admin, I edit hazard types and subtypes without changing code. | C |

### System behaviour

| ID | Story | Priority |
|---|---|---|
| S-01 | Reports of the same type close together are merged into one incident (e.g. potholes within 15 m). | M |
| S-02 | Short-lived hazards expire unless re-confirmed (broken-down vehicle 6 h, accident 3 h, flooding 24 h). | M |
| S-03 | Faces and number plates are blurred before any photo is shown to anyone other than moderators. | M |
| S-04 | Reports from outside Ghana or with very poor GPS accuracy are rejected or sent for review. | M |
| S-05 | Each new incident is routed to the authority whose area contains it. | M |

## Non-functional requirements (first list)

| ID | Requirement | Target |
|---|---|---|
| NF-01 | Simultaneous users | ≥ 200, proven by a load test |
| NF-02 | Report submission response | < 0.5 s (95% of requests); AI result within 10 s |
| NF-03 | Map loading | < 1 s on a 3G connection for the pilot area |
| NF-04 | Android support | Android 8.0 and newer; usable on 2 GB RAM phones |
| NF-05 | App data use | Photos compressed to ≤ 500 KB before upload |
| NF-06 | Availability during pilot | ≥ 99% |
| NF-07 | Privacy | Compliant with the Data Protection Act, 2012 (Act 843); reporter identity never public |
| NF-08 | Security | HTTPS everywhere; 2FA for officers and admins; rate limits on reporting |
| NF-09 | Running cost | Within GHS 2,650 per month for hosting and AI |
| NF-10 | Accessibility | Large touch targets, readable in sunlight, icons with text labels |

## Open questions

- Which languages should the app support at launch: English only, or also Twi and others?
- Who receives traffic-light reports during the pilot: UG estates, MTTD, or both?
- How many testers and how long should the pilot run?
