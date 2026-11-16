# 10 · Functional Requirements (SRS Part 1)

> Owners: Seth Akoto + Kelly Buabeng · Status: DRAFT v0.1 · 16 Nov 2026
> Sources: [features.md](features.md) (F#), [03-requirements.md](03-requirements.md) (story IDs).
> Non-functional requirements will be SRS Part 2.

## How to read this

- Every requirement has an ID (`FR-AREA-NN`) that never changes. If a requirement is dropped, mark it **Withdrawn**; never reuse its ID.
- **Priority:** M = must have for the pilot · S = should have · C = could have (nice to have). These match the tiers in the feature list.
- **"Shall"** means required. **"Should"** inside a requirement means recommended behaviour.
- **Acceptance** is how we test it. A requirement is done only when its acceptance check passes.
- Numbers marked † are **starting values**. Week-2 feasibility work may tune them. Change them here, with a note in `decisions.md`.

## Contents

1. [Actors and roles](#1-actors-and-roles)
2. [Hazard catalogue](#2-hazard-catalogue)
3. [Accounts and sign-in (AUTH)](#3-accounts-and-sign-in-auth)
4. [Submitting a report (REP)](#4-submitting-a-report-rep)
5. [Photos (MED)](#5-photos-med)
6. [AI analysis (AI)](#6-ai-analysis-ai)
7. [Incidents: merging, lifecycle, expiry (INC)](#7-incidents-merging-lifecycle-expiry-inc)
8. [Authorities and routing (AGY)](#8-authorities-and-routing-agy)
9. [Authority dashboard (DSH)](#9-authority-dashboard-dsh)
10. [Maps and public views (MAP)](#10-maps-and-public-views-map)
11. [Citizen follow-up and notifications (NOT)](#11-citizen-follow-up-and-notifications-not)
12. [Moderation (MOD)](#12-moderation-mod)
13. [Administration (ADM)](#13-administration-adm)
14. [Privacy, audit and abuse protection (PRV)](#14-privacy-audit-and-abuse-protection-prv)
15. [Traceability: features → requirements](#15-traceability-features--requirements)

---

## 1. Actors and roles

| Role | Who | Uses | How they sign in |
|---|---|---|---|
| **Visitor** | Anyone, not signed in | Public web map | — |
| **Citizen** | A registered app user | Android app | Phone number + SMS code |
| **Officer** | Staff of an onboarded authority (UG estates, MTTD, NRSA…) | Web dashboard | Email + password + second factor |
| **Moderator** | Project team member | Web dashboard (moderation pages) | Email + password + second factor |
| **Admin** | Team lead (and deputies) | Web dashboard (admin pages) | Email + password + second factor |
| **System** | Background jobs and the AI worker | — | — |

### Permissions

| Action | Visitor | Citizen | Officer | Moderator | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| View public hazard map | ✓ | ✓ | ✓ | ✓ | ✓ |
| Submit a report | | ✓ | | | |
| Confirm "still there" / "fixed" | | ✓ | | | |
| View own reports | | ✓ | | | |
| View unblurred photos | | | | ✓ | ✓ |
| View incidents in own authority's area | | | ✓ | ✓ (all) | ✓ (all) |
| Change incident status | | | ✓ (own area) | ✓ | ✓ |
| Approve / reject / merge reports | | | | ✓ | ✓ |
| Block a citizen account | | | | ✓ | ✓ |
| Manage authorities, areas, officers | | | | | ✓ |
| Manage hazard types | | | | | ✓ |

---

## 2. Hazard catalogue

The catalogue is data, not code (see FR-ADM-04). These are the starting values.

| Category | Subtypes | Photo | AI check | Merge radius† | Expires after† | Default severity† |
|---|---|---|---|---|---|---|
| **Pothole** | small · large · cluster of potholes · road collapse | Required | Yes, pothole detection | 15 m | Never (until resolved) | From AI (FR-AI-04) |
| **Traffic light** | all lights out · stuck on red · flashing · wrong sequence · damaged or knocked-down pole | Optional | No | Same junction | Never | 4 (pole: 5) |
| **Broken-down vehicle** | on the road · on a bend or hill · blocking a lane | Required | Scene check only (FR-AI-05) | 50 m | 6 h | 4 |
| **Accident** | collision · overturned vehicle · vehicle hit pedestrian | Optional | Scene check only | 50 m | 3 h | 5 |
| **Flooding** | road flooded · washed-out section | Required | Scene check only | 150 m | 24 h | 4 |
| **Obstruction** | fallen tree · debris or rocks · abandoned vehicle | Required | Scene check only | 50 m | 24 h | 3 |
| **Road infrastructure** | missing drain or manhole cover · damaged guardrail · missing or damaged sign · broken streetlight · collapsed culvert | Required | Scene check only | 25 m | Never | 3 (missing cover: 5) |
| **Pedestrian hazard** | open drain on walkway · broken footbridge · blocked walkway | Required | Scene check only | 25 m | Never | 3 |

Severity scale: **1** minor · **2** low · **3** moderate · **4** high · **5** dangerous to life.

---

## 3. Accounts and sign-in (AUTH)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-AUTH-01 | The app shall register and sign in citizens with a Ghanaian mobile number (+233) and a 6-digit code sent by SMS. | M | A valid +233 number receives a code; entering it signs the user in. Non-+233 numbers are rejected with a clear message. | F1, C-01 |
| FR-AUTH-02 | An SMS code shall expire 5 minutes† after it is sent and shall work once only. | M | A code used twice, or after 5 minutes, is refused. | F1 |
| FR-AUTH-03 | The system shall allow at most 5† wrong code attempts per number per hour, and at most 1 new code per 60 seconds and 5 per hour. | M | The 6th wrong attempt within an hour is blocked; requesting a code twice within 60 s is refused. | F1, F24 |
| FR-AUTH-04 | A signed-in citizen shall stay signed in on that phone for 30 days† without re-entering a code, unless they sign out. | M | After 29 days the user is still signed in; after signing out a new code is required. | F1 |
| FR-AUTH-05 | On first sign-in the app shall ask for a display name (optional) and show the privacy notice, which the citizen must accept to continue. | M | No report can be sent before the notice is accepted; acceptance is stored with a timestamp. | F9 |
| FR-AUTH-06 | Officers, moderators and admins shall sign in to the dashboard with email and password plus a second factor (authenticator app code). | M | Login without the second factor fails. | F17, A-01 |
| FR-AUTH-07 | Dashboard accounts shall be created only by invitation from an admin; there shall be no public sign-up for the dashboard. | M | The dashboard has no sign-up page; an invite link expires after 72 h. | F23, M-03 |
| FR-AUTH-08 | Dashboard sessions shall end after 30 minutes† of inactivity. | M | After 30 idle minutes, the next action asks for login. | F17 |
| FR-AUTH-09 | Users shall be able to reset a forgotten dashboard password by email link valid for 1 hour. | M | Link works once within 1 h; older links are refused. | F17 |

---

## 4. Submitting a report (REP)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-REP-01 | The app shall let a signed-in citizen start a report by choosing one category from the hazard catalogue, then a subtype. | M | All categories and subtypes in §2 appear; a report cannot be sent without both. | F2–F4 |
| FR-REP-02 | The app shall show a safety reminder before the first report, and on each report if the phone is moving faster than 15 km/h†: "Don't use your phone while driving. Ask a passenger or stop safely." | M | Reminder appears on first use and when moving above the threshold. | Safety |
| FR-REP-03 | The app shall capture the phone's GPS position, its accuracy in metres, the compass heading (if available) and the time, at the moment the photo is taken (or, with no photo, when the report is started). | M | Submitted report contains lat, lng, accuracy, heading (or null) and capture time. | F2, C-10 |
| FR-REP-04 | The app shall show the captured position on a map and let the citizen drag the pin up to 100 m† from the captured GPS position. | M | Pin cannot be moved further than 100 m; the original GPS and the adjusted position are both stored. | F5, C-11 |
| FR-REP-05 | If GPS accuracy is worse than 50 m†, the app shall ask the citizen to confirm the pin before sending. If worse than 200 m†, the app shall not send until a better fix is obtained or the pin is confirmed on the map. | M | Tested with simulated accuracies of 30 m, 80 m and 250 m. | F5, F15 |
| FR-REP-06 | For a traffic-light report, the app shall show known traffic-light junctions within 500 m† of the citizen and let them choose one, or choose "not listed" and place a pin. | M | Junctions list loads from the server; "not listed" creates a new candidate junction for moderator review. | F3, C-12 |
| FR-REP-07 | The citizen may add a description of up to 280 characters. | S | 281st character cannot be typed; description shown to officers. | F32, C-14 |
| FR-REP-08 | The app shall show a summary (category, subtype, photo, map pin, description) and require the citizen to tap **Send report**. | M | No report is sent without the explicit tap. | — |
| FR-REP-09 | The server shall reply to a valid report within 0.5 s (95% of requests) with a report ID and status "Received", before AI analysis finishes. | M | Measured under the 200-user load test. | F26 |
| FR-REP-10 | The server shall reject a report whose position is outside Ghana, with the message "This location is outside Ghana." | M | Report at a Lomé or Abidjan position is rejected; Accra is accepted. Already in the prototype. | F15, S-04 |
| FR-REP-11 | If the phone has no connection, the app shall save the report on the phone, show it in My reports as "Waiting to send", and send it automatically when connected. Saved reports keep their original capture time. | M | Report made in airplane mode is sent after airplane mode is off; capture time unchanged. | F6, C-15 |
| FR-REP-12 | The app shall keep up to 20† unsent reports and delete unsent reports older than 48 hours†, telling the citizen. | M | 21st offline report is refused with a message; 49-hour-old report is removed with a notice. | F6 |
| FR-REP-13 | The server shall ignore an exact duplicate submission (same device report ID sent twice, e.g. after a network retry). | M | Re-sending the same report creates one record only. | F6 |
| FR-REP-14 | Before creating a new report, the app should show existing open incidents of the same category within the merge radius and offer "Same as this one?" | S | Accepting adds a confirmation (FR-INC-08) instead of a new report. | F30, C-17 |

---

## 5. Photos (MED)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-MED-01 | Photos shall be taken with the in-app camera only. Choosing from the gallery shall not be offered. | M | No gallery option exists in the report flow. | F2, anti-fraud |
| FR-MED-02 | The app shall resize and compress each photo to at most 1600 px on the long side and about 500 KB† before upload. | S | Uploaded file ≤ 1600 px and ≤ 600 KB for typical scenes. | F37 |
| FR-MED-03 | A report may carry 1 to 3† photos where a photo is required, and 0 to 3 where it is optional (§2). | M | 4th photo cannot be added; required-photo categories cannot be sent with none. | F2–F4 |
| FR-MED-04 | Photos shall upload directly to file storage using a short-lived upload link (valid 10 minutes†) issued by the server for that report only. | M | An expired or reused link is refused by storage. | Architecture |
| FR-MED-05 | The server shall accept only JPEG or PNG files up to 5 MB†, and shall reject the report's photo if the file type does not match its contents. | M | A renamed .exe or a 10 MB file is rejected. | F25 |
| FR-MED-06 | The system shall store the original photo privately, plus a blurred copy and a thumbnail for display (FR-AI-06). | M | Original is never returned to visitors, citizens or officers. | F12 |
| FR-MED-07 | The system shall remove location and device details (EXIF metadata) from every displayed copy of a photo. | M | Downloaded displayed copy contains no EXIF GPS or device fields. | Privacy |

---

## 6. AI analysis (AI)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-AI-01 | The system shall run the pothole model on every photo of a pothole report and store, for each photo: detected boxes, confidence per box, model name and model version. | M | Every pothole report has a stored result naming the model version. | F10, F11 |
| FR-AI-02 | AI analysis shall finish within 10 seconds of upload for 95% of photos under normal load. | M | Measured during the load test. | F26 |
| FR-AI-03 | Pothole reports shall be routed by the highest confidence: **≥ 0.60†** → verified automatically · **0.30–0.59†** → moderation queue · **< 0.30†** → moderation queue, flagged "no pothole detected". | M | Test photos at each band land in the right place. | F11, F22 |
| FR-AI-04 | The system should estimate pothole severity (1–5) from the size of the detected area relative to the image, and show it to officers. | S | Severity shown on the incident; moderators can override it. | F33 |
| FR-AI-05 | For other categories with a required photo, the system shall check the photo is a plausible outdoor road scene and is not inappropriate; failures go to the moderation queue. | M | Indoor selfie or blank photo is queued, not published. | F11, F22 |
| FR-AI-06 | The system shall blur faces and vehicle number plates in every photo before a blurred copy is made available to anyone except moderators and admins. | M | On a test set of 50 street photos, all visible faces and plates are blurred in the displayed copy. | F12, S-03 |
| FR-AI-07 | If AI analysis fails or times out, the report shall go to the moderation queue (never be lost or published unchecked). | M | Stopping the AI worker sends new reports to the queue; restarting it does not duplicate them. | F22 |
| FR-AI-08 | The app should tell the citizen within 15 seconds whether a pothole was seen, and offer "Retake photo" if not. | S | "We couldn't see a pothole. Retake the photo?" appears for a no-pothole test photo. | F31, C-16 |
| FR-AI-09 | Moderator decisions (approve, reject, correct category) shall be stored with the photo so they can be used as training labels later. | M | Each moderation action is linked to the photo and model version. | F10, ML loop |

---

## 7. Incidents: merging, lifecycle, expiry (INC)

An **incident** is the real-world hazard. A **report** is one citizen's submission about it. Many reports can belong to one incident.

### Incident statuses

| Status | Meaning | Shown publicly? |
|---|---|:-:|
| Reported | Created, waiting for AI or moderation | No |
| Verified | Confirmed real by AI or a moderator | Yes |
| Assigned | An officer has taken responsibility | Yes |
| In progress | Repair or response under way | Yes |
| Resolved | Officer says it is fixed or cleared | Yes (as "Fixed") for 7 days |
| Closed | Finished | No |
| Rejected | Spam, duplicate or not a hazard | No |
| Expired | Short-lived hazard not re-confirmed in time | No |

### Allowed status changes

| From → To | Who or what | Condition |
|---|---|---|
| Reported → Verified | System or moderator | AI confidence ≥ threshold, or moderator approves |
| Reported → Rejected | Moderator | Reason required |
| Verified → Assigned | Officer | Incident is in the officer's area |
| Verified → Expired | System | Category has an expiry time and no confirmation arrived in time |
| Assigned → In progress | Officer | — |
| Assigned / In progress → Resolved | Officer | Note required; "after" photo optional (FR-DSH-08) |
| Resolved → Closed | System | 7 days† pass with fewer than 2 "still there" votes |
| Resolved → Assigned (reopened) | System | 2† or more "still there" votes from different citizens within 7 days |
| Any open status → Verified | Moderator | Undo of a wrong officer action, with a note |

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-INC-01 | When a report is verified, the system shall attach it to an open incident of the same category within that category's merge radius (§2), or create a new incident if none exists. | M | Two pothole reports 10 m apart → 1 incident; 40 m apart → 2 incidents. | F13, S-01 |
| FR-INC-02 | Traffic-light reports shall merge by junction: all open reports for the same junction and fault belong to one incident. | M | Three "all out" reports for one junction → 1 incident with 3 reports. | F13 |
| FR-INC-03 | An incident shall record its category, subtype, severity, status, position (the first verified report's position), number of reports, first and last report times, and responsible authority. | M | All fields present on every incident. | F20 |
| FR-INC-04 | The incident's severity shall be the highest severity of its reports. Moderators may override it, with a note. | M | Adding a severity-5 report to a severity-3 incident makes it 5. | F33 |
| FR-INC-05 | The system shall only allow the status changes listed in the table above and shall refuse all others. | M | Attempting Verified → Closed directly returns an error. | F21 |
| FR-INC-06 | Every status change shall store who made it, when, the old and new status, and any note. | M | Incident history shows every change in order. | F28 |
| FR-INC-07 | Short-lived hazards shall change to Expired when their expiry time (§2), counted from the latest report or confirmation, passes without a new one. The check shall run at least every 5 minutes. | M | Broken-down vehicle reported at 10:00 and not confirmed is Expired by 16:05. | F14, S-02 |
| FR-INC-08 | A citizen near an open incident (within 200 m†) may confirm it as "still there" or "fixed", once per incident per 24 hours. "Still there" resets the expiry time. | S | Second vote within 24 h refused; "still there" on a breakdown extends it by 6 h. | F30, C-17 |
| FR-INC-09 | Reopening (Resolved → Assigned) shall notify the responsible officers and every citizen who reported the incident. | S | Officer and reporters receive a notification. | F29, F30 |

---

## 8. Authorities and routing (AGY)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-AGY-01 | Each authority shall have a name, type (e.g. campus estates, MTTD, NRSA, municipal assembly), one or more service areas drawn on a map, and the hazard categories it handles. | M | Admin can create "UG Estates" with the Legon campus area and all categories. | F23, M-03 |
| FR-AGY-02 | When an incident is verified, the system shall assign it to every authority whose service area contains its position and that handles its category. | M | Pothole inside the campus area → UG Estates; accident inside the area → MTTD if configured. | F16, S-05 |
| FR-AGY-03 | If no authority covers an incident, it shall still appear on the public map and in a "Not covered" list for admins. | M | Incident outside all areas is listed under "Not covered". | F16 |
| FR-AGY-04 | When service areas change, the system shall re-route open incidents to match the new areas. | S | Enlarging an area moves open incidents inside it to that authority. | F23 |

---

## 9. Authority dashboard (DSH)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-DSH-01 | An officer shall see only incidents routed to their own authority. | M | Officer of authority A cannot open an incident of authority B, even by changing the URL. | F18, A-02 |
| FR-DSH-02 | The dashboard shall show incidents both on a map and in a list, with the same filters applied to both. | M | Filtering to "Pothole" updates map and list together. | F18 |
| FR-DSH-03 | Officers shall filter by category, subtype, status, severity, date range and minimum number of reports, and sort by severity, number of reports, newest or oldest. | M | Each filter and sort works alone and combined. | F19, A-03 |
| FR-DSH-04 | The default list shall show open incidents sorted by severity, then number of reports. | M | Highest-severity, most-reported incident is first. | F19 |
| FR-DSH-05 | An incident page shall show: category, subtype, severity, status, map position, nearest road name (if known), all reports with blurred photos and descriptions, report count and full status history. | M | All items visible for a test incident. | F20, A-04 |
| FR-DSH-06 | Officers shall change status using only the allowed transitions (§7), and must add a note when resolving. | M | Resolve without a note is refused. | F21, A-05 |
| FR-DSH-07 | Officers should be able to assign an incident to a named colleague in the same authority. | S | Assignee shown on the incident and in the list. | F21 |
| FR-DSH-08 | When resolving, an officer should be able to add 1–3 "after" photos, which are blurred like citizen photos and shown next to the "before" photos. | S | Resolved incident shows before and after photos. | F35 |
| FR-DSH-09 | Officers should be able to export the current filtered list to CSV, with formula-injection protection. | S | CSV opens in a spreadsheet; cells starting with `=` are escaped. Already in the prototype. | F34, A-06 |
| FR-DSH-10 | The dashboard could show statistics for the officer's area: open incidents by category, average time from verified to resolved, and a hotspot heatmap. | C | Figures match a manual count on test data. | F39, F40, A-07 |
| FR-DSH-11 | The dashboard could send each authority a weekly email summary of new, open and resolved incidents. | C | Email received every Monday with correct counts. | F49 |

---

## 10. Maps and public views (MAP)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-MAP-01 | The app shall show a map of public incidents (Verified, Assigned, In progress, and Resolved for 7 days) around the citizen's location. | M | Rejected, expired and closed incidents never appear. | F8, C-22 |
| FR-MAP-02 | Each category shall have its own icon and colour; resolved incidents shall look clearly different (e.g. greyed with a tick). | M | Legend on the map explains every icon. | F8 |
| FR-MAP-03 | The citizen shall filter the map by category. | M | Turning off "Pothole" hides all pothole icons. | F8 |
| FR-MAP-04 | When zoomed out, nearby incidents shall group into a numbered cluster. | M | 50 incidents in one area show as clusters at city zoom. | F8 |
| FR-MAP-05 | Tapping an incident shall show its category, subtype, status, severity, how long ago it was first reported, the number of reports and a blurred photo. Reporter identity shall never be shown. | M | Detail card contains no name or phone number. | F8, privacy |
| FR-MAP-06 | A public web map with the same content as FR-MAP-01 to FR-MAP-05 should be available in a browser without signing in. | S | Map loads in a private browser window. | F38 |
| FR-MAP-07 | The map could offer a heatmap layer of hazard density. | C | Toggle shows heatmap. | F40 |

---

## 11. Citizen follow-up and notifications (NOT)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-NOT-01 | **My reports** shall list the citizen's reports, newest first, each with category, date, photo thumbnail and a plain-language status: Waiting to send · Received · Being checked · Confirmed · Assigned · Being fixed · Fixed · Not accepted · Expired. | M | Each internal status maps to exactly one plain label. | F7, C-20 |
| FR-NOT-02 | If a report is not accepted, My reports shall show a short reason (e.g. "Duplicate", "No hazard visible in photo", "Outside Ghana"). | M | Rejected test report shows its reason. | F7 |
| FR-NOT-03 | The app should send a push notification when the citizen's report is confirmed, assigned, and fixed. | S | Three notifications received for a report taken through those states. | F29, C-21 |
| FR-NOT-04 | Citizens shall be able to turn notifications on or off in settings. | S | With notifications off, none are received. | F29 |
| FR-NOT-05 | Officers should receive an email when a new severity-5 incident is routed to their authority. | S | Email received within 5 minutes of verification. | F29 |

---

## 12. Moderation (MOD)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-MOD-01 | Moderators shall have a queue of reports needing review, oldest first, showing the reason each is there (low AI confidence, no pothole detected, scene check failed, AI error, new traffic-light junction). | M | Each queue item states its reason. | F22, M-01 |
| FR-MOD-02 | For each report, a moderator shall be able to: **approve**, **reject** with a reason, **change category or subtype**, or **merge** into a chosen existing incident. | M | All four actions work and are recorded. | F22 |
| FR-MOD-03 | Moderators shall see the original (unblurred) photo, the AI result with boxes drawn on the photo, the position on a map and nearby open incidents. | M | All shown on the review screen. | F22 |
| FR-MOD-04 | Moderators should be able to block a citizen account for a set period or permanently, with a reason. Blocked accounts cannot send reports. | S | Blocked account's report is refused with a message. | F36, M-02 |
| FR-MOD-05 | Moderators should be able to approve a new traffic-light junction proposed by citizens, adding it to the junction list. | S | Approved junction appears in FR-REP-06 for other users. | F3 |
| FR-MOD-06 | Citizens whose last 10† reports were all approved could skip the moderation queue for low-confidence results (trust score). | C | Trusted user's 0.45-confidence report is verified automatically. | F46 |

---

## 13. Administration (ADM)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-ADM-01 | Admins shall create, edit and deactivate authorities and draw their service areas on a map. | M | Area drawn on the map is saved and used for routing. | F23, M-03 |
| FR-ADM-02 | Admins shall invite officers and moderators by email and choose their role and authority; and deactivate them. | M | Deactivated user cannot sign in. | F23 |
| FR-ADM-03 | Admins shall load and edit the list of known traffic-light junctions (name and position), including bulk import from a CSV file. | M | Importing 50 junctions from CSV adds 50 rows. | F3 |
| FR-ADM-04 | Admins could edit the hazard catalogue (categories, subtypes, merge radius, expiry, default severity, photo rule) without a code change. | C | Changing the breakdown expiry to 4 h takes effect for new reports. | F47, M-04 |
| FR-ADM-05 | Admins shall see a list of incidents not covered by any authority (FR-AGY-03). | M | List matches test data. | F16 |

---

## 14. Privacy, audit and abuse protection (PRV)

| ID | Requirement | Pri | Acceptance | Traces |
|---|---|:-:|---|---|
| FR-PRV-01 | Reporter phone numbers and names shall never be shown to visitors, other citizens or officers. | M | Inspecting public and officer API responses shows no reporter identity. | Privacy |
| FR-PRV-02 | A citizen shall be able to delete their account in the app. Their personal details shall be erased within 30 days; their reports stay as anonymous records. | M | After deletion, the phone number is not in the database; incidents still show report counts. | F9, C-02 |
| FR-PRV-03 | A citizen shall be able to download a copy of their account details and reports. | S | Download contains profile and all their reports. | F9 |
| FR-PRV-04 | Each citizen shall be limited to 10† reports per hour and 30 per day. | M | 11th report within an hour is refused with a message. | F24 |
| FR-PRV-05 | The system shall keep an audit log of sign-ins to the dashboard, status changes, moderation actions, blocks and admin changes, kept for at least 12 months and not editable by any role. | M | Each listed action creates an audit entry; no role can edit or delete entries. | F28 |
| FR-PRV-06 | Original (unblurred) photos shall be deleted 12 months† after their incident is closed or rejected. | S | Scheduled job removes originals past the limit. | Privacy |

---

## 15. Traceability: features → requirements

| Feature | Requirements |
|---|---|
| F1 Phone sign-in | FR-AUTH-01–05 |
| F2 Pothole report | FR-REP-01, 03, 08; FR-MED-01, 03 |
| F3 Traffic-light report | FR-REP-06; FR-MOD-05; FR-ADM-03 |
| F4 Other hazards | FR-REP-01; §2 catalogue |
| F5 Adjust pin | FR-REP-04, 05 |
| F6 Offline reporting | FR-REP-11–13 |
| F7 My reports | FR-NOT-01, 02 |
| F8 Hazard map | FR-MAP-01–05 |
| F9 Delete account | FR-AUTH-05; FR-PRV-02, 03 |
| F10 Retrained model | FR-AI-01, 09 |
| F11 AI photo check | FR-AI-01, 03, 05 |
| F12 Blurring | FR-AI-06; FR-MED-06 |
| F13 Duplicate merging | FR-INC-01, 02 |
| F14 Expiry | FR-INC-07 |
| F15 Location checks | FR-REP-05, 10 |
| F16 Routing | FR-AGY-02, 03; FR-ADM-05 |
| F17 Officer login | FR-AUTH-06–09 |
| F18 Incidents in my area | FR-DSH-01, 02 |
| F19 Filter and sort | FR-DSH-03, 04 |
| F20 Incident details | FR-DSH-05; FR-INC-03 |
| F21 Update status | FR-DSH-06, 07; FR-INC-05 |
| F22 Moderation queue | FR-MOD-01–03; FR-AI-03, 07 |
| F23 Admin setup | FR-ADM-01, 02; FR-AGY-01 |
| F24 Rate limits | FR-AUTH-03; FR-PRV-04 |
| F26 Load test | FR-REP-09; FR-AI-02 (and SRS Part 2) |
| F28 Audit log | FR-INC-06; FR-PRV-05 |
| F29 Push notifications | FR-NOT-03–05; FR-INC-09 |
| F30 Still there / fixed | FR-INC-08; FR-REP-14 |
| F31 Instant AI feedback | FR-AI-08 |
| F32 Description | FR-REP-07 |
| F33 Severity | FR-AI-04; FR-INC-04 |
| F34 CSV export | FR-DSH-09 |
| F35 "After" photo | FR-DSH-08 |
| F36 Block spam accounts | FR-MOD-04 |
| F37 Photo compression | FR-MED-02 |
| F38 Public web map | FR-MAP-06 |
| F39 / F40 Statistics, heatmap | FR-DSH-10; FR-MAP-07 |
| F46 Trust score | FR-MOD-06 |
| F47 Editable hazard types | FR-ADM-04 |
| F49 Weekly summary | FR-DSH-11 |

F25, F27 (security basics, monitoring) are non-functional and go in SRS Part 2. Nice-to-haves F41–F45 and F48 have no requirements yet; add them only if the team schedules them.

---

## Summary

| Area | Must | Should | Could | Total |
|---|:-:|:-:|:-:|:-:|
| AUTH | 9 | 0 | 0 | 9 |
| REP | 12 | 2 | 0 | 14 |
| MED | 6 | 1 | 0 | 7 |
| AI | 7 | 2 | 0 | 9 |
| INC | 7 | 2 | 0 | 9 |
| AGY | 3 | 1 | 0 | 4 |
| DSH | 6 | 3 | 2 | 11 |
| MAP | 5 | 1 | 1 | 7 |
| NOT | 2 | 3 | 0 | 5 |
| MOD | 3 | 2 | 1 | 6 |
| ADM | 4 | 0 | 1 | 5 |
| PRV | 4 | 2 | 0 | 6 |
| **Total** | **68** | **19** | **5** | **92** |

## Open questions for the team

1. **Pothole AI thresholds** (0.60 / 0.30): confirm after Nathaniel's model spike in week 2.
2. **Who handles traffic-light and accident reports in the pilot?** UG estates for campus roads, and MTTD if they agree? This sets the authority areas in FR-AGY-01.
3. **Where do the traffic-light junction locations come from?** OpenStreetMap, an authority's list, or our own survey of the pilot area?
4. **Is 2 "still there" votes enough to reopen a fixed incident** (FR-INC-08), or should moderators confirm?
5. **Photo retention** (12 months, FR-PRV-06): check against Data Protection Commission guidance in deliverable 7.
