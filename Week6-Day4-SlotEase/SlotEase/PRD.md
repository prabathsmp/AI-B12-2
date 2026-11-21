# SlotEase — Product Requirements Document

| | |
|---|---|
| **Product** | SlotEase — appointment booking micro-SaaS |
| **Source** | `requirements.docx` (Track 4 · MicroSaaS · Frontend + Backend + Database) |
| **Business model** | ₹499 / month per business (tenant) |
| **Level / build time** | Intermediate · 4–5 days |
| **Status** | v1.0 implemented (this repository) |

---

## 1. Problem

Small clinics, salons and physiotherapy centres still take bookings by phone and WhatsApp. That causes:

- **Double bookings**: two customers get the same slot.
- **Lost bookings**: staff forget to write them down.
- **No record of no-shows**, so owners can't see how much money they lose.

These owners will pay a small monthly fee for a simple tool that fixes this.

## 2. Goals and non-goals

**Goals**
1. A customer can book in **about 30 seconds** from a phone, with no account.
2. Double booking is **impossible**, and the database itself enforces it.
3. An owner can **run the day from one screen**: today's list, one-tap Completed / No-show.
4. Each business is a **separate tenant**. No business can read or change another business's data.
5. **Simple stats** (bookings, no-show rate, revenue estimate, busiest day) that show the product's value.

**Non-goals (v1)**
- Online payments and billing collection (the ₹499 plan is shown in the app but not charged).
- Multiple staff calendars or resource scheduling (there is one calendar per business).
- Native mobile apps (the web app is mobile-first instead).
- Automated SMS or WhatsApp reminders through paid APIs (v1 uses click-to-chat links).

## 3. Personas

| Persona | Needs |
|---|---|
| **Owner / admin** (e.g. Glow Salon owner) | Sign up, set services and hours, share a link, see today's schedule, mark outcomes, understand the business |
| **Customer** (public) | Open link → pick service, date, free slot → enter name and phone → get confirmation |

## 4. User stories and acceptance criteria

### Customer (public booking page `/{slug}`)
| ID | Story | Acceptance criteria |
|---|---|---|
| C1 | As a customer I see the business name, address and services | Only **active** services of **that** business, with duration and price |
| C2 | I pick a date | Next 21 days shown; closed weekdays are disabled |
| C3 | I see the free slots for my service | Slots fall within working hours, step every 15 min, the full service duration fits before closing, overlaps with existing bookings are excluded, and past times are hidden |
| C4 | I confirm with name and phone (email optional) | `201` with booking ID `APT-YYYYMMDD-NNNN` and a friendly message |
| C5 | If someone else got my slot first, I am told clearly | `409 SLOT_TAKEN`; the UI shows a banner, refreshes the slots and lets me choose again |
| C6 | I can confirm with the business | WhatsApp click-to-chat link, plus an *Add to Google Calendar* link |
| C7 | It works well on my phone | Mobile-first layout, sticky action bar, large tap targets |

### Owner (dashboard `/dashboard`)
| ID | Story | Acceptance criteria |
|---|---|---|
| O1 | Sign up and log in | `POST /auth/register` creates the business, the owner and default hours (Mon–Sat 9–18), and returns a JWT. Passwords are hashed with bcrypt |
| O2 | See today's appointments | List sorted by time, with counts for bookings, completed, no-shows and estimated revenue, plus an "Up next" card |
| O3 | Mark Completed / No-show / Cancel / Undo | `PATCH /appointments/{id}`; the UI updates immediately |
| O4 | Weekly calendar | 7-day time grid with closed hours shaded and colour-coded by status. Click an appointment to see details and actions |
| O5 | Manage services | Create, edit, hide and delete. Deleting a service that has bookings archives it instead, so history is kept |
| O6 | Set working hours | Toggle each day open or closed and set open and close times; copy Monday to Saturday |
| O7 | Add phone or walk-in bookings | Uses the same slot engine and the same 409 protection |
| O8 | See monthly stats | Bookings, no-show rate, revenue estimate, busiest day, peak hour, daily and weekday charts, top services, repeat customers, rule-based insights |
| O9 | Customer history | Customer list with visits, no-shows and last visit, plus call and WhatsApp buttons |
| O10 | (Optional) AI coach | Owner pastes an **OpenAI API key in Settings**. This enables AI advice on the Stats page and "Write with AI" for service descriptions. Without a key everything else works |

## 5. Functional requirements

### 5.1 Slot calculation
```
slots(date, service) =
  for t from open_time step 15min while t + duration <= close_time:
      if t > now and no live appointment overlaps [t, t+duration): free
```
- "Live" means any status other than `cancelled`.
- The timezone is set per business (default `Asia/Kolkata`). All slot maths happens in the business's local time.

### 5.2 Booking and double-booking protection (defence in depth)
1. **Tenant row lock**: `SELECT … FROM businesses WHERE id=? FOR UPDATE` serialises concurrent bookings for one business.
2. **Validation**: the time must be within hours, aligned to the 15-min grid, in the future and not overlapping.
3. **Database rule**: a partial unique index `uq_appointment_slot (business_id, start_time) WHERE status <> 'cancelled'`. Any `IntegrityError` becomes `409 SLOT_TAKEN`. Cancelled rows free the slot so it can be booked again.

### 5.3 Notifications
- Confirmation is shown on screen with the booking ID.
- An email is sent if SMTP is configured and the customer gave an email. Otherwise the confirmation is logged.
- WhatsApp click-to-chat links go customer→business (after booking) and business→customer (on the dashboard).

### 5.4 Multi-tenancy
- The JWT carries `sub` (user) and `bid` (business). Every owner query filters on `business_id = token.bid`.
- Accessing another tenant's resource returns **404**, not 403, so the API doesn't reveal that the resource exists.
- Public endpoints resolve the tenant from the `slug`, and services are checked against that tenant.

## 6. Data model (PostgreSQL, 6 tables)

| Table | Key columns | Notes |
|---|---|---|
| `businesses` | id, name, **slug (unique)**, phone, plan, category, address, timezone, created_at | One row per tenant |
| `users` | id, business_id → businesses, **email (unique)**, password_hash (bcrypt), role | Owners/staff |
| `services` | id, business_id, name, duration_min (>0), price, description, is_active | |
| `working_hours` | id, business_id, weekday 0–6, open_time, close_time | unique (business_id, weekday); close > open; no row = closed |
| `customers` | id, business_id, name, phone, email | unique (business_id, phone) → repeat-visit history |
| `appointments` | id, business_id, service_id, customer_id, booking_ref, start_time, end_time, status, source, notes | status ∈ booked/completed/cancelled/no_show; **unique (business_id, start_time) where status ≠ cancelled** |

## 7. API (summary)

| Method + path | Caller | Purpose |
|---|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Owner | Account + JWT |
| `GET /public/{slug}` | Customer | Business profile + open weekdays |
| `GET /public/{slug}/services` | Customer | Active services |
| `GET /public/{slug}/slots?service_id&date` | Customer | Slots with `available` flag |
| `POST /public/{slug}/bookings` | Customer | Create booking (201 / 409) |
| `GET /appointments?date=` or `?from=&to=` | Owner | Day or week list |
| `POST /appointments` | Owner | Walk-in booking |
| `PATCH /appointments/{id}` | Owner | Change status |
| `GET/POST /services`, `GET/PUT/DELETE /services/{id}` | Owner | Services CRUD |
| `GET/PUT /working-hours` | Owner | Weekly hours |
| `GET /customers` | Owner | Customer history |
| `GET /stats?month=YYYY-MM` | Owner | Monthly stats + insights |
| `GET/PUT /business` | Owner | Profile |
| `POST /ai/insights`, `POST /ai/service-description` | Owner | Optional, requires `X-OpenAI-Key` header |

Errors are always returned as `{"error": "CODE", "message": "human text"}`.

## 8. Non-functional requirements
- **Security**: bcrypt (12 rounds); HS256 JWT with expiry; secrets in `.env` (git-ignored); CORS allow-list; container runs as non-root user. The OpenAI key is never stored server-side.
- **Performance**: slot computation is one query per day, and owner lists use joined loads.
- **Usability**: dark "aurora" theme with high-contrast text (slate-100 on ink-950) and colour plus a label for every status. Mobile-first booking flow, and reduced-motion is respected.
- **Deployability**: `docker compose up -d --build` gives db, backend and frontend (nginx) on Docker Desktop, with health checks and a persistent volume.

## 9. Success metrics
- Booking completion rate (page opened → booking created).
- No-show rate trend per business (target: under 8%).
- Monthly retention of paying businesses.

## 10. Done checklist (from the requirement), with how it is verified
| Requirement | Verified by |
|---|---|
| Two browsers booking the same slot at the same time: one 201, one 409 | `scripts/acceptance_test.py` (threaded race) |
| Business A can't read or change Business B's data | acceptance test: list/patch/edit/cross-book checks |
| Slots respect hours, duration and bookings | acceptance test: first/last slot, blocked range |
| Booking page works on mobile | responsive layout, sticky bar, tested at phone width |
| Passwords hashed, secrets in `.env`, deployable | bcrypt `$2b$12$…`, `.env`, Docker Compose |
| README covers setup, tables and endpoints | `README.md` |

## 11. Future scope
Razorpay subscription billing · staff-level calendars · automated reminders (Twilio WhatsApp) · customer self-cancel link · Google Calendar sync · multi-location tenants.
