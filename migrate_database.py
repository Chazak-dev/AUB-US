#!/usr/bin/env python3
"""
Database Migration Script
Adds driver connection info columns to ride_requests table
"""

import sqlite3
import os
import sys

def migrate_database(db_path="aubus.db"):
    """Add IP/port columns to ride_requests table"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("Please run this script from the AUBus project directory")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        print(f"📂 Connected to database: {db_path}")
        
        # Check if columns already exist
        cur.execute("PRAGMA table_info(ride_requests)")
        columns = [col[1] for col in cur.fetchall()]
        
        changes_made = False
        
        # Add driver_ip column
        if 'driver_ip' not in columns:
            print("➕ Adding column: driver_ip")
            cur.execute("""
                ALTER TABLE ride_requests 
                ADD COLUMN driver_ip VARCHAR(45)
            """)
            changes_made = True
        else:
            print("✅ Column driver_ip already exists")
        
        # Add driver_port column
        if 'driver_port' not in columns:
            print("➕ Adding column: driver_port")
            cur.execute("""
                ALTER TABLE ride_requests 
                ADD COLUMN driver_port INTEGER
            """)
            changes_made = True
        else:
            print("✅ Column driver_port already exists")
        
        # Add driver_p2p_status column
        if 'driver_p2p_status' not in columns:
            print("➕ Adding column: driver_p2p_status")
            cur.execute("""
                ALTER TABLE ride_requests 
                ADD COLUMN driver_p2p_status VARCHAR(20) DEFAULT 'pending'
            """)
            changes_made = True
        else:
            print("✅ Column driver_p2p_status already exists")
        
        if changes_made:
            conn.commit()
            print("\n✅ Database migration completed successfully!")
        else:
            print("\n✅ Database already up to date - no changes needed")
        
        # Verify the changes
        print("\n📊 Current ride_requests schema:")
        cur.execute("PRAGMA table_info(ride_requests)")
        for col in cur.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AUBus Database Migration - Add P2P Connection Fields")
    print("=" * 60)
    print()
    
    # Allow custom database path as argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "aubus.db"
    
    success = migrate_database(db_path)
    
    if success:
        print("\n🎉 Migration complete! You can now run the updated application.")
        sys.exit(0)
    else:
        print("\n❌ Migration failed! Please check the error messages above.")
        sys.exit(1)
