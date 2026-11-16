# Feature List: Must-haves, Nice-to-haves and Later

> Owner: Kelly Buabeng (with Seth and Nathaniel) · Status: DRAFT for team review
> Detailed user stories are in [03-requirements.md](03-requirements.md); story IDs are shown in brackets.

**How to read this**

| Tier | Meaning | Rule |
|---|---|---|
| 🔴 **Must have** | The 6-month pilot fails or breaks a promise in the proposal without it | Built first. Cutting one needs a team decision recorded in `decisions.md` |
| 🟠 **Should have** | Important and expected, but the pilot still works without it | Built once the must-haves work |
| 🟢 **Nice to have** | Improves the experience; cheap wins if time allows | Only in spare time, or if a must-have finishes early |
| ⚪ **Later** | Valuable, but outside the GHS 60k / 6-month scope | Kept for the next funding round |

---

## 🔴 Must have (pilot launch)

### Citizen app (Android)

| # | Feature | Why it's a must |
|---|---|---|
| F1 | **Phone number sign-in** with an SMS code (C-01) | Stops fake accounts; no passwords for users to forget |
| F2 | **Report a pothole** with an in-app photo and automatic GPS location (C-10) | The core promise; the prototype already proves it |
| F3 | **Report a faulty traffic light**: pick the junction on a map, then the fault (all out, stuck on red, flashing, damaged pole) (C-12) | Promised in the proposal |
| F4 | **Report other road hazards**: broken-down vehicle, accident, flooding, fallen tree, missing drain or manhole cover, damaged sign, pedestrian danger (C-13) | Promised in the proposal |
| F5 | **Adjust the pin** if the GPS position is slightly wrong (C-11) | "Exact location" is the whole point |
| F6 | **Offline reporting**: reports are saved and sent when signal returns (C-15) | Patchy signal is normal on many roads |
| F7 | **My reports**: a list with the status of each report (C-20) | Citizens stop reporting if they never hear back |
| F8 | **Hazard map** of active hazards nearby, filtered by type (C-22) | Promised in the proposal ("public map") |
| F9 | **Delete my account and data** (C-02) | Required by the Data Protection Act |

### AI and processing

| # | Feature | Why it's a must |
|---|---|---|
| F10 | **Retrained pothole model**, using public data plus Ghana road photos | Success target: ≥ 85% of potholes found |
| F11 | **Automatic check of every pothole photo**, with confidence and estimated size | Filters out bad and fake reports |
| F12 | **Face and number-plate blurring** before photos are shown (S-03) | Privacy; required before any photo is public |
| F13 | **Duplicate merging**: reports of the same hazard nearby become one incident (S-01) | Without it, authorities see ten tickets for one pothole |
| F14 | **Automatic expiry** of short-lived hazards unless re-confirmed (S-02) | Stops the map filling with stale breakdowns and accidents |
| F15 | **Location checks**: reject reports outside Ghana or with very poor GPS (S-04) | Already in the prototype; keep it |
| F16 | **Routing**: each incident goes to the authority whose area contains it (S-05) | Reports must reach someone who can act |

### Authority dashboard (web)

| # | Feature | Why it's a must |
|---|---|---|
| F17 | **Secure officer login** with a second factor (A-01) | Officers can change public data |
| F18 | **Incidents in my area**, on a map and in a list (A-02) | Promised in the proposal |
| F19 | **Filter and sort** by type, severity, status and number of reports (A-03) | Officers need to see the worst problems first |
| F20 | **Incident details**: blurred photos, location, report count, history (A-04) | Enough to decide and dispatch |
| F21 | **Update status**: assigned → in progress → fixed, with a note (A-05) | Closes the loop for citizens |

### Moderation and admin

| # | Feature | Why it's a must |
|---|---|---|
| F22 | **Moderation queue** for reports the AI wasn't sure about: approve, reject or merge (M-01) | Keeps spam and mistakes off the map |
| F23 | **Admin setup**: create authorities, draw their areas, invite officers (M-03) | Needed to onboard UG estates, MTTD and others |

### Platform, security and quality

| # | Feature | Why it's a must |
|---|---|---|
| F24 | **Rate limits** on reporting and login | Stops abuse and SMS cost blow-ups |
| F25 | **HTTPS everywhere**, secrets kept out of code, daily database backups | Basic security for public data |
| F26 | **Load tested for ≥ 200 simultaneous users** | Success target in the proposal |
| F27 | **Error monitoring** for the app and server | So we find problems before users tell us |
| F28 | **Audit log** of every status change by officers and moderators | Accountability and trust |

---

## 🟠 Should have

| # | Feature | Area | Notes |
|---|---|---|---|
| F29 | **Push notifications** when my report is confirmed, assigned and fixed (C-21) | App | Free with Firebase; big boost to trust |
| F30 | **"Still there" / "Fixed" buttons** on nearby incidents (C-17) | App | Fewer duplicate reports; confirms fixes |
| F31 | **Instant AI feedback**: "We couldn't see a pothole, retake the photo?" (C-16) | App + AI | Improves photo quality |
| F32 | **Short description** on a report (C-14) | App | Context the photo can't give |
| F33 | **Severity rating** (1–5) estimated by the AI and shown to officers | AI + dashboard | Helps officers prioritise |
| F34 | **CSV export** of incidents (A-06) | Dashboard | Already in the prototype; officers like spreadsheets |
| F35 | **"Fixed" photo**: the officer adds an after photo when closing an incident | Dashboard | Proves the repair happened; good for demos to NRSA and the Ministry |
| F36 | **Block spam accounts** (M-02) | Moderation | |
| F37 | **Photo compression** to ≤ 500 KB before upload | App | Saves users' data bundles and our storage costs |
| F38 | **Public web map** in a browser, not only in the app | Web | Authorities and the press can see it without installing anything |

---

## 🟢 Nice to have

| # | Feature | Area | Notes |
|---|---|---|---|
| F39 | **Dashboard statistics**: open incidents, average time to fix, hotspots (A-07) | Dashboard | Strong for authority demos; partly in the prototype (heatmap, stats) |
| F40 | **Heatmap view** of where hazards cluster | Map | Prototype already has heatmap data |
| F41 | **Local languages**: Twi first, then others | App | Wider reach beyond campus |
| F42 | **Voice note** instead of typing a description | App | Helps drivers who can't type safely |
| F43 | **Share a report** link on WhatsApp or social media | App | Free publicity; pressure for repairs |
| F44 | **Emergency shortcut** on accident reports to call the emergency numbers (112, police 191, ambulance 193) | App | Safety; confirm the numbers before release |
| F45 | **Reporter points and badges** for verified reports | App | Encourages good reporting; can also feed the trust score |
| F46 | **Trust score**: reports from reliable users skip moderation | Moderation | Less moderator work as the pilot grows |
| F47 | **Editable hazard types** without changing code (M-04) | Admin | |
| F48 | **Dark mode** and a large-text option | App | Accessibility, battery |
| F49 | **Weekly email summary** for each authority | Dashboard | Keeps officers engaged without logging in |

---

## ⚪ Later (next phase, outside this funding)

| # | Feature | Why later |
|---|---|---|
| F50 | **iOS app** | Proposal promises Android only; adds Apple fees and testing time |
| F51 | **Alerts near me while driving** (C-23) | Needs background location; battery, privacy and safety work |
| F52 | **USSD reporting** for feature phones | Needs a telco or aggregator agreement and costs per session |
| F53 | **WhatsApp reporting bot** | WhatsApp Business API costs; moderation load |
| F54 | **Passive dashcam mode**: the phone detects potholes automatically while driving | Needs an on-device model and heavy testing |
| F55 | **On-device AI** for instant offline detection | Model size and phone performance work |
| F56 | **Road condition score** for each road, and repair priority predictions | Needs months of data first |
| F57 | **Open data API** for researchers, planners and navigation apps | After the data and privacy rules are proven |
| F58 | **Integration with authorities' own systems** | Depends on formal agreements with NRSA, MTTD and others |
| F59 | **Public accountability board**: response times per authority | Politically sensitive; only with authority agreement |
| F60 | **Nationwide rollout** to all regions and assemblies | Needs follow-on funding and authority partnerships |

---

## Summary

| Tier | Count | Fits in 6 months? |
|---|---|---|
| 🔴 Must have | 28 | Yes: this is the pilot |
| 🟠 Should have | 10 | Most of them, from month 4 |
| 🟢 Nice to have | 11 | A few, in spare time |
| ⚪ Later | 11 | No: next funding round |

**Already partly built in the prototype:** F2 and F11 (pothole photo + AI check), F15 (Ghana location check), F34 (CSV export), F39 and F40 (statistics and heatmap data).
