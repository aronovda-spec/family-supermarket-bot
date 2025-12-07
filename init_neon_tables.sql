-- Initialize Neon PostgreSQL Database
-- Run this script in Neon SQL Editor to create all tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    is_authorized BOOLEAN DEFAULT FALSE,
    language TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lists table
CREATE TABLE IF NOT EXISTS lists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    list_type TEXT DEFAULT 'custom',
    created_by INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    is_frozen BOOLEAN DEFAULT FALSE,
    frozen_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (user_id)
);

-- Shopping items table
CREATE TABLE IF NOT EXISTS shopping_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER DEFAULT 1,
    item_name TEXT NOT NULL,
    category TEXT,
    notes TEXT,
    added_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES lists (id),
    FOREIGN KEY (added_by) REFERENCES users (user_id)
);

-- Item notes table
CREATE TABLE IF NOT EXISTS item_notes (
    id SERIAL PRIMARY KEY,
    item_id INTEGER,
    user_id INTEGER,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES shopping_items (id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Broadcast messages table
CREATE TABLE IF NOT EXISTS broadcast_messages (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER,
    message TEXT NOT NULL,
    sent_to_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users (user_id)
);

-- Item suggestions table
CREATE TABLE IF NOT EXISTS item_suggestions (
    id SERIAL PRIMARY KEY,
    suggested_by INTEGER,
    category_key TEXT NOT NULL,
    item_name_en TEXT NOT NULL,
    item_name_he TEXT,
    status TEXT DEFAULT 'pending',
    approved_by INTEGER,
    approved_at TIMESTAMP,
    list_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggested_by) REFERENCES users (user_id),
    FOREIGN KEY (approved_by) REFERENCES users (user_id)
);

-- Maintenance mode table
CREATE TABLE IF NOT EXISTS maintenance_mode (
    id SERIAL PRIMARY KEY,
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
);

-- List sharing table
CREATE TABLE IF NOT EXISTS list_sharing (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    can_edit BOOLEAN DEFAULT TRUE,
    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES lists (id),
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    UNIQUE(list_id, user_id)
);

-- Item status tracking table
CREATE TABLE IF NOT EXISTS item_status_tracking (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('bought', 'not_found', 'pending')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES shopping_items (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(item_id, user_id)
);

-- Custom categories table
CREATE TABLE IF NOT EXISTS custom_categories (
    id SERIAL PRIMARY KEY,
    category_key TEXT UNIQUE NOT NULL,
    emoji TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_he TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (user_id)
);

-- Category suggestions table
CREATE TABLE IF NOT EXISTS category_suggestions (
    id SERIAL PRIMARY KEY,
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
);

-- Deleted items table
CREATE TABLE IF NOT EXISTS deleted_items (
    id SERIAL PRIMARY KEY,
    category_key TEXT NOT NULL,
    item_name TEXT NOT NULL,
    deleted_by INTEGER,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deleted_by) REFERENCES users(user_id)
);

-- Dynamic category items table
CREATE TABLE IF NOT EXISTS dynamic_category_items (
    id SERIAL PRIMARY KEY,
    category_key TEXT NOT NULL,
    item_name_en TEXT NOT NULL,
    item_name_he TEXT,
    added_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (added_by) REFERENCES users(user_id)
);

-- Templates table
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_he TEXT,
    description TEXT,
    description_he TEXT,
    list_type TEXT NOT NULL,
    items TEXT NOT NULL,
    items_he TEXT,
    created_by INTEGER NOT NULL,
    is_system_template BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Template categories table
CREATE TABLE IF NOT EXISTS template_categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    list_type TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Template usage tracking table
CREATE TABLE IF NOT EXISTS template_usage (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    usage_type TEXT NOT NULL,
    items_added INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create default supermarket list
INSERT INTO lists (id, name, description, list_type, created_by)
VALUES (1, 'Supermarket List', 'Weekly family shopping list', 'supermarket', 1)
ON CONFLICT (id) DO NOTHING;

-- Verify tables were created
SELECT 'Tables created successfully!' as status;
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

