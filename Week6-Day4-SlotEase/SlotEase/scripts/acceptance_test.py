"""SlotEase acceptance test - verifies the PRD "Done checklist" against a running stack.

Usage:  python scripts/acceptance_test.py [base_url]     (default http://localhost:8080/api)
Only the standard library is used.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/api").rstrip("/")
PASS, FAIL = 0, 0


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def check(name, cond, extra=""):
    global PASS, FAIL
    PASS, FAIL = (PASS + 1, FAIL) if cond else (PASS, FAIL + 1)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{' - ' + extra if extra and not cond else ''}")


def main():
    tag = uuid.uuid4().hex[:6]
    print(f"SlotEase acceptance test against {BASE}\n")

    # --- Setup: two fresh tenants ---
    s, a = call("POST", "/auth/register", {"business_name": f"Test Salon A {tag}", "email": f"a-{tag}@test.dev", "password": "password123", "phone": "9000000001"})
    s2, b = call("POST", "/auth/register", {"business_name": f"Test Clinic B {tag}", "email": f"b-{tag}@test.dev", "password": "password123"})
    check("Owner sign-up returns JWT (201)", s == 201 and s2 == 201 and "access_token" in a, str(a))
    ta, tb, slug_a = a["access_token"], b["access_token"], a["business"]["slug"]

    s, _ = call("POST", "/auth/login", {"email": f"a-{tag}@test.dev", "password": "wrong-password"})
    check("Wrong password rejected (401)", s == 401)

    # Open every day 10:00-14:00 so the test is weekday-independent
    days = [{"weekday": d, "is_open": True, "open_time": "10:00", "close_time": "14:00"} for d in range(7)]
    s, _ = call("PUT", "/working-hours", {"days": days}, token=ta)
    check("PUT /working-hours", s == 200)
    s, svc = call("POST", "/services", {"name": "Haircut + Beard", "duration_min": 45, "price": 400}, token=ta)
    check("POST /services", s == 201)
    _, svc_b = call("POST", "/services", {"name": "Consult", "duration_min": 30, "price": 500}, token=tb)

    # --- Slots respect hours, duration and bookings ---
    day = (date.today() + timedelta(days=3)).isoformat()
    s, sl = call("GET", f"/public/{slug_a}/slots?service_id={svc['id']}&date={day}")
    labels = [x["label"] for x in sl["slots"]]
    check("Slots start at opening time (10:00)", labels[:1] == ["10:00"], str(labels[:3]))
    check("Last slot leaves room for 45 min before 14:00 (13:15)", labels[-1:] == ["13:15"], str(labels[-3:]))
    check("Slots step every 15 minutes", len(labels) == 14, str(len(labels)))

    target = sl["slots"][4]  # 11:00
    # --- Race: two phones book the same slot at the same moment ---
    results, barrier = [], threading.Barrier(2)

    def book(name, phone):
        barrier.wait()
        results.append(call("POST", f"/public/{slug_a}/bookings", {"service_id": svc["id"], "start_time": target["start_time"], "name": name, "phone": phone}))

    threads = [threading.Thread(target=book, args=("Priya R", "9876500001")), threading.Thread(target=book, args=("Arun K", "9876500002"))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    codes = sorted(r[0] for r in results)
    check("Concurrent same-slot bookings: one 201, one 409", codes == [201, 409], str(results))
    win = next(r[1] for r in results if r[0] == 201)
    lose = next(r[1] for r in results if r[0] == 409)
    check("201 body has booking_id/service/start/end/status/message",
          all(k in win for k in ("booking_id", "service", "start_time", "end_time", "status", "message")) and win["booking_id"].startswith("APT-"), str(win))
    check("409 body is SLOT_TAKEN", lose.get("error") == "SLOT_TAKEN", str(lose))

    # Overlapping (different start time) is also refused: 11:15 overlaps 11:00-11:45
    s, body = call("POST", f"/public/{slug_a}/bookings", {"service_id": svc["id"], "start_time": sl["slots"][5]["start_time"], "name": "Overlap", "phone": "9876500003"})
    check("Overlapping booking refused (409)", s == 409, str(body))

    s, sl2 = call("GET", f"/public/{slug_a}/slots?service_id={svc['id']}&date={day}")
    taken = [x["label"] for x in sl2["slots"] if not x["available"]]
    check("Booked time blocked in slot list (10:30-11:30 starts unavailable)", taken == ["10:30", "10:45", "11:00", "11:15", "11:30"], str(taken))

    s, body = call("POST", f"/public/{slug_a}/bookings", {"service_id": svc["id"], "start_time": f"{day}T13:30:00+05:30", "name": "Late", "phone": "9876500004"})
    check("Booking past closing time refused (422)", s == 422, str(body))

    # --- Tenant isolation ---
    s, appts_a = call("GET", f"/appointments?date={day}", token=ta)
    check("Owner A sees own appointment", s == 200 and len(appts_a) == 1, str(appts_a)[:300])
    appt_id = appts_a[0]["id"]
    s, appts_b = call("GET", f"/appointments?date={day}", token=tb)
    check("Owner B does not see A's appointments", s == 200 and appts_b == [])
    s, _ = call("PATCH", f"/appointments/{appt_id}", {"status": "cancelled"}, token=tb)
    check("Owner B cannot change A's appointment (404)", s == 404)
    s, _ = call("PUT", f"/services/{svc['id']}", {"name": "Hacked", "duration_min": 5, "price": 0}, token=tb)
    check("Owner B cannot edit A's service (404)", s == 404)
    s, _ = call("POST", f"/public/{slug_a}/bookings", {"service_id": svc_b["id"], "start_time": sl["slots"][0]["start_time"], "name": "Cross", "phone": "9876500005"})
    check("Cannot book B's service on A's page (404)", s == 404)
    s, cust_b = call("GET", "/customers", token=tb)
    check("Owner B customer list excludes A's customers", s == 200 and cust_b == [])
    s, _ = call("GET", "/appointments")
    check("Dashboard API requires JWT (401)", s == 401)

    # --- Status flow + stats ---
    s, upd = call("PATCH", f"/appointments/{appt_id}", {"status": "no_show"}, token=ta)
    check("Owner marks No-show", s == 200 and upd["status"] == "no_show")
    s, st = call("GET", f"/stats?month={day[:7]}", token=ta)
    check("Stats: bookings + no-show rate computed", s == 200 and st["no_shows"] == 1 and st["no_show_rate"] == 100.0, str({k: st.get(k) for k in ("total_bookings", "no_shows", "no_show_rate")}))

    # Cancel frees the slot again
    call("PATCH", f"/appointments/{appt_id}", {"status": "cancelled"}, token=ta)
    s, _ = call("POST", f"/public/{slug_a}/bookings", {"service_id": svc["id"], "start_time": target["start_time"], "name": "Rebook", "phone": "9876500006"})
    check("Cancelled slot can be re-booked (201)", s == 201)

    # AI is optional - without a key we get a clean error, not a crash
    s, body = call("POST", "/ai/insights", {}, token=ta)
    check("AI endpoint without key -> 400 NO_API_KEY", s == 400 and body.get("error") == "NO_API_KEY", str(body))

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
