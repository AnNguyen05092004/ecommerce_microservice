# ecommerce_microservice
# 1. Build + chạy toàn bộ services
docker compose up -d --build

# 2. Chờ services khởi động xong (~30-60 giây)
sleep 60

# 3. Seed dữ liệu
python scripts/seed_test_data.py

# 4. Check status
docker compose ps