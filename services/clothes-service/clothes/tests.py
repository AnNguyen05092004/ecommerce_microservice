from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Clothes
from categories.models import ClothesCategory


class ClothesAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = ClothesCategory.objects.create(name="T-Shirts", description="Casual T-Shirts")
        self.clothes = Clothes.objects.create(
            name="Basic Tee",
            brand="H&M",
            price=199000,
            stock=50,
            gender="unisex",
            category=self.category,
        )

    def test_list_clothes(self):
        response = self.client.get("/api/clothes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_get_clothes_detail(self):
        response = self.client.get(f"/api/clothes/{self.clothes.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Basic Tee")

    def test_create_clothes_requires_staff(self):
        response = self.client.post("/api/clothes/", {
            "name": "New Shirt",
            "brand": "Zara",
            "price": 300000,
            "stock": 10,
            "category_id": self.category.pk,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_clothes_as_staff(self):
        self.client.credentials(HTTP_X_USER_TYPE="staff")
        response = self.client.post("/api/clothes/", {
            "name": "Staff Shirt",
            "brand": "Zara",
            "price": 350000,
            "stock": 20,
            "category_id": self.category.pk,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok"})
