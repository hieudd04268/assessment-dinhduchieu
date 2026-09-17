# Manual Test Plan: Fabbi Todo App — Authentication & Authorization

## 1. Scope & Objective
- **Mục tiêu kiểm thử**: Xác thực các tính năng Authentication, Authorization, Todo CRUD, Caching sau khi fix các bug.
- **Phạm vi kiểm thử**: Register, Login, JWT Token validation, Todo CRUD, Cross-user data isolation, Cache invalidation.

## 2. Test Environment & Prerequisites
- **Base URL Backend**: `http://localhost:8000`
- **Base URL Frontend**: `http://localhost:5174` (Vite dev server)
- **API Docs**: `http://localhost:8000/docs`
- **Test Database**: PostgreSQL (Docker container `test-postgres-1`)
- **Cache**: Redis (Docker container `test-redis-1`)
- **Pre-seeded Demo Account**: `demo@test.com` / `Demo@123`

## 3. Test Cases Matrix

| TC ID | Module / Feature | Test Scenario                                                    | Preconditions              | Test Steps                                                                 | Expected Result                                                                 | Priority / Severity | Status |
|-------|------------------|------------------------------------------------------------------|----------------------------|----------------------------------------------------------------------|---------------------------------------------------------------------------------|---------------------|-------|
| TC-01 | Auth             | Register thành công với email mới                                | Backend đang chạy          | 1. POST /api/v1/auth/register với email/pass mới<br>2. Kiểm tra response   | HTTP 201, trả về access_token + refresh_token                                   | High / Blocker      | Pass   |
| TC-02 | Auth             | Register thất bại với email đã tồn tại                           | User đã đăng ký            | 1. POST /api/v1/auth/register với email cũ<br>2. Kiểm tra response         | HTTP 400, detail "Email already registered"                                     | Medium / Major      | Pass   |
| TC-03 | Auth             | Login thành công với credentials đúng                            | User đã đăng ký            | 1. POST /api/v1/auth/login với email/pass đúng<br>2. Kiểm tra response     | HTTP 200, trả về access_token + refresh_token                                   | High / Blocker      | Pass   |
| TC-04 | Auth             | Login thất bại với mật khẩu sai (User Enumeration protection)    | User đã đăng ký            | 1. POST /api/v1/auth/login với email đúng, pass sai<br>2. Kiểm tra response | HTTP 401, detail "Incorrect password"                                           | Medium / Security   | Pass   |
| TC-05 | Auth             | Login thất bại với user không tồn tại                            | -                          | 1. POST /api/v1/auth/login với email không tồn tại<br>2. Kiểm tra response  | HTTP 404, detail "User with this email not found"                               | Medium / Security   | Pass   |
| TC-06 | Auth             | JWT token hết hạn bị từ chối                                     | Có valid token             | 1. Tạo token với expires_delta=-1s<br>2. GET /api/v1/auth/me với token đó  | HTTP 401, detail "Invalid authentication token"                                 | High / Critical     | Pass   |
| TC-07 | Auth             | JWT token bị chỉnh sửa (tampered) bị từ chối                     | Có valid token             | 1. Lấy valid token, thay đổi 1 ký tự cuối<br>2. GET /api/v1/auth/me với token đó | HTTP 401, detail "Invalid authentication token"                              | High / Critical     | Pass   |
| TC-08 | Auth             | Refresh token tạo access token mới                               | Có valid refresh token     | 1. POST /api/v1/auth/refresh với refresh_token<br>2. Kiểm tra response     | HTTP 200, trả về access_token + refresh_token mới                               | High / Blocker      | Pass   |
| TC-09 | Auth             | Logout xóa token client-side                                     | User đã login              | 1. POST /api/v1/auth/logout với access_token<br>2. Kiểm tra response       | HTTP 200, message "Successfully logged out"                                     | Medium / Major      | Pass   |
| TC-10 | Auth             | /me trả về thông tin user hiện tại                               | User đã login, có token    | 1. GET /api/v1/auth/me với Authorization header<br>2. Kiểm tra response    | HTTP 200, trả về id, email, created_at                                          | High / Blocker      | Pass   |
| TC-11 | Todo CRUD        | Tạo todo mới thành công                                          | User đã login              | 1. POST /api/v1/todos với title, description<br>2. Kiểm tra response       | HTTP 201, trả về todo với đúng dữ liệu                                          | High / Blocker      | Pass   |
| TC-12 | Todo CRUD        | Lấy danh sách todo có phân trang                                 | User đã có todo            | 1. GET /api/v1/todos?page=1&size=20<br>2. Kiểm tra response                | HTTP 200, trả về items[], total, page, size                                     | High / Blocker      | Pass   |
| TC-13 | Todo CRUD        | Lấy chi tiết 1 todo                                              | User đã có todo            | 1. GET /api/v1/todos/{id}<br>2. Kiểm tra response                          | HTTP 200, trả về todo đầy đủ                                                    | Medium / Major      | Pass   |
| TC-14 | Todo CRUD        | Cập nhật todo (title, description, completed)                    | User đã có todo            | 1. PUT /api/v1/todos/{id} với dữ liệu mới<br>2. Kiểm tra response          | HTTP 200, dữ liệu cập nhật đúng                                                 | High / Blocker      | Pass   |
| TC-15 | Todo CRUD        | Xóa todo                                                         | User đã có todo            | 1. DELETE /api/v1/todos/{id}<br>2. Kiểm tra response                       | HTTP 204, todo không còn tồn tại                                                | High / Blocker      | Pass   |
| TC-16 | Authorization    | User A KHÔNG đọc được todo của User B                            | User A, B đã có todo       | 1. User B tạo todo<br>2. User A GET /api/v1/todos/{id_B}                   | HTTP 404 Not Found                                                              | High / Critical     | Pass   |
| TC-17 | Authorization    | User A KHÔNG sửa được todo của User B                            | User A, B đã có todo       | 1. User B tạo todo<br>2. User A PUT /api/v1/todos/{id_B}                   | HTTP 404 Not Found                                                              | High / Critical     | Pass   |
| TC-18 | Authorization    | User A KHÔNG xóa được todo của User B                            | User A, B đã có todo       | 1. User B tạo todo<br>2. User A DELETE /api/v1/todos/{id_B}                | HTTP 404 Not Found                                                              | High / Critical     | Pass   |
| TC-19 | Authorization    | User A KHÔNG liệt kê được todo của User B                        | User A, B đã có todo       | 1. User B tạo 2-3 todo<br>2. User A GET /api/v1/todos                      | HTTP 200, chỉ trả về todo của User A (total=0)                                  | High / Critical     | Pass   |
| TC-20 | Logic            | Toggle completed: true → false lưu đúng                          | Todo đang completed=true   | 1. PUT /api/v1/todos/{id} với completed=false<br>2. GET lại todo           | completed=false được lưu và persist                                             | Medium / Major      | Pass   |
| TC-21 | Logic            | Partial update title KHÔNG xóa description                       | Todo có description        | 1. PUT /api/v1/todos/{id} chỉ gửi title<br>2. GET lại todo                 | Description được giữ nguyên                                                     | Medium / Major      | Pass   |
| TC-22 | Cache            | Tạo todo mới vô hiệu hóa cache                                   | Cache đã có dữ liệu        | 1. GET /api/v1/todos (populate cache)<br>2. POST tạo todo mới<br>3. GET lại /api/v1/todos | Trả về dữ liệu mới (total tăng +1), không nhận cache cũ             | Medium / Major      | Pass   |
| TC-23 | Cache            | Cập nhật todo vô hiệu hóa cache                                  | Cache đã có dữ liệu        | 1. GET /api/v1/todos (populate cache)<br>2. PUT cập nhật title<br>3. GET lại /api/v1/todos | Trả về title mới, không nhận cache cũ                              | Medium / Major      | Pass   |
| TC-24 | Cache            | Xóa todo vô hiệu hóa cache                                       | Cache đã có dữ liệu        | 1. GET /api/v1/todos (populate cache)<br>2. DELETE todo<br>3. GET lại /api/v1/todos | Trả về total giảm, không nhận cache cũ                              | Medium / Major      | Pass   |
| TC-25 | Frontend E2E     | Full User Journey: Register → Login → Create → Toggle → Logout   | Frontend + Backend chạy    | 1. Mở /register, điền form, submit<br>2. Tạo todo qua UI<br>3. Toggle checkbox<br>4. Logout | Hoàn thành không lỗi, redirect đúng trang                        | High / Blocker      | Pass   |
| TC-26 | Frontend E2E     | Cross-User Data Isolation: User A không thấy todo của User B     | 2 browser contexts         | 1. User A tạo todo<br>2. Mở context mới cho User B<br>3. User B đăng ký, check danh sách | User B KHÔNG thấy todo của User A                                | High / Critical     | Pass   |
| TC-27 | Frontend Cache   | Đổi tài khoản KHÔNG bị lộ dữ liệu user trước (same browser)      | User A đã login + có todo  | 1. User A tạo todo<br>2. Logout<br>3. Đăng nhập User B (cùng trình duyệt)<br>4. Check dashboard ngay (trong 5 phút) | User B thấy email + todo của User B, KHÔNG thấy dữ liệu User A | High / Critical     | Pass   |

## 4. Automation Coverage Summary
|           Layer          |    Tool    | Tests |                               Coverage                           |
|--------------------------|------------|-------|------------------------------------------------------------------|
| Backend Unit/Integration | pytest |   19  | Auth (8), Todo CRUD (5), Authorization (3), Logic (2), Cache (1) |
| Frontend E2E             | Playwright |   3   | Full Journey (1), Cross-User Isolation (1), Session Switch Cache (1) |

## 5. Defect Tracking & Known Limitations
- **Fixed in this assessment**: 
  1. JWT expiration not verified (security.py:56)
  2. Cache key missing user_id → data leak (todos.py:37)
  3. get_todo missing ownership check (todos.py:92-99)
  4. update_todo broken logic + no ownership + no cache invalidation (todos.py:105-134)
  5. delete_todo missing ownership + no cache invalidation (todos.py:137-155)
  6. Frontend: React key using index instead of todo.id (TodoList.tsx:42)
  7. Frontend: Query key missing page/size params (todos.ts:37)
  8. Frontend: React Query cache không bị xóa khi đổi tài khoản → User B login vẫn thấy data User A trong 5 phút (staleTime). Phải gọi `queryClient.clear()` ở login/register/logout và khi bị 401 (auth.ts:26-28,39-41; useAuth.ts:23-35; api.ts:30-33)
- **Known limitation**: Cache invalidation uses Redis `KEYS` pattern (not production-ready for large datasets; should use SCAN or tag-based invalidation)
- **Out of scope**: Rate limiting, password reset, email verification, multi-factor auth