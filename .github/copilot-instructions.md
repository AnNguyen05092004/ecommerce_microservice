# GitHub Copilot — Custom Instructions
# Docs: https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions
#
# Full project rules and context: .ai/AGENTS.md
# This file contains a summary for Copilot. Edit .ai/AGENTS.md for the source of truth.

## Project

Microservices university assignment. Technology-agnostic.
Run with: `docker compose up --build`

## Key Rules

- Every service exposes `GET /health` → `{"status": "ok"}`
- Services communicate via Docker Compose DNS (service names, not localhost)
- API specs in `docs/api-specs/*.yaml` (OpenAPI 3.0)
- Use environment variables for config — never hardcode secrets
- Code runs inside Docker containers
- Follow OpenAPI specs when implementing endpoints
- Generate tests alongside code
<!-- - Mỗi khi tạo api, create dockerfile, debugging, create new-service, testing hay vào .ai/prompts/ để lấy prompt phù hợp với yêu cầu và custom lại cho phù hợp  -->


## Requirement: Xây dựng website bán laptop, điện thoại
1. Tạo các service
-- staff-service
-- customer-service
-- computer-service
-- mobile-service

2. 
Staff 
- Đăng nhập
- Nhập hàng
- Câp nhật
Giao diện web cho staff khác với customer,staff có thể quản lý sản phẩm, đơn hàng,... trong khi customer chỉ có thể mua hàng, xem đơn hàng của mình, đánh giá sản phẩm,...
2 giao diện khác nhau cho loại mặt hàng
-- Giao diện computer
-- Giao diện mobile

Customer
- Đăng nhập
- Tạo giỏ hàng
- Giao diện web khác với staff

3. Database
- Mỗi service có database riêng
- Staff, customer: dùng mySQL
- computer, mobile: dùng posgreSQL

