# fix_db.py
import sqlite3
conn = sqlite3.connect('db/music_crm.sqlite')
cursor = conn.cursor()

# Треки в band_pages
for i in range(1, 4):
    try: cursor.execute(f"ALTER TABLE band_pages ADD COLUMN track{i}_path TEXT")
    except: pass
    try: cursor.execute(f"ALTER TABLE band_pages ADD COLUMN track{i}_name TEXT")
    except: pass

# Просмотры, рейтинг, голоса
try: cursor.execute("ALTER TABLE band_pages ADD COLUMN views INTEGER DEFAULT 0")
except: pass
try: cursor.execute("ALTER TABLE band_pages ADD COLUMN rating REAL DEFAULT 0.0")
except: pass
try: cursor.execute("ALTER TABLE band_pages ADD COLUMN votes INTEGER DEFAULT 0")
except: pass

# Поля представителя в users
try: cursor.execute("ALTER TABLE users ADD COLUMN rep_name TEXT")
except: pass
try: cursor.execute("ALTER TABLE users ADD COLUMN rep_email TEXT")
except: pass

conn.commit()
conn.close()
print("✅ База обновлена!")