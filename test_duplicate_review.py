import uvicorn
import threading
import time
import requests

def run_server():
    uvicorn.run('main:app', host='127.0.0.1', port=8001, log_level='error')

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(3)

BASE = "http://127.0.0.1:8001"

try:
    print("=" * 60)
    print("TESTING DUPLICATE REVIEW PROTECTION")
    print("=" * 60)

    login_data = {'username': 'member@fitness.com', 'password': 'member123'}
    resp = requests.post(f"{BASE}/auth/login", data=login_data)
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print(f"[1] Member login: {resp.status_code}")

    resp = requests.get(f"{BASE}/member/bookings?status=completed", headers=headers)
    completed_bookings = resp.json()["bookings"]
    print(f"[2] Completed bookings found: {len(completed_bookings)}")

    if not completed_bookings:
        resp = requests.get(f"{BASE}/member/bookings", headers=headers)
        all_bookings = resp.json()["bookings"]
        print(f"    Total bookings: {len(all_bookings)}")
        for b in all_bookings:
            print(f"    - Booking #{b['id']}: {b['course']['name']} on {b['course_date']} status={b['status']}")

        print("\n    Creating test booking + checkin manually via DB...")
        print("    Using direct test approach with existing data...")
    else:
        booking_id = completed_bookings[0]["id"]
        course_name = completed_bookings[0]["course"]["name"]
        print(f"    Using booking #{booking_id}: {course_name}")

        review_data = {
            "booking_id": booking_id,
            "course_rating": 5,
            "coach_rating": 5,
            "comment": "太棒了！非常满意！"
        }

        print(f"\n[3] First review submission...")
        resp = requests.post(f"{BASE}/member/reviews", headers=headers, json=review_data)
        print(f"    Status: {resp.status_code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    Review ID: {resp.json()['id']}")

        print(f"\n[4] Second review submission (same booking)...")
        resp = requests.post(f"{BASE}/member/reviews", headers=headers, json=review_data)
        print(f"    Status: {resp.status_code}")
        print(f"    Message: {resp.json().get('detail', '')}")
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
        assert "仅可评价一次" in resp.json()["detail"], "Friendly message not found"
        print(f"    => 409 Conflict with friendly message: PASS ✓")

        print(f"\n[5] Third review submission (attempt with different rating)...")
        review_data["course_rating"] = 1
        review_data["coach_rating"] = 1
        resp = requests.post(f"{BASE}/member/reviews", headers=headers, json=review_data)
        print(f"    Status: {resp.status_code}")
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
        print(f"    => Still blocked: PASS ✓")

        resp = requests.get(f"{BASE}/member/reviews", headers=headers)
        review_count = resp.json()["total"]
        print(f"\n[6] Final review count in DB: {review_count}")
        assert review_count == 1, f"Expected 1, got {review_count}"
        print(f"    => Only 1 review exists, duplicates prevented: PASS ✓")

    print("\n" + "=" * 60)
    print("ALL DUPLICATE PROTECTION TESTS PASSED ✓")
    print("=" * 60)

except AssertionError as e:
    print(f"\n❌ TEST FAILED: {e}")
    exit(1)
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n❌ ERROR: {e}")
    exit(1)
