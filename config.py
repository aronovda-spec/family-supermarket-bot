import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Admin Configuration
ADMIN_IDS = []
admin_ids_str = os.getenv('ADMIN_IDS', '')
if admin_ids_str:
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'shopping_bot.db')

# Categories Configuration
CATEGORIES = {
    'dairy': {'name': 'Dairy', 'emoji': '🥛', 'items': ['Milk', 'Cheese', 'Yogurt', 'Butter', 'Cream', 'Eggs']},
    'fruits_vegetables': {'name': 'Fruits & Vegetables', 'emoji': '🥦🍎', 'items': ['Apples', 'Bananas', 'Carrots', 'Broccoli', 'Tomatoes', 'Onions', 'Potatoes', 'Lettuce']},
    'meat_fish': {'name': 'Meat & Fish', 'emoji': '🍗🐟', 'items': ['Chicken', 'Beef', 'Pork', 'Salmon', 'Tuna', 'Ground meat']},
    'staples': {'name': 'Staples', 'emoji': '🍞🍝', 'items': ['Bread', 'Pasta', 'Rice', 'Flour', 'Cereal', 'Oats']},
    'snacks': {'name': 'Snacks', 'emoji': '🍫', 'items': ['Chocolate', 'Chips', 'Cookies', 'Nuts', 'Crackers', 'Ice cream']},
    'cleaning_household': {'name': 'Cleaning & Household', 'emoji': '🧴🧻', 'items': ['Toilet paper', 'Paper towels', 'Detergent', 'Soap', 'Shampoo', 'Toothpaste']},
    'beverages': {'name': 'Beverages', 'emoji': '🥤', 'items': ['Coffee', 'Tea', 'Juice', 'Soda', 'Water', 'Beer', 'Wine']},
    'frozen': {'name': 'Frozen Foods', 'emoji': '🧊', 'items': ['Frozen vegetables', 'Ice cream', 'Frozen pizza', 'Frozen meals', 'Frozen fruit']},
    'condiments': {'name': 'Condiments & Spices', 'emoji': '🧂', 'items': ['Salt', 'Pepper', 'Ketchup', 'Mustard', 'Olive oil', 'Vinegar', 'Garlic', 'Herbs']},
    'baby_pet': {'name': 'Baby & Pet', 'emoji': '👶🐕', 'items': ['Diapers', 'Baby food', 'Pet food', 'Cat litter', 'Dog treats']},
    'pharmacy': {'name': 'Pharmacy & Health', 'emoji': '💊', 'items': ['Vitamins', 'Pain relievers', 'First aid', 'Bandages', 'Thermometer']},
    'bakery': {'name': 'Bakery', 'emoji': '🥐', 'items': ['Fresh bread', 'Croissants', 'Muffins', 'Bagels', 'Donuts']}
}

# Bot Messages
MESSAGES = {
    'welcome': "🛒 Welcome to Family Shopping List Bot!\n\nThis bot helps manage your weekly shopping list with your family.\n\nUse /help to see available commands.",
    'help': """
🛒 **Family Shopping List Bot Commands**

**Main Commands:**
/start - Start the bot and register
/help - Show this help message
/categories - Browse and add items by category
/add - Add a custom item to the list
/list - View current shopping list
/summary - Get formatted shopping report
/myitems - View items you've added

**Admin Commands:**
/reset - 🔴 Reset the entire list
/users - 👥 Manage users and view status
/authorize <user_id> - ✅ Authorize a regular user
/addadmin <user_id> - 👑 Promote user to admin

**Quick Actions:**
- Tap ✅ next to category items to add them
- Add notes when prompted (quantity, brand, etc.)
- Only admins can delete items and reset the list

**Features:**
✅ Pre-defined categories for quick selection
✅ Custom item addition
✅ Optional notes (quantity, brand, priority)
✅ Duplicate handling with note merging
✅ Admin controls for deletion and reset
✅ Summary reports by category and user
✅ User authorization system
    """,
    'not_registered': "❌ You need to be registered to use this bot. Please contact an admin to get access.",
    'admin_only': "❌ This command is only available to administrators.",
    'list_empty': "📝 Your shopping list is currently empty.\n\nUse /categories to browse items or /add to add custom items!",
    'list_reset': "🗑️ Shopping list has been reset by admin.",
    'item_deleted': "🗑️ Item deleted: {item} (by {admin})",
}
