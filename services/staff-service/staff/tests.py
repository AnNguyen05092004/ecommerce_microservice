from django.test import TestCase, Client
from .models import Staff


class StaffServiceTests(TestCase):
    def setUp(self):
        self.client = Client()
        staff = Staff(
            username="admin01",
            full_name="Admin User",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        staff.set_password("password123")
        staff.save()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_staff_list_requires_staff_header(self):
        response = self.client.get("/api/staff/")
        self.assertEqual(response.status_code, 403)

    def test_login_returns_token(self):
        response = self.client.post(
            "/api/auth/login/",
            data={"username": "admin01", "password": "password123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("token", body)
        self.assertEqual(body["user"]["username"], "admin01")
