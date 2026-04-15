from django.test import TestCase, Client


class PeripheralServiceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_create_peripheral_requires_staff_header(self):
        response = self.client.post(
            "/api/peripherals/", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_public_peripheral_list(self):
        response = self.client.get("/api/peripherals/")
        self.assertEqual(response.status_code, 200)
