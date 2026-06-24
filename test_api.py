import uvicorn
import threading
import time
import requests

def run_server():
    uvicorn.run('main:app', host='127.0.0.1', port=8000, log_level='error')

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(3)

try:
    resp = requests.get('http://127.0.0.1:8000/health')
    print(f'Health check: {resp.status_code} - {resp.json()}')
    
    login_data = {'username': 'member@fitness.com', 'password': 'member123'}
    resp = requests.post('http://127.0.0.1:8000/auth/login', data=login_data)
    print(f'Login test: {resp.status_code}')
    if resp.status_code == 200:
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        resp = requests.get('http://127.0.0.1:8000/member/schedule', headers=headers)
        schedule_data = resp.json()
        print(f'Schedule API: {resp.status_code} - {len(schedule_data)} courses found')
        
        resp = requests.get('http://127.0.0.1:8000/member/bookings', headers=headers)
        bookings_data = resp.json()
        print(f'Bookings API: {resp.status_code} - {bookings_data["total"]} bookings found')
        
        resp = requests.get('http://127.0.0.1:8000/member/membership-cards', headers=headers)
        cards_data = resp.json()
        print(f'Membership API: {resp.status_code} - {len(cards_data)} cards found')

    coach_login = {'username': 'wang@fitness.com', 'password': 'coach123'}
    resp = requests.post('http://127.0.0.1:8000/auth/login', data=coach_login)
    print(f'Coach login: {resp.status_code}')
    if resp.status_code == 200:
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.get('http://127.0.0.1:8000/coach/bookings/today', headers=headers)
        print(f'Coach bookings API: {resp.status_code} - {len(resp.json())} bookings found')

    admin_login = {'username': 'admin@fitness.com', 'password': 'admin123'}
    resp = requests.post('http://127.0.0.1:8000/auth/login', data=admin_login)
    print(f'Admin login: {resp.status_code}')
    if resp.status_code == 200:
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        today = time.localtime()
        resp = requests.get(f'http://127.0.0.1:8000/admin/checkins/export/csv?year={today.tm_year}&month={today.tm_mon}', headers=headers)
        print(f'CSV export API: {resp.status_code}')
        resp = requests.get('http://127.0.0.1:8000/admin/statistics', headers=headers)
        print(f'Statistics API: {resp.status_code} - {resp.json()}')

    print("\nTesting Review API...")
    login_data = {'username': 'member@fitness.com', 'password': 'member123'}
    resp = requests.post('http://127.0.0.1:8000/auth/login', data=login_data)
    if resp.status_code == 200:
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        resp = requests.get('http://127.0.0.1:8000/member/reviews', headers=headers)
        print(f'Member reviews API: {resp.status_code} - {resp.json()["total"]} reviews found')

        resp = requests.get('http://127.0.0.1:8000/member/bookings?status=completed', headers=headers)
        bookings = resp.json()["bookings"]
        if bookings:
            booking_id = bookings[0]["id"]
            review_data = {
                "booking_id": booking_id,
                "course_rating": 5,
                "coach_rating": 4,
                "comment": "Test review from API"
            }
            resp = requests.post('http://127.0.0.1:8000/member/reviews', headers=headers, json=review_data)
            print(f'Create review API: {resp.status_code}')

            print("Testing duplicate review protection...")
            resp = requests.post('http://127.0.0.1:8000/member/reviews', headers=headers, json=review_data)
            print(f'Duplicate review test: {resp.status_code} - {resp.json().get("detail", "")[:50]}')
            assert resp.status_code == 409, f"Expected 409 Conflict, got {resp.status_code}"
            print("Duplicate protection working correctly!")

    coach_login = {'username': 'wang@fitness.com', 'password': 'coach123'}
    resp = requests.post('http://127.0.0.1:8000/auth/login', data=coach_login)
    if resp.status_code == 200:
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.get('http://127.0.0.1:8000/coach/reviews', headers=headers)
        data = resp.json()
        print(f'Coach reviews API: {resp.status_code} - {data["total"]} reviews, avg coach rating: {data.get("average_coach_rating")}')
    
    print('\nAll tests passed!')
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'Error: {e}')
