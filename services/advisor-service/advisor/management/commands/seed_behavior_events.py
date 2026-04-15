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

PRODUCT_TYPES = ["computer", "mobile", "clothes"]


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
                    event = UserEvent.objects.create(
                        user_id=user_id,
                        session_id=session_id,
                        event_type=event_type,
                        product_type=product_type,
                        product_id=base_product_id + (offset % 3),
                        category_id=random.randint(1, 6),
                        query_text=(
                            (
                                "laptop gaming"
                                if product_type == "computer"
                                else (
                                    "dien thoai pin trau"
                                    if product_type == "mobile"
                                    else "ao khoac"
                                )
                            )
                            if event_type == "search"
                            else ""
                        ),
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
