# 01 · Project Charter

> Owner: Kelly Buabeng · Status: DRAFT for team review · Based on the submitted funding proposal (GHS 60,000, 6 months)

## 1. Project

**Name:** National Road Hazard Reporting Platform (Pothole Detection v2)
**Sponsor / partner:** Department of Computer Science, University of Ghana (Dr Prince Ansah)
**Funding:** GHS 60,000 (government youth fund, application submitted)
**Duration:** 6 months of build and pilot, after this 3-week planning stage

## 2. Purpose

Give road users in Ghana one simple, trusted way to report road hazards from their exact location, and get each report to the authority that can fix it.

## 3. Starting point

We already have a working pothole detection prototype (our University of Ghana final-year project). It is ready for demonstration:

- A YOLOv8 model we trained to detect potholes in road photos (569 training images).
- A FastAPI backend that receives a photo and GPS position, runs the model, and stores confirmed potholes in PostgreSQL/PostGIS.
- Ghana location check, heatmap and statistics data, reports, CSV export, API-key security and automated tests.

Version 2 keeps what the prototype proved and rebuilds the rest for public use.

## 4. Objectives (what "done" means at month 6)

| # | Objective | Measure |
|---|---|---|
| O1 | A more accurate pothole model | ≥ 85% recall at IoU 0.5 on a Ghana-only test set the model never trained on |
| O2 | Citizens can report all three hazard types | Android app live for pilot users: pothole, faulty traffic light, other hazard |
| O3 | Authorities can act on reports | Web dashboard where an authority sees reports in its area and marks them fixed |
| O4 | The system holds up under load | Load test passes with ≥ 200 simultaneous users |
| O5 | Real-world pilot | Pilot running with the University of Ghana community |
| O6 | National authority engagement | ≥ 1 of NRSA, MTTD or Ministry of Transport has seen a demo and agreed next steps |

## 5. Scope

**In scope (6 months)**

- Retrained AI model using public road-damage data plus our own photos of Ghanaian roads.
- Android app: phone-number sign-in, report with photo and exact GPS position, 3 hazard types, "my reports" with status, offline queueing.
- Public map of active hazards.
- Authority web dashboard: area-based list and map, status updates (assigned, in progress, fixed).
- Merging of duplicate reports, automatic expiry of short-lived hazards, face and number-plate blurring, basic moderation.
- Pilot with the UG community; demos for NRSA, MTTD and the Ministry of Transport.

**Out of scope for now (later phases, if funded)**

- iOS app.
- USSD and WhatsApp reporting.
- Push alerts for hazards near the user while driving (the public map covers this need for now).
- Passive dashcam mode and on-device AI.
- Nationwide rollout and integration with authorities' own systems.

## 6. Constraints

- **Budget:** GHS 60,000 total, no stipends. Cloud and AI training are capped at GHS 16,000 (about GHS 2,650 per month), so the architecture must run on small, low-cost servers.
- **Time:** 6 months.
- **People:** 3 team members, part of whose time may go to other commitments.
- **Law:** Data Protection Act, 2012 (Act 843). We must register with the Data Protection Commission before collecting user data.

## 7. Assumptions

- The grant is approved at, or close to, GHS 60,000.
- The UG Department of Computer Science provides supervision, pilot access and, if possible, computing resources.
- Public datasets (RDD2022 and others) can be used under their licences; to be confirmed in deliverable 4.
- Pilot testers can be recruited from UG students and staff.

## 8. Roles

| Person | Role | Main responsibilities |
|---|---|---|
| Kelly Buabeng | Team lead, backend, project manager | Planning, budget, stakeholders, API and database, deployment |
| Nathaniel Addo | AI / ML developer | Datasets, labelling, model training and evaluation, ML worker |
| Seth Akoto | Frontend and UX developer | Research with users, wireframes, Android app, public map, dashboard |
| Dr Prince Ansah | Partner and supervisor (UG Computer Science) | Guidance, reviews, pilot support |

## 9. Milestones

| Milestone | Target |
|---|---|
| Planning & feasibility review with Dr Ansah | Fri 4 Dec 2026 |
| Build month 2: improved model + platform foundations | ~end of Feb 2027* |
| Build month 4: Android test version with volunteer testers | ~end of Apr 2027* |
| Build month 6: pilot running, authority demos, results report | ~end of Jun 2027* |

\* Build dates depend on when funds arrive. They move together if the start slips.

## 10. Approval

| Name | Role | Decision | Date |
|---|---|---|---|
| Kelly Buabeng | Team lead | | |
| Nathaniel Addo | AI / ML | | |
| Seth Akoto | Frontend / UX | | |
| Dr Prince Ansah | Partner | | |
