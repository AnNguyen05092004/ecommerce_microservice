# 📋 Khảo Sát Đặc Tả — Website Bán Máy Tính & Điện Thoại

Hãy tích `[x]` vào các lựa chọn phù hợp. Mục nào cần bổ sung thì ghi thêm vào dòng `Khác`.

---

## 1. 🏷️ Tên hệ thống

> Ghi tên bạn muốn đặt: __________________

---

## 2. 👥 Vai trò người dùng (Actors)

- [ x] Khách vãng lai (Guest) — xem sản phẩm, không cần đăng nhập
- [ x] Khách hàng (Customer) — đăng ký, đăng nhập, mua hàng
- [ x] Nhân viên bán hàng (Staff / Sales)
- [ ] Nhân viên kho (Warehouse Staff)
- [ x] Quản trị viên (Admin) — quản lý toàn hệ thống
- [ ] Khác: __________________

---

## 3. ✅ Tính năng chính (In Scope)

### Phía khách hàng (Customer-facing)
- [ x] Xem danh mục sản phẩm (máy tính, điện thoại)
- [ x] Xem chi tiết sản phẩm
- [ x] Tìm kiếm sản phẩm
- [ x] Lọc sản phẩm theo giá / thương hiệu / loại
- [ x] Đăng ký / Đăng nhập
- [ x] Giỏ hàng (thêm, xoá, sửa số lượng)
- [ x] Đặt hàng (checkout)
- [ x] Xem lịch sử đơn hàng
- [ x] Đánh giá / nhận xét sản phẩm
- [ ] Yêu thích (wishlist)
- [ ] So sánh sản phẩm
- [ ] Khác: __________________


### Phía Nhân viên (Staff)
- [ x] Quản lý sản phẩm (CRUD)
- [ x] Quản lý danh mục sản phẩm
- [ x] Quản lý đơn hàng (xem, cập nhật trạng thái)
- [ x] Quản lý khách hàng
- [ x] Quản lý kho hàng / tồn kho
- [ ] Thống kê doanh thu / báo cáo
- [ ] Quản lý khuyến mãi / mã giảm giá
- [ ] Quản lý nhân viên / phân quyền
- [ ] Khác: __________________

### Phía Quản lý (Manager)
- [ ] Quản lý sản phẩm (CRUD)
- [ x] Quản lý danh mục sản phẩm
- [ ] Quản lý đơn hàng (xem, cập nhật trạng thái)
- [ ] Quản lý khách hàng
- [ x] Quản lý kho hàng / tồn kho
- [ x] Thống kê doanh thu / báo cáo
- [ ] Quản lý khuyến mãi / mã giảm giá
- [ x] Quản lý nhân viên / phân quyền
- [ ] Khác: __________________

---

## 4. ❌ Ngoài phạm vi (Out of Scope) — v1

- [ x] Thanh toán online thật (Momo, VNPay, Stripe...)
- [ x] Tích hợp đơn vị vận chuyển (GHN, GHTK...)
- [ x] Chat hỗ trợ trực tuyến
- [ x] Đa ngôn ngữ (i18n)
- [ x] Ứng dụng mobile native
- [ ] Khác: __________________

---

## 5. 📦 Thuộc tính sản phẩm

### Chung (tất cả sản phẩm)
- [ x] Tên sản phẩm
- [ x] Giá
- [ ] Giá khuyến mãi
- [ x] Thương hiệu (brand)
- [ x] Mô tả
- [ x] Ảnh sản phẩm (1 hoặc nhiều ảnh)
- [ x] Số lượng tồn kho
- [ x] Danh mục (category)
- [ x] Trạng thái (còn hàng / hết hàng)
- [ ] Khác: __________________

### Riêng cho Máy tính (Laptop/PC)
- [ x] CPU
- [ x] RAM
- [ x] Ổ cứng (SSD/HDD)
- [ x] Card đồ họa (GPU)
- [ x] Kích thước màn hình
- [ x] Hệ điều hành
- [ ] Khác: __________________

### Riêng cho Điện thoại
- [ x] Kích thước màn hình
- [ x] Dung lượng pin
- [ x] Camera
- [ x] Bộ nhớ trong
- [ x] RAM
- [ x] Hệ điều hành (iOS/Android)
- [ ] Khác: __________________

---

## 6. 🧱 Kiến trúc Microservices

### Các service (Đây là theo yêu cầu của giảng viên, bạn có thể thêm service khác nếu thực sự cần thiết):
-- staff-service
-- customer-service
-- computer-service
-- mobile-service
-- API Gateway** — Routing, xác thực, rate limiting


---

## 7. 🔌 Giao tiếp giữa các Service

- [ x] Chỉ REST API (đồng bộ — đơn giản, đủ cho bài tập)
- [ ] REST API + Message Queue (RabbitMQ) cho một số tác vụ bất đồng bộ
- [ ] REST API + Redis Pub/Sub
- [ ] Khác: __________________

---

## 8. 🗄️ Database: chỉ dùng mysql hoặc posgreSQL, mối service 1 database riêng

- [ x] PostgreSQL (computer, mobile service)
- [ x] MySQL (staff, customer service)
- [ ] SQLite (đơn giản, phù hợp bài tập nhỏ)
- [ ] Mix (VD: PostgreSQL cho chính, Redis cho cache)
- [ ] Khác: __________________

---

## 9. 🔐 Xác thực (Authentication)

- [ x] JWT (JSON Web Token)
- [ ] Session-based
- [ ] Django REST Framework Token Auth
- [ ] Khác: __________________

---

## 10. 🖥️ Frontend

- [ x] Django Templates (server-side rendering — đơn giản, nhanh)
- [ ] React.js (SPA, tách riêng frontend service)
- [ ] Vue.js
- [ ] HTML/CSS/JS thuần
- [ ] Khác: __________________

---

## 11. 🐳 Deployment

- [ x] Docker Compose (đủ cho bài tập)
- [ ] Kubernetes
- [ ] Khác: __________________

---

## 12. 📊 Quy trình nghiệp vụ chính muốn mô tả chi tiết

- [ x] Quy trình mua hàng (browse → cart → checkout → confirm)
- [ x] Quy trình quản lý sản phẩm (admin CRUD)
- [ x] Quy trình xử lý đơn hàng (đặt → xác nhận → giao → hoàn thành)
- [ x] Tất cả các quy trình trên
- [ ] Khác: __________________

---

> 💡 **Hướng dẫn**: Tích `[x]` vào ô bạn chọn, ghi thêm thông tin ở dòng `Khác` nếu cần. Sau khi xong, gửi lại cho tôi để tôi hoàn thiện file `analysis-and-design.md`!
