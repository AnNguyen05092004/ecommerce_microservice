from django.test import TestCase, Client


class MobileServiceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_create_mobile_requires_staff_header(self):
        response = self.client.post(
            "/api/mobiles/", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_public_mobile_list(self):
        response = self.client.get("/api/mobiles/")
        self.assertEqual(response.status_code, 200)
