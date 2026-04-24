import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from advisor.models import UserEvent


EVENT_TEMPLATES = {
    "impulse_buyer": [
        "product_list_view",
        "product_detail_view",
        "add_to_cart",
        "checkout_start",
        "order_created",
    ],
    "researcher": [
        "search",
        "search",
        "product_list_view",
        "product_detail_view",
        "product_detail_view",
        "chat_message_sent",
    ],
    "loyal_customer": [
        "product_detail_view",
        "add_to_cart",
        "checkout_start",
        "order_created",
        "review_created",
        "order_created",
    ],
    "price_sensitive": [
        "search",
        "product_detail_view",
        "add_to_cart",
        "update_cart",
        "remove_from_cart",
        "search",
    ],
    "window_shopper": [
        "product_list_view",
        "product_detail_view",
        "product_detail_view",
        "chat_open",
    ],
}

PRODUCT_TYPES = [
    "computer",
    "mobile",
    "tablet",
    "audio",
    "wearable",
    "component",
    "peripheral",
    "monitor",
    "accessory",
    "charging",
    "book",
    "clothes",
]

SEARCH_QUERY_BY_TYPE = {
    "computer": ["laptop gaming", "may tinh van phong", "pc do hoa"],
    "mobile": ["dien thoai pin trau", "smartphone chup anh", "phone cho sinh vien"],
    "tablet": ["ipad hoc online", "tablet ve design", "may tinh bang doc sach"],
    "audio": ["tai nghe chong on", "loa bluetooth", "headphone nghe nhac"],
    "wearable": ["dong ho thong minh", "smartwatch the thao", "vong deo suc khoe"],
    "component": ["ssd nvme", "ram ddr5", "cpu gaming"],
    "peripheral": ["ban phim co", "chuot gaming", "webcam hoc online"],
    "monitor": ["man hinh 2k", "monitor do hoa", "man hinh 144hz"],
    "accessory": ["phu kien laptop", "op lung dien thoai", "de do laptop"],
    "charging": ["cu sac nhanh", "sac du phong", "charger type c"],
    "book": ["sach cong nghe", "sach lap trinh", "book machine learning"],
    "clothes": ["ao khoac", "quan jean", "thoi trang cong so"],
}


class Command(BaseCommand):
    help = "Seed synthetic behavior events for advisor model training and evaluation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-profile",
            type=int,
            default=40,
            help="Number of synthetic users per behavior profile",
        )
        parser.add_argument(
            "--reset-bench",
            action="store_true",
            help="Delete previous synthetic bench events before seeding",
        )

    def handle(self, *args, **options):
        per_profile = max(1, int(options["per_profile"]))
        reset_bench = bool(options["reset_bench"])

        if reset_bench:
            deleted, _ = UserEvent.objects.filter(user_id__startswith="bench-").delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} synthetic events"))

        now = timezone.now()
        created = 0
        for profile, template in EVENT_TEMPLATES.items():
            for idx in range(per_profile):
                user_id = f"bench-{profile}-{idx:03d}"
                session_id = f"bench-sess-{profile}-{idx:03d}"
                product_type = random.choice(PRODUCT_TYPES)
                base_product_id = random.randint(1, 20)

                for offset, event_type in enumerate(template):
                    query_text = ""
                    if event_type == "search":
                        choices = SEARCH_QUERY_BY_TYPE.get(product_type, [product_type])
                        query_text = random.choice(choices)

                    event = UserEvent.objects.create(
                        user_id=user_id,
                        session_id=session_id,
                        event_type=event_type,
                        product_type=product_type,
                        product_id=base_product_id + (offset % 3),
                        category_id=random.randint(1, len(PRODUCT_TYPES)),
                        query_text=query_text,
                        language="vi" if random.random() < 0.7 else "en",
                        metadata={
                            "seeded": True,
                            "profile": profile,
                            "template_event_index": offset,
                        },
                    )
                    event.created_at = now - timedelta(
                        minutes=random.randint(10, 10000),
                        seconds=offset,
                    )
                    event.save(update_fields=["created_at"])
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} events across {len(EVENT_TEMPLATES) * per_profile} synthetic users"
            )
        )
