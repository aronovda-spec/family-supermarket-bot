import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('bot_config.env')

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

# Categories Configuration - Multi-language
CATEGORIES = {
    'dairy': {
        'emoji': '🥛',
        'name': {'en': 'Dairy', 'he': 'חלבי'},
        'items': {
            'en': ['Milk', 'Cheese', 'Yogurt', 'Butter', 'Cream', 'Eggs'],
            'he': ['חלב', 'גבינה', 'יוגורט', 'חמאה', 'שמנת', 'ביצים']
        }
    },
    'fruits_vegetables': {
        'emoji': '🥦🍎',
        'name': {'en': 'Fruits & Vegetables', 'he': 'פירות וירקות'},
        'items': {
            'en': ['Apples', 'Bananas', 'Carrots', 'Broccoli', 'Tomatoes', 'Onions', 'Potatoes', 'Lettuce'],
            'he': ['תפוחים', 'בננות', 'גזר', 'ברוקולי', 'עגבניות', 'בצל', 'תפוחי אדמה', 'חסה']
        }
    },
    'meat_fish': {
        'emoji': '🍗🐟',
        'name': {'en': 'Meat & Fish', 'he': 'בשר ודגים'},
        'items': {
            'en': ['Chicken', 'Beef', 'Pork', 'Salmon', 'Tuna', 'Ground meat'],
            'he': ['עוף', 'בקר', 'חזיר', 'סלמון', 'טונה', 'בשר טחון']
        }
    },
    'staples': {
        'emoji': '🍞🍝',
        'name': {'en': 'Staples', 'he': 'מוצרי יסוד'},
        'items': {
            'en': ['Bread', 'Pasta', 'Rice', 'Flour', 'Cereal', 'Oats'],
            'he': ['לחם', 'פסטה', 'אורז', 'קמח', 'דגנים', 'שיבולת שועל']
        }
    },
    'snacks': {
        'emoji': '🍫',
        'name': {'en': 'Snacks', 'he': 'חטיפים'},
        'items': {
            'en': ['Chocolate', 'Chips', 'Cookies', 'Nuts', 'Crackers', 'Ice cream'],
            'he': ['שוקולד', 'צ\'יפס', 'עוגיות', 'אגוזים', 'קרקרים', 'גלידה']
        }
    },
    'cleaning_household': {
        'emoji': '🧴🧻',
        'name': {'en': 'Cleaning & Household', 'he': 'ניקוי ומוצרי בית'},
        'items': {
            'en': ['Toilet paper', 'Paper towels', 'Detergent', 'Soap', 'Shampoo', 'Toothpaste'],
            'he': ['נייר טואלט', 'מגבות נייר', 'אבקת כביסה', 'סבון', 'שמפו', 'משחת שיניים']
        }
    },
    'beverages': {
        'emoji': '🥤',
        'name': {'en': 'Beverages', 'he': 'משקאות'},
        'items': {
            'en': ['Coffee', 'Tea', 'Juice', 'Soda', 'Water', 'Beer', 'Wine'],
            'he': ['קפה', 'תה', 'מיץ', 'משקה מוגז', 'מים', 'בירה', 'יין']
        }
    },
    'frozen': {
        'emoji': '🧊',
        'name': {'en': 'Frozen Foods', 'he': 'מוצרים קפואים'},
        'items': {
            'en': ['Frozen vegetables', 'Ice cream', 'Frozen pizza', 'Frozen meals', 'Frozen fruit'],
            'he': ['ירקות קפואים', 'גלידה', 'פיצה קפואה', 'ארוחות קפואות', 'פירות קפואים']
        }
    },
    'condiments': {
        'emoji': '🧂',
        'name': {'en': 'Condiments & Spices', 'he': 'תבלינים ורטבים'},
        'items': {
            'en': ['Salt', 'Pepper', 'Ketchup', 'Mustard', 'Olive oil', 'Vinegar', 'Garlic', 'Herbs'],
            'he': ['מלח', 'פלפל', 'קטשופ', 'חרדל', 'שמן זית', 'חומץ', 'שום', 'עשבי תיבול']
        }
    },
    'baby_pet': {
        'emoji': '👶🐕',
        'name': {'en': 'Baby & Pet', 'he': 'תינוק וחיות מחמד'},
        'items': {
            'en': ['Diapers', 'Baby food', 'Pet food', 'Cat litter', 'Dog treats'],
            'he': ['חיתולים', 'אוכל תינוקות', 'אוכל חיות', 'חול חתולים', 'פינוקים לכלבים']
        }
    },
    'pharmacy': {
        'emoji': '💊',
        'name': {'en': 'Pharmacy & Health', 'he': 'בית מרקחת ובריאות'},
        'items': {
            'en': ['Vitamins', 'Pain relievers', 'First aid', 'Bandages', 'Thermometer'],
            'he': ['ויטמינים', 'משככי כאבים', 'עזרה ראשונה', 'תחבושות', 'מדחום']
        }
    },
    'bakery': {
        'emoji': '🥐',
        'name': {'en': 'Bakery', 'he': 'מאפייה'},
        'items': {
            'en': ['Fresh bread', 'Croissants', 'Muffins', 'Bagels', 'Donuts'],
            'he': ['לחם טרי', 'קרואסון', 'מאפינס', 'בייגלים', 'סופגניות']
        }
    }
}

# Language Configuration
LANGUAGES = {
    'en': {
        'name': 'English',
        'emoji': '🇺🇸'
    },
    'he': {
        'name': 'עברית',
        'emoji': '🇮🇱'
    }
}

# Bot Messages - Multi-language
MESSAGES = {
    'en': {
        'welcome': "🛒 Welcome to Family Shopping List Bot!\n\nThis bot helps manage your weekly shopping list with your family.\n\nUse /help to see available commands.",
        'help': """🛒 **Family Shopping List Bot - Complete Guide**

📋 **MAIN FUNCTIONS:**

**🛒 Shopping Lists:**
• **Supermarket List** - Main family shopping list
• **Custom Lists** - Create lists for Pharmacy, Party, Trip, etc.
• **Multi-List Management** - Switch between different lists

**➕ Adding Items:**
• **Categories** - Browse predefined categories (Dairy, Fruits, Meat, etc.)
• **Search** - Find existing items across all categories
• **Custom Items** - Add items not in categories
• **Notes** - Add quantities, brands, or special instructions

**📊 Viewing & Management:**
• **View List** - See all items in current list
• **Summary** - Formatted report with categories and notes
• **My Items** - See items you personally added
• **Export** - Generate shareable list (Admin only)

**🔍 Advanced Features:**
• **Language Support** - English/Hebrew interface
• **Item Suggestions** - Suggest new items for categories
• **Broadcast Messages** - Send messages to all family members
• **Maintenance Mode** - Scheduled list resets (Supermarket only)

⚙️ **ADMIN FUNCTIONS:**
• **User Management** - Add/remove authorized users
• **List Management** - Create, edit, delete lists
• **Item Management** - Remove items from lists
• **Permanent Items** - Delete items from categories
• **Suggestions** - Approve/reject item suggestions
• **Broadcast** - Send announcements to all users

📱 **HOW TO USE:**

**For Regular Users:**
1. Select a list (Supermarket, Pharmacy, etc.)
2. Click "Add Item" → Choose category → Select item
3. Add notes if needed (quantities, brands)
4. Use "Search" to find specific items
5. View your list anytime with "View List"

**For Admins:**
• All regular functions plus admin controls
• Access admin panel for user/list management
• Approve item suggestions from other users
• Send broadcast messages to family

🔄 **COMMANDS:**
/start - Register and start using the bot
/menu - Show main menu
/help - Show this help guide

💡 **TIPS:**
• Use notes for quantities: "2 liters", "Brand X"
• Search before adding to avoid duplicates
• Check "My Items" to see your contributions
• Admins can reset lists after shopping

For support, contact your family admin.""",
        'not_registered': "❌ You need to be registered to use this bot. Please contact an admin to get access.",
        'admin_only': "❌ This command is only available to administrators.",
        'list_empty': "📝 Your shopping list is currently empty.\n\nUse /categories to browse items or /add to add custom items!",
        'list_reset': "🗑️ Shopping list has been reset by admin.",
        'item_deleted': "🗑️ Item deleted: {item} (by {admin})",
        'main_menu': "🛒 What would you like to do?",
        'categories_title': "🛒 Select a category to browse items:",
        'adding_item': "✅ Adding: {item}",
        'add_notes_prompt': "Would you like to add it directly or include notes?\n\n📝 Notes can include: quantity, brand, priority, etc.\nExample: 2 bottles, organic brand\n\nChoose an option:",
        'add_notes_input': "📝 Adding notes for: {item}\n\nPlease type your notes (quantity, brand, priority, etc.):\n\nExamples:\n• 2 bottles\n• Organic brand\n• 500ml, low-fat\n• High priority\n\nType your note:",
        'item_added': "✅ Added to shopping list:\n🛒 {item}{note}\n\nUse /list to view the complete shopping list.",
        'error_adding': "❌ Error adding item. Please try again.",
        'language_selected': "🌐 Language changed to English",
        'select_language': "🌐 Select your language:",
        'my_items_empty': "📝 You haven't added any items to the shopping list yet.\n\nUse /categories to browse items or /add to add custom items!",
        # Broadcast messages
        'broadcast_prompt': "📢 BROADCAST MESSAGE\n\nType your message to send to all authorized users:\n\n💡 Tips:\n• Keep messages clear and concise\n• Use emojis for better visibility\n• Include important updates or announcements\n\nType your message:",
        'broadcast_sent': "📢 Broadcast sent successfully!\n\n✅ Sent to {count} users\n📝 Message: {message}\n\nUse /broadcast to send another message.",
        'broadcast_error': "❌ Error sending broadcast message. Please try again.",
        'broadcast_empty': "❌ Please provide a message to broadcast.",
        'broadcast_no_users': "❌ No authorized users found to send broadcast to.",
        'broadcast_received': "📢 BROADCAST MESSAGE\n\nFrom: {sender}\n\n{message}",
        'broadcast_history': "📢 BROADCAST HISTORY\n\nRecent messages sent to all users:",
        'broadcast_history_empty': "📢 No broadcast messages sent yet.",
        # Suggestion messages
        'suggest_item_prompt': "💡 SUGGEST NEW ITEM\n\nChoose a category to suggest a new item for:",
        'suggest_item_input': "💡 Suggest New Item\n\nCategory: {category}\n\nPlease type the item name in English:\n\n💡 Tips:\n• Use clear, simple names\n• Avoid brand names\n• Examples: 'Organic honey', 'Fresh basil', 'Whole wheat bread'\n\nType the item name:",
        'suggest_item_translation': "🌐 Translation Required\n\nItem: {item_name}\nCategory: {category}\n\nPlease provide the Hebrew translation:\n\n💡 Tips:\n• Use common Hebrew terms\n• Keep it simple and clear\n• Examples: 'דבש אורגני', 'בזיליקום טרי', 'לחם מחיטה מלאה'\n\nType the Hebrew translation:",
        'suggestion_submitted': "✅ Suggestion Submitted!\n\n📝 Item: {item_name_en}\n🌐 Hebrew: {item_name_he}\n📂 Category: {category}\n\nYour suggestion has been sent to admins for approval. You'll be notified when it's reviewed!",
        'suggestion_error': "❌ Error submitting suggestion. Please try again.",
        'suggestion_empty': "❌ Please provide an item name.",
        'suggestion_translation_empty': "❌ Please provide a Hebrew translation.",
        'suggestions_pending': "⏳ PENDING SUGGESTIONS\n\nItems waiting for admin approval:",
        'suggestions_empty': "✅ No pending suggestions.",
        'suggestion_approved': "✅ Suggestion Approved!\n\n📝 Item: {item_name_en}\n🌐 Hebrew: {item_name_he}\n📂 Category: {category}\n\nThis item has been added to the category and is now available for everyone!",
        'suggestion_rejected': "❌ Suggestion Rejected\n\n📝 Item: {item_name_en}\n📂 Category: {category}\n\nThis suggestion was not approved. You can suggest other items anytime!",
        # Search messages
        'search_prompt': "🔍 SEARCH ITEMS\n\nType the name of an item you're looking for:\n\n💡 Tips:\n• Search in English or Hebrew\n• Partial matches are supported\n• Examples: 'milk', 'חלב', 'bread', 'לחם'\n\nType your search:",
        'search_results': "🔍 SEARCH RESULTS\n\nFound {count} item(s) matching '{query}':",
        'search_no_results': "🔍 NO RESULTS FOUND\n\nNo items found matching '{query}'.\n\nWould you like to:",
        'search_item_found': "📝 {item_name}\n📂 Category: {category}\n🌐 Hebrew: {hebrew_name}",
        'search_add_existing': "➕ Add to List",
        'search_suggest_new': "💡 Suggest New Item",
        'search_error': "❌ Error searching items. Please try again.",
        'search_empty': "❌ Please provide a search term.",
        # Button texts
        'btn_categories': "📋 Categories",
        'btn_add_item': "➕ Add Item",
        'btn_view_list': "📝 View List",
        'btn_summary': "📊 Summary",
        'btn_my_items': "👤 My Items",
        'btn_search': "🔍 Search",
        'btn_help': "❓ Help",
        'btn_reset_list': "🗑️ Reset List",
        'btn_manage_users': "👥 Manage Users",
        'btn_broadcast': "📢 Broadcast",
        'btn_suggest_item': "💡 Suggest Item",
        'btn_manage_suggestions': "💡 Manage Suggestions",
        'btn_new_item': "➕ New Item",
        'btn_language': "🌐 Language",
        'btn_add': "✅ Add",
        'btn_notes': "📝 Notes",
        'btn_approve': "✅ Approve",
        'btn_reject': "❌ Reject",
        'btn_back_categories': "🔙 Back to Categories",
        'btn_main_menu': "🏠 Main Menu",
        'btn_back_menu': "🔙 Back to Menu",
        # Multi-list messages
        'btn_supermarket_list': "🛒 Supermarket List",
        'supermarket_list': "Supermarket List",
        'btn_new_list': "➕ New List",
        'btn_my_lists': "📋 My Lists",
        'btn_manage_lists': "📂 Manage Lists",
        'btn_edit_list': "✏️ Edit List",
        'btn_reset_list_items': "🔄 Reset Items/List",
        'btn_delete_list': "🗑️ Delete List",
        'btn_export_list': "📤 Export List",
        'btn_select_list': "📋 Select List",
        'btn_back_to_lists': "🔙 Back to Lists",
        'btn_maintenance_mode': "⏰ Maintenance Mode",
        'btn_set_schedule': "📅 Set Schedule",
        'btn_view_schedule': "📅 View Schedule",
        'btn_disable_maintenance': "❌ Disable Maintenance",
        'btn_confirm_reset': "✅ Yes, Reset List",
        'btn_decline_reset': "❌ No, Keep List",
        'create_list_prompt': "➕ CREATE NEW LIST\n\nEnter a name for your new list:\n\n💡 Tips:\n• Use clear, descriptive names\n• Examples: 'Pharmacy', 'Party Supplies', 'Trip Essentials'\n• Keep names short and memorable\n\nType the list name:",
        'create_list_description': "📝 LIST DESCRIPTION (Optional)\n\nList: {list_name}\n\nWould you like to add a description?\n\n💡 Examples:\n• 'Weekly pharmacy items'\n• 'Items for birthday party'\n• 'Essentials for weekend trip'\n\nChoose an option:",
        'create_list_description_input': "📝 ADD DESCRIPTION\n\nList: {list_name}\n\nType a description for your list:\n\n💡 Tips:\n• Keep it brief and clear\n• Describe the purpose or occasion\n• Examples: 'Weekly pharmacy items', 'Birthday party supplies'\n\nType the description:",
        'list_created': "✅ List Created Successfully!\n\n📋 List: {list_name}\n📝 Description: {description}\n\nYour new list is ready! You can now add items to it.",
        'list_creation_error': "❌ Error creating list. Please try again.",
        'list_name_empty': "❌ Please provide a list name.",
        'list_name_exists': "❌ A list with this name already exists. Please choose a different name.",
        'my_lists_title': "📋 MY LISTS\n\nLists you've created:",
        'my_lists_empty': "📝 You haven't created any lists yet.\n\nUse 'New List' to create your first custom list!",
        'list_actions': "📋 LIST ACTIONS\n\nList: {list_name}\n\nWhat would you like to do?",
        'list_not_found': "❌ List not found or you don't have permission to access it.",
        'list_deleted': "🗑️ List '{list_name}' has been deleted.",
        'list_reset_items': "🔄 List '{list_name}' items have been reset.",
        'list_name_updated': "✏️ List name updated to '{new_name}'.",
        'list_description_updated': "📝 List description updated.",
        'list_export': "📤 LIST EXPORT\n\nList: {list_name}\nGenerated: {export_date}\n\n{items_text}\n\n📝 This is a read-only snapshot. The list remains unchanged.",
        'list_export_empty': "📤 LIST EXPORT\n\nList: {list_name}\nGenerated: {export_date}\n\n📝 This list is empty.\n\n📝 This is a read-only snapshot. The list remains unchanged.",
        'manage_lists_title': "📂 MANAGE ALL LISTS\n\nAll active lists in the system:",
        'manage_lists_empty': "📝 No lists found.",
        'list_info': "📋 {list_name}\n📝 {description}\n👤 Created by: {creator}\n📅 Created: {created_at}\n📊 Items: {item_count}",
        'list_info_no_description': "📋 {list_name}\n👤 Created by: {creator}\n📅 Created: {created_at}\n📊 Items: {item_count}",
        'edit_list_name_prompt': "✏️ EDIT LIST NAME\n\nCurrent name: {current_name}\n\nEnter new name:",
        'edit_list_description_prompt': "📝 EDIT LIST DESCRIPTION\n\nList: {list_name}\nCurrent description: {current_description}\n\nEnter new description:",
        'confirm_delete_list': "🗑️ CONFIRM DELETE LIST\n\nList: {list_name}\nItems: {item_count}\n\n⚠️ This action cannot be undone!\n\nAre you sure you want to delete this list?",
        'confirm_reset_list': "🔄 CONFIRM RESET ITEMS\n\nList: {list_name}\nItems: {item_count}\n\n⚠️ This will remove all items from the list!\n\nAre you sure you want to reset the items?",
        'select_list_prompt': "📋 SELECT A LIST\n\nChoose a list to add items to:",
        'list_selected': "✅ Selected list: {list_name}\n\nYou can now add items to this list.",
        'maintenance_mode_title': "🧩 MAINTENANCE MODE\n\n{supermarket_list} Maintenance Settings:",
        'maintenance_mode_disabled': "❌ Maintenance mode is currently disabled.",
        'maintenance_mode_enabled': "✅ Maintenance mode is enabled.\n\n⏰ Schedule: {schedule}\n📅 Next reset: {next_reset}",
        'set_maintenance_schedule': "⏰ SET MAINTENANCE SCHEDULE\n\nChoose when to remind about supermarket list reset:",
        'maintenance_schedule_set': "✅ Maintenance schedule set!\n\n⏰ Schedule: {schedule}\n📅 Next reminder: {next_reminder}",
        'maintenance_reminder': "🛒 MAINTENANCE REMINDER\n\nIt's {day} {time} - time for your weekly supermarket visit!\n\nDid you complete your shopping? Should I reset the list now?",
        'maintenance_reset_confirmed': "✅ List Reset Confirmed!\n\n🛒 The {supermarket_list} has been reset.\n📢 All users have been notified.",
        'maintenance_reset_declined': "❌ Reset Declined\n\n📝 The list will remain active.\n⏰ I'll remind you again in 24 hours.",
        'maintenance_disabled': "❌ Maintenance Mode Disabled\n\nNo more automatic reminders will be sent.",
        # Additional missing translations
        'add_new_item_to_category': "📝 Add New Item to Category\n\nCategory: {category}\n\nPlease type the name of the new item you want to add to this category:\n\n_Example: Organic honey_",
        'add_new_item_to_list': "📝 Add New Item to Current List\n\nCategory: {category}\n\nPlease type the name of the new item you want to add to your current shopping list:\n\n_Example: Organic honey_",
        'shopping_list_default': "Shopping List",
        'add_custom_item_prompt': "Please type the item name you want to add to the shopping list:\n\n_Example: Organic honey_",
        'authorize_example': "Example: `/authorize 123456789`\n\nUse `/users` to see pending users and their IDs.",
        'user_authorized_message': "You've been authorized by {admin_name} to use the Family Shopping List Bot!\n\nYou can now:\n• Browse categories with /categories\n• Add custom items with /add\n• View the shopping list with /list\n• Get summaries with /summary\n\nWelcome to the family! 🛒",
        'addadmin_example': "Example: `/addadmin 123456789`\n\n⚠️ **Warning:** This gives the user full admin privileges including:\n• User management\n• Item deletion\n• List reset\n• Broadcast messages\n\nUse with caution!",
        'user_promoted_message': "👑 **Congratulations!**\n\nYou've been promoted to **Family Admin** by {admin_name}!\n\n🔑 **Your new admin privileges:**\n• `/users` - Manage family members\n• `/authorize <user_id>` - Authorize new users\n• `/addadmin <user_id>` - Promote users to admin\n• `/reset` - Reset shopping list\n• Delete items from shopping list\n\n🛒 You now have full control over the family shopping bot!\n\nWelcome to the admin team! 👑",
        # Day names for maintenance mode
        'day_monday': "Monday",
        'day_tuesday': "Tuesday", 
        'day_wednesday': "Wednesday",
        'day_thursday': "Thursday",
        'day_friday': "Friday",
        'day_saturday': "Saturday",
        'day_sunday': "Sunday",
        # Common action messages
        'choose_action': "Choose an action:",
        'no_items_found_category': "No items found in this category.",
        'item_not_found': "Item not found.",
        'are_you_sure_continue': "Are you sure you want to continue?",
        'all_items_cleared': "All items have been cleared. You can start adding new items for your next shopping trip.",
        'users_must_start_first': "Users must send `/start` to the bot first before they can be authorized.",
        'users_must_start_first_promote': "Users must send `/start` to the bot first before they can be promoted.",
        'will_be_notified_features': "They will be notified and can start using all bot features.",
        'will_be_notified_admin': "They will be notified of their new admin status.",
        'now_have_privileges': "They now have full admin privileges.",
        'no_pending_suggestions': "No pending suggestions for this list.",
        'item_added_to_list': "The item has been added to your current shopping list.",
        'however_delete_permanent': "However, you can still delete permanent items from categories:",
        'choose_what_remove': "Choose what you want to remove:\n\n",
        'select_items_remove': "Select items to remove:\n\n",
        'select_items_delete_permanently': "Select items to delete permanently:\n\n",
        # Main menu buttons
        'btn_new_list': "➕ New List",
        'btn_admin': "⚙️ Admin",
        'btn_broadcast': "📢 Broadcast",
        # List menu buttons
        'btn_add_item': "➕ Add Item",
        'btn_search': "🔍 Search",
        'btn_view_items': "📖 View Items",
        'btn_summary': "📊 Summary",
        'btn_my_items': "👤 My Items",
        'btn_export': "📤 Export",
        'btn_manage_suggestions': "💡 Manage Suggestions",
        'btn_edit_name': "✏️ Edit Name",
        'btn_remove_items': "🗑️ Remove Items",
        'btn_reset_items': "🔄 Reset Items/List",
        'btn_maintenance_mode': "⏰ Maintenance Mode",
        'btn_delete_list': "🗑️ Delete List",
        'btn_back_to_main_menu': "🏠 Back to Main Menu",
        'btn_back_to_list': "🏠 Back to List",
        'btn_yes': "✅ Yes",
        'btn_no': "❌ No",
        'btn_edit_description': "📝 Edit Description",
        'btn_view_statistics': "📊 View Statistics",
        'btn_export_list': "📤 Export List"
    },
    'he': {
        'welcome': "🛒 ברוכים הבאים לבוט רשימת הקניות המשפחתית!\n\nהבוט עוזר לנהל את רשימת הקניות השבועית עם המשפחה.\n\nהשתמש ב-/help כדי לראות את כל הפקודות.",
        'help': """🛒 **בוט רשימת הקניות המשפחתית - מדריך מלא**

📋 **פונקציות עיקריות:**

**🛒 רשימות קניות:**
• **רשימת סופר** - רשימת הקניות המשפחתית הראשית
• **רשימות מותאמות** - צור רשימות לבית מרקחת, מסיבה, טיול וכו'
• **ניהול רשימות מרובות** - החלף בין רשימות שונות

**➕ הוספת פריטים:**
• **קטגוריות** - עיין בקטגוריות מוגדרות מראש (חלב, פירות, בשר וכו')
• **חיפוש** - מצא פריטים קיימים בכל הקטגוריות
• **פריטים מותאמים** - הוסף פריטים שלא נמצאים בקטגוריות
• **הערות** - הוסף כמויות, מותגים או הוראות מיוחדות

**📊 צפייה וניהול:**
• **צפה ברשימה** - ראה את כל הפריטים ברשימה הנוכחית
• **סיכום** - דוח מעוצב עם קטגוריות והערות
• **הפריטים שלי** - ראה פריטים שהוספת אישית
• **ייצוא** - צור רשימה לשיתוף (מנהלים בלבד)

**🔍 תכונות מתקדמות:**
• **תמיכה בשפות** - ממשק עברית/אנגלית
• **הצעות פריטים** - הצע פריטים חדשים לקטגוריות
• **הודעות שידור** - שלח הודעות לכל בני המשפחה
• **מצב תחזוקה** - איפוס רשימות מתוזמן (סופר בלבד)

⚙️ **פונקציות מנהל:**
• **ניהול משתמשים** - הוסף/הסר משתמשים מורשים
• **ניהול רשימות** - צור, ערוך, מחק רשימות
• **ניהול פריטים** - הסר פריטים מרשימות
• **פריטים קבועים** - מחק פריטים מקטגוריות
• **הצעות** - אשר/דחה הצעות פריטים
• **שידור** - שלח הודעות לכל המשתמשים

📱 **איך להשתמש:**

**למשתמשים רגילים:**
1. בחר רשימה (סופר, בית מרקחת וכו')
2. לחץ "הוסף פריט" → בחר קטגוריה → בחר פריט
3. הוסף הערות אם נדרש (כמויות, מותגים)
4. השתמש ב"חיפוש" כדי למצוא פריטים ספציפיים
5. צפה ברשימה שלך בכל עת עם "צפה ברשימה"

**למנהלים:**
• כל הפונקציות הרגילות בתוספת בקרות מנהל
• גישה לפאנל מנהל לניהול משתמשים/רשימות
• אשר הצעות פריטים ממשתמשים אחרים
• שלח הודעות שידור למשפחה

🔄 **פקודות:**
/start - הרשמה והתחלת השימוש בבוט
/menu - הצגת תפריט ראשי
/help - הצגת מדריך עזרה זה

💡 **טיפים:**
• השתמש בהערות לכמויות: "2 ליטר", "מותג X"
• חפש לפני הוספה כדי למנוע כפילויות
• בדוק "הפריטים שלי" כדי לראות את התרומות שלך
• מנהלים יכולים לאפס רשימות אחרי קניות

לתמיכה, פנה למנהל המשפחה שלך.""",
        'not_registered': "❌ עליך להיות רשום כדי להשתמש בבוט זה. אנא פנה למנהל לקבלת גישה.",
        'admin_only': "❌ פקודה זו זמינה רק למנהלים.",
        'list_empty': "📝 רשימת הקניות שלך ריקה כרגע.\n\nהשתמש ב-/categories לעיון בפריטים או ב-/add להוספת פריטים מותאמים!",
        'list_reset': "🗑️ רשימת הקניות אופסה על ידי מנהל.",
        'item_deleted': "🗑️ פריט נמחק: {item} (על ידי {admin})",
        'main_menu': "🛒 מה תרצה לעשות?",
        'categories_title': "🛒 בחר קטגוריה לעיון בפריטים:",
        'adding_item': "✅ מוסיף: {item}",
        'add_notes_prompt': "האם תרצה להוסיף ישירות או לכלול הערות?\n\n📝 הערות יכולות לכלול: כמות, מותג, עדיפות, וכו'\nדוגמה: 2 בקבוקים, מותג אורגני\n\nבחר אפשרות:",
        'add_notes_input': "📝 הוספת הערות עבור: {item}\n\nאנא הקלד את ההערות שלך (כמות, מותג, עדיפות, וכו'):\n\nדוגמאות:\n• 2 בקבוקים\n• מותג אורגני\n• 500 מ\"ל, דל שומן\n• עדיפות גבוהה\n\nהקלד את ההערה:",
        'item_added': "✅ נוסף לרשימת הקניות:\n🛒 {item}{note}\n\nהשתמש ב-/list לצפייה ברשימת הקניות המלאה.",
        'error_adding': "❌ שגיאה בהוספת הפריט. אנא נסה שוב.",
        'language_selected': "🌐 השפה שונתה לעברית",
        'select_language': "🌐 בחר את השפה שלך:",
        'my_items_empty': "📝 עדיין לא הוספת פריטים לרשימת הקניות.\n\nהשתמש ב-/categories לעיון בפריטים או ב-/add להוספת פריטים מותאמים!",
        # Broadcast messages in Hebrew
        'broadcast_prompt': "📢 הודעת שידור\n\nהקלד את ההודעה שלך לשליחה לכל המשתמשים המורשים:\n\n💡 טיפים:\n• שמור על הודעות ברורות ותמציתיות\n• השתמש באמוג'ים לנראות טובה יותר\n• כלול עדכונים או הודעות חשובות\n\nהקלד את ההודעה שלך:",
        'broadcast_sent': "📢 השידור נשלח בהצלחה!\n\n✅ נשלח ל-{count} משתמשים\n📝 הודעה: {message}\n\nהשתמש ב-/broadcast לשליחת הודעה נוספת.",
        'broadcast_error': "❌ שגיאה בשליחת הודעת השידור. אנא נסה שוב.",
        'broadcast_empty': "❌ אנא ספק הודעה לשידור.",
        'broadcast_no_users': "❌ לא נמצאו משתמשים מורשים לשליחת השידור אליהם.",
        'broadcast_received': "📢 הודעת שידור\n\nמאת: {sender}\n\n{message}",
        'broadcast_history': "📢 היסטוריית שידורים\n\nהודעות אחרונות שנשלחו לכל המשתמשים:",
        'broadcast_history_empty': "📢 עדיין לא נשלחו הודעות שידור.",
        # Suggestion messages in Hebrew
        'suggest_item_prompt': "💡 הצע פריט חדש\n\nבחר קטגוריה להצעת פריט חדש:",
        'suggest_item_input': "💡 הצע פריט חדש\n\nקטגוריה: {category}\n\nאנא הקלד את שם הפריט באנגלית:\n\n💡 טיפים:\n• השתמש בשמות ברורים ופשוטים\n• הימנע משמות מותגים\n• דוגמאות: 'Organic honey', 'Fresh basil', 'Whole wheat bread'\n\nהקלד את שם הפריט:",
        'suggest_item_translation': "🌐 נדרש תרגום\n\nפריט: {item_name}\nקטגוריה: {category}\n\nאנא ספק את התרגום לעברית:\n\n💡 טיפים:\n• השתמש במונחים עבריים נפוצים\n• שמור על פשטות ובהירות\n• דוגמאות: 'דבש אורגני', 'בזיליקום טרי', 'לחם מחיטה מלאה'\n\nהקלד את התרגום לעברית:",
        'suggestion_submitted': "✅ ההצעה נשלחה!\n\n📝 פריט: {item_name_en}\n🌐 עברית: {item_name_he}\n📂 קטגוריה: {category}\n\nההצעה שלך נשלחה למנהלים לאישור. תתעדכן כשתקבל החלטה!",
        'suggestion_error': "❌ שגיאה בשליחת ההצעה. אנא נסה שוב.",
        'suggestion_empty': "❌ אנא ספק שם פריט.",
        'suggestion_translation_empty': "❌ אנא ספק תרגום לעברית.",
        'suggestions_pending': "⏳ הצעות ממתינות\n\nפריטים הממתינים לאישור מנהל:",
        'suggestions_empty': "✅ אין הצעות ממתינות.",
        'suggestion_approved': "✅ ההצעה אושרה!\n\n📝 פריט: {item_name_en}\n🌐 עברית: {item_name_he}\n📂 קטגוריה: {category}\n\nהפריט הזה נוסף לקטגוריה וזמין כעת לכולם!",
        'suggestion_rejected': "❌ ההצעה נדחתה\n\n📝 פריט: {item_name_en}\n📂 קטגוריה: {category}\n\nההצעה הזו לא אושרה. אתה יכול להציע פריטים אחרים בכל עת!",
        # Search messages in Hebrew
        'search_prompt': "🔍 חיפוש פריטים\n\nהקלד את שם הפריט שאתה מחפש:\n\n💡 טיפים:\n• חפש באנגלית או עברית\n• תמיכה בחיפוש חלקי\n• דוגמאות: 'milk', 'חלב', 'bread', 'לחם'\n\nהקלד את החיפוש שלך:",
        'search_results': "🔍 תוצאות חיפוש\n\nנמצאו {count} פריט(ים) התואמים ל-'{query}':",
        'search_no_results': "🔍 לא נמצאו תוצאות\n\nלא נמצאו פריטים התואמים ל-'{query}'.\n\nהאם תרצה:",
        'search_item_found': "📝 {item_name}\n📂 קטגוריה: {category}\n🌐 עברית: {hebrew_name}",
        'search_add_existing': "➕ הוסף לרשימה",
        'search_suggest_new': "💡 הצע פריט חדש",
        'search_error': "❌ שגיאה בחיפוש פריטים. אנא נסה שוב.",
        'search_empty': "❌ אנא ספק מונח חיפוש.",
        # Button texts in Hebrew
        'btn_categories': "📋 קטגוריות",
        'btn_add_item': "➕ הוסף פריט", 
        'btn_view_list': "📝 צפה ברשימה",
        'btn_summary': "📊 סיכום",
        'btn_my_items': "👤 הפריטים שלי",
        'btn_search': "🔍 חיפוש",
        'btn_help': "❓ עזרה",
        'btn_reset_list': "🗑️ אפס רשימה",
        'btn_manage_users': "👥 נהל משתמשים",
        'btn_broadcast': "📢 שידור",
        'btn_suggest_item': "💡 הצע פריט",
        'btn_manage_suggestions': "💡 נהל הצעות",
        'btn_new_item': "➕ פריט חדש",
        'btn_language': "🌐 שפה",
        'btn_add': "✅ הוסף",
        'btn_notes': "📝 הערות",
        'btn_approve': "✅ אשר",
        'btn_reject': "❌ דחה",
        'btn_back_categories': "🔙 חזרה לקטגוריות",
        'btn_main_menu': "🏠 תפריט ראשי",
        'btn_back_menu': "🔙 חזרה לתפריט",
        # Multi-list messages in Hebrew
        'btn_supermarket_list': "🛒 רשימת סופר",
        'supermarket_list': "רשימת סופר",
        'btn_new_list': "➕ רשימה חדשה",
        'btn_my_lists': "📋 הרשימות שלי",
        'btn_manage_lists': "📂 נהל רשימות",
        'btn_edit_list': "✏️ ערוך רשימה",
        'btn_reset_list_items': "🔄 אפס פריטים/רשימה",
        'btn_delete_list': "🗑️ מחק רשימה",
        'btn_export_list': "📤 ייצא רשימה",
        'btn_select_list': "📋 בחר רשימה",
        'btn_back_to_lists': "🔙 חזרה לרשימות",
        'create_list_prompt': "➕ צור רשימה חדשה\n\nהכנס שם לרשימה החדשה שלך:\n\n💡 טיפים:\n• השתמש בשמות ברורים ותיאוריים\n• דוגמאות: 'בית מרקחת', 'אספקת מסיבה', 'ציוד לטיול'\n• שמור על שמות קצרים וזכירים\n\nהקלד את שם הרשימה:",
        'create_list_description': "📝 תיאור רשימה (אופציונלי)\n\nרשימה: {list_name}\n\nהאם תרצה להוסיף תיאור?\n\n💡 דוגמאות:\n• 'פריטי בית מרקחת שבועיים'\n• 'פריטים למסיבת יום הולדת'\n• 'ציוד חיוני לטיול סוף שבוע'\n\nבחר אפשרות:",
        'create_list_description_input': "📝 הוסף תיאור\n\nרשימה: {list_name}\n\nהקלד תיאור לרשימה שלך:\n\n💡 טיפים:\n• שמור על זה קצר וברור\n• תאר את המטרה או האירוע\n• דוגמאות: 'פריטי בית מרקחת שבועיים', 'אספקת מסיבת יום הולדת'\n\nהקלד את התיאור:",
        'list_created': "✅ רשימה נוצרה בהצלחה!\n\n📋 רשימה: {list_name}\n📝 תיאור: {description}\n\nהרשימה החדשה שלך מוכנה! אתה יכול כעת להוסיף אליה פריטים.",
        'list_creation_error': "❌ שגיאה ביצירת הרשימה. אנא נסה שוב.",
        'list_name_empty': "❌ אנא ספק שם רשימה.",
        'list_name_exists': "❌ רשימה עם השם הזה כבר קיימת. אנא בחר שם אחר.",
        'my_lists_title': "📋 הרשימות שלי\n\nרשימות שיצרת:",
        'my_lists_empty': "📝 עדיין לא יצרת רשימות.\n\nהשתמש ב-'רשימה חדשה' כדי ליצור את הרשימה המותאמת הראשונה שלך!",
        'list_actions': "📋 פעולות רשימה\n\nרשימה: {list_name}\n\nמה תרצה לעשות?",
        'list_not_found': "❌ רשימה לא נמצאה או שאין לך הרשאה לגשת אליה.",
        'list_deleted': "🗑️ הרשימה '{list_name}' נמחקה.",
        'list_reset_items': "🔄 פריטי הרשימה '{list_name}' אופסו.",
        'list_name_updated': "✏️ שם הרשימה עודכן ל-'{new_name}'.",
        'list_description_updated': "📝 תיאור הרשימה עודכן.",
        'list_export': "📤 ייצוא רשימה\n\nרשימה: {list_name}\nנוצר: {export_date}\n\n{items_text}\n\n📝 זהו צילום מסך לקריאה בלבד. הרשימה נותרת ללא שינוי.",
        'list_export_empty': "📤 ייצוא רשימה\n\nרשימה: {list_name}\nנוצר: {export_date}\n\n📝 הרשימה הזו ריקה.\n\n📝 זהו צילום מסך לקריאה בלבד. הרשימה נותרת ללא שינוי.",
        'manage_lists_title': "📂 נהל את כל הרשימות\n\nכל הרשימות הפעילות במערכת:",
        'manage_lists_empty': "📝 לא נמצאו רשימות.",
        'list_info': "📋 {list_name}\n📝 {description}\n👤 נוצר על ידי: {creator}\n📅 נוצר: {created_at}\n📊 פריטים: {item_count}",
        'list_info_no_description': "📋 {list_name}\n👤 נוצר על ידי: {creator}\n📅 נוצר: {created_at}\n📊 פריטים: {item_count}",
        'edit_list_name_prompt': "✏️ ערוך שם רשימה\n\nשם נוכחי: {current_name}\n\nהכנס שם חדש:",
        'edit_list_description_prompt': "📝 ערוך תיאור רשימה\n\nרשימה: {list_name}\nתיאור נוכחי: {current_description}\n\nהכנס תיאור חדש:",
        'confirm_delete_list': "🗑️ אשר מחיקת רשימה\n\nרשימה: {list_name}\nפריטים: {item_count}\n\n⚠️ פעולה זו לא ניתנת לביטול!\n\nהאם אתה בטוח שברצונך למחוק את הרשימה הזו?",
        'confirm_reset_list': "🔄 אשר איפוס פריטים\n\nרשימה: {list_name}\nפריטים: {item_count}\n\n⚠️ זה יסיר את כל הפריטים מהרשימה!\n\nהאם אתה בטוח שברצונך לאפס את הפריטים?",
        'select_list_prompt': "📋 בחר רשימה\n\nבחר רשימה להוספת פריטים:",
        'list_selected': "✅ נבחרה רשימה: {list_name}\n\nאתה יכול כעת להוסיף פריטים לרשימה הזו.",
        'maintenance_mode_title': "🧩 מצב תחזוקה\n\nהגדרות תחזוקה של {supermarket_list}:",
        'maintenance_mode_disabled': "❌ מצב התחזוקה כרגע מושבת.",
        'maintenance_mode_enabled': "✅ מצב התחזוקה מופעל.\n\n⏰ לוח זמנים: {schedule}\n📅 איפוס הבא: {next_reset}",
        'set_maintenance_schedule': "⏰ הגדר לוח זמנים לתחזוקה\n\nבחר מתי להזכיר על איפוס רשימת הסופר:",
        'maintenance_schedule_set': "✅ לוח הזמנים לתחזוקה הוגדר!\n\n⏰ לוח זמנים: {schedule}\n📅 תזכורת הבאה: {next_reminder}",
        'maintenance_reminder': "🛒 תזכורת תחזוקה\n\nזה {day} {time} - זמן לביקור השבועי בסופר!\n\nהאם סיימת את הקניות? האם לאפס את הרשימה עכשיו?",
        'maintenance_reset_confirmed': "✅ איפוס הרשימה אושר!\n\n🛒 {supermarket_list} אופסה.\n📢 כל המשתמשים קיבלו הודעה.",
        'maintenance_reset_declined': "❌ איפוס נדחה\n\n📝 הרשימה תישאר פעילה.\n⏰ אזכיר לך שוב בעוד 24 שעות.",
        'maintenance_disabled': "❌ מצב התחזוקה הושבת\n\nלא יישלחו עוד תזכורות אוטומטיות.",
        # Additional missing translations
        'add_new_item_to_category': "📝 הוסף פריט חדש לקטגוריה\n\nקטגוריה: {category}\n\nאנא הקלד את שם הפריט החדש שברצונך להוסיף לקטגוריה הזו:\n\nדוגמה: דבש אורגני",
        'add_new_item_to_list': "📝 הוסף פריט חדש לרשימה הנוכחית\n\nקטגוריה: {category}\n\nאנא הקלד את שם הפריט החדש שברצונך להוסיף לרשימת הקניות הנוכחית שלך:\n\nדוגמה: דבש אורגני",
        'shopping_list_default': "רשימת קניות",
        'add_custom_item_prompt': "אנא הקלד את שם הפריט שברצונך להוסיף לרשימת הקניות:\n\nדוגמה: דבש אורגני",
        'authorize_example': "דוגמה: `/authorize 123456789`\n\nהשתמש ב-`/users` כדי לראות משתמשים ממתינים ומזהים שלהם.",
        'user_authorized_message': "אושרת על ידי {admin_name} להשתמש בבוט רשימת הקניות המשפחתית!\n\nאתה יכול כעת:\n• לעיין בקטגוריות עם /categories\n• להוסיף פריטים מותאמים עם /add\n• לצפות ברשימת הקניות עם /list\n• לקבל סיכומים עם /summary\n\nברוכים הבאים למשפחה! 🛒",
        'addadmin_example': "דוגמה: `/addadmin 123456789`\n\n⚠️ **אזהרה:** זה נותן למשתמש הרשאות מנהל מלאות כולל:\n• ניהול משתמשים\n• מחיקת פריטים\n• איפוס רשימות\n• הודעות שידור\n\nהשתמש בזהירות!",
        'user_promoted_message': "👑 **מזל טוב!**\n\nקודמת ל-**מנהל משפחה** על ידי {admin_name}!\n\n🔑 **הרשאות המנהל החדשות שלך:**\n• `/users` - נהל בני משפחה\n• `/authorize <user_id>` - אשר משתמשים חדשים\n• `/addadmin <user_id>` - קדם משתמשים למנהל\n• `/reset` - אפס רשימת קניות\n• מחק פריטים מרשימת הקניות\n\n🛒 יש לך כעת שליטה מלאה על בוט הקניות המשפחתי!\n\nברוכים הבאים לצוות המנהלים! 👑",
        # Day names for maintenance mode
        'day_monday': "יום שני",
        'day_tuesday': "יום שלישי", 
        'day_wednesday': "יום רביעי",
        'day_thursday': "יום חמישי",
        'day_friday': "יום שישי",
        'day_saturday': "יום שבת",
        'day_sunday': "יום ראשון",
        # Common action messages
        'choose_action': "בחר פעולה:",
        'no_items_found_category': "לא נמצאו פריטים בקטגוריה זו.",
        'item_not_found': "פריט לא נמצא.",
        'are_you_sure_continue': "האם אתה בטוח שברצונך להמשיך?",
        'all_items_cleared': "כל הפריטים נוקו. אתה יכול להתחיל להוסיף פריטים חדשים לטיול הקניות הבא שלך.",
        'users_must_start_first': "משתמשים חייבים לשלוח `/start` לבוט קודם לפני שניתן יהיה לאשר אותם.",
        'users_must_start_first_promote': "משתמשים חייבים לשלוח `/start` לבוט קודם לפני שניתן יהיה לקדם אותם.",
        'will_be_notified_features': "הם יקבלו הודעה ויכולים להתחיל להשתמש בכל תכונות הבוט.",
        'will_be_notified_admin': "הם יקבלו הודעה על מעמד המנהל החדש שלהם.",
        'now_have_privileges': "יש להם כעת הרשאות מנהל מלאות.",
        'no_pending_suggestions': "אין הצעות ממתינות לרשימה זו.",
        'item_added_to_list': "הפריט נוסף לרשימת הקניות הנוכחית שלך.",
        'however_delete_permanent': "עם זאת, אתה עדיין יכול למחוק פריטים קבועים מקטגוריות:",
        'choose_what_remove': "בחר מה להסיר:\n\n",
        'select_items_remove': "בחר פריטים להסרה:\n\n",
        'select_items_delete_permanently': "בחר פריטים למחיקה קבועה:\n\n",
        # Main menu buttons
        'btn_new_list': "➕ רשימה חדשה",
        'btn_admin': "⚙️ מנהל",
        'btn_broadcast': "📢 שידור",
        # List menu buttons
        'btn_add_item': "➕ הוסף פריט",
        'btn_search': "🔍 חיפוש",
        'btn_view_items': "📖 צפה בפריטים",
        'btn_summary': "📊 סיכום",
        'btn_my_items': "👤 הפריטים שלי",
        'btn_export': "📤 ייצא",
        'btn_manage_suggestions': "💡 נהל הצעות",
        'btn_edit_name': "✏️ ערוך שם",
        'btn_remove_items': "🗑️ הסר פריטים",
        'btn_reset_items': "🔄 אפס פריטים/רשימה",
        'btn_maintenance_mode': "⏰ מצב תחזוקה",
        'btn_delete_list': "🗑️ מחק רשימה",
        'btn_back_to_main_menu': "🏠 חזרה לתפריט הראשי",
        'btn_back_to_list': "🏠 חזרה לרשימה",
        'btn_yes': "✅ כן",
        'btn_no': "❌ לא",
        'btn_edit_description': "📝 ערוך תיאור",
        'btn_view_statistics': "📊 צפה בסטטיסטיקות",
        'btn_export_list': "📤 ייצא רשימה"
    }
}
