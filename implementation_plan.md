# Implementation Plan — TechStore Microservices

## Goal

Xây dựng toàn bộ hệ thống bán máy tính & điện thoại theo kiến trúc microservices với Django, dựa trên [analysis-and-design.md](file:///Users/an/Documents/Ptit%20Docs/Ki%E1%BA%BFn%20tr%C3%BAc%20v%C3%A0%20thi%E1%BA%BFt%20k%E1%BA%BF%20pm/KIEMTRA01/docs/analysis-and-design.md) và API specs đã thiết kế.

## User Review Required

> [!IMPORTANT]
> Dự án có **10 containers** (6 app + 4 database). Tôi sẽ triển khai theo thứ tự phụ thuộc: databases → services → gateway → frontend.

> [!WARNING]
> Đây là một project lớn. Tôi sẽ bắt đầu từng service một, mỗi service build + test trước khi chuyển sang service tiếp theo. Bạn có muốn tôi làm tất cả cùng lúc hay từng service?

---

## Proposed Changes

### Phase 1: Project Foundation

#### [NEW] [.env.example](file:///Users/an/Documents/Ptit%20Docs/Ki%E1%BA%BFn%20tr%C3%BAc%20v%C3%A0%20thi%E1%BA%BFt%20k%E1%BA%BF%20pm/KIEMTRA01/.env.example)
- Tất cả environment variables cho 4 services + databases + JWT config

#### [NEW] [docker-compose.yml](file:///Users/an/Documents/Ptit%20Docs/Ki%E1%BA%BFn%20tr%C3%BAc%20v%C3%A0%20thi%E1%BA%BFt%20k%E1%BA%BF%20pm/KIEMTRA01/docker-compose.yml)
- 10 containers: frontend, gateway, staff-service, customer-service, computer-service, mobile-service, staff-db (MySQL), customer-db (MySQL), computer-db (PostgreSQL), mobile-db (PostgreSQL)
- Health checks, depends_on, volumes, network

---

### Phase 2: Backend Services (Django + DRF)

Mỗi service sẽ bao gồm:
- Django project scaffold (`manage.py`, `settings.py`, `urls.py`)
- Models (theo data model trong analysis-and-design.md)
- Serializers
- Views (DRF ViewSets/APIViews)
- URLs
- Dockerfile (theo [.ai/prompts/create-dockerfile.md](file:///Users/an/Documents/Ptit%20Docs/Ki%E1%BA%BFn%20tr%C3%BAc%20v%C3%A0%20thi%E1%BA%BFt%20k%E1%BA%BF%20pm/KIEMTRA01/.ai/prompts/create-dockerfile.md))
- `requirements.txt`
- `GET /health` endpoint
- `readme.md`

#### [NEW] Staff Service — `services/staff-service/`
- **Database**: MySQL (staff-db)
- **Models**: Staff (username, password, full_name, email, phone, role, is_active)
- **Endpoints**: auth/login, auth/verify, CRUD staff
- **Port**: 8001

#### [NEW] Customer Service — `services/customer-service/`
- **Database**: MySQL (customer-db)
- **Models**: Customer, Cart, CartItem, Order, OrderItem, Review
- **Endpoints**: auth/register, auth/login, auth/verify, profile, cart, orders, reviews
- **Inter-service**: Gọi Computer/Mobile Service để verify product & update stock
- **Port**: 8002

#### [NEW] Computer Service — `services/computer-service/`
- **Database**: PostgreSQL (computer-db)
- **Models**: Computer, ComputerSpec, ComputerCategory
- **Endpoints**: CRUD computers, categories, stock update, search/filter
- **Port**: 8003

#### [NEW] Mobile Service — `services/mobile-service/`
- **Database**: PostgreSQL (mobile-db)
- **Models**: Mobile, MobileSpec, MobileCategory
- **Endpoints**: CRUD mobiles, categories, stock update, search/filter
- **Port**: 8004

---

### Phase 3: API Gateway

#### [NEW] Gateway — `gateway/`
- Django-based reverse proxy
- JWT token verification (gọi staff/customer service)
- Route mapping đến 4 services
- Health check aggregation
- **Port**: 8000

---

### Phase 4: Frontend

#### [NEW] Frontend — `frontend/`
- Django Templates (SSR)
- **Customer views**: trang chủ, danh sách SP, chi tiết SP, giỏ hàng, checkout, lịch sử đơn hàng, đánh giá
- **Staff/Admin views**: dashboard, quản lý SP, quản lý đơn hàng, quản lý khách hàng, quản lý kho, thống kê
- Giao diện web khác nhau cho Customer và Staff
- **Port**: 8080

---

## Verification Plan

### Automated Tests

1. **Docker Compose build & start**:
   ```bash
   cd "/Users/an/Documents/Ptit Docs/Kiến trúc và thiết kế pm/KIEMTRA01"
   docker compose up --build -d
   ```

2. **Health checks** — tất cả services phải trả `{"status": "ok"}`:
   ```bash
   curl http://localhost:8000/health  # Gateway
   curl http://localhost:8001/health  # Staff
   curl http://localhost:8002/health  # Customer
   curl http://localhost:8003/health  # Computer
   curl http://localhost:8004/health  # Mobile
   ```

3. **API endpoint tests** — dùng browser subagent hoặc curl để test basic CRUD flows

### Manual Verification

- Mở browser tại `http://localhost:8080` và verify giao diện Customer/Staff
- Test quy trình mua hàng end-to-end (duyệt SP → giỏ hàng → checkout)
- Test quy trình quản lý SP (staff đăng nhập → CRUD sản phẩm)
