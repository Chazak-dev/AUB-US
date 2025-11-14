# init_database.py
import sqlite3
import os

def initialize_database():
    # Remove existing database if you want to start fresh
    db_path = "C:/Users/itsch/Desktop/aubus.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Creating database tables...")
    
    # Users table (referenced in auth.py)
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            address TEXT NOT NULL,
            photo TEXT,
            is_driver BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'users' table")
    
    # Profiles table (referenced in profile.py)
    cursor.execute("""
        CREATE TABLE profiles (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            area TEXT,
            is_driver BOOLEAN DEFAULT 0,
            profile_photo_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'profiles' table")
    
    # Sessions table (referenced in auth.py)
    cursor.execute("""
        CREATE TABLE sessions (
            user_id INTEGER,
            session_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, session_token)
        )
    """)
    print("✓ Created 'sessions' table")
    
    # Ride requests table (referenced in ride.py)
    cursor.execute("""
        CREATE TABLE ride_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_id INTEGER NOT NULL,
            pickup_area TEXT NOT NULL,
            destination TEXT NOT NULL,
            request_time TIMESTAMP NOT NULL,
            preferred_vehicle_type TEXT,
            status TEXT DEFAULT 'pending',
            is_locked BOOLEAN DEFAULT 0,
            accepted_driver_id INTEGER,
            acceptance_time TIMESTAMP,
            completion_time TIMESTAMP,
            fare_final REAL,
            current_status TEXT,
            eta_minutes INTEGER,
            current_location TEXT,
            FOREIGN KEY (passenger_id) REFERENCES users (id),
            FOREIGN KEY (accepted_driver_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'ride_requests' table")
    
    # Driver status table (referenced in driver.py)
    cursor.execute("""
        CREATE TABLE driver_status (
            user_id INTEGER PRIMARY KEY,
            is_online BOOLEAN DEFAULT 0,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'driver_status' table")
    
    # Drivers table (for availability - referenced in realtime_availability.py)
    cursor.execute("""
        CREATE TABLE drivers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            vehicle TEXT,
            availability INTEGER DEFAULT 0
        )
    """)
    print("✓ Created 'drivers' table")
    
    # Driver status logs (referenced in realtime_availability.py)
    cursor.execute("""
        CREATE TABLE driver_status_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'driver_status_logs' table")
    
    # Ride ratings table (referenced in rating.py)
    cursor.execute("""
        CREATE TABLE ride_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            rater_id INTEGER,
            target_id INTEGER,
            target_role TEXT,
            rating INTEGER,
            comment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES ride_requests (request_id)
        )
    """)
    print("✓ Created 'ride_ratings' table")
    
    # Chat messages table (referenced in chat_and_communications.py)
    cursor.execute("""
        CREATE TABLE chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            sender_id INTEGER,
            message_text TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES ride_requests (request_id)
        )
    """)
    print("✓ Created 'chat_messages' table")
    
    # Chat media table (referenced in chat_and_communications.py)
    cursor.execute("""
        CREATE TABLE chat_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            sender_id INTEGER,
            media_type TEXT,
            media_data TEXT,
            file_extension TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'chat_media' table")
    
    # Chat status table (referenced in chat_and_communications.py)
    cursor.execute("""
        CREATE TABLE chat_status (
            user_id INTEGER PRIMARY KEY,
            status TEXT,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'chat_status' table")
    
    # Notifications table (referenced in notifications.py)
    cursor.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            notification_type TEXT,
            title TEXT,
            message TEXT,
            related_id INTEGER,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'notifications' table")
    
    # Ride locations table (referenced in ride.py)
    cursor.execute("""
        CREATE TABLE ride_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            user_id INTEGER,
            latitude REAL,
            longitude REAL,
            timestamp TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES ride_requests (request_id)
        )
    """)
    print("✓ Created 'ride_locations' table")
    
    # Driver cars table (referenced in driver.py)
    cursor.execute("""
        CREATE TABLE driver_cars (
            user_id INTEGER PRIMARY KEY,
            car_model TEXT,
            car_color TEXT,
            license_plate TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'driver_cars' table")
    
    # Driver routes table (referenced in driver.py)
    cursor.execute("""
        CREATE TABLE driver_routes (
            user_id INTEGER PRIMARY KEY,
            start_location TEXT,
            end_location TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'driver_routes' table")
    
    # Driver schedules table (referenced in driver.py)
    cursor.execute("""
        CREATE TABLE driver_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day TEXT,
            enabled BOOLEAN DEFAULT 0,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("✓ Created 'driver_schedules' table")
    
    # Ride notifications table (referenced in ride.py)
    cursor.execute("""
        CREATE TABLE ride_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            passenger_name TEXT,
            passenger_rating REAL,
            pickup_area TEXT,
            destination TEXT,
            estimated_fare REAL,
            timeout_seconds INTEGER,
            is_locked BOOLEAN
        )
    """)
    print("✓ Created 'ride_notifications' table")
    
    # Ride declines table (referenced in ride.py)
    cursor.execute("""
        CREATE TABLE ride_declines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            request_id INTEGER,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'ride_declines' table")
    
    # Ride cancellations table (referenced in ride.py)
    cursor.execute("""
        CREATE TABLE ride_cancellations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            cancelled_by TEXT,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'ride_cancellations' table")
    
    # Rides table (referenced in data_retrieve.py)
    cursor.execute("""
        CREATE TABLE rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            passenger_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            fare REAL,
            status TEXT DEFAULT 'active'
        )
    """)
    print("✓ Created 'rides' table")
    
    # Add some indexes for better performance
    print("Creating indexes...")
    cursor.execute("CREATE INDEX idx_ride_requests_status ON ride_requests(status)")
    cursor.execute("CREATE INDEX idx_ride_requests_passenger ON ride_requests(passenger_id)")
    cursor.execute("CREATE INDEX idx_chat_messages_request ON chat_messages(request_id)")
    cursor.execute("CREATE INDEX idx_ride_ratings_target ON ride_ratings(target_id, target_role)")
    cursor.execute("CREATE INDEX idx_notifications_user ON notifications(user_id)")
    
    conn.commit()
    conn.close()
    print("\n🎉 Database initialized successfully with ALL required tables!")
    print("You can now run: python server.py")

if __name__ == "__main__":
    initialize_database()