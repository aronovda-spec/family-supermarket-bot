import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_admin BOOLEAN DEFAULT FALSE,
                        is_authorized BOOLEAN DEFAULT FALSE,
                        language TEXT DEFAULT 'en',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Lists table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS lists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        list_type TEXT DEFAULT 'custom',
                        created_by INTEGER,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Shopping items table (now with list_id)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shopping_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        list_id INTEGER DEFAULT 1,
                        item_name TEXT NOT NULL,
                        category TEXT,
                        notes TEXT,
                        added_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (list_id) REFERENCES lists (id),
                        FOREIGN KEY (added_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Item notes table (for handling multiple notes from different users)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS item_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_id INTEGER,
                        user_id INTEGER,
                        note TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (item_id) REFERENCES shopping_items (id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Broadcast messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS broadcast_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER,
                        message TEXT NOT NULL,
                        sent_to_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sender_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Item suggestions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS item_suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        suggested_by INTEGER,
                        category_key TEXT NOT NULL,
                        item_name_en TEXT NOT NULL,
                        item_name_he TEXT,
                        status TEXT DEFAULT 'pending',
                        approved_by INTEGER,
                        approved_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (suggested_by) REFERENCES users (user_id),
                        FOREIGN KEY (approved_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Maintenance mode table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS maintenance_mode (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        list_id INTEGER DEFAULT 1,
                        scheduled_day TEXT NOT NULL,
                        scheduled_time TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_reminder TIMESTAMP,
                        reminder_count INTEGER DEFAULT 0,
                        created_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (list_id) REFERENCES lists (id),
                        FOREIGN KEY (created_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Create default supermarket list if it doesn't exist
                cursor.execute('SELECT COUNT(*) FROM lists WHERE list_type = "supermarket"')
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO lists (id, name, description, list_type, created_by)
                        VALUES (1, "Supermarket List", "Weekly family shopping list", "supermarket", 1)
                    ''')
                
                # Ensure supermarket list always exists and is protected
                self._ensure_supermarket_list_protection(cursor)
                
                # Migration: Add list_id column to shopping_items if it doesn't exist
                try:
                    cursor.execute('ALTER TABLE shopping_items ADD COLUMN list_id INTEGER DEFAULT 1')
                    print("Added list_id column to shopping_items table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("list_id column already exists in shopping_items table")
                    else:
                        print(f"Error adding list_id column: {e}")
                
                # Migration: Add list_id column to item_suggestions if it doesn't exist
                try:
                    cursor.execute('ALTER TABLE item_suggestions ADD COLUMN list_id INTEGER DEFAULT 1')
                    print("Added list_id column to item_suggestions table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("list_id column already exists in item_suggestions table")
                    else:
                        print(f"Error adding list_id column to item_suggestions: {e}")
                
                # Custom categories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS custom_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_key TEXT UNIQUE NOT NULL,
                        emoji TEXT NOT NULL,
                        name_en TEXT NOT NULL,
                        name_he TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Category suggestions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS category_suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        suggested_by INTEGER NOT NULL,
                        category_key TEXT NOT NULL,
                        emoji TEXT NOT NULL,
                        name_en TEXT NOT NULL,
                        name_he TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        approved_by INTEGER,
                        approved_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (suggested_by) REFERENCES users (user_id),
                        FOREIGN KEY (approved_by) REFERENCES users (user_id)
                    )
                ''')
                
                # Deleted items table (items permanently removed from categories)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS deleted_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_key TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        deleted_by INTEGER,
                        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (deleted_by) REFERENCES users(user_id)
                    )
                ''')
                
                # Dynamic category items table (for approved suggestions)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dynamic_category_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_key TEXT NOT NULL,
                        item_name_en TEXT NOT NULL,
                        item_name_he TEXT,
                        added_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (added_by) REFERENCES users(user_id)
                    )
                ''')
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")

    def _ensure_supermarket_list_protection(self, cursor):
        """Ensure the supermarket list is always protected and exists"""
        try:
            # Check if supermarket list exists
            cursor.execute('SELECT id, name, list_type FROM lists WHERE list_type = "supermarket"')
            supermarket_list = cursor.fetchone()
            
            if not supermarket_list:
                # Create supermarket list if it doesn't exist
                cursor.execute('''
                    INSERT INTO lists (id, name, description, list_type, created_by)
                    VALUES (1, "Supermarket List", "Weekly family shopping list", "supermarket", 1)
                ''')
                logging.info("Created protected supermarket list")
            else:
                # Ensure it has the correct properties
                list_id, name, list_type = supermarket_list
                
                # If somehow the list_type was changed, fix it
                if list_type != 'supermarket':
                    cursor.execute('UPDATE lists SET list_type = "supermarket" WHERE id = ?', (list_id,))
                    logging.warning(f"Fixed supermarket list type for list {list_id}")
                
                # Ensure it has ID 1 (critical for maintenance mode and other features)
                if list_id != 1:
                    # Move the supermarket list to ID 1
                    cursor.execute('UPDATE lists SET id = 1 WHERE list_type = "supermarket"')
                    logging.warning(f"Moved supermarket list to ID 1")
                
                # Ensure it's always active
                cursor.execute('UPDATE lists SET is_active = TRUE WHERE list_type = "supermarket"')
                
            logging.info("Supermarket list protection verified")
            
        except Exception as e:
            logging.error(f"Error ensuring supermarket list protection: {e}")

    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, is_admin: bool = False) -> bool:
        """Add or update a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, is_admin, is_authorized)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, is_admin, True))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return False

    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_authorized FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result and result[0]
        except Exception as e:
            logging.error(f"Error checking user authorization: {e}")
            return False

    def remove_user_authorization(self, user_id: int) -> bool:
        """Remove user authorization (but keep user in database)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET is_authorized = FALSE 
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error removing user authorization: {e}")
            return False

    def is_user_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result and result[0]
        except Exception as e:
            logging.error(f"Error checking user admin status: {e}")
            return False

    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, is_admin, is_authorized
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'first_name': result[2],
                        'last_name': result[3],
                        'is_admin': result[4],
                        'is_authorized': result[5]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting user info: {e}")
            return None

    def add_item(self, item_name: str, category: str = None, notes: str = None, 
                 added_by: int = None) -> Optional[int]:
        """Add an item to the supermarket list (default list)"""
        return self.add_item_to_list(1, item_name, category, notes, added_by)

    def get_shopping_list(self) -> List[Dict]:
        """Get the supermarket shopping list with notes"""
        return self.get_supermarket_list()

    def get_items_by_user(self, user_id: int) -> List[Dict]:
        """Get items added by a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT si.id, si.item_name, si.category, si.notes, si.created_at
                    FROM shopping_items si
                    WHERE si.added_by = ?
                    ORDER BY si.category, si.item_name
                ''', (user_id,))
                
                items = []
                for row in cursor.fetchall():
                    item_id, item_name, category, notes, created_at = row
                    
                    # Get notes for this item
                    cursor.execute('''
                        SELECT in_.note, u.first_name, u.username
                        FROM item_notes in_
                        LEFT JOIN users u ON in_.user_id = u.user_id
                        WHERE in_.item_id = ?
                        ORDER BY in_.created_at
                    ''', (item_id,))
                    
                    item_notes = []
                    for note_row in cursor.fetchall():
                        note_text, note_first_name, note_username = note_row
                        item_notes.append({
                            'note': note_text,
                            'user_name': note_first_name or note_username or 'Unknown'
                        })
                    
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': category,
                        'notes': notes,
                        'created_at': created_at,
                        'item_notes': item_notes
                    })
                
                return items
                
        except Exception as e:
            logging.error(f"Error getting items by user: {e}")
            return []

    def get_items_by_user_in_list(self, user_id: int, list_id: int) -> List[Dict]:
        """Get items added by a specific user in a specific list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT si.id, si.item_name, si.category, si.notes, si.created_at
                    FROM shopping_items si
                    WHERE si.added_by = ? AND si.list_id = ?
                    ORDER BY si.category, si.item_name
                ''', (user_id, list_id))
                
                items = []
                for row in cursor.fetchall():
                    item_id, item_name, category, notes, created_at = row
                    
                    # Get notes for this item
                    cursor.execute('''
                        SELECT in_.note, u.first_name, u.username
                        FROM item_notes in_
                        LEFT JOIN users u ON in_.user_id = u.user_id
                        WHERE in_.item_id = ?
                        ORDER BY in_.created_at
                    ''', (item_id,))
                    
                    item_notes = []
                    for note_row in cursor.fetchall():
                        note_text, note_first_name, note_username = note_row
                        item_notes.append({
                            'note': note_text,
                            'user_name': note_first_name or note_username or 'Unknown'
                        })
                    
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': category,
                        'notes': notes,
                        'created_at': created_at,
                        'item_notes': item_notes
                    })
                
                return items
                
        except Exception as e:
            logging.error(f"Error getting items by user in list: {e}")
            return []

    def delete_item(self, item_id: int) -> Optional[str]:
        """Delete an item from the shopping list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get item name before deletion
                cursor.execute('SELECT item_name FROM shopping_items WHERE id = ?', (item_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                
                item_name = result[0]
                
                # Delete item notes first
                cursor.execute('DELETE FROM item_notes WHERE item_id = ?', (item_id,))
                
                # Delete the item
                cursor.execute('DELETE FROM shopping_items WHERE id = ?', (item_id,))
                conn.commit()
                
                return item_name
                
        except Exception as e:
            logging.error(f"Error deleting item: {e}")
            return None

    def reset_shopping_list(self) -> bool:
        """Reset the supermarket shopping list"""
        return self.reset_list(1)

    def get_all_users(self) -> List[Dict]:
        """Get all registered users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, is_admin, is_authorized
                    FROM users
                    ORDER BY first_name, username
                ''')
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'is_admin': row[4],
                        'is_authorized': row[5]
                    })
                
                return users
                
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return []

    def get_admin_users(self) -> List[Dict]:
        """Get all admin users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, is_admin, is_authorized
                    FROM users
                    WHERE is_admin = 1
                    ORDER BY first_name, username
                ''')
                
                admins = []
                for row in cursor.fetchall():
                    admins.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'is_admin': row[4],
                        'is_authorized': row[5]
                    })
                
                return admins
                
        except Exception as e:
            logging.error(f"Error getting admin users: {e}")
            return []

    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else 'en'
        except Exception as e:
            logging.error(f"Error getting user language: {e}")
            return 'en'

    def set_user_language(self, user_id: int, language: str) -> bool:
        """Set user's preferred language"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error setting user language: {e}")
            return False

    def get_all_authorized_users(self) -> List[Dict]:
        """Get all authorized users for broadcasting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, language 
                    FROM users 
                    WHERE is_authorized = TRUE
                ''')
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'language': row[4] or 'en'
                    })
                return users
        except Exception as e:
            logging.error(f"Error getting authorized users: {e}")
            return []

    def save_broadcast_message(self, sender_id: int, message: str, sent_to_count: int) -> bool:
        """Save broadcast message to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO broadcast_messages (sender_id, message, sent_to_count)
                    VALUES (?, ?, ?)
                ''', (sender_id, message, sent_to_count))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error saving broadcast message: {e}")
            return False

    def get_broadcast_history(self, limit: int = 10) -> List[Dict]:
        """Get recent broadcast message history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT bm.id, bm.message, bm.sent_to_count, bm.created_at,
                           u.username, u.first_name, u.last_name
                    FROM broadcast_messages bm
                    JOIN users u ON bm.sender_id = u.user_id
                    ORDER BY bm.created_at DESC
                    LIMIT ?
                ''', (limit,))
                broadcasts = []
                for row in cursor.fetchall():
                    broadcasts.append({
                        'id': row[0],
                        'message': row[1],
                        'sent_to_count': row[2],
                        'created_at': row[3],
                        'sender_username': row[4],
                        'sender_first_name': row[5],
                        'sender_last_name': row[6]
                    })
                return broadcasts
        except Exception as e:
            logging.error(f"Error getting broadcast history: {e}")
            return []

    def add_item_suggestion(self, suggested_by: int, category_key: str, item_name_en: str, item_name_he: str = None, list_id: int = 1) -> bool:
        """Add a new item suggestion (with duplicate checking)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if item already exists in category (static or dynamic)
                if self.is_item_in_category(category_key, item_name_en):
                    return False  # Item already exists
                
                # Check if there's already a pending suggestion for this item
                cursor.execute('''
                    SELECT COUNT(*) FROM item_suggestions
                    WHERE category_key = ? AND LOWER(item_name_en) = LOWER(?) AND status = 'pending'
                ''', (category_key, item_name_en))
                
                if cursor.fetchone()[0] > 0:
                    return False  # Already suggested
                
                cursor.execute('''
                    INSERT INTO item_suggestions (suggested_by, category_key, item_name_en, item_name_he, list_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (suggested_by, category_key, item_name_en, item_name_he, list_id))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding item suggestion: {e}")
            return False

    def get_pending_suggestions(self, list_id: int = None) -> List[Dict]:
        """Get pending item suggestions, optionally filtered by list_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if list_id is not None:
                    cursor.execute('''
                        SELECT s.id, s.category_key, s.item_name_en, s.item_name_he, s.created_at, s.list_id,
                               u.username, u.first_name, u.last_name
                        FROM item_suggestions s
                        JOIN users u ON s.suggested_by = u.user_id
                        WHERE s.status = 'pending' AND s.list_id = ?
                        ORDER BY s.created_at DESC
                    ''', (list_id,))
                else:
                    cursor.execute('''
                        SELECT s.id, s.category_key, s.item_name_en, s.item_name_he, s.created_at, s.list_id,
                               u.username, u.first_name, u.last_name
                        FROM item_suggestions s
                        JOIN users u ON s.suggested_by = u.user_id
                        WHERE s.status = 'pending'
                        ORDER BY s.created_at DESC
                    ''')
                
                suggestions = []
                for row in cursor.fetchall():
                    suggestions.append({
                        'id': row[0],
                        'category_key': row[1],
                        'item_name_en': row[2],
                        'item_name_he': row[3],
                        'created_at': row[4],
                        'list_id': row[5],
                        'suggested_by_username': row[6],
                        'suggested_by_first_name': row[7],
                        'suggested_by_last_name': row[8]
                    })
                return suggestions
        except Exception as e:
            logging.error(f"Error getting pending suggestions: {e}")
            return []

    def approve_suggestion(self, suggestion_id: int, approved_by: int) -> bool:
        """Approve an item suggestion and add it to the category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the suggestion details
                cursor.execute('''
                    SELECT category_key, item_name_en, item_name_he FROM item_suggestions
                    WHERE id = ? AND status = 'pending'
                ''', (suggestion_id,))
                
                suggestion = cursor.fetchone()
                if not suggestion:
                    return False
                
                category_key, item_name_en, item_name_he = suggestion
                
                # Add the item to the dynamic category items
                success = self.add_dynamic_category_item(category_key, item_name_en, item_name_he, approved_by)
                if not success:
                    return False  # Failed to add item (probably duplicate)
                
                # Update the suggestion status
                cursor.execute('''
                    UPDATE item_suggestions 
                    SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                ''', (approved_by, suggestion_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error approving suggestion: {e}")
            return False

    def reject_suggestion(self, suggestion_id: int, rejected_by: int) -> bool:
        """Reject an item suggestion"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE item_suggestions 
                    SET status = 'rejected', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                ''', (rejected_by, suggestion_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error rejecting suggestion: {e}")
            return False

    def get_suggestion_by_id(self, suggestion_id: int) -> Optional[Dict]:
        """Get suggestion details by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.id, s.category_key, s.item_name_en, s.item_name_he, s.status, s.created_at, s.suggested_by,
                           u.username, u.first_name, u.last_name
                    FROM item_suggestions s
                    JOIN users u ON s.suggested_by = u.user_id
                    WHERE s.id = ?
                ''', (suggestion_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'category_key': row[1],
                        'item_name_en': row[2],
                        'item_name_he': row[3],
                        'status': row[4],
                        'created_at': row[5],
                        'suggested_by': row[6],
                        'suggested_by_username': row[7],
                        'suggested_by_first_name': row[8],
                        'suggested_by_last_name': row[9]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting suggestion by ID: {e}")
            return None

    # Multi-list functionality methods
    def create_list(self, name: str, description: str = None, created_by: int = None, list_type: str = 'custom') -> Optional[int]:
        """Create a new list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO lists (name, description, list_type, created_by)
                    VALUES (?, ?, ?, ?)
                ''', (name, description, list_type, created_by))
                list_id = cursor.lastrowid
                conn.commit()
                return list_id
        except Exception as e:
            logging.error(f"Error creating list: {e}")
            return None

    def get_all_lists(self) -> List[Dict]:
        """Get all active lists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.id, l.name, l.description, l.list_type, l.created_by, l.created_at,
                           u.username, u.first_name, u.last_name
                    FROM lists l
                    LEFT JOIN users u ON l.created_by = u.user_id
                    WHERE l.is_active = TRUE
                    ORDER BY l.list_type, l.name
                ''')
                lists = []
                for row in cursor.fetchall():
                    lists.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'created_by': row[4],
                        'created_at': row[5],
                        'creator_username': row[6],
                        'creator_first_name': row[7],
                        'creator_last_name': row[8]
                    })
                return lists
        except Exception as e:
            logging.error(f"Error getting all lists: {e}")
            return []

    def get_list_by_id(self, list_id: int) -> Optional[Dict]:
        """Get list details by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.id, l.name, l.description, l.list_type, l.created_by, l.created_at,
                           u.username, u.first_name, u.last_name
                    FROM lists l
                    LEFT JOIN users u ON l.created_by = u.user_id
                    WHERE l.id = ? AND l.is_active = TRUE
                ''', (list_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'created_by': row[4],
                        'created_at': row[5],
                        'creator_username': row[6],
                        'creator_first_name': row[7],
                        'creator_last_name': row[8]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting list by ID: {e}")
            return None

    def get_user_lists(self, user_id: int) -> List[Dict]:
        """Get lists created by a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.id, l.name, l.description, l.list_type, l.created_at
                    FROM lists l
                    WHERE l.created_by = ? AND l.is_active = TRUE
                    ORDER BY l.created_at DESC
                ''', (user_id,))
                lists = []
                for row in cursor.fetchall():
                    lists.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'created_at': row[4]
                    })
                return lists
        except Exception as e:
            logging.error(f"Error getting user lists: {e}")
            return []

    def update_list_name(self, list_id: int, new_name: str) -> bool:
        """Update list name"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lists SET name = ? WHERE id = ?', (new_name, list_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating list name: {e}")
            return False

    def delete_list(self, list_id: int) -> Optional[str]:
        """Delete a list (soft delete) - with supermarket list protection"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if this is the supermarket list
                cursor.execute('SELECT name, list_type FROM lists WHERE id = ?', (list_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                
                list_name, list_type = result
                
                # PROTECTION: Never allow deletion of supermarket list
                if list_type == 'supermarket':
                    logging.warning(f"Attempted to delete protected supermarket list (ID: {list_id})")
                    return "PROTECTED"  # Special return value to indicate protection
                
                # Soft delete the list
                cursor.execute('UPDATE lists SET is_active = FALSE WHERE id = ?', (list_id,))
                
                # Delete all items in the list
                cursor.execute('DELETE FROM item_notes WHERE item_id IN (SELECT id FROM shopping_items WHERE list_id = ?)', (list_id,))
                cursor.execute('DELETE FROM shopping_items WHERE list_id = ?', (list_id,))
                
                conn.commit()
                return list_name
                
        except Exception as e:
            logging.error(f"Error deleting list: {e}")
            return None

    def reset_list(self, list_id: int) -> bool:
        """Reset a specific list (clear all items)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM item_notes WHERE item_id IN (SELECT id FROM shopping_items WHERE list_id = ?)', (list_id,))
                cursor.execute('DELETE FROM shopping_items WHERE list_id = ?', (list_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error resetting list: {e}")
            return False

    def add_item_to_list(self, list_id: int, item_name: str, category: str = None, notes: str = None, added_by: int = None) -> Optional[int]:
        """Add an item to a specific list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if item already exists in this list
                cursor.execute('SELECT id FROM shopping_items WHERE list_id = ? AND LOWER(item_name) = LOWER(?)', 
                             (list_id, item_name))
                existing_item = cursor.fetchone()
                
                if existing_item:
                    item_id = existing_item[0]
                    # Add note if provided
                    if notes:
                        cursor.execute('''
                            INSERT INTO item_notes (item_id, user_id, note)
                            VALUES (?, ?, ?)
                        ''', (item_id, added_by, notes))
                        conn.commit()
                    return item_id
                else:
                    # Add new item
                    cursor.execute('''
                        INSERT INTO shopping_items (list_id, item_name, category, notes, added_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (list_id, item_name, category, notes, added_by))
                    item_id = cursor.lastrowid
                    
                    # Add note if provided
                    if notes:
                        cursor.execute('''
                            INSERT INTO item_notes (item_id, user_id, note)
                            VALUES (?, ?, ?)
                        ''', (item_id, added_by, notes))
                    
                    conn.commit()
                    return item_id
                    
        except Exception as e:
            logging.error(f"Error adding item to list: {e}")
            return None

    def get_shopping_list_by_id(self, list_id: int) -> List[Dict]:
        """Get items from a specific list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT si.id, si.item_name, si.category, si.notes, si.added_by,
                           u.first_name, u.username, si.created_at
                    FROM shopping_items si
                    LEFT JOIN users u ON si.added_by = u.user_id
                    WHERE si.list_id = ?
                    ORDER BY si.category, si.item_name
                ''', (list_id,))
                
                items = []
                for row in cursor.fetchall():
                    item_id, item_name, category, notes, added_by, first_name, username, created_at = row
                    
                    # Get all notes for this item
                    cursor.execute('''
                        SELECT in_.note, u.first_name, u.username
                        FROM item_notes in_
                        LEFT JOIN users u ON in_.user_id = u.user_id
                        WHERE in_.item_id = ?
                        ORDER BY in_.created_at
                    ''', (item_id,))
                    
                    item_notes = []
                    for note_row in cursor.fetchall():
                        note_text, note_first_name, note_username = note_row
                        item_notes.append({
                            'note': note_text,
                            'user_name': note_first_name or note_username or 'Unknown'
                        })
                    
                    items.append({
                        'id': item_id,
                        'name': item_name,
                        'category': category,
                        'notes': notes,
                        'added_by': added_by,
                        'added_by_name': first_name or username or 'Unknown',
                        'created_at': created_at,
                        'item_notes': item_notes
                    })
                
                return items
                
        except Exception as e:
            logging.error(f"Error getting shopping list by ID: {e}")
            return []

    def get_supermarket_list(self) -> List[Dict]:
        """Get the supermarket list (list_id = 1)"""
        return self.get_shopping_list_by_id(1)
    
    def get_supermarket_list_id(self) -> int:
        """Get the supermarket list ID safely (always returns 1, but verifies it exists)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM lists WHERE list_type = "supermarket" AND is_active = TRUE')
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # If supermarket list doesn't exist, create it
                    cursor.execute('''
                        INSERT INTO lists (id, name, description, list_type, created_by)
                        VALUES (1, "Supermarket List", "Weekly family shopping list", "supermarket", 1)
                    ''')
                    conn.commit()
                    logging.warning("Created missing supermarket list")
                    return 1
        except Exception as e:
            logging.error(f"Error getting supermarket list ID: {e}")
            return 1  # Fallback to ID 1
    
    # Maintenance mode methods
    def set_maintenance_mode(self, list_id: int, scheduled_day: str, scheduled_time: str, created_by: int) -> bool:
        """Set maintenance mode for a list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Deactivate any existing maintenance mode for this list
                cursor.execute('''
                    UPDATE maintenance_mode 
                    SET is_active = FALSE 
                    WHERE list_id = ?
                ''', (list_id,))
                
                # Insert new maintenance mode
                cursor.execute('''
                    INSERT INTO maintenance_mode (list_id, scheduled_day, scheduled_time, created_by)
                    VALUES (?, ?, ?, ?)
                ''', (list_id, scheduled_day, scheduled_time, created_by))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error setting maintenance mode: {e}")
            return False
    
    def get_maintenance_mode(self, list_id: int = 1) -> Optional[Dict]:
        """Get active maintenance mode for a list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, scheduled_day, scheduled_time, last_reminder, reminder_count, created_at
                    FROM maintenance_mode 
                    WHERE list_id = ? AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (list_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'scheduled_day': row[1],
                        'scheduled_time': row[2],
                        'last_reminder': row[3],
                        'reminder_count': row[4],
                        'created_at': row[5]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting maintenance mode: {e}")
            return None
    
    def update_maintenance_reminder(self, maintenance_id: int) -> bool:
        """Update the last reminder timestamp and count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE maintenance_mode 
                    SET last_reminder = CURRENT_TIMESTAMP, reminder_count = reminder_count + 1
                    WHERE id = ?
                ''', (maintenance_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating maintenance reminder: {e}")
            return False
    
    def deactivate_maintenance_mode(self, list_id: int) -> bool:
        """Deactivate maintenance mode for a list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE maintenance_mode 
                    SET is_active = FALSE 
                    WHERE list_id = ?
                ''', (list_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deactivating maintenance mode: {e}")
            return False

    # Custom Categories Methods
    def add_custom_category(self, category_key: str, emoji: str, name_en: str, name_he: str, created_by: int) -> bool:
        """Add a new custom category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO custom_categories (category_key, emoji, name_en, name_he, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (category_key, emoji, name_en, name_he, created_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            logging.warning(f"Category key '{category_key}' already exists")
            return False
        except Exception as e:
            logging.error(f"Error adding custom category: {e}")
            return False

    def get_custom_categories(self) -> List[Dict]:
        """Get all custom categories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT category_key, emoji, name_en, name_he, created_by, created_at
                    FROM custom_categories
                    ORDER BY created_at DESC
                ''')
                categories = []
                for row in cursor.fetchall():
                    categories.append({
                        'category_key': row[0],
                        'emoji': row[1],
                        'name_en': row[2],
                        'name_he': row[3],
                        'created_by': row[4],
                        'created_at': row[5]
                    })
                return categories
        except Exception as e:
            logging.error(f"Error getting custom categories: {e}")
            return []

    def get_custom_category(self, category_key: str) -> Optional[Dict]:
        """Get a specific custom category by key"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT category_key, emoji, name_en, name_he, created_by, created_at
                    FROM custom_categories
                    WHERE category_key = ?
                ''', (category_key,))
                row = cursor.fetchone()
                if row:
                    return {
                        'category_key': row[0],
                        'emoji': row[1],
                        'name_en': row[2],
                        'name_he': row[3],
                        'created_by': row[4],
                        'created_at': row[5]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting custom category: {e}")
            return None

    def delete_custom_category(self, category_key: str) -> bool:
        """Delete a custom category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM custom_categories WHERE category_key = ?', (category_key,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting custom category: {e}")
            return False

    def count_items_in_category(self, category_key: str) -> int:
        """Count items in a specific category across all lists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM shopping_items 
                    WHERE category = ?
                ''', (category_key,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logging.error(f"Error counting items in category: {e}")
            return 0

    # Category Suggestions Methods
    def add_category_suggestion(self, suggested_by: int, category_key: str, emoji: str, name_en: str, name_he: str) -> bool:
        """Add a new category suggestion (with duplicate checking)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if category already exists (predefined or custom)
                cursor.execute('''
                    SELECT COUNT(*) FROM custom_categories
                    WHERE LOWER(category_key) = LOWER(?) OR LOWER(name_en) = LOWER(?)
                ''', (category_key, name_en))
                
                if cursor.fetchone()[0] > 0:
                    return False  # Category already exists
                
                # Check if there's already a pending suggestion for this category
                cursor.execute('''
                    SELECT COUNT(*) FROM category_suggestions
                    WHERE LOWER(category_key) = LOWER(?) OR LOWER(name_en) = LOWER(?) AND status = 'pending'
                ''', (category_key, name_en))
                
                if cursor.fetchone()[0] > 0:
                    return False  # Already suggested
                
                cursor.execute('''
                    INSERT INTO category_suggestions (suggested_by, category_key, emoji, name_en, name_he)
                    VALUES (?, ?, ?, ?, ?)
                ''', (suggested_by, category_key, emoji, name_en, name_he))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding category suggestion: {e}")
            return False

    def get_pending_category_suggestions(self) -> List[Dict]:
        """Get pending category suggestions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.id, s.category_key, s.emoji, s.name_en, s.name_he, s.created_at,
                           u.username, u.first_name, u.last_name
                    FROM category_suggestions s
                    JOIN users u ON s.suggested_by = u.user_id
                    WHERE s.status = 'pending'
                    ORDER BY s.created_at DESC
                ''')
                
                suggestions = []
                for row in cursor.fetchall():
                    suggestions.append({
                        'id': row[0],
                        'category_key': row[1],
                        'emoji': row[2],
                        'name_en': row[3],
                        'name_he': row[4],
                        'created_at': row[5],
                        'suggested_by_username': row[6],
                        'suggested_by_first_name': row[7],
                        'suggested_by_last_name': row[8]
                    })
                return suggestions
        except Exception as e:
            logging.error(f"Error getting pending category suggestions: {e}")
            return []

    def get_pending_item_suggestions_count(self) -> int:
        """Get count of pending item suggestions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM item_suggestions 
                    WHERE status = 'pending'
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting pending item suggestions count: {e}")
            return 0

    def get_pending_category_suggestions_count(self) -> int:
        """Get count of pending category suggestions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM category_suggestions 
                    WHERE status = 'pending'
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting pending category suggestions count: {e}")
            return 0

    def get_total_pending_suggestions_count(self) -> int:
        """Get total count of pending suggestions (items + categories)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        (SELECT COUNT(*) FROM item_suggestions WHERE status = 'pending') +
                        (SELECT COUNT(*) FROM category_suggestions WHERE status = 'pending')
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting total pending suggestions count: {e}")
            return 0

    def get_recently_used_items(self, days: int = 7) -> List[Dict]:
        """Get items that were added to lists in the past N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT item_name, category, COUNT(*) as usage_count
                    FROM shopping_items 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY item_name, category
                    ORDER BY usage_count DESC, MAX(created_at) DESC
                    LIMIT 20
                '''.format(days))
                
                results = cursor.fetchall()
                return [{'name': row[0], 'category': row[1], 'usage_count': row[2]} for row in results]
        except Exception as e:
            logging.error(f"Error getting recently used items: {e}")
            return []

    def approve_category_suggestion(self, suggestion_id: int, approved_by: int) -> bool:
        """Approve a category suggestion and create the category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get suggestion details
                cursor.execute('''
                    SELECT category_key, emoji, name_en, name_he, suggested_by
                    FROM category_suggestions
                    WHERE id = ? AND status = 'pending'
                ''', (suggestion_id,))
                
                suggestion = cursor.fetchone()
                if not suggestion:
                    return False
                
                category_key, emoji, name_en, name_he, suggested_by = suggestion
                
                # Create the category
                cursor.execute('''
                    INSERT INTO custom_categories (category_key, emoji, name_en, name_he, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (category_key, emoji, name_en, name_he, suggested_by))
                
                # Update suggestion status
                cursor.execute('''
                    UPDATE category_suggestions 
                    SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (approved_by, suggestion_id))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error approving category suggestion: {e}")
            return False

    def reject_category_suggestion(self, suggestion_id: int, rejected_by: int) -> bool:
        """Reject a category suggestion"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE category_suggestions 
                    SET status = 'rejected', approved_by = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                ''', (rejected_by, suggestion_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error rejecting category suggestion: {e}")
            return False

    def get_category_suggestion_by_id(self, suggestion_id: int) -> Optional[Dict]:
        """Get a specific category suggestion by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.id, s.category_key, s.emoji, s.name_en, s.name_he, s.status, s.created_at, s.suggested_by,
                           u.username, u.first_name, u.last_name
                    FROM category_suggestions s
                    JOIN users u ON s.suggested_by = u.user_id
                    WHERE s.id = ?
                ''', (suggestion_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'category_key': row[1],
                        'emoji': row[2],
                        'name_en': row[3],
                        'name_he': row[4],
                        'status': row[5],
                        'created_at': row[6],
                        'suggested_by': row[7],
                        'suggested_by_username': row[8],
                        'suggested_by_first_name': row[9],
                        'suggested_by_last_name': row[10]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting category suggestion by ID: {e}")
            return None

    # Deleted Items Methods
    def add_deleted_item(self, category_key: str, item_name: str, deleted_by: int) -> bool:
        """Add an item to the deleted items list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO deleted_items (category_key, item_name, deleted_by)
                    VALUES (?, ?, ?)
                ''', (category_key, item_name, deleted_by))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding deleted item: {e}")
            return False

    def get_deleted_items_by_category(self, category_key: str) -> List[str]:
        """Get all deleted items for a category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT item_name FROM deleted_items
                    WHERE category_key = ?
                ''', (category_key,))
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logging.error(f"Error getting deleted items by category: {e}")
            return []

    def is_item_deleted(self, category_key: str, item_name: str) -> bool:
        """Check if an item is deleted from a category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM deleted_items
                    WHERE category_key = ? AND item_name = ?
                ''', (category_key, item_name))
                result = cursor.fetchone()
                return result[0] > 0 if result else False
        except Exception as e:
            logging.error(f"Error checking if item is deleted: {e}")
            return False

    # Dynamic Category Items Methods
    def add_dynamic_category_item(self, category_key: str, item_name_en: str, item_name_he: str = None, added_by: int = None) -> bool:
        """Add a new item to a category dynamically"""
        try:
            # Check if item already exists in static or dynamic items
            if self.is_item_in_category(category_key, item_name_en):
                return False  # Item already exists
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO dynamic_category_items (category_key, item_name_en, item_name_he, added_by)
                    VALUES (?, ?, ?, ?)
                ''', (category_key, item_name_en, item_name_he, added_by))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding dynamic category item: {e}")
            return False

    def get_dynamic_category_items(self, category_key: str) -> List[Dict]:
        """Get all dynamic items for a category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT item_name_en, item_name_he FROM dynamic_category_items
                    WHERE category_key = ?
                    ORDER BY item_name_en
                ''', (category_key,))
                rows = cursor.fetchall()
                return [{'en': row[0], 'he': row[1] or row[0]} for row in rows]
        except Exception as e:
            logging.error(f"Error getting dynamic category items: {e}")
            return []

    def is_item_in_category(self, category_key: str, item_name: str) -> bool:
        """Check if an item exists in a category (static or dynamic)"""
        try:
            # Import here to avoid circular imports
            from config import CATEGORIES
            
            # Check static items from config.py
            category = CATEGORIES.get(category_key, {})
            if category:
                static_items_en = category.get('items', {}).get('en', [])
                static_items_he = category.get('items', {}).get('he', [])
                
                # Check if item exists in static items (case-insensitive)
                for static_item in static_items_en + static_items_he:
                    if static_item.lower() == item_name.lower():
                        # Check if item is deleted
                        if not self.is_item_deleted(category_key, item_name):
                            return True
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check dynamic items
                cursor.execute('''
                    SELECT COUNT(*) FROM dynamic_category_items
                    WHERE category_key = ? AND LOWER(item_name_en) = LOWER(?)
                ''', (category_key, item_name))
                
                if cursor.fetchone()[0] > 0:
                    return True
                
                return False
        except Exception as e:
            logging.error(f"Error checking if item is in category: {e}")
            return False

    def remove_dynamic_category_item(self, category_key: str, item_name: str) -> bool:
        """Remove a dynamic item from a category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM dynamic_category_items
                    WHERE category_key = ? AND LOWER(item_name_en) = LOWER(?)
                ''', (category_key, item_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error removing dynamic category item: {e}")
            return False

    def rename_item(self, old_name: str, new_name_en: str, category_key: str, new_name_he: str = None) -> bool:
        """Rename an item in a category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Use Hebrew name if provided, otherwise use English name for both
                if new_name_he is None:
                    new_name_he = new_name_en
                
                # Check if it's a static item (from config.py) or dynamic item
                is_static_item = self.is_static_item(old_name, category_key)
                
                if is_static_item:
                    # For static items, we need to add them to dynamic_category_items with new name
                    # and add the old name to deleted_items to hide it from static list
                    
                    # Add old name to deleted_items to hide it from static list
                    cursor.execute('''
                        INSERT OR IGNORE INTO deleted_items (item_name, category_key)
                        VALUES (?, ?)
                    ''', (old_name, category_key))
                    
                    # Add new name to dynamic_category_items
                    cursor.execute('''
                        INSERT OR IGNORE INTO dynamic_category_items (category_key, item_name_en, item_name_he)
                        VALUES (?, ?, ?)
                    ''', (category_key, new_name_en, new_name_he))
                    
                else:
                    # For dynamic items, just update the existing record
                    cursor.execute('''
                        UPDATE dynamic_category_items
                        SET item_name_en = ?, item_name_he = ?
                        WHERE category_key = ? AND LOWER(item_name_en) = LOWER(?)
                    ''', (new_name_en, new_name_he, category_key, old_name))
                
                # Update in shopping_items table (for items currently in shopping lists)
                cursor.execute('''
                    UPDATE shopping_items
                    SET item_name = ?
                    WHERE category = ? AND LOWER(item_name) = LOWER(?)
                ''', (new_name_en, category_key, old_name))
                
                conn.commit()
                return True  # Always return True for static items, check rowcount for dynamic items
        except Exception as e:
            logging.error(f"Error renaming item: {e}")
            return False

    def rename_category(self, category_key: str, new_name_en: str, new_name_he: str) -> bool:
        """Rename a custom category"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update in custom_categories table
                cursor.execute('''
                    UPDATE custom_categories
                    SET name_en = ?, name_he = ?
                    WHERE category_key = ?
                ''', (new_name_en, new_name_he, category_key))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error renaming category: {e}")
            return False

    def is_category_name_exists(self, category_name: str) -> bool:
        """Check if a category name already exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check in custom_categories table
                cursor.execute('''
                    SELECT COUNT(*) FROM custom_categories
                    WHERE LOWER(name_en) = LOWER(?)
                ''', (category_name,))
                
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logging.error(f"Error checking if category name exists: {e}")
            return False

    def is_static_item(self, item_name: str, category_key: str) -> bool:
        """Check if an item is a static item from config.py"""
        try:
            # Import here to avoid circular imports
            from config import CATEGORIES
            
            # Check if the item exists in the static categories
            if category_key in CATEGORIES:
                items_dict = CATEGORIES[category_key].get('items', {})
                # Check both English and Hebrew items
                en_items = items_dict.get('en', [])
                he_items = items_dict.get('he', [])
                return (any(item.lower() == item_name.lower() for item in en_items) or
                        any(item.lower() == item_name.lower() for item in he_items))
            
            return False
        except Exception as e:
            logging.error(f"Error checking if item is static: {e}")
            return False

    def get_category_by_key(self, category_key: str) -> Optional[dict]:
        """Get a custom category by its key"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT category_key, name_en, name_he, emoji, created_at
                    FROM custom_categories
                    WHERE category_key = ?
                ''', (category_key,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'category_key': result[0],
                        'name_en': result[1],
                        'name_he': result[2],
                        'emoji': result[3],
                        'created_at': result[4]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting category by key: {e}")
            return None
