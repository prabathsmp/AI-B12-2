# SlotEase — Appointment booking for clinics & salons

SlotEase is a multi-tenant micro-SaaS (₹499/month) for small clinics, salons and physio centres:

- **Customers book online in about 30 seconds.** They open a link like `/glow-salon`, pick a service, a date and a free slot, then confirm.
- **Owners run their day from one dashboard.**
- **Double bookings never happen.** The database itself refuses them.

> 📄 Docs: [PRD.md](PRD.md) (requirements) · [design.md](design.md) (architecture, flows, UI system)

---

## ✨ Features

| Customer (public page) | Owner (dashboard) |
|---|---|
| Mobile-first 3-step booking | **Today**: stats, up-next card, one-tap *Complete* / *No-show* / *Cancel* / *Undo* |
| Live free-slot grid (taken slots struck out, auto-refresh) | **Weekly calendar** with colour-coded statuses |
| Booking ID + confirmation message | **Services** CRUD (archive if a service has bookings) |
| WhatsApp click-to-chat + Add to Google Calendar | **Working hours** per weekday |
| Friendly "slot just taken" recovery (409) | **Walk-in / phone bookings** |
| | **Customers** history (visits, no-shows) |
| | **Stats**: bookings, no-show rate, revenue estimate, busiest day, charts, insights |
| | **Optional AI coach** and "Write with AI", using an OpenAI key pasted in Settings |

## 🧱 Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS 3, lucide-react, served by **nginx** |
| Backend | **FastAPI**, SQLAlchemy 2, PyJWT, bcrypt, httpx |
| Database | **PostgreSQL 16** |
| Auth | JWT (HS256) + bcrypt-hashed passwords |
| Notifications | SMTP e-mail (optional) + WhatsApp click-to-chat links |
| Deploy | Docker Compose (Docker Desktop) |

## 🚀 Run locally with Docker Desktop

**Prerequisite:** Docker Desktop is running.

```bash
# 1. Configure secrets (a ready-made .env with random secrets is already included;
#    otherwise:)
cp .env.example .env        # then edit POSTGRES_PASSWORD and JWT_SECRET

# 2. Build and start
docker compose up -d --build

# 3. Open
#   App ............ http://localhost:8080
#   Demo booking ... http://localhost:8080/glow-salon
#   API docs ....... http://localhost:8000/docs
```

**Demo logins** (seeded when `SEED_DEMO=true`):

| Business | Booking page | Owner login |
|---|---|---|
| Glow Salon | `/glow-salon` | `demo@slotease.app` / `demo1234` |
| CarePlus Physio | `/care-physio` | `physio@slotease.app` / `demo1234` |

Useful commands:
```bash
docker compose logs -f backend     # see booking confirmations being "sent"
docker compose down                # stop (data kept in volume pgdata)
docker compose down -v             # stop and wipe the database
```

### Run without Docker (development)
```bash
# DB: any Postgres; then
cd backend && pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/slotease   # (export on mac/linux)
uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev     # http://localhost:5173 (proxies /api → :8000)
```

## ✅ Verify the "Done checklist"

```bash
python scripts/acceptance_test.py              # against http://localhost:8080/api
```
It creates two fresh tenants and checks 24 things, including:
- **A race**: two threads book the same slot at the same instant, and exactly one gets `201` while the other gets `409 SLOT_TAKEN`.
- **Overlap refusal**: an overlapping start time is refused, and booking past closing time is refused.
- **Slot rules**: slots respect opening time, service duration and the 15-minute step.
- **Tenant isolation**: B cannot list, patch or edit A's data, or book A's page with B's service.
- **Status and stats**: status changes are reflected in the stats.
- **Cancellation**: cancelling frees the slot for re-booking.
- **AI without a key**: returns a clean `400`.

Last run: **24 passed, 0 failed.**

You can also show that the database alone refuses a duplicate:
```bash
docker compose exec db psql -U slotease -d slotease -c \
 "INSERT INTO appointments (business_id,service_id,customer_id,booking_ref,start_time,end_time,status,source,notes)
  SELECT business_id,service_id,customer_id,'DUP',start_time,end_time,'booked','online','' FROM appointments WHERE status<>'cancelled' LIMIT 1;"
# ERROR: duplicate key value violates unique constraint "uq_appointment_slot"
```

## 🗄️ Database tables

| Table | Key columns | Purpose / rules |
|---|---|---|
| `businesses` | id, name, **slug** (unique), phone, plan, category, address, timezone, created_at | One row per tenant |
| `users` | id, business_id, **email** (unique), password_hash, role | Owners who log in (bcrypt hash) |
| `services` | id, business_id, name, duration_min, price, description, is_active | e.g. *Haircut 30 min ₹300* |
| `working_hours` | id, business_id, weekday (0=Mon), open_time, close_time | Unique per (business, weekday). No row means closed |
| `customers` | id, business_id, name, phone, email | Unique (business, phone), which gives repeat-visit history |
| `appointments` | id, business_id, service_id, customer_id, booking_ref, start_time, end_time, status, source, notes | status ∈ `booked, completed, cancelled, no_show`. **`UNIQUE (business_id, start_time) WHERE status <> 'cancelled'`** |

Tables are created automatically on backend start (`Base.metadata.create_all`).

## 🔌 API endpoints

All routes are served at `/api/*` behind nginx, and directly on `:8000`. Swagger is at `/docs`.

| Method + path | Auth | Description |
|---|---|---|
| `POST /auth/register` | – | Create business + owner, returns JWT |
| `POST /auth/login` | – | Returns JWT |
| `GET /auth/me` | JWT | Current user + business |
| `GET /public/{slug}` | – | Business profile, open weekdays, today |
| `GET /public/{slug}/services` | – | Active services |
| `GET /public/{slug}/slots?service_id=&date=YYYY-MM-DD` | – | Slots (`available` true/false) |
| `POST /public/{slug}/bookings` | – | Create booking → **201** or **409 SLOT_TAKEN** |
| `GET /appointments?date=` / `?from=&to=` | JWT | Day / range list (with WhatsApp links) |
| `POST /appointments` | JWT | Walk-in booking |
| `PATCH /appointments/{id}` | JWT | `{status: booked\|completed\|cancelled\|no_show}` |
| `GET /services` · `POST /services` | JWT | List / create |
| `GET/PUT/DELETE /services/{id}` | JWT | Read / update / delete (archives if used) |
| `GET /working-hours` · `PUT /working-hours` | JWT | Weekly hours `{days:[{weekday,is_open,open_time,close_time}]}` |
| `GET /customers` | JWT | Customers with visits / no-shows |
| `GET /stats?month=YYYY-MM` | JWT | Bookings, no-show rate, revenue estimate, busiest day, charts, insights |
| `GET /business` · `PUT /business` | JWT | Business profile |
| `POST /ai/insights` | JWT + `X-OpenAI-Key` | Optional AI advice from monthly stats |
| `POST /ai/service-description` | JWT + `X-OpenAI-Key` | Optional AI service description |
| `GET /health` | – | Liveness (DB ping) |

**Sample: success**
```json
HTTP 201
{ "booking_id": "APT-20261010-0007", "service": "Haircut + Beard",
  "start_time": "2026-10-10T17:30:00+05:30", "end_time": "2026-10-10T18:15:00+05:30",
  "status": "booked", "message": "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM",
  "notification": "log", "whatsapp_link": "https://wa.me/91987..." }
```
**Sample: slot taken**
```json
HTTP 409
{ "error": "SLOT_TAKEN", "message": "This slot was just booked. Please pick another time." }
```

## 🤖 Optional OpenAI integration
The core product does not need an LLM. If an owner wants AI help:
1. Go to **Dashboard → Settings → AI features** and paste an OpenAI key (`sk-…`), then choose a model.
2. The key is stored **only in that browser** (localStorage) and is sent per request as `X-OpenAI-Key`. The server never stores or logs it.
3. This unlocks **AI business coach** on the Stats page (only aggregated numbers are sent, no names or phones) and **Write with AI** for service descriptions.

## ⚙️ Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | slotease / slotease / – | Database credentials (password **required**) |
| `JWT_SECRET` | – | Long random string used to sign tokens |
| `JWT_EXPIRE_MINUTES` | 720 | Token lifetime |
| `FRONTEND_PORT` / `BACKEND_PORT` | 8080 / 8000 | Host ports |
| `CORS_ORIGINS` | localhost:8080,5173 | Allowed origins (dev) |
| `DEFAULT_TIMEZONE` | Asia/Kolkata | New-business timezone |
| `SLOT_STEP_MINUTES` | 15 | Slot grid |
| `SEED_DEMO` | true | Seed demo tenants on first start |
| `SMTP_HOST` … `SMTP_FROM` | empty | Enables e-mail confirmations if set |

## 📁 Project structure
```
SlotEase/
├── docker-compose.yml   .env.example   .env (git-ignored)
├── PRD.md   design.md   README.md   requirements.docx
├── backend/
│   ├── Dockerfile   requirements.txt
│   └── app/
│       ├── main.py        # app, startup (create tables + seed under advisory lock)
│       ├── models.py      # 6 tables + constraints
│       ├── booking.py     # slot engine + race-safe booking
│       ├── security.py    # bcrypt + JWT
│       ├── notify.py      # e-mail / WhatsApp links
│       ├── seed.py        # demo tenants
│       └── routers/       # auth, public, owner, ai
├── frontend/
│   ├── Dockerfile   nginx.conf   tailwind.config.js
│   └── src/
│       ├── pages/Landing, AuthPage, Booking
│       ├── pages/dashboard/Layout, Today, Calendar, Services, Hours, Customers, Stats, Settings
│       └── components/ui.jsx, WalkInModal.jsx
└── scripts/acceptance_test.py
```

## 🔐 Security notes
- Passwords: bcrypt with 12 rounds. JWT: HS256 with expiry. A 401 response clears the session on the client.
- All secrets live in `.env`, which `.gitignore` excludes. The backend container runs as a non-root user.
- Every owner query is scoped by `business_id` from the token, and cross-tenant access returns 404.
- For a public deployment, put the stack behind HTTPS (e.g. Caddy or Traefik), set a strong `JWT_SECRET` and turn off `SEED_DEMO`.
