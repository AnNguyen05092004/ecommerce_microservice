# 📖 TechStore — Giải Thích Chi Tiết Cấu Trúc Dự Án

---

## 🗺️ TỔNG QUAN CẤU TRÚC THƯ MỤC

```
KIEMTRA01/
├── gateway/                   ← API Gateway (cổng vào duy nhất)
├── services/
│   ├── staff-service/         ← Quản lý nhân viên
│   ├── customer-service/      ← Khách hàng, giỏ hàng, đơn hàng
│   ├── computer-service/      ← Máy tính, laptop
│   └── mobile-service/        ← Điện thoại
├── docs/                      ← Tài liệu thiết kế
├── docker-compose.yml         ← Khởi chạy toàn bộ hệ thống
└── .env                       ← Biến môi trường (mật khẩu, ports)
```

**Nguyên tắc hoạt động:** Frontend → Gateway → (1 trong 4 services) → Database

---

# 🔀 GATEWAY (`gateway/`)

## Mục đích
Gateway là **điểm vào duy nhất** của hệ thống. Mọi request từ Frontend đều phải đi qua đây trước khi đến service. Không có database riêng vì chỉ có nhiệm vụ định tuyến và xác thực.

## Cấu trúc thư mục

```
gateway/
├── Dockerfile                 ← Build Docker image cho gateway
├── manage.py                  ← Django CLI (chạy server, migrate...)
├── requirements.txt           ← Thư viện Python cần cài (django, PyJWT, requests...)
├── gateway/
│   ├── __init__.py            ← Đánh dấu đây là Python package
│   ├── settings.py            ← ⭐ Cấu hình Django của Gateway
│   ├── urls.py                ← ⭐ Định nghĩa route → proxy function
│   └── wsgi.py                ← Entry point khi chạy bằng gunicorn/uwsgi
└── proxy/
    ├── __init__.py
    └── views.py               ← ⭐⭐ LOGIC CHÍNH: xác thực JWT & forward request
```

---

## [gateway/gateway/settings.py](../gateway/gateway/settings.py)

**Mục đích:** Cấu hình Django cho Gateway.

**Điểm đặc biệt so với các service khác:** `DATABASES = {}` — Gateway **không có database**, chỉ là proxy.

```python
# Không có database
DATABASES = {}

# JWT secret dùng chung với tất cả services
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret')

# URL nội bộ Docker để gọi đến từng service
STAFF_SERVICE_URL    = 'http://staff-service:8001'
CUSTOMER_SERVICE_URL = 'http://customer-service:8002'
COMPUTER_SERVICE_URL = 'http://computer-service:8003'
MOBILE_SERVICE_URL   = 'http://mobile-service:8004'
```

> Tên `staff-service`, `customer-service`... là Docker DNS — các container gọi nhau qua tên, không phải localhost.

---

## [gateway/gateway/urls.py](../gateway/gateway/urls.py)

**Mục đích:** Quy tắc định tuyến — URL nào thì gọi proxy function nào.

```python
urlpatterns = [
    path('health', health_check),   # GET /health → {"status": "ok"}

    # Bắt tất cả URL bắt đầu bằng api/staff-service/ → chuyển đến Staff Service
    re_path(r'^api/staff-service/(?P<path>.*)$',    views.proxy_staff_service),

    # Bắt tất cả URL bắt đầu bằng api/customer-service/ → chuyển đến Customer Service
    re_path(r'^api/customer-service/(?P<path>.*)$', views.proxy_customer_service),

    # Bắt tất cả URL bắt đầu bằng api/computer-service/ → chuyển đến Computer Service
    re_path(r'^api/computer-service/(?P<path>.*)$', views.proxy_computer_service),

    # Bắt tất cả URL bắt đầu bằng api/mobile-service/ → chuyển đến Mobile Service
    re_path(r'^api/mobile-service/(?P<path>.*)$',   views.proxy_mobile_service),
]
```

**Ví dụ thực tế:**
```
Frontend gửi: POST /api/customer-service/orders/
                          ↓
urls.py khớp pattern api/customer-service/(?P<path>.*)$
                          ↓
Gọi proxy_customer_service(request, path="orders/")
```

---

## [gateway/proxy/views.py](../gateway/proxy/views.py)

**Mục đích:** Trái tim của Gateway — nơi thực hiện xác thực JWT và forward request.

### Phần 1 — `PUBLIC_ROUTES` (Danh sách URL không cần token)

```python
PUBLIC_ROUTES = [
    "api/auth/login/",       # Đăng nhập chưa có token, nên phải public
    "api/auth/register/",    # Đăng ký cũng chưa có token
    "api/computers/",        # Xem sản phẩm không cần đăng nhập
    "api/mobiles/",
    "api/categories/",
    "api/reviews/",
]
```

### Phần 2 — `is_public_route(path, method)` (Kiểm tra có cần token không)

```python
def is_public_route(path, method):
    # Luôn public: login, register, verify
    if "auth/login" in path or "auth/register" in path:
        return True

    # GET sản phẩm/danh mục/đánh giá → public (ai cũng xem được)
    if method == "GET":
        public_prefixes = ["computers", "mobiles", "categories", "reviews"]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True

    return False  # Còn lại đều cần token
```

**Ví dụ:**
| Request | Kết quả |
|---------|---------|
| `GET /computers/` | ✅ Public — không cần token |
| `POST /auth/login/` | ✅ Public — chưa có token |
| `POST /cart/items/` | ❌ Cần token — thêm giỏ hàng |
| `POST /orders/` | ❌ Cần token — đặt hàng |
| `DELETE /cart/items/5/` | ❌ Cần token — xoá sản phẩm |

### Phần 3 — `verify_jwt_token(token)` (Giải mã token)

```python
def verify_jwt_token(token):
    try:
        # Giải mã token bằng secret key chung
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
        # Trả về: {user_id: 4, username: "customer_1", user_type: "customer", role: ""}

    except jwt.ExpiredSignatureError:
        return None  # Token hết hạn (mặc định 24h)

    except jwt.InvalidTokenError:
        return None  # Token sai, bị giả mạo
```

### Phần 4 — `forward_request(request, target_url, path)` (Chuyển tiếp request)

```python
def forward_request(request, target_url, path):
    # Xây dựng URL đích
    url = f"{target_url}/api/{path}"
    # Ví dụ: http://customer-service:8002/api/orders/

    headers = {"Content-Type": "application/json"}

    # Nếu người dùng đã đăng nhập → thêm thông tin user vào header
    # Để service phía sau biết "ai" đang gửi request
    if hasattr(request, "_jwt_payload"):
        payload = request._jwt_payload
        headers["X-User-ID"]   = str(payload.get("user_id"))    # "4"
        headers["X-Username"]  = str(payload.get("username"))   # "customer_1"
        headers["X-User-Type"] = str(payload.get("user_type"))  # "customer"
        headers["X-User-Role"] = str(payload.get("role"))       # "admin" hoặc ""

    # Forward body (với POST/PATCH/DELETE)
    if method in ("post", "put", "patch", "delete"):
        kwargs["data"] = request.body

    # Thực sự gửi request đến service
    response = getattr(requests, method)(**kwargs)

    # Trả response của service về cho Frontend
    return HttpResponse(response.content, status=response.status_code)
```

> **Tại sao cần `X-User-ID` trong header?**
> Vì Customer Service không có token. Nó chỉ nhận HTTP request từ Gateway và đọc `request.META.get("HTTP_X_USER_ID")` để biết customer_id là bao nhiêu.

### Phần 5 — `gateway_view()` và 4 proxy functions (Hàm điều phối chính)

```python
def gateway_view(request, path, service_url):
    # Bước 1: Cần token không?
    if not is_public_route(path, request.method):

        # Bước 2: Lấy token từ header "Authorization: Bearer <token>"
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Bước 3: Giải mã token
        token = auth_header.split(" ")[1]
        payload = verify_jwt_token(token)
        if not payload:
            return JsonResponse({"error": "Invalid or expired token"}, status=401)

        # Bước 4: Lưu payload để forward_request dùng
        request._jwt_payload = payload

    # Bước 5: Forward đến service đích
    return forward_request(request, service_url, path)


@csrf_exempt  # Bỏ CSRF vì đây là API, không phải form HTML
def proxy_staff_service(request, path):
    return gateway_view(request, path, settings.STAFF_SERVICE_URL)

@csrf_exempt
def proxy_customer_service(request, path):
    return gateway_view(request, path, settings.CUSTOMER_SERVICE_URL)

@csrf_exempt
def proxy_computer_service(request, path):
    return gateway_view(request, path, settings.COMPUTER_SERVICE_URL)

@csrf_exempt
def proxy_mobile_service(request, path):
    return gateway_view(request, path, settings.MOBILE_SERVICE_URL)
```

**Flow hoàn chỉnh:**
```
Frontend: POST /api/customer-service/orders/
          Authorization: Bearer eyJhbGci...
          Body: {shipping_address: "...", phone: "..."}
                      ↓
urls.py → proxy_customer_service(request, path="orders/")
                      ↓
gateway_view(request, "orders/", "http://customer-service:8002")
                      ↓
is_public_route("orders/", "POST") → False (cần token)
                      ↓
verify_jwt_token("eyJhbGci...") → {user_id:4, username:"customer_1", user_type:"customer"}
                      ↓
request._jwt_payload = {user_id:4, ...}
                      ↓
forward_request():
  - URL: http://customer-service:8002/api/orders/
  - Headers: X-User-ID:4, X-User-Type:customer, Authorization: Bearer ...
  - Body: {shipping_address:"...", phone:"..."}
                      ↓
Customer Service nhận, tạo order, trả response
                      ↓
Gateway trả response về Frontend ✅
```

---

# 👥 STAFF SERVICE (`services/staff-service/`)

## Mục đích
Quản lý tài khoản **nhân viên** và **admin**. Phát hành JWT token khi đăng nhập. Phân quyền `staff` vs `admin`.

## Cấu trúc thư mục

```
services/staff-service/
├── Dockerfile                     ← Build Docker image
├── manage.py                      ← Django CLI
├── requirements.txt               ← Django, DRF, PyJWT, mysqlclient
├── staff_service/
│   ├── __init__.py
│   ├── settings.py                ← ⭐ Cấu hình (MySQL, DRF, JWT)
│   ├── urls.py                    ← ⭐ Route chính: /health, /api/auth/, /api/staff/
│   └── wsgi.py
├── authentication/
│   ├── __init__.py
│   ├── views.py                   ← ⭐ login(), verify_token()
│   └── urls.py                    ← /login/, /verify/
└── staff/
    ├── __init__.py
    ├── models.py                  ← ⭐ Staff model (username, password, role)
    ├── serializers.py             ← Chuyển Staff object ↔ JSON
    ├── views.py                   ← ⭐ CRUD nhân viên
    └── urls.py                    ← /, /<id>/
```

---

## [services/staff-service/staff_service/settings.py](../services/staff-service/staff_service/settings.py)

```python
INSTALLED_APPS = [
    'rest_framework',     # Django REST Framework
    'corsheaders',        # Cho phép cross-origin request
    'authentication',     # App xác thực
    'staff',              # App quản lý nhân viên
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',   # Dùng MySQL
        'NAME': os.environ.get('DB_NAME'),       # staff_db
        'HOST': os.environ.get('DB_HOST'),       # staff-db (Docker DNS)
        'PORT': '3306',
    }
}

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')   # Cùng secret với Gateway
JWT_EXPIRATION_HOURS = 24                            # Token hết hạn sau 24 giờ
```

---

## [services/staff-service/staff_service/urls.py](../services/staff-service/staff_service/urls.py)

```python
urlpatterns = [
    path('health', health_check),         # GET /health → {"status": "ok"}
    path('api/auth/', include('authentication.urls')),   # /api/auth/login/, /api/auth/verify/
    path('api/staff/', include('staff.urls')),           # /api/staff/, /api/staff/<id>/
]
```

---

## [services/staff-service/staff/models.py](../services/staff-service/staff/models.py)

```python
class Staff(models.Model):
    ROLE_CHOICES = [('staff', 'Staff'), ('admin', 'Admin')]

    username   = CharField(max_length=150, unique=True)   # Tên đăng nhập
    password   = CharField(max_length=128)                # Mật khẩu đã hash
    full_name  = CharField(max_length=255)                # Họ và tên
    email      = EmailField(unique=True)
    phone      = CharField(max_length=20)
    role       = CharField(choices=ROLE_CHOICES)          # staff hoặc admin
    is_active  = BooleanField(default=True)               # Còn hoạt động không
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)   # Hash password trước khi lưu

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)  # So sánh với hash
```

> **Tại sao hash password?** Lưu mật khẩu dạng hash (bcrypt) để kể cả khi database bị lộ, kẻ tấn công không đọc được mật khẩu gốc.

---

## [services/staff-service/authentication/views.py](../services/staff-service/authentication/views.py)

### Hàm `login()` — Đăng nhập và tạo JWT

```python
@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    staff = Staff.objects.get(username=username)  # Tìm user

    if not staff.is_active:
        return 401 "Account is deactivated"

    if not staff.check_password(password):
        return 401 "Invalid username or password"

    # Tạo JWT payload
    payload = {
        'user_id':   staff.id,
        'username':  staff.username,
        'role':      staff.role,        # "admin" hoặc "staff"
        'user_type': 'staff',
        'exp':       now + 24h,         # Hết hạn sau 24 giờ
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

    return {"token": token, "user": {id, username, full_name, role}}
```

### Hàm `verify_token()` — Kiểm tra token còn hợp lệ không

```python
@api_view(['POST'])
def verify_token(request):
    token = request.data.get('token')
    payload = jwt.decode(token, JWT_SECRET_KEY)
    # Kiểm tra user còn tồn tại và is_active trong DB
    return {"valid": True, "user_id": ..., "username": ..., "role": ...}
```

---

## [services/staff-service/staff/views.py](../services/staff-service/staff/views.py)

```python
@api_view(["GET", "POST"])
def staff_list_create(request):
    if request.method == "GET":
        # Chỉ staff/admin mới xem được
        forbidden = _require_staff_user(request)  # Đọc X-User-Type header
        if forbidden: return forbidden

    if request.method == "POST":
        # Chỉ ADMIN mới tạo được nhân viên mới
        forbidden = _require_admin_user(request)  # Đọc X-User-Role header
        if forbidden: return forbidden
        # Tạo Staff mới...

# _require_staff_user: Đọc header X-User-Type, kiểm tra == "staff"
# _require_admin_user: Đọc header X-User-Role, kiểm tra == "admin"
# Những header này được Gateway gửi kèm sau khi giải mã JWT
```

**API Endpoints:**
| Method | URL | Quyền | Mô tả |
|--------|-----|-------|-------|
| GET | `/api/staff/` | staff, admin | Danh sách nhân viên |
| POST | `/api/staff/` | admin only | Tạo nhân viên mới |
| GET | `/api/staff/<id>/` | staff, admin | Chi tiết nhân viên |
| PATCH | `/api/staff/<id>/` | admin only | Cập nhật nhân viên |
| DELETE | `/api/staff/<id>/` | admin only | Xoá nhân viên |

---

# 👤 CUSTOMER SERVICE (`services/customer-service/`)

## Mục đích
Service phức tạp nhất. Quản lý tất cả nghiệp vụ liên quan đến **khách hàng**: đăng ký/đăng nhập, giỏ hàng, đặt hàng, đánh giá.

## Cấu trúc thư mục

```
services/customer-service/
├── Dockerfile
├── manage.py
├── requirements.txt               ← Django, DRF, PyJWT, mysqlclient, requests
├── customer_service/
│   ├── settings.py                ← ⭐ MySQL, inter-service URLs
│   └── urls.py                    ← ⭐ Route đến 5 app
├── authentication/
│   ├── views.py                   ← ⭐ register(), login()
│   └── urls.py                    ← /register/, /login/
├── customers/
│   ├── models.py                  ← ⭐ Customer model
│   ├── serializers.py
│   ├── views.py                   ← CRUD profile
│   └── urls.py
├── cart/
│   ├── models.py                  ← ⭐ Cart, CartItem models
│   ├── serializers.py
│   ├── views.py                   ← Thêm/xoá/sửa giỏ hàng
│   └── urls.py
├── orders/
│   ├── models.py                  ← ⭐ Order, OrderItem models
│   ├── serializers.py
│   ├── views.py                   ← ⭐⭐ LOGIC PHỨC TẠP: tạo đơn, trừ kho
│   └── urls.py
└── reviews/
    ├── models.py                  ← ⭐ Review model
    ├── serializers.py
    ├── views.py                   ← Tạo/xem đánh giá
    └── urls.py
```

---

## [services/customer-service/customer_service/settings.py](../services/customer-service/customer_service/settings.py)

```python
INSTALLED_APPS = [
    'authentication', 'customers', 'cart', 'orders', 'reviews'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # MySQL
        'NAME': 'customer_db',
        'HOST': 'customer-db',  # Docker DNS
    }
}

# ⭐ URL để gọi sang service khác khi checkout
COMPUTER_SERVICE_URL = 'http://computer-service:8003'
MOBILE_SERVICE_URL   = 'http://mobile-service:8004'
```

---

## [services/customer-service/customer_service/urls.py](../services/customer-service/customer_service/urls.py)

```python
urlpatterns = [
    path('health', health_check),
    path('api/auth/',      include('authentication.urls')),  # Đăng ký, đăng nhập
    path('api/customers/', include('customers.urls')),       # Profile
    path('api/cart/',      include('cart.urls')),            # Giỏ hàng
    path('api/orders/',    include('orders.urls')),          # Đơn hàng
    path('api/reviews/',   include('reviews.urls')),         # Đánh giá
]
```

---

## [services/customer-service/customers/models.py](../services/customer-service/customers/models.py)

```python
class Customer(models.Model):
    username   = CharField(max_length=150, unique=True)
    password   = CharField(max_length=128)   # bcrypt hash
    full_name  = CharField(max_length=255)
    email      = EmailField(unique=True)
    phone      = CharField(max_length=20)
    address    = TextField()                 # Địa chỉ mặc định
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def set_password(self, raw_password): ...
    def check_password(self, raw_password): ...
```

---

## [services/customer-service/authentication/views.py](../services/customer-service/authentication/views.py)

```python
@api_view(['POST'])
def register(request):
    """POST /api/auth/register/"""
    # Tạo Customer mới
    customer = serializer.save()
    # Tự động đăng nhập sau khi đăng ký → tạo JWT ngay
    payload = {user_id, username, user_type: "customer", exp: +24h}
    token = jwt.encode(payload, JWT_SECRET_KEY)
    return {"token": token, "user": {id, username, full_name}}

@api_view(['POST'])
def login(request):
    """POST /api/auth/login/"""
    # Tìm customer, kiểm tra mật khẩu, tạo JWT
    return {"token": token, "user": {...}}
```

---

## [services/customer-service/cart/models.py](../services/customer-service/cart/models.py)

```python
class Cart(models.Model):
    customer_id = IntegerField(unique=True)  # Mỗi customer chỉ có 1 giỏ hàng
    created_at  = DateTimeField(auto_now_add=True)
    updated_at  = DateTimeField(auto_now=True)

class CartItem(models.Model):
    PRODUCT_TYPE = [('computer', 'Computer'), ('mobile', 'Mobile')]

    cart         = ForeignKey(Cart, related_name='items')   # Thuộc giỏ hàng nào
    product_id   = IntegerField()                           # ID trong Computer/Mobile Service
    product_type = CharField(choices=PRODUCT_TYPE)          # "computer" hoặc "mobile"
    product_name = CharField(max_length=255)                # Tên sản phẩm (lưu tại thời điểm thêm)
    product_image= CharField(max_length=500)                # URL ảnh
    quantity     = PositiveIntegerField(default=1)
    price        = DecimalField(max_digits=12, decimal_places=2)  # Giá tại thời điểm thêm

    @property
    def subtotal(self):
        return self.price * self.quantity                   # Thành tiền của 1 dòng
```

> **Lưu ý:** `product_id` là ID từ Computer Service hoặc Mobile Service, không phải Customer Service. Nên khi cần lấy chi tiết sản phẩm thì phải gọi sang service kia.

---

## [services/customer-service/orders/models.py](../services/customer-service/orders/models.py)

```python
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),    # Chờ xác nhận
        ('confirmed', 'Confirmed'),  # Đã xác nhận
        ('shipping',  'Shipping'),   # Đang giao
        ('completed', 'Completed'),  # Hoàn thành
        ('cancelled', 'Cancelled'),  # Đã huỷ
    ]

    customer_id      = IntegerField()           # ID khách hàng (từ JWT)
    total_amount     = DecimalField(14, 2)      # Tổng tiền
    status           = CharField(choices=STATUS, default='pending')
    shipping_address = TextField()              # Địa chỉ giao hàng
    phone            = CharField(max_length=20)
    note             = TextField(blank=True)    # Ghi chú của khách
    created_at       = DateTimeField(auto_now_add=True)
    updated_at       = DateTimeField(auto_now=True)


class OrderItem(models.Model):
    order        = ForeignKey(Order, related_name='items')
    product_id   = IntegerField()               # ID sản phẩm
    product_type = CharField(choices=[...])     # computer hoặc mobile
    product_name = CharField(max_length=255)    # Tên (lưu tại thời điểm đặt)
    quantity     = PositiveIntegerField()
    price        = DecimalField(12, 2)          # Giá tại thời điểm đặt
```

---

## [services/customer-service/orders/views.py](../services/customer-service/orders/views.py)

**Đây là file quan trọng và phức tạp nhất trong toàn bộ project.**

### Hàm `order_list_create()` — GET danh sách / POST tạo đơn

```python
# GET — Xem đơn hàng
if request.method == "GET":
    if user_type == "staff":
        queryset = Order.objects.all()     # Staff xem được tất cả đơn
    else:
        queryset = Order.objects.filter(customer_id=customer_id)  # Customer chỉ xem của mình
```

```python
# POST — Tạo đơn hàng (LOGIC PHỨC TẠP)
elif request.method == "POST":
    # 1. Lấy giỏ hàng của customer
    cart = Cart.objects.get(customer_id=customer_id)

    # 2. Kiểm tra tồn kho từng sản phẩm
    for item in cart.items.all():
        current_stock = get_product_stock(item.product_id, item.product_type)
        if current_stock < item.quantity:
            return 400 "Not enough stock"

    # 3. Tạo Order + OrderItems trong 1 transaction (nguyên tử)
    with transaction.atomic():
        order = Order.objects.create(
            customer_id=customer_id,
            total_amount=sum(item.subtotal for item in cart_items),
            shipping_address=data['shipping_address'],
            phone=data['phone'],
        )
        for item in cart_items:
            OrderItem.objects.create(order=order, ...)

        # 4. Trừ kho từng sản phẩm (gọi sang Computer/Mobile Service)
        for item in cart_items:
            new_stock = get_product_stock(item.product_id, item.product_type) - item.quantity
            update_product_stock(item.product_id, item.product_type, new_stock)

        # 5. Xoá giỏ hàng sau khi đặt hàng thành công
        cart.items.all().delete()

    return 201 OrderSerializer(order).data
```

### Hàm helper gọi sang service khác:

```python
def get_product_stock(product_id, product_type):
    """Gọi Computer/Mobile Service để lấy tồn kho hiện tại"""
    if product_type == "computer":
        url = f"{settings.COMPUTER_SERVICE_URL}/api/computers/{product_id}/"
    else:
        url = f"{settings.MOBILE_SERVICE_URL}/api/mobiles/{product_id}/"
    response = requests.get(url, timeout=5)
    return response.json().get("stock", 0)

def update_product_stock(product_id, product_type, new_stock):
    """Gọi Computer/Mobile Service để cập nhật tồn kho"""
    if product_type == "computer":
        url = f"{settings.COMPUTER_SERVICE_URL}/api/computers/{product_id}/stock/"
    else:
        url = f"{settings.MOBILE_SERVICE_URL}/api/mobiles/{product_id}/stock/"
    requests.patch(url, json={"stock": new_stock}, timeout=5)
```

---

## [services/customer-service/reviews/models.py](../services/customer-service/reviews/models.py)

```python
class Review(models.Model):
    customer_id   = IntegerField()
    customer_name = CharField(max_length=255)  # Lưu tên (tránh join cross-service)
    product_id    = IntegerField()
    product_type  = CharField(choices=[('computer',...), ('mobile',...)])
    rating        = IntegerField()              # Điểm 1-5 sao
    comment       = TextField()
    created_at    = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['customer_id', 'product_id', 'product_type']
        # Mỗi customer chỉ được đánh giá 1 sản phẩm 1 lần
```

---

# 💻 COMPUTER SERVICE (`services/computer-service/`)

## Mục đích
Quản lý toàn bộ **máy tính** (laptop, desktop): CRUD sản phẩm, danh mục, cấu hình kỹ thuật, tồn kho.

## Cấu trúc thư mục

```
services/computer-service/
├── Dockerfile
├── manage.py
├── requirements.txt               ← Django, DRF, psycopg2 (PostgreSQL driver)
├── computer_service/
│   ├── settings.py                ← ⭐ PostgreSQL, DRF, JWT
│   └── urls.py                    ← /health, /api/computers/, /api/categories/
├── computers/
│   ├── models.py                  ← ⭐ Computer, ComputerSpec
│   ├── serializers.py             ← Chuyển object ↔ JSON
│   ├── views.py                   ← ⭐ CRUD + stock update endpoint
│   └── urls.py
└── categories/
    ├── models.py                  ← ⭐ ComputerCategory
    ├── serializers.py
    ├── views.py                   ← CRUD danh mục
    └── urls.py
```

---

## [services/computer-service/computer_service/settings.py](../services/computer-service/computer_service/settings.py)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',   # Dùng PostgreSQL
        'NAME': 'computer_db',
        'HOST': 'computer-db',  # Docker DNS
        'PORT': '5432',
    }
}
```

---

## [services/computer-service/computers/models.py](../services/computer-service/computers/models.py)

```python
class Computer(models.Model):
    STATUS = [('available', 'Available'), ('unavailable', 'Unavailable')]

    name        = CharField(max_length=255)        # "MacBook Pro M3"
    brand       = CharField(max_length=100)        # "Apple"
    price       = DecimalField(max_digits=12, 2)   # 35000000.00
    description = TextField()
    image       = CharField(max_length=500)        # URL ảnh
    stock       = PositiveIntegerField(default=0)  # ⭐ Tồn kho
    status      = CharField(choices=STATUS)        # available/unavailable
    category    = ForeignKey(ComputerCategory)     # Laptop/Desktop/...
    created_at  = DateTimeField(auto_now_add=True)
    updated_at  = DateTimeField(auto_now=True)


class ComputerSpec(models.Model):
    """Cấu hình kỹ thuật chi tiết — quan hệ 1-1 với Computer"""
    computer    = OneToOneField(Computer, related_name='specs')
    cpu         = CharField()   # "Intel Core i7-13700H"
    ram         = CharField()   # "16GB DDR5"
    storage     = CharField()   # "512GB NVMe SSD"
    gpu         = CharField()   # "NVIDIA RTX 4060"
    screen_size = CharField()   # "15.6 inch"
    os          = CharField()   # "Windows 11"
```

---

## [services/computer-service/computers/views.py](../services/computer-service/computers/views.py)

```python
@api_view(["GET", "POST"])
def computer_list_create(request):
    """GET: Danh sách (có filter/search/sort) | POST: Tạo mới (Staff only)"""

    if request.method == "GET":
        queryset = Computer.objects.select_related("category").all()

        # Filter theo từng điều kiện query param
        search    = request.query_params.get("search")    # ?search=MacBook
        brand     = request.query_params.get("brand")     # ?brand=Apple
        category  = request.query_params.get("category")  # ?category=1
        price_min = request.query_params.get("price_min") # ?price_min=10000000
        price_max = request.query_params.get("price_max") # ?price_max=50000000
        ordering  = request.query_params.get("ordering")  # ?ordering=-price (đắt nhất trước)
        # ... filter, paginate, return

    if request.method == "POST":
        # Chỉ staff có quyền tạo sản phẩm mới
        # Đọc header X-User-Type từ Gateway
        forbidden = _require_staff_user(request)


def computer_stock_update(request, pk):
    """PATCH /api/computers/<pk>/stock/ — Cập nhật tồn kho"""
    # Cho phép: Staff (qua Gateway) HOẶC Customer Service (internal call)
    forbidden = _allow_stock_update(request)  
    # Kiểm tra: X-User-Type == "staff" OR X-Internal-Service == "customer-service"
```

> **`_allow_stock_update` quan trọng:** Endpoint `/stock/` phải được gọi bởi 2 nguồn: Staff (qua Gateway để nhập hàng) và Customer Service (internal, khi checkout để trừ kho tự động). Hàm này cho phép cả hai.

---

## [services/computer-service/categories/models.py](../services/computer-service/categories/models.py)

```python
class ComputerCategory(models.Model):
    name        = CharField(max_length=100, unique=True)  # "Laptop Gaming", "MacBook"
    description = TextField()

    class Meta:
        db_table = 'computer_categories'
```

---

# 📱 MOBILE SERVICE (`services/mobile-service/`)

## Mục đích
Giống Computer Service nhưng cho **điện thoại**. Cấu trúc gần như giống hệt, chỉ khác ở model specs.

## Cấu trúc thư mục

```
services/mobile-service/
├── Dockerfile
├── manage.py
├── requirements.txt
├── mobile_service/
│   ├── settings.py     ← ⭐ PostgreSQL (mobile-db)
│   └── urls.py         ← /health, /api/mobiles/, /api/categories/
├── mobiles/
│   ├── models.py       ← ⭐ Mobile, MobileSpec
│   ├── serializers.py
│   ├── views.py        ← ⭐ CRUD + stock update
│   └── urls.py
└── categories/
    ├── models.py       ← ⭐ MobileCategory
    ├── serializers.py
    ├── views.py
    └── urls.py
```

---

## [services/mobile-service/mobiles/models.py](../services/mobile-service/mobiles/models.py)

```python
class Mobile(models.Model):
    name        = CharField(max_length=255)   # "iPhone 15 Pro"
    brand       = CharField(max_length=100)   # "Apple"
    price       = DecimalField(12, 2)         # 27000000.00
    description = TextField()
    image       = CharField(max_length=500)
    stock       = PositiveIntegerField()      # ⭐ Tồn kho
    status      = CharField(choices=STATUS)
    category    = ForeignKey(MobileCategory)
    created_at  = DateTimeField(auto_now_add=True)
    updated_at  = DateTimeField(auto_now=True)


class MobileSpec(models.Model):
    """Cấu hình kỹ thuật — khác Computer ở chỗ có battery, camera"""
    mobile      = OneToOneField(Mobile, related_name='specs')
    screen_size = CharField()    # "6.1 inch"
    battery     = CharField()    # "3279 mAh"
    camera      = CharField()    # "48MP Main + 12MP Ultra Wide"
    storage     = CharField()    # "256GB"
    ram         = CharField()    # "8GB"
    os          = CharField()    # "iOS 17"
```

**Điểm khác biệt so với Computer:**
- `MobileSpec` có `battery`, `camera` thay vì `cpu`, `gpu`, `screen_size`
- Database: `mobile-db` (PostgreSQL riêng, port 5433)
- URL prefix: `/api/mobiles/` thay vì `/api/computers/`

---

# 🔗 GIAO TIẾP GIỮA SERVICES

## Cách services đọc thông tin user

Khi Gateway forward request, nó thêm headers:
```
X-User-ID:   4          ← customer_id hoặc staff_id
X-Username:  customer_1
X-User-Type: customer   ← "customer" hoặc "staff"
X-User-Role: admin      ← chỉ có với staff
```

Trong mỗi service, đọc header bằng:
```python
customer_id = request.META.get("HTTP_X_USER_ID")    # Django đổi X-User-ID → HTTP_X_USER_ID
user_type   = request.META.get("HTTP_X_USER_TYPE")
user_role   = request.META.get("HTTP_X_USER_ROLE")
```

## Customer Service → Computer/Mobile Service

Khi **checkout**, Customer Service gọi nội bộ sang service khác:
```python
# Kiểm tra còn hàng không
GET http://computer-service:8003/api/computers/58/
→ {id:58, name:"...", stock:10, ...}

# Trừ kho sau khi đặt thành công
PATCH http://computer-service:8003/api/computers/58/stock/
Body: {"stock": 9}
Header: {"X-Internal-Service": "customer-service"}
```

Computer Service nhận và xác nhận:
```python
def _allow_stock_update(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type == "staff":
        return None  # ✅ Staff được phép

    internal = request.META.get("HTTP_X_INTERNAL_SERVICE")
    if internal == "customer-service":
        return None  # ✅ Customer Service được phép gọi nội bộ
```

---

# 📊 BẢNG TÓM TẮT FILE QUAN TRỌNG

| File | Mục đích |
|------|---------|
| [gateway/gateway/settings.py](../gateway/gateway/settings.py) | Cấu hình Gateway, service URLs, không có DB |
| [gateway/gateway/urls.py](../gateway/gateway/urls.py) | Route mapping: URL → proxy function |
| [gateway/proxy/views.py](../gateway/proxy/views.py) | JWT verify + forward request (trái tim Gateway) |
| [staff-service/staff/models.py](../services/staff-service/staff/models.py) | Model nhân viên (username, password hash, role) |
| [staff-service/authentication/views.py](../services/staff-service/authentication/views.py) | Login → JWT, verify token |
| [staff-service/staff/views.py](../services/staff-service/staff/views.py) | CRUD nhân viên, phân quyền staff/admin |
| [customer-service/customers/models.py](../services/customer-service/customers/models.py) | Model khách hàng |
| [customer-service/cart/models.py](../services/customer-service/cart/models.py) | Cart + CartItem (giỏ hàng) |
| [customer-service/orders/models.py](../services/customer-service/orders/models.py) | Order + OrderItem (đơn hàng, trạng thái) |
| [customer-service/orders/views.py](../services/customer-service/orders/views.py) | Tạo đơn hàng: kiểm tra kho, trừ kho, atomic transaction |
| [customer-service/reviews/models.py](../services/customer-service/reviews/models.py) | Đánh giá sản phẩm (rating 1-5) |
| [customer-service/authentication/views.py](../services/customer-service/authentication/views.py) | Đăng ký, đăng nhập khách hàng → JWT |
| [computer-service/computers/models.py](../services/computer-service/computers/models.py) | Computer + ComputerSpec (cấu hình kỹ thuật) |
| [computer-service/computers/views.py](../services/computer-service/computers/views.py) | CRUD máy tính, filter/search, stock update endpoint |
| [computer-service/categories/models.py](../services/computer-service/categories/models.py) | Danh mục máy tính |
| [mobile-service/mobiles/models.py](../services/mobile-service/mobiles/models.py) | Mobile + MobileSpec (battery, camera) |
| [mobile-service/mobile_service/urls.py](../services/mobile-service/mobile_service/urls.py) | Route: /api/mobiles/, /api/categories/ |
