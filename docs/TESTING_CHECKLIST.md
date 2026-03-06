# Full Project Testing Checklist — Office Workplace Intelligence Platform

**For group members who have Firebase credentials.** Use this checklist to test the entire project end-to-end. Tick off each step as you complete it; note any failures and report them using the bug report section at the end.

---

## Before You Start — Setup (Everyone)

Do this once so that **real Firebase data** is used and actions (approve, check-in, check-out, blacklist) persist.

### 1. Prerequisites

- [ ] **Python 3.8+** installed
- [ ] **Firebase credentials**: `firebase_credentials.json` from your project lead or Firebase Console (Project Settings → Service Accounts → Generate New Private Key)
- [ ] **Place the file** in all three app folders:
  - `Admin/firebase_credentials.json`
  - `Register_App/firebase_credentials.json`
  - `Webcam/firebase_credentials.json`
- [ ] **Dependencies installed** (from project root):
  ```bash
  pip install -r Register_App/requirements.txt
  pip install -r Admin/requirements.txt
  pip install -r Webcam/requirements.txt
  ```
- [ ] **Model files** (for registration and webcam): see [TESTING_GUIDE.md](TESTING_GUIDE.md) — `shape_predictor_68_face_landmarks.dat` and `dlib_face_recognition_resnet_model_v1.dat` in `Register_App/` and `Webcam/`

### 2. Use real Firebase (not mock data)

- [ ] In **Admin**: set `USE_MOCK_DATA=False` in `Admin/.env` (or create `.env` with that line).  
  If you omit this, the Admin app will use mock data and **approve/check-in/check-out/blacklist will not persist** in Firebase.
- [ ] In **Register_App** and **Webcam**: ensure they use Firebase (no mock mode, or follow existing .env in repo).

### 3. Start all three apps

Use **3 terminals** (or split among group members):

| Terminal | Directory    | Command      | URL                    |
|----------|--------------|-------------|------------------------|
| 1        | `Register_App` | `python app.py` | http://localhost:5001 |
| 2        | `Admin`        | `python app.py` | http://localhost:5000 |
| 3        | `Webcam`       | `python app.py` | http://localhost:5002 |

- [ ] All three start without errors. Admin should log something like “Using REAL data” (not “Using MOCK DATA”) if you set `USE_MOCK_DATA=False`.

Detailed setup (env vars, Firebase rules, model files) is in [TESTING_GUIDE.md](TESTING_GUIDE.md).

---

## Part A — Registration & Gate (Register_App + Webcam)

### A1. Registration (Register_App — http://localhost:5001)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| A1.1 | Open http://localhost:5001 | Home/landing page loads | |
| A1.2 | Start new registration (e.g. “Register as New Visitor” or open invite link with `?token=...`) | Registration form appears | |
| A1.3 | Fill name, email, purpose, visit date; select meeting room if shown | Fields accept input; room dropdown works if present | |
| A1.4 | Capture/upload photo (webcam or file) | Photo captured or uploaded | |
| A1.5 | Submit registration | Success message; QR code shown; redirect or confirmation | |
| A1.6 | (If invite flow) Open registration link from email | Same form or pre-filled; submit works | |

**Edge cases:** Invalid token → clear error. Missing required fields → validation message.

### A2. Gate — Check-in (Webcam — http://localhost:5002)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| A2.1 | Open gate URL (e.g. http://localhost:5002 or /checkin_gate) | Gate / check-in page loads | |
| A2.2 | Use QR from registration + face in front of camera (hybrid mode) | “Access Granted” or check-in success; check-in time recorded | |
| A2.3 | (If QR-only mode) Scan valid QR only | Check-in succeeds per mode | |
| A2.4 | (If face-only mode) Face only | Check-in succeeds per mode | |

### A3. Gate — Check-out (Webcam)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| A3.1 | At gate, use same visitor (QR + face or per mode) for check-out | “Checkout successful”; check_out_time set; time spent calculated | |
| A3.2 | Verify in Admin (see Part B): visitor status = Checked Out | Status and times match in Admin | |

**Optional:** Security scenarios (QR mismatch, stolen QR) are in [TESTING_GUIDE.md](TESTING_GUIDE.md) Step 7.

---

## Part B — Admin Dashboard (Full Walkthrough)

Base URL: **http://localhost:5000**

### B1. Admin Home (`/`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B1.1 | Open http://localhost:5000 | Admin home with cards: Dashboard, Visitors, Rooms, Blacklist, Feedback, Employees, Upload Invitations | |
| B1.2 | Click each card | Each goes to the correct page | |

### B2. Dashboard (`/dashboard`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B2.1 | Click Dashboard | Metrics, charts, filters load | |
| B2.2 | Check “Currently Active” (occupancy) | Shows number; updates automatically (e.g. every 5 s) or on refresh | |
| B2.3 | Change time/date filters (e.g. Today, custom range) | Charts and counts update | |
| B2.4 | Check occupancy-over-time (if present) | Chart or table shows trend for selected period | |
| B2.5 | Check predictions (if present) | Peak time / visitor forecast or “no data” | |
| B2.6 | Click “Back to Admin” | Returns to Admin home | |
| B2.7 | Click “View Visitors” | Goes to /visitors | |

### B3. Visitors List (`/visitors`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B3.1 | Open Visitors | Table with Visitor ID, Details, Purpose, Status, Visits, Blacklist, **Actions** | |
| B3.2 | Search by name | List filters to matching names | |
| B3.3 | Filter by status (e.g. Registered, Approved, Checked In) | Only that status shown | |
| B3.4 | Set date range + time range, click Apply | List updates; Clear resets | |
| B3.5 | Pagination | Next/Previous or page numbers work; “Showing X to Y of Z” correct | |
| B3.6 | **Approve**: for a *Registered* visitor, click green check (Approve) | Status becomes Approved; page reloads with new status | |
| B3.7 | **Check-in**: for an *Approved* visitor, click check-in icon | Status becomes Checked In; occupancy increases | |
| B3.8 | **Check-out**: for a *Checked In* visitor, click check-out icon | Status becomes Checked Out | |
| B3.9 | **Reject**: for *Registered*, click red X (Reject), enter reason | Status becomes Rejected | |
| B3.10 | **Blacklist**: toggle blacklist checkbox (or similar); enter reason if asked | Visitor appears on Blacklist page | |
| B3.11 | Export CSV | File downloads with visitor data | |
| B3.12 | Click a visitor ID / row | Visitor detail page opens | |
| B3.13 | Click “Back to Admin” | Returns to Admin home | |

### B4. Visitor Detail (`/visitor/<id>`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B4.1 | Open from Visitors list (click visitor ID) | Full profile: name, contact, status, timeline, visits | |
| B4.2 | Use any status action (e.g. Check-in, Check-out) if shown | Status updates; UI reflects it | |
| B4.3 | Click “Back to Visitors” | Returns to /visitors | |
| B4.4 | Open invalid ID (e.g. /visitor/invalid123) | 404 or clear error, no crash | |

### B5. Rooms (`/rooms`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B5.1 | Open Rooms | Room list (table or card grid) with name, capacity, floor, amenities | |
| B5.2 | **Add Room**: click “Add Room”, fill name, capacity, floor, amenities, Save | New room appears in list | |
| B5.3 | **Edit Room**: click Edit on a room, change fields, Save | Room updates in list | |
| B5.4 | **Delete Room**: click Delete, confirm | Room removed from list | |
| B5.5 | If **search** is present: type in search box | List filters by name/floor/amenities | |
| B5.6 | If **Book slot** is present: open Book, choose date and time, submit | Booking created; “Next booking” or schedule updates | |
| B5.7 | If **View schedule** is present: open for a room | Modal/page shows list of bookings for that room | |
| B5.8 | If **room status** (Available/Occupied) is shown: check-in a visitor with that room | Room shows Occupied; after check-out, shows Available | |
| B5.9 | Click “Back to Admin” | Returns to Admin home | |

### B6. Blacklist (`/blacklist`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B6.1 | Open Blacklist | List of blacklisted visitors (or “No blacklisted individuals”) | |
| B6.2 | Click “View full profile” on one | Visitor detail page opens | |
| B6.3 | Click “Remove from blacklist” | Visitor removed; list updates (or redirect); visitor no longer on blacklist | |
| B6.4 | Pagination (if multiple pages) | Previous/Next work | |
| B6.5 | Click “Back to Admin” / “Admin Home” | Returns to Admin home | |

### B7. Feedback Analysis (`/feedback-analysis`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B7.1 | Open Feedback Analysis | Sentiment summary (Positive/Neutral/Negative) and feedback list/table | |
| B7.2 | Check counts | Match stored feedback or show zeros; no crash if no data | |
| B7.3 | Click “Back to Admin” | Returns to Admin home | |

### B8. Employees (`/employees`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B8.1 | Open Employees | Employee list/table with name, department, role, visitor count, etc. | |
| B8.2 | **Edit**: click pencil (Edit) on a row | Modal opens with that employee’s data; Save updates (with Firebase, data persists) | |
| B8.3 | **View visitors**: click eye icon | New tab/page opens with “Visitors for &lt;name&gt;” and list of linked visitors | |
| B8.4 | **Delete**: click delete, confirm | Employee removed (with Firebase); list updates | |
| B8.5 | **Add Employee**: click Add, fill form, Save | New employee appears (with Firebase) | |
| B8.6 | Search/filter (if present) | List filters correctly | |
| B8.7 | Export CSV (if present) | File downloads | |
| B8.8 | Click “Back to Admin” | Returns to Admin home | |

### B9. Upload Invitations (`/upload_invitations`)

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B9.1 | Open Upload Invitations | Upload form / UI loads | |
| B9.2 | Upload valid Excel (.xlsx/.xls) with an “Email” column | Success message; invitations sent or listed (if email is configured) | |
| B9.3 | Upload invalid file (wrong type or no Email column) | Clear error message | |
| B9.4 | Click “Back to Home” / back link | Returns to Admin home | |

### B10. Cross-cutting

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| B10.1 | On every Admin sub-page, use “Back to Admin” or “Back to Visitors” | Correct previous page | |
| B10.2 | Refresh key pages (Dashboard, Visitors, Rooms) | No broken layout; data reloads | |
| B10.3 | Use date/time filters on Dashboard and Visitors | No console errors; results make sense | |

---

## Part C — End-to-End Flow (Full Project)

Run this once to confirm the full pipeline with Firebase.

| Step | Action | Expected | ✓ |
|------|--------|----------|---|
| C1 | **Register** a new visitor (Register_App, http://localhost:5001) with name, email, room, photo | QR code; record in Firebase | |
| C2 | Open **Admin** → Visitors | New visitor appears as Registered (or Pending) | |
| C3 | In Admin, **Approve** that visitor | Status → Approved | |
| C4 | In Admin, **Check-in** that visitor | Status → Checked In; Dashboard “Currently Active” increases | |
| C5 | (Optional) At **Webcam** gate, perform check-in/check-out with QR + face | Gate shows success; Admin status/times stay in sync | |
| C6 | In Admin, **Check-out** that visitor | Status → Checked Out; occupancy decreases | |
| C7 | In Admin, **Blacklist** that visitor (toggle on in Visitors) | Visitor appears on Blacklist page | |
| C8 | Open Blacklist, **Remove from blacklist** | Visitor removed from blacklist list | |
| C9 | Open **Visitor detail** from Visitors list | Full profile and history correct | |

---

## How to Report Bugs

When something fails, include:

1. **Steps to reproduce** — Numbered list (e.g. “1. Go to /visitors 2. Click Approve on first row 3. Page reloads”).  
2. **Expected result** — What should happen.  
3. **Actual result** — What happened (error message, wrong data, no change).  
4. **URL and environment** — Full URL, query params; browser and version (e.g. Chrome 120).  
5. **Screenshot or error** — Console error, HTTP status, or UI message.  
6. **Data context** — e.g. “Only one visitor in DB,” “USE_MOCK_DATA=False,” “Firebase credentials in Admin and Register_App.”

Save reports in your shared doc or issue tracker and tag by area (e.g. Visitors, Rooms, Register_App, Webcam).

---

*Last updated: March 2025*
