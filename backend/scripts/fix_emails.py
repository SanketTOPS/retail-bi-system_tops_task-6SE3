import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("UPDATE users SET email = REPLACE(email, '.local', '.com')"))
db.commit()
print("Emails updated successfully!")
for row in db.execute(text("SELECT email, role FROM users")).fetchall():
    print(f"User: {row[0]} | Role: {row[1]}")
db.close()
