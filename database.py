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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Shopping items table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shopping_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_name TEXT NOT NULL,
                        category TEXT,
                        notes TEXT,
                        added_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        """Add an item to the shopping list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if item already exists
                cursor.execute('SELECT id FROM shopping_items WHERE LOWER(item_name) = LOWER(?)', 
                             (item_name,))
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
                        INSERT INTO shopping_items (item_name, category, notes, added_by)
                        VALUES (?, ?, ?, ?)
                    ''', (item_name, category, notes, added_by))
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
            logging.error(f"Error adding item: {e}")
            return None

    def get_shopping_list(self) -> List[Dict]:
        """Get the current shopping list with notes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT si.id, si.item_name, si.category, si.notes, si.added_by,
                           u.first_name, u.username, si.created_at
                    FROM shopping_items si
                    LEFT JOIN users u ON si.added_by = u.user_id
                    ORDER BY si.category, si.item_name
                ''')
                
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
            logging.error(f"Error getting shopping list: {e}")
            return []

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
        """Reset the entire shopping list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM item_notes')
                cursor.execute('DELETE FROM shopping_items')
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error resetting shopping list: {e}")
            return False

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
