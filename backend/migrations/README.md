# Alembic Migrations

Thư mục này lưu migration chính thức cho schema backend.

Trạng thái hiện tại:
- `20260411_0001_case_centric_legal_intelligence.py` là baseline cho pha refactor case-centric.
- codebase hiện vẫn dùng `Base.metadata.create_all()` và `schema_bootstrap` để tương thích nhanh với DB đang có.

Hướng sử dụng tiếp theo:
- môi trường mới: ưu tiên chạy Alembic trước
- môi trường dev hiện tại: có thể giữ bootstrap trong giai đoạn chuyển tiếp
- khi schema ổn định hơn, cần giảm dần logic `schema_bootstrap` và chuyển thay đổi schema sang migration
