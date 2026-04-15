from django.test import TestCase, Client


class BookServiceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_create_book_requires_staff_header(self):
        response = self.client.post(
            "/api/books/", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_public_book_list(self):
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, 200)
