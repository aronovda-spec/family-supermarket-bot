#!/usr/bin/env python3
"""
Optional: Migrate SQLite Data to Neon PostgreSQL
Only use this if you want to transfer existing SQLite data to Neon
"""

import os
import sys
from dotenv import load_dotenv

print("="*70)
print("SQLite to Neon PostgreSQL Data Migration")
print("="*70)

# Load environment
load_dotenv('bot_config.env')

# Check if SQLite database exists
sqlite_db = os.getenv('DATABASE_PATH', 'shopping_bot.db')
if not os.path.exists(sqlite_db):
    print(f"\n❌ SQLite database not found: {sqlite_db}")
    print("   Nothing to migrate.")
    sys.exit(0)

# Check if DATABASE_URL is set
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("\n❌ DATABASE_URL not set!")
    print("   Set DATABASE_URL to your Neon connection string first.")
    sys.exit(1)

print(f"\n📊 Source: SQLite ({sqlite_db})")
print(f"📊 Destination: Neon PostgreSQL")

# Confirm migration
response = input("\n⚠️ This will copy data from SQLite to Neon.\n   Continue? (yes/no): ")
if response.lower() != 'yes':
    print("Migration cancelled.")
    sys.exit(0)

try:
    import sqlite3
    import psycopg2
    
    # Connect to both databases
    print("\n🔌 Connecting to databases...")
    sqlite_conn = sqlite3.connect(sqlite_db)
    neon_conn = psycopg2.connect(database_url)
    
    sqlite_cursor = sqlite_conn.cursor()
    neon_cursor = neon_conn.cursor()
    
    print("✅ Connected to both databases")
    
    # Migrate users
    print("\n👥 Migrating users...")
    sqlite_cursor.execute('SELECT user_id, username, first_name, last_name, is_admin, is_authorized, language, created_at FROM users')
    users = sqlite_cursor.fetchall()
    
    migrated_users = 0
    for user in users:
        try:
            neon_cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, is_admin, is_authorized, language, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                is_admin = EXCLUDED.is_admin,
                is_authorized = EXCLUDED.is_authorized,
                language = EXCLUDED.language
            ''', user)
            migrated_users += 1
        except Exception as e:
            print(f"   ⚠️ Error migrating user {user[0]}: {e}")
    
    print(f"   ✅ Migrated {migrated_users} users")
    
    # Migrate lists
    print("\n📋 Migrating lists...")
    sqlite_cursor.execute('SELECT id, name, description, list_type, created_by, is_active, is_frozen, frozen_at, created_at FROM lists')
    lists = sqlite_cursor.fetchall()
    
    migrated_lists = 0
    for lst in lists:
        try:
            neon_cursor.execute('''
                INSERT INTO lists (id, name, description, list_type, created_by, is_active, is_frozen, frozen_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                list_type = EXCLUDED.list_type,
                is_active = EXCLUDED.is_active,
                is_frozen = EXCLUDED.is_frozen
            ''', lst)
            migrated_lists += 1
        except Exception as e:
            print(f"   ⚠️ Error migrating list {lst[0]}: {e}")
    
    print(f"   ✅ Migrated {migrated_lists} lists")
    
    # Migrate shopping items
    print("\n🛒 Migrating shopping items...")
    sqlite_cursor.execute('SELECT id, list_id, item_name, category, notes, added_by, created_at FROM shopping_items')
    items = sqlite_cursor.fetchall()
    
    migrated_items = 0
    for item in items:
        try:
            neon_cursor.execute('''
                INSERT INTO shopping_items (id, list_id, item_name, category, notes, added_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', item)
            migrated_items += 1
        except Exception as e:
            print(f"   ⚠️ Error migrating item {item[0]}: {e}")
    
    print(f"   ✅ Migrated {migrated_items} shopping items")
    
    # Commit changes
    neon_conn.commit()
    
    # Close connections
    sqlite_conn.close()
    neon_conn.close()
    
    print("\n" + "="*70)
    print("✅ Migration Complete!")
    print("="*70)
    print(f"   Users: {migrated_users}")
    print(f"   Lists: {migrated_lists}")
    print(f"   Items: {migrated_items}")
    print("\n💡 Verify in Neon SQL Editor:")
    print("   SELECT COUNT(*) FROM users;")
    print("   SELECT COUNT(*) FROM lists;")
    print("   SELECT COUNT(*) FROM shopping_items;")
    
except ImportError as e:
    print(f"\n❌ Missing dependency: {e}")
    print("   Install with: pip install psycopg2-binary")
except Exception as e:
    print(f"\n❌ Migration error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

