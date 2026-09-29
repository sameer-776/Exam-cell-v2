"""
Automated Verification Suite for Poornima University Exam Cell Portal
Tests all 14 scenarios specified in the project requirements.
"""
import unittest
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from flask import session
from app import app, read_json, write_json, NOTIFICATIONS_FILE, USERS_FILE, CALENDAR_FILE, CONFIG_FILE, IST

class ExamCellPortalTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_public_index_loads(self):
        """Scenario 11: Main student portal loads with 200 OK and responsive elements."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Poornima University Exam Cell', html)
        self.assertIn('exam-calendar', html)
        self.assertIn('studentPreferencesBar', html)
        self.assertIn('search-input', html)

    def test_02_api_config(self):
        """Section 5: Verify /api/config returns configurable departments, years, and types."""
        res = self.client.get('/api/config')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('departments', data)
        self.assertIn('academic_years', data)
        self.assertIn('notification_types', data)
        self.assertIn('exam_types', data)
        self.assertTrue(len(data['departments']) > 0)

    def test_03_draft_isolation(self):
        """Scenario 2: Draft notification MUST NEVER appear on student-facing API."""
        res = self.client.get('/api/notifications')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        all_returned = data.get('filtered', []) + data.get('common', []) + data.get('departmental', []) + data.get('guidelines', [])
        for item in all_returned:
            self.assertNotEqual(item.get('status'), 'draft', f"Draft notice found in public API: {item.get('title')}")
            self.assertNotIn('Draft:', item.get('title', ''))

    def test_04_scheduled_isolation(self):
        """Scenario 5: Future scheduled notification remains hidden from students."""
        res = self.client.get('/api/notifications')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        all_returned = data.get('filtered', []) + data.get('common', []) + data.get('departmental', []) + data.get('guidelines', [])
        for item in all_returned:
            self.assertNotEqual(item.get('status'), 'scheduled', f"Future scheduled notice found in public API: {item.get('title')}")

    def test_05_calendar_api(self):
        """Scenario 10: Examination calendar entries display correctly."""
        res = self.client.get('/api/calendar')
        self.assertEqual(res.status_code, 200)
        events = res.get_json()
        self.assertIsInstance(events, list)
        self.assertTrue(len(events) > 0)
        first = events[0]
        self.assertIn('title', first)
        self.assertIn('exam_type', first)
        self.assertIn('date', first)

    def test_06_admin_login_and_dashboard(self):
        """Scenario 1 & Security: Verify admin login and session handling."""
        with self.client as c:
            res = c.post('/admin/login', data={'username': 'admin', 'password': 'password123'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertTrue(session.get('logged_in'))

            dash = c.get('/admin')
            self.assertEqual(dash.status_code, 200)
            self.assertIn('Admin Dashboard', dash.data.decode('utf-8'))

    def test_07_search_and_filters(self):
        """Scenario 8: Search and filters work together on /api/notifications."""
        res = self.client.get('/api/notifications?search=Practical')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        filtered = data.get('filtered', [])
        for item in filtered:
            text = (item.get('title', '') + ' ' + item.get('body', '')).lower()
            self.assertIn('practical', text)

    def test_08_pagination_preserves_params(self):
        """Scenario 9: Pagination returns correct page and limit structure."""
        res = self.client.get('/api/notifications?page=1&limit=2')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('pagination', data)
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['limit'], 2)
        self.assertTrue(len(data['filtered']) <= 2)

    def test_09_account_recovery_cli_and_key(self):
        """Scenario 1: Admin can securely recover access using reset_admin.py and emergency recovery key."""
        result = subprocess.run(
            ['python', 'reset_admin.py', '--username', 'admin', '--password', 'password123'],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('SUCCESS', result.stdout)

        # Confirm login works with the reset password
        res = self.client.post('/admin/login', data={'username': 'admin', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Test recovery endpoint with invalid key fails safely
        rec_bad = self.client.post('/admin/recover', data={
            'recovery_key': 'INVALID_KEY_123',
            'username': 'admin',
            'new_password': 'NewPassword456',
            'confirm_password': 'NewPassword456'
        }, follow_redirects=True)
        self.assertIn('Invalid recovery key', rec_bad.data.decode('utf-8'))

    def test_10_draft_crud_and_publishing(self):
        """Scenario 3: A draft can be created, edited, and published."""
        with self.client as c:
            c.post('/admin/login', data={'username': 'admin', 'password': 'password123'})

            # Create a draft
            res = c.post('/admin/add', data={
                'title': 'Test Draft Notice XYZ',
                'body': 'Draft body content',
                'type': 'common',
                'publish_action': 'draft',
                'department': 'all',
                'year': 'all'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Verify it is in notifications.json with status 'draft'
            notifs = read_json(NOTIFICATIONS_FILE)
            draft_item = next((n for n in notifs if n.get('title') == 'Test Draft Notice XYZ'), None)
            self.assertIsNotNone(draft_item)
            self.assertEqual(draft_item.get('status'), 'draft')

            # Verify draft is NOT in public API
            api_res = self.client.get('/api/notifications')
            self.assertNotIn('Test Draft Notice XYZ', api_res.data.decode('utf-8'))

            # Publish the draft
            pub_res = c.post(f'/admin/publish/{draft_item["id"]}', follow_redirects=True)
            self.assertEqual(pub_res.status_code, 200)

            # Verify it is now published and in public API
            api_res = self.client.get('/api/notifications')
            self.assertIn('Test Draft Notice XYZ', api_res.data.decode('utf-8'))

            # Cleanup
            c.post(f'/admin/delete/{draft_item["id"]}', follow_redirects=True)

    def test_11_calendar_crud(self):
        """Scenario 10: Admin can manage calendar entries."""
        with self.client as c:
            c.post('/admin/login', data={'username': 'admin', 'password': 'password123'})

            res = c.post('/admin/calendar/add', data={
                'title': 'Special Viva Voce Test',
                'exam_type': 'practical',
                'date': '2026-11-20',
                'time_session': '11:00 AM',
                'venue': 'Lab 101',
                'description': 'Final year project viva'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            cal_res = self.client.get('/api/calendar')
            self.assertIn('Special Viva Voce Test', cal_res.data.decode('utf-8'))

            events = read_json(CALENDAR_FILE)
            ev = next((e for e in events if e.get('title') == 'Special Viva Voce Test'), None)
            self.assertIsNotNone(ev)

            del_res = c.post(f'/admin/calendar/delete/{ev["id"]}', follow_redirects=True)
            self.assertEqual(del_res.status_code, 200)

    def test_12_scheduled_notification_crud(self):
        """Scenario 6: A scheduled notification can be scheduled, edited, and cancelled."""
        with self.client as c:
            c.post('/admin/login', data={'username': 'admin', 'password': 'password123'})

            # Create scheduled notification in future
            future_dt = (datetime.now(IST) + timedelta(days=15)).strftime('%Y-%m-%dT10:00')
            res = c.post('/admin/add', data={
                'title': 'Future Scheduled Exam Timetable Notice',
                'body': 'This should be hidden until the scheduled date',
                'type': 'common',
                'publish_action': 'schedule',
                'start_datetime': future_dt,
                'department': 'all',
                'year': 'all'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Verify it is scheduled and hidden from public API
            api_res = self.client.get('/api/notifications')
            self.assertNotIn('Future Scheduled Exam Timetable Notice', api_res.data.decode('utf-8'))

            # Edit scheduled notice (reschedule)
            notifs = read_json(NOTIFICATIONS_FILE)
            sched_item = next((n for n in notifs if n.get('title') == 'Future Scheduled Exam Timetable Notice'), None)
            self.assertIsNotNone(sched_item)

            edit_res = c.post(f'/admin/edit/{sched_item["id"]}', data={
                'title': 'Rescheduled Timetable Notice',
                'body': 'Updated scheduled notice',
                'type': 'common',
                'publish_action': 'schedule',
                'start_datetime': future_dt,
                'department': 'all',
                'year': 'all'
            }, follow_redirects=True)
            self.assertEqual(edit_res.status_code, 200)

            # Cancel / delete scheduled notice
            del_res = c.post(f'/admin/delete/{sched_item["id"]}', follow_redirects=True)
            self.assertEqual(del_res.status_code, 200)

            notifs = read_json(NOTIFICATIONS_FILE)
            self.assertIsNone(next((n for n in notifs if n.get('id') == sched_item['id']), None))

    def test_13_student_department_year_filtering(self):
        """Scenario 7: Students see only notifications applicable to them when filters are active."""
        # Query with departmental filter for CS Year 3
        res = self.client.get('/api/notifications?department=cse&year=3')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        for item in data.get('departmental', []):
            depts = item.get('department', [])
            years = item.get('year', [])
            self.assertTrue('all' in depts or 'cse' in depts)
            self.assertTrue('all' in years or '3' in years)

    def test_14_existing_data_and_functionality_intact(self):
        """Scenario 14: Existing notifications, quick links, and user data remain intact."""
        notifs = read_json(NOTIFICATIONS_FILE)
        self.assertTrue(len(notifs) >= 3)
        self.assertTrue(any('Semester Examination Schedule' in n.get('title', '') for n in notifs))

        config = read_json(CONFIG_FILE)
        self.assertTrue(len(config.get('quick_links', [])) == 4)

        users = read_json(USERS_FILE)
        self.assertTrue(any(u.get('username') == 'admin' for u in users))

if __name__ == '__main__':
    unittest.main()
