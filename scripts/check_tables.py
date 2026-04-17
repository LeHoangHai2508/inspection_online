import sqlite3
from pathlib import Path

# Đường dẫn tới file database
db_path = Path("data/sqlite/inspection.db")

# In ra để kiểm tra chắc chắn đang trỏ đúng file
print("DB exists:", db_path.exists())
print("DB path:", db_path.resolve())

# Kết nối SQLite
conn = sqlite3.connect(db_path)

# Lấy danh sách bảng
rows = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
).fetchall()

print("Tables:", rows)

conn.close()