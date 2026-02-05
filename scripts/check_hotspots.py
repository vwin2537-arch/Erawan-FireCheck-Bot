"""Check hotspots data in database"""
import sqlite3
from datetime import date, datetime

conn = sqlite3.connect('firms_bot.db')
cur = conn.cursor()

print("=" * 60)
print("HOTSPOTS DATABASE CHECK")
print("=" * 60)

# Total count
cur.execute('SELECT COUNT(*) FROM hotspots')
print(f"\nTotal hotspots in DB: {cur.fetchone()[0]}")

# Today's data
today = date.today().isoformat()
cur.execute('SELECT COUNT(*) FROM hotspots WHERE acq_date = ?', (today,))
print(f"Hotspots for today ({today}): {cur.fetchone()[0]}")

# Recent check logs
print("\n--- Recent Check Logs ---")
cur.execute('SELECT checked_at, hotspots_found, new_hotspots, status FROM check_logs ORDER BY id DESC LIMIT 10')
for row in cur.fetchall():
    print(f"  {row[0]} | Found: {row[1]} | New: {row[2]} | {row[3]}")

# Recent hotspots
print("\n--- Most Recent Hotspots (last 15) ---")
cur.execute('SELECT id, acq_date, acq_time, satellite, created_at FROM hotspots ORDER BY id DESC LIMIT 15')
for row in cur.fetchall():
    print(f"  ID:{row[0]} | {row[1]} {row[2]} | {row[3]} | created: {row[4]}")

# Group by date
print("\n--- Hotspots by Date ---")
cur.execute('SELECT acq_date, COUNT(*) FROM hotspots GROUP BY acq_date ORDER BY acq_date DESC LIMIT 7')
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} จุด")

conn.close()
