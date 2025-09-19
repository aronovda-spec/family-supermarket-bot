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
                
                conn.commit()
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")

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
        """Add a new item suggestion"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
        """Approve an item suggestion"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                    SELECT s.id, s.category_key, s.item_name_en, s.item_name_he, s.status, s.created_at,
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
                        'suggested_by_username': row[6],
                        'suggested_by_first_name': row[7],
                        'suggested_by_last_name': row[8]
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
        """Delete a list (soft delete)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get list name before deletion
                cursor.execute('SELECT name FROM lists WHERE id = ?', (list_id,))
                result = cursor.fetchone()
                if not result:
                    return None
                
                list_name = result[0]
                
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
