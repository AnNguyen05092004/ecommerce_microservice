import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from advisor.models import UserEvent


class Command(BaseCommand):
    help = "Export user behavior data to CSV with format: user_id, product_id, action, timestamp, and 4 more behavior metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=500,
            help="Number of users to export (default: 500)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="data_user500.csv",
            help="Output CSV filename (default: data_user500.csv)",
        )
        parser.add_argument(
            "--generate",
            action="store_true",
            help="Generate synthetic data if not enough data in DB",
        )

    def handle(self, *args, **options):
        num_users = options["users"]
        output_file = Path(options["output"])
        generate_synthetic = options["generate"]

        # Get existing events or generate synthetic data
        events = list(UserEvent.objects.all().order_by("created_at"))

        if len(events) < num_users * 4 and generate_synthetic:
            self.stdout.write(
                self.style.WARNING(
                    f"Only {len(events)} events found. Generating synthetic data..."
                )
            )
            events = self._generate_synthetic_events(num_users)

        # Export to CSV
        rows = self._process_events_to_rows(events, num_users)
        self._write_csv(output_file, rows, num_users)

        self.stdout.write(
            self.style.SUCCESS(f"✓ Exported {len(rows)} user records to {output_file}")
        )

    def _generate_synthetic_events(self, num_users):
        """Generate synthetic user behavior events."""
        events = []
        base_time = timezone.now() - timedelta(days=30)

        action_types = [
            "view",
            "click",
            "add_to_cart",
            "checkout",
            "review",
            "chat",
            "search",
            "wishlist",
        ]
        product_ids = list(range(1, 101))  # 100 products

        for user_idx in range(num_users):
            user_id = f"user_{user_idx+1:04d}"
            num_events = random.randint(4, 12)

            for event_idx in range(num_events):
                event = UserEvent(
                    user_id=user_id,
                    session_id=f"session_{user_idx+1:04d}_{event_idx}",
                    event_type=random.choice(
                        [
                            "product_detail_view",
                            "search",
                            "add_to_cart",
                            "checkout_start",
                            "order_created",
                            "review_created",
                            "chat_message_sent",
                            "product_list_view",
                        ]
                    ),
                    product_type=random.choice(
                        [
                            "computer",
                            "mobile",
                            "tablet",
                            "audio",
                            "wearable",
                            "component",
                        ]
                    ),
                    product_id=random.choice(product_ids),
                    price=random.uniform(100, 5000),
                    quantity=random.randint(1, 3),
                    created_at=base_time + timedelta(hours=random.randint(0, 720)),
                )
                events.append(event)

        # Bulk create
        UserEvent.objects.bulk_create(events, batch_size=1000)
        self.stdout.write(
            self.style.SUCCESS(f"Generated {len(events)} synthetic events")
        )
        return events

    def _process_events_to_rows(self, events, num_users):
        """Process events into user behavior rows."""
        from collections import Counter, defaultdict

        rows = []
        grouped = defaultdict(list)

        # Group events by user_id
        for event in events:
            user_id = event.user_id or event.session_id
            grouped[user_id].append(event)

        # Process each user
        user_count = 0
        for user_id, user_events in sorted(grouped.items())[:num_users]:
            user_count += 1

            # Calculate 8 behavior metrics
            event_counts = Counter(evt.event_type for evt in user_events)
            product_counts = Counter(evt.product_id for evt in user_events)

            views = event_counts.get("product_detail_view", 0)
            clicks = event_counts.get("search", 0)
            cart_adds = event_counts.get("add_to_cart", 0)
            checkouts = event_counts.get("checkout_start", 0)
            orders = event_counts.get("order_created", 0)
            reviews = event_counts.get("review_created", 0)
            chat_messages = event_counts.get("chat_message_sent", 0)
            total_events = len(user_events)

            # Pick one most-viewed product
            top_product_id = (
                product_counts.most_common(1)[0][0]
                if product_counts
                else random.randint(1, 100)
            )

            # Determine action based on event distribution
            if orders >= 1:
                action = "checkout"
            elif cart_adds >= 2:
                action = "add_to_cart"
            elif clicks >= 3:
                action = "search"
            elif views >= 3:
                action = "click"
            else:
                action = "view"

            # Get timestamp from last event
            timestamp = user_events[-1].created_at.isoformat() if user_events else ""

            rows.append(
                {
                    "user_id": user_id,
                    "product_id": top_product_id,
                    "action": action,
                    "timestamp": timestamp,
                    "views": views,
                    "clicks": clicks,
                    "cart_adds": cart_adds,
                    "checkouts": checkouts,
                    "orders": orders,
                    "reviews": reviews,
                    "chat_messages": chat_messages,
                    "total_events": total_events,
                }
            )

        return rows

    def _write_csv(self, output_file, rows, num_users):
        """Write rows to CSV file."""
        if not rows:
            self.stdout.write(
                self.style.ERROR("No data to export. Try with --generate flag.")
            )
            return

        fieldnames = [
            "user_id",
            "product_id",
            "action",
            "timestamp",
            "views",
            "clicks",
            "cart_adds",
            "checkouts",
            "orders",
            "reviews",
            "chat_messages",
            "total_events",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows[:num_users])

        self.stdout.write(
            self.style.SUCCESS(f"CSV written to {output_file} ({len(rows)} rows)")
        )
