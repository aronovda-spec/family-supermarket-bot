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
                        is_frozen BOOLEAN DEFAULT FALSE,
                        frozen_at TIMESTAMP DEFAULT NULL,
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
                
                # List sharing table for custom shared lists
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS list_sharing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        list_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        can_edit BOOLEAN DEFAULT TRUE,
                        shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (list_id) REFERENCES lists (id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        UNIQUE(list_id, user_id)
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
                
                # Migration: Add frozen fields to lists table if they don't exist
                try:
                    cursor.execute('ALTER TABLE lists ADD COLUMN is_frozen BOOLEAN DEFAULT FALSE')
                    cursor.execute('ALTER TABLE lists ADD COLUMN frozen_at TIMESTAMP DEFAULT NULL')
                    print("Added frozen fields to lists table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("Frozen columns already exist in lists table")
                    else:
                        print(f"Error adding frozen columns to lists table: {e}")
                
                # Create item_status_tracking table for frozen mode functionality
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS item_status_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        status TEXT NOT NULL CHECK (status IN ('bought', 'not_found', 'pending')),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (item_id) REFERENCES shopping_items (id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                        UNIQUE(item_id, user_id)
                    )
                ''')
                
                # Migration: Add Hebrew columns to templates table
                try:
                    cursor.execute('ALTER TABLE templates ADD COLUMN name_he TEXT')
                    print("Added name_he column to templates table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("name_he column already exists in templates table")
                    else:
                        print(f"Error adding name_he column to templates: {e}")
                
                try:
                    cursor.execute('ALTER TABLE templates ADD COLUMN description_he TEXT')
                    print("Added description_he column to templates table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("description_he column already exists in templates table")
                    else:
                        print(f"Error adding description_he column to templates: {e}")
                
                try:
                    cursor.execute('ALTER TABLE templates ADD COLUMN items_he TEXT')
                    print("Added items_he column to templates table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print("items_he column already exists in templates table")
                    else:
                        print(f"Error adding items_he column to templates: {e}")
                
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
                
                # Templates table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        name_he TEXT,
                        description TEXT,
                        description_he TEXT,
                        list_type TEXT NOT NULL,
                        items TEXT NOT NULL,  -- JSON array of items
                        items_he TEXT,  -- JSON array of Hebrew items
                        created_by INTEGER NOT NULL,
                        is_system_template BOOLEAN DEFAULT FALSE,
                        usage_count INTEGER DEFAULT 0,
                        last_used TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(user_id)
                    )
                ''')
                
                # Template categories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS template_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        list_type TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(user_id)
                    )
                ''')
                
                # Template usage tracking table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS template_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        usage_type TEXT NOT NULL,  -- 'load', 'preview', 'customize'
                        items_added INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (template_id) REFERENCES templates(id),
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
                
                conn.commit()
                
                # Create default system templates
                self.create_default_templates()
                
                logging.info("Database initialized successfully")
                
        except Exception as e:
            logging.error(f"Error initializing database: {e}")

    def create_default_templates(self):
        """Create default system templates if they don't exist"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if we already have system templates
                cursor.execute('SELECT COUNT(*) FROM templates WHERE is_system_template = TRUE')
                existing_count = cursor.fetchone()[0]
                
                # Get admin user ID for template creation
                cursor.execute('SELECT user_id FROM users WHERE is_admin = TRUE LIMIT 1')
                admin_user = cursor.fetchone()
                if not admin_user:
                    logging.warning("No admin user found for template creation")
                    return
                
                admin_user_id = admin_user[0]
                
                if existing_count > 0:
                    logging.info(f"System templates already exist ({existing_count} found)")
                    # Still create missing templates
                    self.create_missing_templates(cursor, admin_user_id)
                    return
                
                # Define default templates
                default_templates = [
                    # Supermarket Templates
                    {
                        'name': 'Weekly Groceries',
                        'description': 'Standard weekly shopping essentials',
                        'list_type': 'supermarket',
                        'items': ['Milk', 'Bread', 'Eggs', 'Cheese', 'Yogurt', 'Apples', 'Bananas', 'Carrots', 'Onions', 'Potatoes', 'Chicken', 'Ground meat', 'Rice', 'Pasta', 'Cereal', 'Coffee', 'Tea']
                    },
                    {
                        'name': 'Breakfast Essentials',
                        'description': 'Everything needed for breakfast',
                        'list_type': 'supermarket',
                        'items': ['Milk', 'Cereal', 'Oats', 'Bread', 'Butter', 'Jam', 'Eggs', 'Coffee', 'Tea', 'Orange juice', 'Yogurt', 'Fruits']
                    },
                    {
                        'name': 'Dinner Party',
                        'description': 'Ingredients for hosting dinner guests',
                        'list_type': 'supermarket',
                        'items': ['Wine', 'Cheese', 'Olives', 'Bread', 'Salmon', 'Beef', 'Vegetables', 'Herbs', 'Olive oil', 'Vinegar', 'Dessert', 'Coffee']
                    },
                    {
                        'name': 'BBQ/Grill',
                        'description': 'Everything for a barbecue',
                        'list_type': 'supermarket',
                        'items': ['Chicken', 'Beef', 'Pork', 'Sausages', 'Bacon', 'Bread', 'Ketchup', 'Mustard', 'BBQ sauce', 'Charcoal', 'Vegetables', 'Beer', 'Soda']
                    },
                    {
                        'name': 'Kids Lunch',
                        'description': 'School lunch items and snacks',
                        'list_type': 'supermarket',
                        'items': ['Bread', 'Cheese', 'Ham', 'Yogurt', 'Fruits', 'Juice boxes', 'Crackers', 'Cookies', 'Nuts', 'Granola bars']
                    },
                    {
                        'name': 'Vegetarian Week',
                        'description': 'Plant-based meal ingredients',
                        'list_type': 'supermarket',
                        'items': ['Tofu', 'Beans', 'Lentils', 'Quinoa', 'Vegetables', 'Fruits', 'Nuts', 'Seeds', 'Olive oil', 'Herbs', 'Rice', 'Pasta']
                    },
                    {
                        'name': 'Budget Shopping',
                        'description': 'Essential items for tight budgets',
                        'list_type': 'supermarket',
                        'items': ['Rice', 'Pasta', 'Beans', 'Potatoes', 'Onions', 'Carrots', 'Eggs', 'Milk', 'Bread', 'Oats', 'Bananas', 'Ground meat']
                    },
                    
                    # Pharmacy Templates
                    {
                        'name': 'First Aid Kit',
                        'description': 'Essential first aid supplies',
                        'list_type': 'pharmacy',
                        'items': ['Bandages', 'Antiseptic', 'Pain relievers', 'Thermometer', 'Gauze', 'Medical tape', 'Scissors', 'Tweezers']
                    },
                    {
                        'name': 'Cold & Flu',
                        'description': 'Medicine and supplies for cold and flu',
                        'list_type': 'pharmacy',
                        'items': ['Pain relievers', 'Cough syrup', 'Throat lozenges', 'Tissues', 'Nasal spray', 'Vitamins', 'Tea', 'Honey']
                    },
                    {
                        'name': 'Baby Care',
                        'description': 'Essential baby care items',
                        'list_type': 'pharmacy',
                        'items': ['Diapers', 'Baby formula', 'Baby food', 'Baby wipes', 'Baby shampoo', 'Baby lotion', 'Thermometer', 'Pacifiers']
                    },
                    
                    # Home Templates
                    {
                        'name': 'New Home',
                        'description': 'Basic household essentials for new home',
                        'list_type': 'home',
                        'items': ['Toilet paper', 'Paper towels', 'Detergent', 'Soap', 'Shampoo', 'Toothpaste', 'Light bulbs', 'Batteries', 'Cleaning supplies']
                    },
                    {
                        'name': 'Home Office',
                        'description': 'Supplies for remote work',
                        'list_type': 'home',
                        'items': ['Notebooks', 'Pens', 'Pencils', 'Stapler', 'Paper clips', 'Folders', 'Printer paper', 'Ink cartridges']
                    },
                    {
                        'name': 'Garden Setup',
                        'description': 'Tools and supplies for gardening',
                        'list_type': 'home',
                        'items': ['Seeds', 'Fertilizer', 'Pots', 'Garden tools', 'Watering can', 'Gloves', 'Soil', 'Plant markers']
                    },
                    
                    # Special Occasion Templates
                    {
                        'name': 'Birthday Party',
                        'description': 'Everything for a birthday celebration',
                        'list_type': 'gifts_cards',
                        'items': ['Balloons', 'Candles', 'Cake', 'Party decorations', 'Gift wrapping', 'Party favors', 'Soda', 'Snacks']
                    },
                    {
                        'name': 'Wedding Shower',
                        'description': 'Items for wedding shower celebration',
                        'list_type': 'gifts_cards',
                        'items': ['Gift wrapping', 'Greeting cards', 'Decorations', 'Candles', 'Party supplies', 'Gifts', 'Flowers', 'Champagne']
                    },
                    
                    # Travel Templates
                    {
                        'name': 'Beach Vacation',
                        'description': 'Essentials for beach vacation',
                        'list_type': 'travel',
                        'items': ['Sunscreen', 'Beach towels', 'Swimwear', 'Sunglasses', 'Hat', 'Snacks', 'Water', 'Beach toys']
                    },
                    {
                        'name': 'Camping Trip',
                        'description': 'Food and supplies for camping',
                        'list_type': 'travel',
                        'items': ['Canned food', 'Water', 'Snacks', 'Coffee', 'Tea', 'Matches', 'Flashlight', 'Batteries', 'First aid kit']
                    },
                    {
                        'name': 'Road Trip',
                        'description': 'Snacks and supplies for road travel',
                        'list_type': 'travel',
                        'items': ['Snacks', 'Water', 'Soda', 'Coffee', 'Maps', 'Phone charger', 'Music', 'Games', 'Blankets']
                    },
                    
                    # Lifestyle Templates
                    {
                        'name': 'Fitness/Workout',
                        'description': 'Supplies for fitness and workout',
                        'list_type': 'personal_care',
                        'items': ['Protein powder', 'Energy bars', 'Water bottle', 'Workout clothes', 'Sneakers', 'Towel', 'Headphones', 'Fitness tracker']
                    },
                    {
                        'name': 'Meal Prep',
                        'description': 'Containers and ingredients for weekly meal prep',
                        'list_type': 'supermarket',
                        'items': ['Meal containers', 'Rice', 'Chicken', 'Vegetables', 'Quinoa', 'Beans', 'Olive oil', 'Herbs', 'Spices']
                    }
                ]
                
                # Insert templates
                for template in default_templates:
                    cursor.execute('''
                        INSERT INTO templates (name, description, list_type, items, created_by, is_system_template, usage_count)
                        VALUES (?, ?, ?, ?, ?, TRUE, 0)
                    ''', (
                        template['name'],
                        template['description'],
                        template['list_type'],
                        json.dumps(template['items']),
                        admin_user_id
                    ))
                
                conn.commit()
                logging.info(f"Created {len(default_templates)} default system templates")
                
        except Exception as e:
            logging.error(f"Error creating default templates: {e}")

    def create_missing_templates(self, cursor, admin_user_id):
        """Create missing templates that don't already exist"""
        try:
            import json
            
            # Get existing template names
            cursor.execute('SELECT name FROM templates WHERE is_system_template = TRUE')
            existing_names = {row[0] for row in cursor.fetchall()}
            
            # Define missing templates
            missing_templates = [
                # Supermarket Templates
                {
                    'name': 'Weekly Groceries',
                    'description': 'Standard weekly shopping essentials',
                    'list_type': 'supermarket',
                    'items': ['Milk', 'Bread', 'Eggs', 'Cheese', 'Yogurt', 'Apples', 'Bananas', 'Carrots', 'Onions', 'Potatoes', 'Chicken', 'Ground meat', 'Rice', 'Pasta', 'Cereal', 'Coffee', 'Tea']
                },
                {
                    'name': 'Breakfast Essentials',
                    'description': 'Everything needed for breakfast',
                    'list_type': 'supermarket',
                    'items': ['Milk', 'Cereal', 'Oats', 'Bread', 'Butter', 'Jam', 'Eggs', 'Coffee', 'Tea', 'Orange juice', 'Yogurt', 'Fruits']
                },
                {
                    'name': 'Dinner Party',
                    'description': 'Ingredients for hosting dinner guests',
                    'list_type': 'supermarket',
                    'items': ['Wine', 'Cheese', 'Olives', 'Bread', 'Salmon', 'Beef', 'Vegetables', 'Herbs', 'Olive oil', 'Vinegar', 'Dessert', 'Coffee']
                },
                {
                    'name': 'BBQ/Grill',
                    'description': 'Everything for a barbecue',
                    'list_type': 'supermarket',
                    'items': ['Chicken', 'Beef', 'Pork', 'Sausages', 'Bacon', 'Bread', 'Ketchup', 'Mustard', 'BBQ sauce', 'Charcoal', 'Vegetables', 'Beer', 'Soda']
                },
                {
                    'name': 'Kids Lunch',
                    'description': 'School lunch items and snacks',
                    'list_type': 'supermarket',
                    'items': ['Bread', 'Cheese', 'Ham', 'Yogurt', 'Fruits', 'Juice boxes', 'Crackers', 'Cookies', 'Nuts', 'Granola bars']
                },
                {
                    'name': 'Vegetarian Week',
                    'description': 'Plant-based meal ingredients',
                    'list_type': 'supermarket',
                    'items': ['Tofu', 'Beans', 'Lentils', 'Quinoa', 'Vegetables', 'Fruits', 'Nuts', 'Seeds', 'Olive oil', 'Herbs', 'Rice', 'Pasta']
                },
                {
                    'name': 'Budget Shopping',
                    'description': 'Essential items for tight budgets',
                    'list_type': 'supermarket',
                    'items': ['Rice', 'Pasta', 'Beans', 'Potatoes', 'Onions', 'Carrots', 'Eggs', 'Milk', 'Bread', 'Oats', 'Bananas', 'Ground meat']
                },
                
                # Pharmacy Templates
                {
                    'name': 'First Aid Kit',
                    'description': 'Essential first aid supplies',
                    'list_type': 'pharmacy',
                    'items': ['Bandages', 'Antiseptic', 'Pain relievers', 'Thermometer', 'Gauze', 'Medical tape', 'Scissors', 'Tweezers']
                },
                {
                    'name': 'Cold & Flu',
                    'description': 'Medicine and supplies for cold and flu',
                    'list_type': 'pharmacy',
                    'items': ['Pain relievers', 'Cough syrup', 'Throat lozenges', 'Tissues', 'Nasal spray', 'Vitamins', 'Tea', 'Honey']
                },
                {
                    'name': 'Baby Care',
                    'description': 'Essential baby care items',
                    'list_type': 'pharmacy',
                    'items': ['Diapers', 'Baby formula', 'Baby food', 'Baby wipes', 'Baby shampoo', 'Baby lotion', 'Thermometer', 'Pacifiers']
                },
                
                # Home Templates
                {
                    'name': 'New Home',
                    'description': 'Basic household essentials for new home',
                    'list_type': 'home',
                    'items': ['Toilet paper', 'Paper towels', 'Detergent', 'Soap', 'Shampoo', 'Toothpaste', 'Light bulbs', 'Batteries', 'Cleaning supplies']
                },
                {
                    'name': 'Home Office',
                    'description': 'Supplies for remote work',
                    'list_type': 'home',
                    'items': ['Notebooks', 'Pens', 'Pencils', 'Stapler', 'Paper clips', 'Folders', 'Printer paper', 'Ink cartridges']
                },
                {
                    'name': 'Garden Setup',
                    'description': 'Tools and supplies for gardening',
                    'list_type': 'home',
                    'items': ['Seeds', 'Fertilizer', 'Pots', 'Garden tools', 'Watering can', 'Gloves', 'Soil', 'Plant markers']
                },
                
                # Special Occasion Templates
                {
                    'name': 'Birthday Party',
                    'description': 'Everything for a birthday celebration',
                    'list_type': 'gifts_cards',
                    'items': ['Balloons', 'Candles', 'Cake', 'Party decorations', 'Gift wrapping', 'Party favors', 'Soda', 'Snacks']
                },
                {
                    'name': 'Wedding Shower',
                    'description': 'Items for wedding shower celebration',
                    'list_type': 'gifts_cards',
                    'items': ['Gift wrapping', 'Greeting cards', 'Decorations', 'Candles', 'Party supplies', 'Gifts', 'Flowers', 'Champagne']
                },
                
                # Travel Templates
                {
                    'name': 'Beach Vacation',
                    'description': 'Essentials for beach vacation',
                    'list_type': 'travel',
                    'items': ['Sunscreen', 'Beach towels', 'Swimwear', 'Sunglasses', 'Hat', 'Snacks', 'Water', 'Beach toys']
                },
                {
                    'name': 'Camping Trip',
                    'description': 'Food and supplies for camping',
                    'list_type': 'travel',
                    'items': ['Canned food', 'Water', 'Snacks', 'Coffee', 'Tea', 'Matches', 'Flashlight', 'Batteries', 'First aid kit']
                },
                {
                    'name': 'Road Trip',
                    'description': 'Snacks and supplies for road travel',
                    'list_type': 'travel',
                    'items': ['Snacks', 'Water', 'Soda', 'Coffee', 'Maps', 'Phone charger', 'Music', 'Games', 'Blankets']
                },
                
                # Lifestyle Templates
                {
                    'name': 'Fitness/Workout',
                    'description': 'Supplies for fitness and workout',
                    'list_type': 'personal_care',
                    'items': ['Protein powder', 'Energy bars', 'Water bottle', 'Workout clothes', 'Sneakers', 'Towel', 'Headphones', 'Fitness tracker']
                },
                {
                    'name': 'Meal Prep',
                    'description': 'Containers and ingredients for weekly meal prep',
                    'list_type': 'supermarket',
                    'items': ['Meal containers', 'Rice', 'Chicken', 'Vegetables', 'Quinoa', 'Beans', 'Olive oil', 'Herbs', 'Spices']
                }
            ]
            
            # Filter out templates that already exist
            new_templates = [t for t in missing_templates if t['name'] not in existing_names]
            
            if not new_templates:
                logging.info("All templates already exist")
                return
            
            # Insert new templates
            for template in new_templates:
                cursor.execute('''
                    INSERT INTO templates (name, description, list_type, items, created_by, is_system_template, usage_count)
                    VALUES (?, ?, ?, ?, ?, TRUE, 0)
                ''', (
                    template['name'],
                    template['description'],
                    template['list_type'],
                    json.dumps(template['items']),
                    admin_user_id
                ))
            
            logging.info(f"Created {len(new_templates)} new system templates")
            
        except Exception as e:
            logging.error(f"Error creating missing templates: {e}")

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
                    SELECT si.id, si.item_name, si.category, si.notes, si.created_at, si.added_by
                    FROM shopping_items si
                    WHERE si.added_by = ?
                    ORDER BY si.category, si.item_name
                ''', (user_id,))
                
                items = []
                for row in cursor.fetchall():
                    item_id, item_name, category, notes, created_at, added_by = row
                    
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
                        'added_by': added_by,
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
                    SELECT si.id, si.item_name, si.category, si.notes, si.created_at, si.added_by
                    FROM shopping_items si
                    WHERE si.added_by = ? AND si.list_id = ?
                    ORDER BY si.category, si.item_name
                ''', (user_id, list_id))
                
                items = []
                for row in cursor.fetchall():
                    item_id, item_name, category, notes, created_at, added_by = row
                    
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
                        'added_by': added_by,
                        'item_notes': item_notes
                    })
                
                return items
                
        except Exception as e:
            logging.error(f"Error getting items by user in list: {e}")
            return []

    def delete_item(self, item_id) -> Optional[str]:
        """Delete an item from the shopping list (handles both regular and dynamic items)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if it's a dynamic item ID
                if isinstance(item_id, str) and item_id.startswith("dynamic_"):
                    # Extract the actual ID from the dynamic item format
                    actual_id = item_id.replace("dynamic_", "")
                    cursor.execute('SELECT item_name_en FROM dynamic_category_items WHERE id = ?', (actual_id,))
                    result = cursor.fetchone()
                    if not result:
                        return None
                    item_name = result[0]
                    cursor.execute('DELETE FROM dynamic_category_items WHERE id = ?', (actual_id,))
                    conn.commit()
                    return item_name
                else:
                    # Regular item from shopping_items table
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

    def get_item_by_id(self, item_id) -> Optional[Dict]:
        """Get an item by its ID (handles both regular and dynamic items)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if it's a dynamic item ID
                if isinstance(item_id, str) and item_id.startswith("dynamic_"):
                    # Extract the actual ID from the dynamic item format
                    actual_id = item_id.replace("dynamic_", "")
                    cursor.execute('''
                        SELECT id, item_name_en, category_key, created_at
                        FROM dynamic_category_items 
                        WHERE id = ?
                    ''', (actual_id,))
                    result = cursor.fetchone()
                    if not result:
                        return None
                    return {
                        'id': f"dynamic_{result[0]}",
                        'name': result[1],
                        'category': result[2],
                        'is_permanent': True,
                        'created_at': result[3]
                    }
                else:
                    # Regular item from shopping_items table
                    cursor.execute('''
                        SELECT id, item_name, category, created_at
                        FROM shopping_items 
                        WHERE id = ?
                    ''', (item_id,))
                    result = cursor.fetchone()
                    if not result:
                        return None
                    return {
                        'id': result[0],
                        'name': result[1],
                        'category': result[2],
                        'is_permanent': False,
                        'created_at': result[3]
                    }
                
        except Exception as e:
            logging.error(f"Error getting item by ID: {e}")
            return None

    def get_items_by_category(self, category_key: str) -> List[Dict]:
        """Get all items in a specific category (both permanent and non-permanent)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                items = []
                
                # Get non-permanent items from shopping_items table
                cursor.execute('''
                    SELECT id, item_name, category, created_at
                    FROM shopping_items 
                    WHERE category = ?
                    ORDER BY item_name
                ''', (category_key,))
                
                for row in cursor.fetchall():
                    items.append({
                        'id': row[0],
                        'name': row[1],
                        'category': row[2],
                        'is_permanent': False,  # Items in shopping_items are not permanent
                        'created_at': row[3]
                    })
                
                # Get permanent items from dynamic_category_items table
                cursor.execute('''
                    SELECT id, item_name_en, category_key, created_at
                    FROM dynamic_category_items 
                    WHERE category_key = ?
                    ORDER BY item_name_en
                ''', (category_key,))
                
                for row in cursor.fetchall():
                    items.append({
                        'id': f"dynamic_{row[0]}",  # Use a different ID format for dynamic items
                        'name': row[1],
                        'category': row[2],
                        'is_permanent': True,  # Items in dynamic_category_items are permanent
                        'created_at': row[3]
                    })
                
                # Sort all items by name
                items.sort(key=lambda x: x['name'])
                
                return items
                
        except Exception as e:
            logging.error(f"Error getting items by category: {e}")
            return []

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
                # Items with numeric notes (quantities) should merge, descriptive notes should stay separate
                if notes:
                    # Check if notes are numeric (quantity) or descriptive
                    import re
                    is_numeric_note = re.match(r'^\d+$', notes.strip())
                    
                    if is_numeric_note:
                        # For numeric notes, check for any existing item with same name (merge quantities)
                        cursor.execute('''
                            SELECT id FROM shopping_items 
                            WHERE list_id = ? AND LOWER(item_name) = LOWER(?)
                        ''', (list_id, item_name))
                    else:
                        # For descriptive notes, check for exact match (name + notes)
                        cursor.execute('''
                            SELECT id FROM shopping_items 
                            WHERE list_id = ? AND LOWER(item_name) = LOWER(?) AND notes = ?
                        ''', (list_id, item_name, notes))
                else:
                    # If adding without notes, check for items without notes
                    cursor.execute('''
                        SELECT id FROM shopping_items 
                        WHERE list_id = ? AND LOWER(item_name) = LOWER(?) AND (notes IS NULL OR notes = '')
                    ''', (list_id, item_name))
                
                existing_item = cursor.fetchone()
                
                if existing_item:
                    item_id = existing_item[0]
                    
                    if notes:
                        # Check if we're dealing with numeric notes (quantities)
                        import re
                        is_numeric_note = re.match(r'^\d+$', notes.strip())
                        
                        if is_numeric_note:
                            # For numeric notes, update the existing item's notes with combined quantity
                            cursor.execute('SELECT notes FROM shopping_items WHERE id = ?', (item_id,))
                            existing_notes = cursor.fetchone()[0]
                            
                            if existing_notes and re.match(r'^\d+$', existing_notes.strip()):
                                # Both are numeric, keep the maximum quantity
                                new_quantity = max(int(existing_notes), int(notes))
                                cursor.execute('''
                                    UPDATE shopping_items SET notes = ?, added_by = ? WHERE id = ?
                                ''', (str(new_quantity), added_by, item_id))
                            else:
                                # Existing item has no notes or descriptive notes, set quantity
                                cursor.execute('''
                                    UPDATE shopping_items SET notes = ?, added_by = ? WHERE id = ?
                                ''', (notes, added_by, item_id))
                        else:
                            # For descriptive notes, add as separate note
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

    def restore_deleted_item(self, category_key: str, item_name: str) -> bool:
        """Restore a previously deleted item by removing it from deleted_items table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM deleted_items 
                    WHERE category_key = ? AND item_name = ?
                ''', (category_key, item_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error restoring deleted item: {e}")
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

    # Template Methods
    def create_template(self, name: str, description: str, list_type: str, items: List[Dict], 
                       created_by: int, is_system_template: bool = False) -> Optional[int]:
        """Create a new template"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO templates (name, description, list_type, items, created_by, is_system_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, description, list_type, json.dumps(items), created_by, is_system_template))
                template_id = cursor.lastrowid
                conn.commit()
                return template_id
        except Exception as e:
            logging.error(f"Error creating template: {e}")
            return None

    def get_all_system_templates(self) -> List[Dict]:
        """Get all system templates (global, not list-specific)"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT t.id, t.name, t.name_he, t.description, t.description_he, t.list_type, t.items, t.items_he, t.created_by, t.is_system_template,
                           t.usage_count, t.last_used, t.created_at,
                           u.username, u.first_name, u.last_name
                    FROM templates t
                    LEFT JOIN users u ON t.created_by = u.user_id
                    WHERE t.is_system_template = TRUE
                    ORDER BY t.usage_count DESC, t.created_at DESC
                ''')
                
                templates = []
                for row in cursor.fetchall():
                    template = {
                        'id': row[0],
                        'name': row[1],
                        'name_he': row[2],
                        'description': row[3],
                        'description_he': row[4],
                        'list_type': row[5],
                        'items': json.loads(row[6]) if row[6] else [],
                        'items_he': json.loads(row[7]) if row[7] else None,
                        'created_by': row[8],
                        'is_system_template': bool(row[9]),
                        'usage_count': row[10] or 0,
                        'last_used': row[11],
                        'created_at': row[12],
                        'username': row[13],
                        'first_name': row[14],
                        'last_name': row[15]
                    }
                    templates.append(template)
                
                return templates
        except Exception as e:
            print(f"Error getting all system templates: {e}")
            return []

    def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        """Get a template by its ID"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT t.id, t.name, t.name_he, t.description, t.description_he, t.list_type, t.items, t.items_he, t.created_by, t.is_system_template,
                           t.usage_count, t.last_used, t.created_at,
                           u.username, u.first_name, u.last_name
                    FROM templates t
                    LEFT JOIN users u ON t.created_by = u.user_id
                    WHERE t.id = ?
                ''', (template_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'name_he': row[2],
                        'description': row[3],
                        'description_he': row[4],
                        'list_type': row[5],
                        'items': json.loads(row[6]) if row[6] else [],
                        'items_he': json.loads(row[7]) if row[7] else None,
                        'created_by': row[8],
                        'is_system_template': bool(row[9]),
                        'usage_count': row[10] or 0,
                        'last_used': row[11],
                        'created_at': row[12],
                        'username': row[13],
                        'first_name': row[14],
                        'last_name': row[15]
                    }
                return None
        except Exception as e:
            print(f"Error getting template by ID: {e}")
            return None

    def add_hebrew_translations_to_templates(self):
        """Add Hebrew translations to existing system templates"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all templates without Hebrew translations
                cursor.execute('''
                    SELECT id, name, description, items 
                    FROM templates 
                    WHERE name_he IS NULL OR name_he = ''
                ''')
                
                templates = cursor.fetchall()
                
                # Translation mappings
                name_translations = {
                    'Weekly Groceries': 'קניות שבועיות',
                    'Breakfast Essentials': 'חיוני לארוחת בוקר',
                    'Dinner Party': 'מסיבת ערב',
                    'BBQ/Grill': 'על האש/גריל',
                    'Kids Lunch': 'ארוחת צהריים לילדים',
                    'Vegetarian Week': 'שבוע צמחוני',
                    'Budget Shopping': 'קניות בתקציב',
                    'First Aid Kit': 'ערכת עזרה ראשונה',
                    'Cold & Flu': 'הצטננות ושפעת',
                    'Baby Care': 'טיפול בתינוק',
                    'New Home': 'בית חדש',
                    'Home Office': 'משרד ביתי',
                    'Garden Setup': 'הקמת גינה',
                    'Birthday Party': 'מסיבת יום הולדת',
                    'Wedding Shower': 'מסיבת רווקות',
                    'Beach Vacation': 'חופשת חוף',
                    'Camping Trip': 'טיול קמפינג',
                    'Road Trip': 'טיול כביש',
                    'Fitness/Workout': 'כושר/אימון',
                    'Meal Prep': 'הכנת ארוחות'
                }
                
                description_translations = {
                    'Standard weekly shopping essentials': 'חיוניות קניות שבועיות סטנדרטיות',
                    'Everything needed for breakfast': 'כל מה שצריך לארוחת בוקר',
                    'Ingredients for hosting dinner guests': 'מרכיבים לאירוח אורחים לארוחת ערב',
                    'Everything for a barbecue': 'כל מה שצריך לעל האש',
                    'School lunch items and snacks': 'פריטי ארוחת צהריים וחטיפים לבית הספר',
                    'Plant-based meal ingredients': 'מרכיבי ארוחות צמחוניות',
                    'Essential items for tight budgets': 'פריטים חיוניים לתקציבים צמודים',
                    'Essential first aid supplies': 'אספקת עזרה ראשונה חיונית',
                    'Medicine and supplies for cold and flu': 'תרופות ואספקה להצטננות ושפעת',
                    'Essential baby care items': 'פריטי טיפול בתינוק חיוניים',
                    'Basic household essentials for new home': 'חיוניות בית בסיסיות לבית חדש',
                    'Supplies for remote work': 'אספקה לעבודה מרחוק',
                    'Tools and supplies for gardening': 'כלים ואספקה לגינון',
                    'Everything for a birthday celebration': 'כל מה שצריך לחגיגת יום הולדת',
                    'Items for wedding shower celebration': 'פריטים לחגיגת מסיבת רווקות',
                    'Essentials for beach vacation': 'חיוניות לחופשת חוף',
                    'Food and supplies for camping': 'אוכל ואספקה לקמפינג',
                    'Snacks and supplies for road travel': 'חטיפים ואספקה לנסיעות כביש',
                    'Supplies for fitness and workout': 'אספקה לכושר ואימון',
                    'Containers and ingredients for weekly meal prep': 'מיכלים ומרכיבים להכנת ארוחות שבועיות'
                }
                
                item_translations = {
                    'Milk': 'חלב', 'Bread': 'לחם', 'Eggs': 'ביצים', 'Cheese': 'גבינה', 'Yogurt': 'יוגורט',
                    'Apples': 'תפוחים', 'Bananas': 'בננות', 'Carrots': 'גזר', 'Onions': 'בצל', 'Potatoes': 'תפוחי אדמה',
                    'Chicken': 'עוף', 'Ground meat': 'בשר טחון', 'Rice': 'אורז', 'Pasta': 'פסטה', 'Cereal': 'דגנים',
                    'Coffee': 'קפה', 'Tea': 'תה', 'Oats': 'שיבולת שועל', 'Butter': 'חמאה', 'Jam': 'ריבה',
                    'Orange juice': 'מיץ תפוזים', 'Fruits': 'פירות', 'Wine': 'יין', 'Olives': 'זיתים',
                    'Salmon': 'סלמון', 'Beef': 'בקר', 'Vegetables': 'ירקות', 'Herbs': 'עשבי תיבול',
                    'Olive oil': 'שמן זית', 'Vinegar': 'חומץ', 'Dessert': 'קינוח', 'Pork': 'חזיר',
                    'Sausages': 'נקניקיות', 'Bacon': 'בייקון', 'Ketchup': 'קטשופ', 'Mustard': 'חרדל',
                    'BBQ sauce': 'רוטב על האש', 'Charcoal': 'פחם', 'Beer': 'בירה', 'Soda': 'משקה מוגז',
                    'Ham': 'נקניק', 'Juice boxes': 'קופסאות מיץ', 'Crackers': 'קרקרים', 'Cookies': 'עוגיות',
                    'Nuts': 'אגוזים', 'Granola bars': 'חטיפי גרנולה', 'Tofu': 'טופו', 'Beans': 'שעועית',
                    'Lentils': 'עדשים', 'Quinoa': 'קינואה', 'Seeds': 'זרעים', 'Bandages': 'תחבושות',
                    'Antiseptic': 'חומר חיטוי', 'Pain relievers': 'משככי כאבים', 'Thermometer': 'מדחום',
                    'Gauze': 'גזה', 'Medical tape': 'סרט רפואי', 'Scissors': 'מספריים', 'Tweezers': 'פינצטה',
                    'Cough syrup': 'סירופ שיעול', 'Throat lozenges': 'סוכריות גרון', 'Tissues': 'ממחטות',
                    'Nasal spray': 'תרסיס אף', 'Vitamins': 'ויטמינים', 'Honey': 'דבש', 'Diapers': 'חיתולים',
                    'Baby formula': 'תחליף חלב', 'Baby food': 'אוכל תינוקות', 'Baby wipes': 'מגבונים לתינוק',
                    'Baby shampoo': 'שמפו לתינוק', 'Baby lotion': 'קרם לתינוק', 'Pacifiers': 'מוצצים',
                    'Toilet paper': 'נייר טואלט', 'Paper towels': 'מגבות נייר', 'Detergent': 'אבקת כביסה',
                    'Soap': 'סבון', 'Shampoo': 'שמפו', 'Toothpaste': 'משחת שיניים', 'Light bulbs': 'נורות',
                    'Batteries': 'סוללות', 'Cleaning supplies': 'אספקת ניקיון', 'Notebooks': 'מחברות',
                    'Pens': 'עטים', 'Pencils': 'עפרונות', 'Stapler': 'מהדק', 'Paper clips': 'סיכות נייר',
                    'Folders': 'תיקיות', 'Printer paper': 'נייר מדפסת', 'Ink cartridges': 'מחסניות דיו',
                    'Fertilizer': 'דשן', 'Pots': 'עציצים', 'Garden tools': 'כלי גינה', 'Watering can': 'משפך השקיה',
                    'Gloves': 'כפפות', 'Soil': 'אדמה', 'Plant markers': 'סימני צמחים', 'Balloons': 'בלונים',
                    'Candles': 'נרות', 'Cake': 'עוגה', 'Party decorations': 'קישוטי מסיבה',
                    'Gift wrapping': 'עטיפת מתנות', 'Party favors': 'מתנות מסיבה', 'Snacks': 'חטיפים',
                    'Greeting cards': 'כרטיסי ברכה', 'Decorations': 'קישוטים', 'Party supplies': 'אספקת מסיבה',
                    'Gifts': 'מתנות', 'Flowers': 'פרחים', 'Champagne': 'שמפניה', 'Sunscreen': 'קרם הגנה',
                    'Beach towels': 'מגבות חוף', 'Swimwear': 'בגדי ים', 'Sunglasses': 'משקפי שמש',
                    'Hat': 'כובע', 'Water': 'מים', 'Beach toys': 'צעצועי חוף', 'Canned food': 'אוכל משומר',
                    'Matches': 'גפרורים', 'Flashlight': 'פנס', 'First aid kit': 'ערכת עזרה ראשונה',
                    'Maps': 'מפות', 'Phone charger': 'מטען טלפון', 'Music': 'מוזיקה', 'Games': 'משחקים',
                    'Blankets': 'שמיכות', 'Protein powder': 'אבקת חלבון', 'Energy bars': 'חטיפי אנרגיה',
                    'Water bottle': 'בקבוק מים', 'Workout clothes': 'בגדי אימון', 'Sneakers': 'נעלי ספורט',
                    'Towel': 'מגבת', 'Headphones': 'אוזניות', 'Fitness tracker': 'מעקב כושר',
                    'Meal containers': 'מיכלי ארוחות', 'Spices': 'תבלינים', 'Drinks': 'משקאות'
                }
                
                updated_count = 0
                for template_id, name, description, items_json in templates:
                    # Get Hebrew translations
                    name_he = name_translations.get(name, name)
                    description_he = description_translations.get(description, description) if description else None
                    
                    # Translate items
                    items = json.loads(items_json) if items_json else []
                    items_he = [item_translations.get(item, item) for item in items]
                    
                    # Update the template
                    cursor.execute('''
                        UPDATE templates 
                        SET name_he = ?, description_he = ?, items_he = ?
                        WHERE id = ?
                    ''', (name_he, description_he, json.dumps(items_he), template_id))
                    
                    updated_count += 1
                
                conn.commit()
                print(f"Successfully added Hebrew translations to {updated_count} templates")
                return True
                
        except Exception as e:
            print(f"Error adding Hebrew translations to templates: {e}")
            return False

    def get_templates_by_list_type(self, list_type: str, user_id: int = None) -> List[Dict]:
        """Get templates for a specific list type"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if user_id:
                    # Get user templates for this list type and ALL system templates
                    cursor.execute('''
                        SELECT t.id, t.name, t.name_he, t.description, t.description_he, t.items, t.items_he, t.created_by, t.is_system_template,
                               t.usage_count, t.last_used, t.created_at,
                               u.username, u.first_name, u.last_name
                        FROM templates t
                        LEFT JOIN users u ON t.created_by = u.user_id
                        WHERE (t.list_type = ? AND t.created_by = ?) OR t.is_system_template = TRUE
                        ORDER BY t.is_system_template DESC, t.usage_count DESC, t.created_at DESC
                    ''', (list_type, user_id))
                else:
                    # Get user templates for this list type and ALL system templates
                    cursor.execute('''
                        SELECT t.id, t.name, t.name_he, t.description, t.description_he, t.items, t.items_he, t.created_by, t.is_system_template,
                               t.usage_count, t.last_used, t.created_at,
                               u.username, u.first_name, u.last_name
                        FROM templates t
                        LEFT JOIN users u ON t.created_by = u.user_id
                        WHERE t.list_type = ? OR t.is_system_template = TRUE
                        ORDER BY t.is_system_template DESC, t.usage_count DESC, t.created_at DESC
                    ''', (list_type,))
                
                templates = []
                for row in cursor.fetchall():
                    templates.append({
                        'id': row[0],
                        'name': row[1],
                        'name_he': row[2],
                        'description': row[3],
                        'description_he': row[4],
                        'items': json.loads(row[5]) if row[5] else [],
                        'items_he': json.loads(row[6]) if row[6] else None,
                        'created_by': row[7],
                        'is_system_template': row[8],
                        'usage_count': row[9],
                        'last_used': row[10],
                        'created_at': row[11],
                        'creator_username': row[12],
                        'creator_first_name': row[13],
                        'creator_last_name': row[14]
                    })
                return templates
        except Exception as e:
            logging.error(f"Error getting templates by list type: {e}")
            return []

    def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        """Get a specific template by ID"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.id, t.name, t.description, t.list_type, t.items, t.created_by, 
                           t.is_system_template, t.usage_count, t.last_used, t.created_at,
                           u.username, u.first_name, u.last_name
                    FROM templates t
                    LEFT JOIN users u ON t.created_by = u.user_id
                    WHERE t.id = ?
                ''', (template_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'items': json.loads(row[4]),
                        'created_by': row[5],
                        'is_system_template': row[6],
                        'usage_count': row[7],
                        'last_used': row[8],
                        'created_at': row[9],
                        'creator_username': row[10],
                        'creator_first_name': row[11],
                        'creator_last_name': row[12]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting template by ID: {e}")
            return None

    def update_template(self, template_id: int, name: str = None, description: str = None, 
                       items: List[Dict] = None) -> bool:
        """Update a template"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if items is not None:
                    updates.append("items = ?")
                    params.append(json.dumps(items))
                
                if not updates:
                    return False
                
                params.append(template_id)
                cursor.execute(f'''
                    UPDATE templates 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error updating template: {e}")
            return False

    def delete_template(self, template_id: int, user_id: int) -> bool:
        """Delete a template (only if user is creator or admin)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user can delete this template
                cursor.execute('''
                    SELECT created_by, is_system_template FROM templates WHERE id = ?
                ''', (template_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                created_by, is_system_template = result
                
                # System templates can only be deleted by admins
                if is_system_template and not self.is_user_admin(user_id):
                    return False
                
                # User templates can only be deleted by creator or admin
                if not is_system_template and created_by != user_id and not self.is_user_admin(user_id):
                    return False
                
                # Delete template usage records first
                cursor.execute('DELETE FROM template_usage WHERE template_id = ?', (template_id,))
                
                # Delete the template
                cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting template: {e}")
            return False

    def increment_template_usage(self, template_id: int, user_id: int, usage_type: str = 'load', 
                                items_added: int = 0) -> bool:
        """Increment template usage count and track usage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update template usage count and last_used
                cursor.execute('''
                    UPDATE templates 
                    SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (template_id,))
                
                # Add usage tracking record
                cursor.execute('''
                    INSERT INTO template_usage (template_id, user_id, usage_type, items_added)
                    VALUES (?, ?, ?, ?)
                ''', (template_id, user_id, usage_type, items_added))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error incrementing template usage: {e}")
            return False

    def get_template_usage_stats(self, template_id: int = None) -> List[Dict]:
        """Get template usage statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if template_id:
                    cursor.execute('''
                        SELECT tu.usage_type, COUNT(*) as count, AVG(tu.items_added) as avg_items,
                               t.name, u.first_name, u.username
                        FROM template_usage tu
                        JOIN templates t ON tu.template_id = t.id
                        JOIN users u ON tu.user_id = u.user_id
                        WHERE tu.template_id = ?
                        GROUP BY tu.usage_type
                        ORDER BY count DESC
                    ''', (template_id,))
                else:
                    cursor.execute('''
                        SELECT t.id, t.name, t.list_type, t.usage_count, t.last_used,
                               COUNT(tu.id) as total_usage, AVG(tu.items_added) as avg_items_added
                        FROM templates t
                        LEFT JOIN template_usage tu ON t.id = tu.template_id
                        GROUP BY t.id
                        ORDER BY t.usage_count DESC, total_usage DESC
                    ''')
                
                stats = []
                for row in cursor.fetchall():
                    if template_id:
                        stats.append({
                            'usage_type': row[0],
                            'count': row[1],
                            'avg_items': row[2],
                            'template_name': row[3],
                            'user_name': row[4] or row[5]
                        })
                    else:
                        stats.append({
                            'template_id': row[0],
                            'template_name': row[1],
                            'list_type': row[2],
                            'usage_count': row[3],
                            'last_used': row[4],
                            'total_usage': row[5],
                            'avg_items_added': row[6]
                        })
                return stats
        except Exception as e:
            logging.error(f"Error getting template usage stats: {e}")
            return []

    def create_template_from_list(self, list_id: int, template_name: str, created_by: int, 
                                 template_description: str = None) -> Optional[int]:
        """Create a template from an existing list"""
        try:
            import json
            
            # Get list items
            items = self.get_shopping_list_by_id(list_id)
            if not items:
                return None
            
            # Convert items to template format
            template_items = []
            for item in items:
                template_items.append({
                    'name': item['name'],
                    'category': item['category'],
                    'notes': item['notes']
                })
            
            # Get list type
            list_info = self.get_list_by_id(list_id)
            list_type = list_info['list_type'] if list_info else 'custom'
            
            # Create template
            return self.create_template(template_name, template_description, list_type, 
                                      template_items, created_by)
        except Exception as e:
            logging.error(f"Error creating template from list: {e}")
            return None

    def add_template_items_to_list(self, template_id: int, list_id: int, selected_items: List[str] = None, 
                                  added_by: int = None) -> int:
        """Add template items to a list"""
        try:
            template = self.get_template_by_id(template_id)
            if not template:
                return 0
            
            items_added = 0
            template_items = template['items']
            
            # If no specific items selected, add all items
            if selected_items is None:
                selected_items = []
                for item in template_items:
                    if isinstance(item, dict):
                        selected_items.append(item.get('name', str(item)))
                    else:
                        selected_items.append(str(item))
            
            for item in template_items:
                # Handle both string items and dict items
                if isinstance(item, dict):
                    item_name = item.get('name', str(item))
                else:
                    item_name = str(item)
                
                if item_name in selected_items:
                    success = self.add_item_to_list(
                        list_id, 
                        item_name,
                        None,  # no category for template items
                        None,  # no notes for template items
                        added_by
                    )
                    if success:
                        items_added += 1
            
            # Track usage
            self.increment_template_usage(template_id, added_by, 'load', items_added)
            
            return items_added
        except Exception as e:
            logging.error(f"Error adding template items to list: {e}")
            return 0

    def get_user_templates(self, user_id: int) -> List[Dict]:
        """Get templates created by a specific user"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, list_type, items, usage_count, last_used, created_at
                    FROM templates
                    WHERE created_by = ?
                    ORDER BY usage_count DESC, created_at DESC
                ''', (user_id,))
                
                templates = []
                for row in cursor.fetchall():
                    templates.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'items': json.loads(row[4]),
                        'usage_count': row[5],
                        'last_used': row[6],
                        'created_at': row[7]
                    })
                return templates
        except Exception as e:
            logging.error(f"Error getting user templates: {e}")
            return []

    def get_list_id_by_type(self, list_type: str) -> Optional[int]:
        """Get list_id by list_type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM lists WHERE list_type = ?', (list_type,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logging.error(f"Error getting list_id by type: {e}")
            return None

    def get_popular_templates(self, list_type: str = None, limit: int = 10) -> List[Dict]:
        """Get most popular templates"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if list_type:
                    cursor.execute('''
                        SELECT t.id, t.name, t.description, t.list_type, t.items, t.usage_count, t.last_used,
                               u.username, u.first_name, u.last_name
                        FROM templates t
                        LEFT JOIN users u ON t.created_by = u.user_id
                        WHERE t.list_type = ?
                        ORDER BY t.usage_count DESC, t.last_used DESC
                        LIMIT ?
                    ''', (list_type, limit))
                else:
                    cursor.execute('''
                        SELECT t.id, t.name, t.description, t.list_type, t.items, t.usage_count, t.last_used,
                               u.username, u.first_name, u.last_name
                        FROM templates t
                        LEFT JOIN users u ON t.created_by = u.user_id
                        ORDER BY t.usage_count DESC, t.last_used DESC
                        LIMIT ?
                    ''', (limit,))
                
                templates = []
                for row in cursor.fetchall():
                    templates.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'list_type': row[3],
                        'items': json.loads(row[4]),
                        'usage_count': row[5],
                        'last_used': row[6],
                        'creator_username': row[7],
                        'creator_first_name': row[8],
                        'creator_last_name': row[9]
                    })
                return templates
        except Exception as e:
            logging.error(f"Error getting popular templates: {e}")
            return []
    
    def create_list_sharing(self, list_id: int, user_ids: List[int]) -> bool:
        """Create sharing records for a custom shared list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for user_id in user_ids:
                    cursor.execute('''
                        INSERT OR IGNORE INTO list_sharing (list_id, user_id)
                        VALUES (?, ?)
                    ''', (list_id, user_id))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error creating list sharing: {e}")
            return False
    
    def get_user_accessible_lists(self, user_id: int, list_types: List[str] = None) -> List[Dict]:
        """Get lists accessible to a specific user (includes custom shared lists)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build base query
                query = '''
                    SELECT DISTINCT l.id, l.name, l.description, l.list_type, l.created_by, l.created_at,
                           u.username, u.first_name, u.last_name
                    FROM lists l
                    LEFT JOIN users u ON l.created_by = u.user_id
                    LEFT JOIN list_sharing ls ON l.id = ls.list_id
                    WHERE l.is_active = TRUE
                    AND (
                        l.list_type IN ('supermarket', 'shared', 'personal')
                        OR (l.list_type = 'custom_shared' AND (l.created_by = ? OR ls.user_id = ?))
                    )
                '''
                params = [user_id, user_id]
                
                # Add list_type filter if specified
                if list_types:
                    placeholders = ','.join(['?' for _ in list_types])
                    query += f' AND l.list_type IN ({placeholders})'
                    params.extend(list_types)
                
                query += ' ORDER BY l.list_type, l.name'
                
                cursor.execute(query, params)
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
            logging.error(f"Error getting user accessible lists: {e}")
            return []
    
    def get_custom_shared_list_users(self, list_id: int) -> List[Dict]:
        """Get users who have access to a custom shared list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.user_id, u.username, u.first_name, u.last_name, ls.can_edit, ls.shared_at
                    FROM list_sharing ls
                    JOIN users u ON ls.user_id = u.user_id
                    WHERE ls.list_id = ?
                    ORDER BY u.first_name, u.last_name
                ''', (list_id,))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'can_edit': row[4],
                        'shared_at': row[5]
                    })
                return users
        except Exception as e:
            logging.error(f"Error getting custom shared list users: {e}")
            return []
    
    def freeze_list(self, list_id: int) -> bool:
        """Freeze a list (cannot add/remove items anymore)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE lists 
                    SET is_frozen = TRUE, frozen_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (list_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error freezing list: {e}")
            return False
    
    def unfreeze_list(self, list_id: int) -> bool:
        """Unfreeze a list (restore normal functionality)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE lists 
                    SET is_frozen = FALSE, frozen_at = NULL
                    WHERE id = ?
                ''', (list_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error unfreezing list: {e}")
            return False
    
    def is_list_frozen(self, list_id: int) -> bool:
        """Check if a list is frozen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_frozen FROM lists WHERE id = ?', (list_id,))
                result = cursor.fetchone()
                return result[0] if result else False
        except Exception as e:
            logging.error(f"Error checking if list is frozen: {e}")
            return False
    
    def get_frozen_info(self, list_id: int) -> Dict:
        """Get frozen information for a list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT is_frozen, frozen_at FROM lists WHERE id = ?
                ''', (list_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'is_frozen': result[0],
                        'frozen_at': result[1]
                    }
                return {'is_frozen': False, 'frozen_at': None}
        except Exception as e:
            logging.error(f"Error getting frozen info: {e}")
            return {'is_frozen': False, 'frozen_at': None}
    
    def mark_item_status(self, item_id: int, status: str, user_id: int) -> bool:
        """Mark an item as bought or not found"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First check if this item exists and get its list_id
                cursor.execute('SELECT id, list_id FROM shopping_items WHERE id = ?', (item_id,))
                item_result = cursor.fetchone()
                
                if not item_result:
                    return False
                
                # Check if the list is frozen (only frozen lists allow status marking)
                if not self.is_list_frozen(item_result[1]):
                    return False
                
                # Insert or update item status
                cursor.execute('''
                    INSERT OR REPLACE INTO item_status_tracking 
                    (item_id, user_id, status, updated_at) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (item_id, user_id, status))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error marking item status: {e}")
            return False
    
    def get_item_status(self, item_id: int, user_id: int) -> str:
        """Get item status for a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT status FROM item_status_tracking 
                    WHERE item_id = ? AND user_id = ?
                ''', (item_id, user_id))
                result = cursor.fetchone()
                return result[0] if result else 'pending'
        except Exception as e:
            logging.error(f"Error getting item status: {e}")
            return 'pending'
    
    def get_shopping_item_by_id(self, item_id: int) -> Dict:
        """Get shopping item by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, item_name, notes, category, list_id 
                    FROM shopping_items WHERE id = ?
                ''', (item_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result[0],
                        'name': result[1],  # item_name from DB
                        'notes': result[2],
                        'category': result[3],
                        'list_id': result[4]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting shopping item by ID: {e}")
            return None
    
    def clear_item_statuses_for_list(self, list_id: int) -> bool:
        """Clear all item status tracking for a specific list"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all items in this list
                cursor.execute('SELECT id FROM shopping_items WHERE list_id = ?', (list_id,))
                item_ids = [row[0] for row in cursor.fetchall()]
                
                if item_ids:
                    # Clear status tracking for all items in this list
                    placeholders = ','.join('?' for _ in item_ids)
                    cursor.execute(f'''
                        DELETE FROM item_status_tracking 
                        WHERE item_id IN ({placeholders})
                    ''', item_ids)
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error clearing item statuses for list: {e}")
            return False
