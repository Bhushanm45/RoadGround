"""Clean test devices from the database, keep only ESP32_BUS_01."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM devices WHERE device_id != 'ESP32_BUS_01'")
print(f"Removed {cursor.rowcount} test device(s). Only ESP32_BUS_01 remains.")
conn.commit()

cursor.execute("SELECT device_id, status, last_seen FROM devices")
for row in cursor.fetchall():
    print(f"  Remaining: {row['device_id']} | status=n/a | last_seen={row['last_seen']}")
conn.close()
