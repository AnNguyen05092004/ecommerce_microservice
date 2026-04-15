from django.test import TestCase, Client
from .models import Customer


class CustomerServiceTests(TestCase):
    def setUp(self):
        self.client = Client()
        customer = Customer(
            username="customer01",
            full_name="Customer User",
            email="customer@example.com",
            phone="0123456789",
            address="Hanoi",
        )
        customer.set_password("password123")
        customer.save()
        self.customer_id = customer.id

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_customer_list_requires_staff_header(self):
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 403)

    def test_my_profile_with_customer_header(self):
        response = self.client.get(
            "/api/customers/me/",
            **{"HTTP_X_USER_TYPE": "customer", "HTTP_X_USER_ID": str(self.customer_id)}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["username"], "customer01")
