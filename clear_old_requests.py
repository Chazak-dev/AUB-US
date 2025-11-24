import sqlite3

conn = sqlite3.connect('aubus.db')
cursor = conn.cursor()

# Clear old pending requests
cursor.execute("DELETE FROM ride_requests WHERE status = 'pending'")
deleted = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Cleared {deleted} old pending requests")
print("You can now test with a fresh ride request!")
