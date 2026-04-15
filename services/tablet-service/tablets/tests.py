from django.test import TestCase, Client


class TabletServiceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_create_tablet_requires_staff_header(self):
        response = self.client.post(
            "/api/tablets/", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_public_tablet_list(self):
        response = self.client.get("/api/tablets/")
        self.assertEqual(response.status_code, 200)
