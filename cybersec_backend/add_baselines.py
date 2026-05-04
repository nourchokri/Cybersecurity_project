#!/usr/bin/env python
"""
Add user baselines to the Behavior Agent database.

This script adds default baselines for real users collected by the Data Agent,
allowing the Behavior Agent to analyze their behavior.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# Path to baselines database
DB_PATH = Path(__file__).parent / 'data' / 'baselines.sqlite'

# Users from your collected data (update this list with your real users)
users_to_add = [
    'moham',
    'MED_AZIZ\\moham',
    # Add more users as needed
]

def add_baseline(cursor, user_id: str):
    """Add a default baseline for a user."""
    cursor.execute('''
        INSERT OR REPLACE INTO baselines (
            user_id, department, last_updated, observation_days, cold_start,
            login_hour_mean, login_hour_std,
            daily_file_access_mean, daily_file_access_std,
            known_devices, recent_scores
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        'IT',  # Department
        datetime.now().isoformat(),
        1,  # observation_days (will increase over time)
        1,  # cold_start = True (will become False after 5 days)
        9.0,  # login_hour_mean (9 AM)
        2.0,  # login_hour_std
        50.0,  # daily_file_access_mean
        15.0,  # daily_file_access_std
        user_id.split('\\')[-1],  # known_devices (just the username)
        '[]'  # recent_scores (empty initially)
    ))

def main():
    """Main function."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Make sure you're running this from the cybersec_backend directory")
        return

    print(f"📂 Database: {DB_PATH}")
    print(f"👥 Adding baselines for {len(users_to_add)} users...\n")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add baseline for each user
    for user_id in users_to_add:
        try:
            add_baseline(cursor, user_id)
            print(f"✅ Added baseline for: {user_id}")
        except Exception as e:
            print(f"❌ Failed to add baseline for {user_id}: {e}")

    conn.commit()
    conn.close()

    print(f"\n🎉 Successfully added {len(users_to_add)} user baselines!")
    print("\n📝 Next steps:")
    print("   1. Restart Django server")
    print("   2. Click 'Start Pipeline' button")
    print("   3. Users should now be analyzed (not skipped)")

if __name__ == '__main__':
    main()
