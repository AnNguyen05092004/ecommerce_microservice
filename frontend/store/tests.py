from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.test import SimpleTestCase

from store.views import PRODUCT_TYPE_CONFIG, _fetch_products_with_filters


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class ProductAggregationSearchTests(SimpleTestCase):
    def _build_item(self, item_id, name, created_at):
        return {
            "id": item_id,
            "name": name,
            "brand": "TestBrand",
            "price": 1000000,
            "stock": 10,
            "created_at": created_at,
            "category": {"id": 1, "name": "Test Category"},
        }

    @patch("store.views.requests.get")
    def test_search_matches_all_12_product_types(self, mock_get):
        captured_page_sizes = []

        service_dataset = {}
        for idx, (ptype, cfg) in enumerate(PRODUCT_TYPE_CONFIG.items(), start=1):
            service_dataset[(cfg["service"], cfg["resource"])] = [
                self._build_item(
                    idx,
                    f"{ptype} omni-keyword item",
                    f"2026-04-{idx:02d}T10:00:00+07:00",
                )
            ]

        def fake_get(url, timeout=4):
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            service_name = parts[1]
            resource_name = parts[2]

            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["12"])[0])
            captured_page_sizes.append(page_size)

            rows = service_dataset.get((service_name, resource_name), [])
            start = (page - 1) * page_size
            end = start + page_size
            page_rows = rows[start:end]
            next_link = "has-next" if end < len(rows) else None
            return _FakeResponse(
                {"count": len(rows), "next": next_link, "results": page_rows}
            )

        mock_get.side_effect = fake_get

        results = _fetch_products_with_filters(
            {"search": "omni-keyword", "type": "all", "sort": "newest", "page": "2"}
        )

        self.assertEqual(
            set(PRODUCT_TYPE_CONFIG.keys()), {r["product_type"] for r in results}
        )
        self.assertEqual(len(PRODUCT_TYPE_CONFIG), len(results))
        self.assertTrue(all(size != 50 for size in captured_page_sizes))
        self.assertTrue(all(size == 12 for size in captured_page_sizes))

    @patch("store.views.requests.get")
    def test_newest_merge_fetches_next_page_only_when_needed(self, mock_get):
        request_log = []

        dominant_service = PRODUCT_TYPE_CONFIG["computer"]
        dominant_key = (dominant_service["service"], dominant_service["resource"])

        service_dataset = {}
        for idx, (ptype, cfg) in enumerate(PRODUCT_TYPE_CONFIG.items(), start=1):
            key = (cfg["service"], cfg["resource"])
            if key == dominant_key:
                rows = [
                    self._build_item(
                        1000 + i,
                        f"computer omni-keyword {i}",
                        f"2026-04-{28 - i:02d}T10:00:00+07:00",
                    )
                    for i in range(12)
                ]
            else:
                rows = [
                    self._build_item(
                        2000 + idx,
                        f"{ptype} old item",
                        "2026-03-01T10:00:00+07:00",
                    )
                ]
            service_dataset[key] = rows

        def fake_get(url, timeout=4):
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            service_name = parts[1]
            resource_name = parts[2]
            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["12"])[0])
            request_log.append((service_name, resource_name, page, page_size))

            rows = service_dataset.get((service_name, resource_name), [])
            start = (page - 1) * page_size
            end = start + page_size
            page_rows = rows[start:end]
            next_link = "has-next" if end < len(rows) else None
            return _FakeResponse(
                {"count": len(rows), "next": next_link, "results": page_rows}
            )

        mock_get.side_effect = fake_get

        results = _fetch_products_with_filters(
            {"search": "omni-keyword", "type": "all", "sort": "newest", "page": "1"}
        )

        self.assertEqual(8, len(results))
        non_dominant_page_two_calls = [
            row
            for row in request_log
            if (row[0], row[1]) != dominant_key and row[2] > 1
        ]
        self.assertEqual([], non_dominant_page_two_calls)
