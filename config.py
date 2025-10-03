import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('bot_config.env')

# Bot Configuration - Support for Developer Mode
DEVELOPER_MODE = os.getenv('DEVELOPER_MODE', 'false').lower() == 'true'

if DEVELOPER_MODE:
    # Use developer bot token
    BOT_TOKEN = os.getenv('DEV_BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("DEV_BOT_TOKEN environment variable is required for developer mode")
    print("Running in DEVELOPER MODE")
else:
    # Use production bot token
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    print("🚀 Running in PRODUCTION MODE")

# Admin Configuration
ADMIN_IDS = []
admin_ids_str = os.getenv('ADMIN_IDS', '')
if admin_ids_str and admin_ids_str != 'your_admin_user_id_here':
    try:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
    except ValueError:
        print(f"⚠️ Warning: Invalid ADMIN_IDS format: {admin_ids_str}")
        print("💡 Please set ADMIN_IDS to your Telegram user ID (numbers only)")
        ADMIN_IDS = []

# Database Configuration - Separate database for developer mode
if DEVELOPER_MODE:
    DATABASE_PATH = os.getenv('DEV_DATABASE_PATH', 'shopping_bot_dev.db')
    print(f"Using developer database: {DATABASE_PATH}")
else:
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'shopping_bot.db')
    print(f"Using production database: {DATABASE_PATH}")

# Categories Configuration - Multi-language
CATEGORIES = {
    'dairy': {
        'emoji': '🥛',
        'name': {'en': 'Dairy', 'he': 'חלבי'},
        'items': {
            'en': ['Milk', 'Cheese', 'Yogurt', 'Butter', 'Cream', 'Eggs', 'Cottage cheese', 'Sour cream', 'Cream cheese', 'Buttermilk'],
            'he': ['חלב', 'גבינה', 'יוגורט', 'חמאה', 'שמנת', 'ביצים', 'גבינת קוטג\'', 'שמנת חמוצה', 'גבינת שמנת', 'חלב חמאה']
        }
    },
    'fruits_vegetables': {
        'emoji': '🥦🍎',
        'name': {'en': 'Fruits & Vegetables', 'he': 'פירות וירקות'},
        'items': {
            'en': ['Apples', 'Bananas', 'Carrots', 'Broccoli', 'Tomatoes', 'Onions', 'Potatoes', 'Lettuce', 'Avocado', 'Cucumber', 'Bell peppers', 'Mushrooms', 'Spinach', 'Strawberries', 'Grapes', 'Oranges', 'Lemons'],
            'he': ['תפוחים', 'בננות', 'גזר', 'ברוקולי', 'עגבניות', 'בצל', 'תפוחי אדמה', 'חסה', 'אבוקדו', 'מלפפון', 'פלפלים', 'פטריות', 'תרד', 'תותים', 'ענבים', 'תפוזים', 'לימונים']
        }
    },
    'meat_fish': {
        'emoji': '🍗🐟',
        'name': {'en': 'Meat & Fish', 'he': 'בשר ודגים'},
        'items': {
            'en': ['Chicken', 'Beef', 'Pork', 'Salmon', 'Tuna', 'Ground meat', 'Turkey', 'Lamb', 'Shrimp', 'Cod', 'Sardines', 'Bacon', 'Sausages'],
            'he': ['עוף', 'בקר', 'חזיר', 'סלמון', 'טונה', 'בשר טחון', 'הודו', 'כבש', 'חסילונים', 'בקלה', 'סרדינים', 'בייקון', 'נקניקיות']
        }
    },
    'staples': {
        'emoji': '🍞🍝',
        'name': {'en': 'Staples', 'he': 'מוצרי יסוד'},
        'items': {
            'en': ['Bread', 'Pasta', 'Rice', 'Flour', 'Cereal', 'Oats', 'Quinoa', 'Couscous', 'Barley', 'Tortillas', 'Crackers', 'Granola'],
            'he': ['לחם', 'פסטה', 'אורז', 'קמח', 'דגנים', 'שיבולת שועל', 'קינואה', 'קוסקוס', 'שעורה', 'טורטיות', 'קרקרים', 'גרנולה']
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
            'en': ['Coffee', 'Tea', 'Juice', 'Soda', 'Water', 'Beer', 'Wine', 'Energy drinks', 'Sports drinks', 'Sparkling water', 'Kombucha', 'Hot chocolate'],
            'he': ['קפה', 'תה', 'מיץ', 'משקה מוגז', 'מים', 'בירה', 'יין', 'משקאות אנרגיה', 'משקאות ספורט', 'מים מוגזים', 'קומבוצ\'ה', 'שוקולד חם']
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
            'en': ['Salt', 'Pepper', 'Ketchup', 'Mustard', 'Olive oil', 'Vinegar', 'Garlic', 'Herbs', 'Soy sauce', 'Hot sauce', 'Worcestershire sauce', 'Sesame oil', 'Cumin', 'Paprika', 'Cinnamon'],
            'he': ['מלח', 'פלפל', 'קטשופ', 'חרדל', 'שמן זית', 'חומץ', 'שום', 'עשבי תיבול', 'רוטב סויה', 'רוטב חריף', 'רוטב ווסטרשייר', 'שמן שומשום', 'כמון', 'פפריקה', 'קינמון']
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
            'en': ['Fresh bread', 'Croissants', 'Muffins', 'Bagels', 'Donuts', 'Cake', 'Cookies', 'Pie', 'Pastries', 'Rolls'],
            'he': ['לחם טרי', 'קרואסון', 'מאפינס', 'בייגלים', 'סופגניות', 'עוגה', 'עוגיות', 'פאי', 'מאפים', 'לחמניות']
        }
    },
    'prepared_foods': {
        'emoji': '🍕',
        'name': {'en': 'Prepared Foods', 'he': 'מזון מוכן'},
        'items': {
            'en': ['Ready meals', 'Sandwiches', 'Salads', 'Sushi', 'Pizza', 'Pasta dishes', 'Soup', 'Deli items'],
            'he': ['ארוחות מוכנות', 'כריכים', 'סלטים', 'סושי', 'פיצה', 'מנות פסטה', 'מרק', 'מוצרי דלי']
        }
    },
    'deli': {
        'emoji': '🧀',
        'name': {'en': 'Deli', 'he': 'דלי'},
        'items': {
            'en': ['Cold cuts', 'Sliced cheese', 'Prepared salads', 'Olives', 'Hummus', 'Tzatziki', 'Pickles', 'Antipasti'],
            'he': ['נקניקים', 'גבינה פרוסה', 'סלטים מוכנים', 'זיתים', 'חומוס', 'צזיקי', 'חמוצים', 'אנטיפסטי']
        }
    },
    'international': {
        'emoji': '🌮',
        'name': {'en': 'International', 'he': 'בינלאומי'},
        'items': {
            'en': ['Asian foods', 'Mexican foods', 'Indian spices', 'Mediterranean', 'Middle Eastern', 'Italian specialties', 'Thai ingredients', 'Chinese sauces'],
            'he': ['מזון אסייתי', 'מזון מקסיקני', 'תבלינים הודיים', 'ים תיכוני', 'מזרח תיכוני', 'מעדנים איטלקיים', 'מרכיבים תאילנדיים', 'רטבים סיניים']
        }
    },
    'home_garden': {
        'emoji': '🏠',
        'name': {'en': 'Home & Garden', 'he': 'בית וגינה'},
        'items': {
            'en': ['Tools', 'Plants', 'Seeds', 'Fertilizer', 'Pots', 'Garden supplies', 'Light bulbs', 'Batteries'],
            'he': ['כלים', 'צמחים', 'זרעים', 'דשן', 'עציצים', 'אספקת גינה', 'נורות', 'סוללות']
        }
    },
    'personal_care': {
        'emoji': '👕',
        'name': {'en': 'Personal Care', 'he': 'טיפוח אישי'},
        'items': {
            'en': ['Cosmetics', 'Toiletries', 'Personal hygiene', 'Skincare', 'Hair care', 'Oral care', 'Deodorant', 'Razors'],
            'he': ['קוסמטיקה', 'מוצרי טואלט', 'היגיינה אישית', 'טיפוח עור', 'טיפוח שיער', 'טיפוח פה', 'דאודורנט', 'סכיני גילוח']
        }
    },
    'electronics': {
        'emoji': '📱',
        'name': {'en': 'Electronics', 'he': 'אלקטרוניקה'},
        'items': {
            'en': ['Batteries', 'Cables', 'Chargers', 'Small electronics', 'Phone accessories', 'USB drives', 'Memory cards', 'Headphones'],
            'he': ['סוללות', 'כבלים', 'מטענים', 'אלקטרוניקה קטנה', 'אביזרי טלפון', 'דיסק און קי', 'כרטיסי זיכרון', 'אוזניות']
        }
    },
    'gifts_cards': {
        'emoji': '🎁',
        'name': {'en': 'Gifts & Cards', 'he': 'מתנות וכרטיסים'},
        'items': {
            'en': ['Gift cards', 'Wrapping paper', 'Greeting cards', 'Balloons', 'Party supplies', 'Candles', 'Decorative items', 'Toys'],
            'he': ['כרטיסי מתנה', 'נייר עטיפה', 'כרטיסי ברכה', 'בלונים', 'אספקת מסיבות', 'נרות', 'פריטי קישוט', 'צעצועים']
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
• **Manage My Lists** - Edit, delete, and manage your own lists
• **Export** - Generate shareable list (Admin only)

**🔍 Advanced Features:**
• **Language Support** - English/Hebrew interface
• **Item Suggestions** - Suggest new items for categories
• **Category Suggestions** - Suggest new categories
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
6. Manage your own lists with "Manage My Lists"
7. Use "Suggestions" to suggest new items or categories

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
               'voice_search_prompt': "🎤 VOICE SEARCH\n\nPress and hold the microphone button to speak your search query.\n\n💡 Tips:\n• Speak clearly in English or Hebrew\n• Examples: 'milk', 'חלב', 'bread', 'לחם'\n• Release the microphone when done - no need to press stop!\n\nTap 'Start Voice Recording' then hold the microphone:",
        'btn_start_voice_recording': "🎤 Start Voice Recording",
        'btn_switch_to_text_search': "✏️ Switch to Text Search",
        'btn_stop_recording': "⏹️ Stop Recording",
        'btn_text_search': "✏️ Text Search",
        'btn_voice_search': "🎤 Voice Search",
        'btn_back_to_list': "🏠 Back to List",
        'btn_back_to_list_actions': "🏠 Back to List Actions",
        'btn_add_new_item': "➕ ADD NEW ITEM",
        'btn_add_to_the_list': "✅ ADD TO THE LIST",
        'shopping_summary_report': "📊 SHOPPING SUMMARY REPORT",
        'voice_search_listening': "🎤 Listening... Speak now!\n\nRelease the microphone when done.",
        'voice_search_processing': "🔄 Processing your voice...",
        'voice_search_error': "❌ Voice recognition failed. Please try again or use text search.",
        'voice_search_timeout': "⏰ Voice recording timeout. Please try again.",
        'item_restoration_detected': "🔄 **ITEM RESTORATION DETECTED**\n\n**'{item_name}'** was previously deleted from the **{category_name}** category.\n\nWhat would you like to do?",
        'btn_restore_original_item': "🔄 Restore Original Item",
        'btn_add_as_new_item': "➕ Add as New Item",
        'btn_cancel_restoration': "❌ Cancel",
        'item_restored_success': "✅ **Item Restored!**\n\n**'{item_name}'** has been restored to the **{category_name}** category and is now visible again.",
        'item_added_as_new_success': "✅ **New Item Added!**\n\n**'{item_name}'** has been added as a new item to the **{category_name}** category.",
        'add_new_item_admin_title': "➕ ADD NEW ITEM (ADMIN)",
        'add_new_item_prompt': "Please type the item name in English:",
        'add_new_item_tips': "💡 Tips:\n• Use clear, simple names\n• Avoid brand names\n• Examples: 'Organic honey', 'Fresh basil', 'Whole wheat bread'",
        'type_item_name': "Type the item name:",
        'translation_required_admin': "🌐 Translation Required (Admin)",
        'provide_hebrew_translation': "Please provide the Hebrew translation:",
        'hebrew_translation_tips': "💡 Tips:\n• Use common Hebrew terms\n• Keep it simple and clear\n• Examples: 'דבש אורגני', 'בזיליקום טרי', 'לחם מחיטה מלאה'",
        'type_hebrew_translation': "Type the Hebrew translation:",
        'please_provide_hebrew': "❌ Please provide a Hebrew translation.",
        'error_processing_new_item': "❌ Error processing new item. Please try again.",
        'error_adding_new_item_duplicate': "❌ Error adding new item - Duplicate!\n\nThe item **{item_name}** already exists in the **{category_name}** category.",
        'error_adding_new_item': "❌ Error adding new item. Please try again.",
        'failed_to_restore_item': "❌ Failed to restore item. Please try again.",
        'error_category_not_found': "❌ Error: Category not found.",
        'failed_to_add_item': "❌ Failed to add item. Please try again.",
        'error_search_query_not_found': "❌ Error: Search query not found. Please try searching again.",
        'error_opening_voice_search': "❌ Error opening voice search. Please try again.",
        'error_changing_language': "❌ Error changing language.",
        'error_approving_suggestion': "❌ Error approving suggestion.",
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
        'btn_search': "🔍🎤 Search",
        'btn_help': "❓ Help",
        'category_not_found': "❌ Category not found!",
        'suggestion_review': "💡 SUGGESTION REVIEW",
        'list_fallback': "List {list_id}",
        'user_fallback': "User {user_id}",
        'admin_fallback': "Admin",
        'someone_fallback': "Someone",
        'none_fallback': "None",
        'all_lists': "all lists",
        'remove_item_failed': "Failed to remove item. Please try again.",
        'items_count': "Items: {count}",
        'list_type': "Type: {type}",
        'total_items': "Total items: {count}",
        'supermarket_list_en': "Supermarket List",
        'items_count_inline': "({count} items)",
        'usage_removeuser': "❌ **Usage:** `/removeuser <user_id>`\n\n**Example:** `/removeuser 123456789`\n\nUse `/users` to see all users and their IDs.",
        'user_not_authorized': "❌ **User Not Authorized**\n\n👤 {user_name} is not currently authorized.\n\nUse `/authorize {user_id}` to authorize them first.",
        'cannot_remove_admin': "❌ **Cannot Remove Admin**\n\n👤 {user_name} is an admin and cannot be removed.\n\nUse `/addadmin` to manage admin privileges.",
        'access_revoked': "❌ **Access Revoked**\n\nYour access to the Family Shopping List Bot has been revoked by an admin.\n\nContact an admin if you need access restored.",
        'error_removing_user': "❌ Error removing user authorization. Please try again.",
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
        'recently_category': "🕒 Recently Used",
        'recently_items_title': "Items used in the past 7 days:",
        'btn_back_menu': "🔙 Back to Menu",
        'btn_cancel': "❌ Cancel",
        # Multi-list messages
        'btn_supermarket_list': "🛒 Supermarket List",
        'supermarket_list': "Supermarket List",
        'btn_new_list': "➕ New List",
        'btn_my_lists': "📋 My Lists",
        'btn_custom_shared_list': "🤝 Custom Shared",
        'custom_shared_lists_title': "🤝 Custom Shared Lists",
        'custom_shared_lists_empty': "🤝 **Custom Shared Lists**\n\nNo custom shared lists available.\n\nUse 'New List' → 'Custom Shared List' to create one!",
        'custom_shared_lists_available': "🤝 **Custom Shared Lists**\n\nCustom shared lists accessible to you:",
        'create_custom_shared_list_prompt': "🤝 **Create Custom Shared List**\n\nEnter a name for your custom shared list:",
        'share_custom_shared_list_title': "🤝 **Share Custom Shared List**",
        'share_custom_shared_list_message': "Select users to share your list '{list_name}' with:\n\nAvailable users: {user_count}\n\nClick users to select/deselect them, then click 'Continue'.",
        'btn_continue_with_selected': "✅ Continue with Selected",
        'btn_select_all': "🚫 Select All",
        'custom_shared_list_created': "✅ **Custom Shared List Created!**\n\n📋 **{list_name}** has been created and shared with {user_count} users.",
        'new_custom_shared_list_notification': "🤝 **New Custom Shared List**\n\n📋 **{list_name}** has been shared with you by {creator_name}!",
        'finalize_list_title': "🔒 FINALIZE LIST",
        'finalize_list_confirm': "🔒 **Finalize List**\n\nList: {list_name}\nItems: {item_count}\n\n⚠️ **This action will freeze the list!**\n\nOnce finalized:\n• ✅ Items can be marked as 'Bought' or 'Not Found'\n• ❌ No items can be added or removed\n• 📋 List becomes a shopping checklist\n\n**This action requires admin privileges.**\n\nAre you sure you want to finalize this list?",
        'list_finalized': "✅ **List Finalized Successfully!**\n\n🔒 **{list_name}** has been frozen.\n\n📋 The list is now in checklist mode:\n• ✅ Mark items as 'Bought' or 'Not Found'\n• ❌ Cannot add or remove items\n• 📤 All users can view and check off items",
        'list_unfrozen': "🔓 **List Unfrozen Successfully!**\n\n📋 **{list_name}** has been restored to normal mode.\n\n✅ Users can now add and remove items again.",
        'list_is_frozen': "🔒 **FROZEN LIST**\n\nThis list has been finalized and is now in frozen mode.\n\n✅ **Available actions:**\n• Mark items as 'Bought' or 'Not Found'\n• View the shopping checklist\n\n❌ **Not available:**\n• Adding new items\n• Removing items\n\n📋 Use this as your shopping checklist!",
        'btn_mark_bought': "✅ Bought",
        'btn_mark_not_found': "❌ Not Found",
        'item_marked_bought': "✅ '{item_name}' marked as purchased!",
        'item_marked_not_found': "❌ '{item_name}' marked as not found!",
        'frozen_mode_action_denied': "🔒 **Frozen List**\n\n❌ This list has been finalized.\n\n✅ **You can only:**\n• Mark items as 'Bought' or 'Not Found'\n• View the shopping checklist\n\n❌ **You cannot:**\n• Add new items\n• Remove items",
        'finalize_permission_denied': "❌ **Permission Denied**\n\nOnly the following can finalize this list:\n• Admin users (for shared lists)\n• List owner/creator (for personal/custom shared lists)",
        'btn_manage_lists': "📂 Manage Lists",
        'btn_manage_my_lists': "📂 Manage My Lists",
        'admin_controls_title': "⚙️ ADMIN CONTROLS\n\nChoose an admin action:",
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
        'bought_items_reset_notification': "🔄 Bought items reset by {reset_by}\n\n✅ {count} bought items have been reset to 'pending' status.\n\n📋 You can now mark them as bought or not found again!",
        'maintenance_disabled': "❌ Maintenance Mode Disabled\n\nNo more automatic reminders will be sent.",
        'maintenance_time_over': "⏰ MAINTENANCE TIME OVER\n\nIt's {day} {time} - your scheduled maintenance time has passed!\n\n🛒 Did you complete your shopping? Should I reset the list now?",
        'maintenance_notification_sent': "📢 Maintenance notification sent to all admins.",
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
        'select_multiple_items': "Select Multiple Items",
        'select_multiple_instructions': "Click items to select/deselect them, then click 'Remove Selected' when done.",
        'items_selected': "{count} items selected",
        'remove_selected': "Remove Selected",
        'clear_selection': "Clear Selection",
        'no_items_selected': "No items selected for removal.",
        'selected_items_not_found': "Selected items not found.",
        'successfully_removed_multiple': "Successfully removed {count} items from the list.",
        # Main menu buttons
        'btn_new_list': "➕ New List",
        'btn_admin': "⚙️ Admin",
        'btn_admin_management': "⚙️ Management",
        'btn_user_management': "👥 Suggestions",
        'btn_broadcast': "📢 Broadcast",
        # List menu buttons
        'btn_add_item': "➕ Add Item",
        'btn_search': "🔍🎤 Search",
        'btn_view_items': "📖 View Items",
        'btn_summary': "📊 Summary",
        'btn_my_items': "👤 My Items",
        'btn_export': "📤 Export",
        'btn_manage_suggestions': "💡 Manage Suggestions",
        'btn_edit_name': "✏️ Edit Name",
        'btn_remove_items': "🗑️ Remove Items",
        'btn_reset_items': "🔄 Reset Items/List",
        'reset_options_title': "🔄 RESET OPTIONS",
        'reset_options_message': "🔧 **Reset Options for {list_name}**\n\nItems: {item_count}\n\nChoose what to reset:",
        'btn_remove_specific_items': "🎯 Remove Specific Items",
        'btn_reset_bought_items': "✅ Reset 'Bought' Items Only", 
        'btn_reset_whole_list': "🔄 Reset Whole List",
        'btn_cancel_reset': "❌ Cancel",
        'remove_item_confirmation': "❓ **Remove Item Confirmation**\n\n📦 **{item_name}**\n📋 From: **{list_name}**\n\nWhy are you removing this item?",
        'btn_bought': "✅ Bought",
        'btn_not_found_button': "❌ Not Found",
        'btn_just_remove': "🗑️ Just Remove",
        'btn_cancel_button': "❌ Cancel",
        'item_removed_with_status': "✅ Successfully removed '{item_name}' from '{list_name}' - marked as {status}.",
        'item_removed_direct': "✅ Successfully removed '{item_name}' from '{list_name}'.",
        'frozen_list_summary_title': "🔒 **FROZEN LIST SUMMARY**",
        'finalized_on': "📅 Finalized: {timestamp}",
        'your_progress': "📊 **Your Progress**: {bought}/{total} items ({percent}%)",
        'status_summary': "✅ Bought: {bought} | ❌ Not Found: {not_found}",
        'category_complete': "✓ **COMPLETE**",
        'category_progress': "{bought}/{total} items",
        'mark_item_status_title': "🔍 **Mark Item Status**",
        'mark_item_status_message': "📦 **{item_name}**\n\nHow would you like to mark this item?",
        'found_and_bought': "✅ Found & Bought",
        'not_found_in_store': "❌ Not Found in Store", 
        'change_item_status_title': "🔄 **Change Item Status**",
        'change_item_status_message': "📦 **{item_name}**\n\nCurrent Status: {current_status}\n\nWhat's the new status?",
        'status_bought_by': "✅ Bought by {user_name}",
        'status_not_found_by': "❌ Not Found by {user_name}",
        'btn_maintenance_mode': "⏰ Maintenance Mode",
        'btn_delete_list': "🗑️ Delete List",
        'btn_back_to_main_menu': "🏠 Back to Main Menu",
        'btn_back_to_list': "🏠 Back to List",
        'btn_yes': "✅ Yes",
        'btn_no': "❌ No",
        'btn_edit_description': "📝 Edit Description",
        'btn_view_statistics': "📊 View Statistics",
        'btn_export_list': "📤 Export List",
        'btn_finalize_list': "🔒 Finalize List",
        'btn_unfreeze_list': "🔓 Unfreeze List",
        'supermarket_protected': "🛡️ PROTECTED LIST\n\n❌ The {supermarket_list} cannot be deleted.\n\nThis is the core list of the bot and must always remain active.",
        'supermarket_core_purpose': "This is the core list of the bot and must always remain active.",
        'btn_new_category': "➕ New Category",
        'btn_manage_categories': "📂 Manage Categories",
        'new_category_title': "➕ CREATE NEW CATEGORY\n\nEnter a name for the new category:",
        'new_category_emoji': "🎨 Choose an emoji for \"{category_name}\":\n\nType an emoji or select from common ones:",
        'new_category_hebrew': "🇮🇱 Enter Hebrew translation for \"{category_name}\":",
        'category_created_success': "✅ Category \"{category_name}\" created successfully!\n\nEmoji: {emoji}\nEnglish: {name_en}\nHebrew: {name_he}",
        'category_already_exists': "❌ Category \"{category_name}\" already exists!",
        'category_creation_cancelled': "❌ Category creation cancelled.",
        'manage_categories_title': "📂 MANAGE CATEGORIES\n\nCustom categories:",
        'btn_delete_category': "🗑️ Delete Category",
        'confirm_delete_category': "⚠️ Are you sure you want to delete category \"{category_name}\"?\n\nThis will remove it from all lists and cannot be undone!",
        'category_deleted_success': "✅ Category \"{category_name}\" deleted successfully!",
        'no_custom_categories': "📂 No custom categories found.\n\nUse /newcategory to create your first custom category!",
        'btn_suggest_category': "💡 Suggest Category",
        'suggest_category_title': "💡 SUGGEST NEW CATEGORY\n\nEnter a name for the new category:",
        'suggest_category_emoji': "🎨 Choose an emoji for \"{category_name}\":\n\nType an emoji or select from common ones:",
        'suggest_category_hebrew': "🇮🇱 Enter Hebrew translation for \"{category_name}\":",
        'category_suggestion_submitted': "✅ Category suggestion \"{category_name}\" submitted successfully!\n\n📋 **What happens next:**\n• Admins will review your suggestion\n• You'll be notified when it's approved or rejected\n• If approved, the category will be available to everyone",
        'category_suggestion_already_exists': "❌ Category \"{category_name}\" already exists or has been suggested!",
        'category_suggestion_cancelled': "❌ Category suggestion cancelled.",
        'manage_category_suggestions_title': "💡 MANAGE CATEGORY SUGGESTIONS\n\nPending suggestions:",
        'btn_approve_category': "✅ Approve Category",
        'btn_reject_category': "❌ Reject Category",
        'category_suggestion_approved': "✅ Category suggestion \"{category_name}\" approved!\n\nThe new category is now available to all users.",
        'category_suggestion_rejected': "❌ Category suggestion \"{category_name}\" rejected.",
        'no_category_suggestions': "💡 No pending category suggestions found.",
        # Rename functionality
        'rename_items_title': "✏️ **Rename Items (Admin)**\n\nSelect a category to rename items from:",
        'rename_categories_title': "✏️ **Rename Categories (Admin)**\n\nSelect a category to rename:",
        'rename_items_category_title': "✏️ **Rename Items - {category_name}**\n\nSelect an item to rename:",
        'rename_items_category_empty': "📝 **Rename Items - {category_name}**\n\n❌ No items found in this category.",
        'rename_categories_empty': "📂 **Rename Categories (Admin)**\n\n❌ No custom categories found to rename.",
        'rename_item_prompt': "✏️ **Rename Item**\n\n**Category:** {category_name}\n**Current Name:** {item_name}\n\nPlease send the new name in English:",
        'rename_item_hebrew_prompt': "🇮🇱 **Hebrew Translation**\n\n**Item:** {item_name_en}\n**Category:** {category_name}\n\nPlease send the Hebrew translation:",
        'rename_category_prompt': "✏️ **Rename Category**\n\n**Current Name:** {category_name_en} ({category_name_he})\n\nPlease send the new name in English:",
        'rename_category_hebrew_prompt': "🇮🇱 **Hebrew Translation**\n\n**Category:** {category_name_en}\n**English:** {category_name_en}\n\nPlease send the Hebrew translation:",
        'item_renamed_success': "✅ **Item Renamed Successfully!**\n\n**Category:** {category_name}\n**Old Name:** {old_name}\n**New Name:** {new_name}",
        'category_renamed_success': "✅ **Category Renamed Successfully!**\n\n**Old Name:** {old_name_en} ({old_name_he})\n**New Name:** {new_name_en} ({new_name_he})",
        'rename_error': "❌ Error: Failed to rename.",
        'rename_duplicate_item': "❌ Error: Item '{new_name}' already exists in this category.",
        'rename_duplicate_category': "❌ Error: Category '{new_name}' already exists.",
        'rename_missing_data': "❌ Error: Missing rename data.",
        'rename_cancelled': "❌ Rename cancelled.",
        'btn_back_to_management': "🔙 Back to Management",
        # Additional button translations
        'btn_select_multiple_items': "🎯 Select Multiple Items",
        'btn_add_to_current_list': "📝 Add to Current List",
        'btn_add_to_category_permanently': "➕ Add to Category Permanently",
        'btn_suggest_for_category': "💡 Suggest for Category",
        'btn_back_to_category': "🏠 Back to Category",
        'btn_manage_items': "📝 Manage Items",
        'btn_manage_categories': "🗂️ Manage Categories",
        'btn_manage_templates': "📋 Manage Templates",
        'btn_templates': "📝 Templates",
        'btn_manage_lists': "📂 Manage Lists",
        'btn_new_item': "➕ New Item",
        'btn_rename_items': "✏️ Rename Items",
        'btn_delete_items': "🗑️ Delete Items",
        'btn_new_category': "📂 New Category",
        'btn_rename_categories': "✏️ Rename Categories",
        # Additional translations for hard-coded strings
        'search_again': "Search Again",
        'restore_original_item': "Restore Original Item",
        'supermarket_list_name': "Supermarket List",
        'weekly_family_shopping_list': "Weekly family shopping list",
        'friday': "Friday",
        'unknown': "Unknown"
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
• **נהל את הרשימות שלי** - ערוך, מחק ונהל את הרשימות שלך
• **ייצוא** - צור רשימה לשיתוף (מנהלים בלבד)

**🔍 תכונות מתקדמות:**
• **תמיכה בשפות** - ממשק עברית/אנגלית
• **הצעות פריטים** - הצע פריטים חדשים לקטגוריות
• **הצעות קטגוריות** - הצע קטגוריות חדשות
• **הודעות שידור** - שלח הודעות לכל בני המשפחה
• **מצב תחזוקה** - איפוס רשימות מתוזמן (רשימת סופר בלבד)

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
6. נהל את הרשימות שלך עם "נהל את הרשימות שלי"
7. השתמש ב"הצעות" כדי להציע פריטים או קטגוריות חדשות

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
               'voice_search_prompt': "🎤 חיפוש קולי\n\nלחץ והחזק על כפתור המיקרופון כדי לדבר את שאילתת החיפוש שלך.\n\n💡 טיפים:\n• דבר בבירור באנגלית או עברית\n• דוגמאות: 'milk', 'חלב', 'bread', 'לחם'\n• שחרר את המיקרופון כשסיימת - אין צורך ללחוץ על עצור!\n\nהקש על 'התחל הקלטת קול' ואז החזק את המיקרופון:",
        'btn_start_voice_recording': "🎤 התחל הקלטת קול",
        'btn_switch_to_text_search': "✏️ עבור לחיפוש טקסט",
        'btn_stop_recording': "⏹️ עצור הקלטה",
        'btn_text_search': "✏️ חיפוש טקסט",
        'btn_voice_search': "🎤 חיפוש קולי",
        'btn_back_to_list': "🏠 חזור לרשימה",
        'btn_back_to_list_actions': "🏠 חזור לפעולות רשימה",
        'btn_add_new_item': "➕ הוסף פריט חדש",
        'btn_add_to_the_list': "✅ הוסף לרשימה",
        'shopping_summary_report': "📊 דוח סיכום קניות",
        'voice_search_listening': "🎤 מקשיב... דבר עכשיו!\n\nשחרר את המיקרופון כשסיימת.",
        'voice_search_processing': "🔄 מעבד את הקול שלך...",
        'voice_search_error': "❌ זיהוי קול נכשל. אנא נסה שוב או השתמש בחיפוש טקסט.",
        'voice_search_timeout': "⏰ פסק זמן בהקלטת קול. אנא נסה שוב.",
        'item_restoration_detected': "🔄 **זוהה שחזור פריט**\n\n**'{item_name}'** נמחק בעבר מהקטגוריה **{category_name}**.\n\nמה תרצה לעשות?",
        'btn_restore_original_item': "🔄 שחזר פריט מקורי",
        'btn_add_as_new_item': "➕ הוסף כפריט חדש",
        'btn_cancel_restoration': "❌ ביטול",
        'item_restored_success': "✅ **הפריט שוחזר!**\n\n**'{item_name}'** שוחזר לקטגוריה **{category_name}** ועכשיו נראה שוב.",
        'item_added_as_new_success': "✅ **פריט חדש נוסף!**\n\n**'{item_name}'** נוסף כפריט חדש לקטגוריה **{category_name}**.",
        'add_new_item_admin_title': "➕ הוסף פריט חדש (מנהל)",
        'add_new_item_prompt': "אנא הקלד את שם הפריט באנגלית:",
        'add_new_item_tips': "💡 טיפים:\n• השתמש בשמות ברורים ופשוטים\n• הימנע משמות מותגים\n• דוגמאות: 'Organic honey', 'Fresh basil', 'Whole wheat bread'",
        'type_item_name': "הקלד את שם הפריט:",
        'translation_required_admin': "🌐 נדרשת תרגום (מנהל)",
        'provide_hebrew_translation': "אנא ספק את התרגום העברי:",
        'hebrew_translation_tips': "💡 טיפים:\n• השתמש במונחים עבריים נפוצים\n• שמור על פשטות ובהירות\n• דוגמאות: 'דבש אורגני', 'בזיליקום טרי', 'לחם מחיטה מלאה'",
        'type_hebrew_translation': "הקלד את התרגום העברי:",
        'please_provide_hebrew': "❌ אנא ספק תרגום עברי.",
        'error_processing_new_item': "❌ שגיאה בעיבוד פריט חדש. אנא נסה שוב.",
        'error_adding_new_item_duplicate': "❌ שגיאה בהוספת פריט חדש - כפילות!\n\nהפריט **{item_name}** כבר קיים בקטגוריה **{category_name}**.",
        'error_adding_new_item': "❌ שגיאה בהוספת פריט חדש. אנא נסה שוב.",
        'failed_to_restore_item': "❌ נכשל בשחזור הפריט. אנא נסה שוב.",
        'error_category_not_found': "❌ שגיאה: קטגוריה לא נמצאה.",
        'failed_to_add_item': "❌ נכשל בהוספת הפריט. אנא נסה שוב.",
        'error_search_query_not_found': "❌ שגיאה: שאילתת חיפוש לא נמצאה. אנא נסה לחפש שוב.",
        'error_opening_voice_search': "❌ שגיאה בפתיחת חיפוש קולי. אנא נסה שוב.",
        'error_changing_language': "❌ שגיאה בשינוי שפה.",
        'error_approving_suggestion': "❌ שגיאה באישור ההצעה.",
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
        'btn_search': "🔍🎤 חיפוש",
        'btn_help': "❓ עזרה",
        'category_not_found': "❌ קטגוריה לא נמצאה!",
        'suggestion_review': "💡 סקירת הצעה",
        'list_fallback': "רשימה {list_id}",
        'user_fallback': "משתמש {user_id}",
        'admin_fallback': "מנהל",
        'someone_fallback': "מישהו",
        'none_fallback': "ללא",
        'all_lists': "כל הרשימות",
        'remove_item_failed': "נכשל בהסרת הפריט. אנא נסה שוב.",
        'items_count': "פריטים: {count}",
        'list_type': "סוג: {type}",
        'total_items': "סך הכל פריטים: {count}",
        'supermarket_list_en': "רשימת סופר",
        'items_count_inline': "({count} פריטים)",
        'usage_removeuser': "❌ **שימוש:** `/removeuser <user_id>`\n\n**דוגמה:** `/removeuser 123456789`\n\nהשתמש ב-`/users` כדי לראות את כל המשתמשים והמזהים שלהם.",
        'user_not_authorized': "❌ **משתמש לא מורשה**\n\n👤 {user_name} אינו מורשה כרגע.\n\nהשתמש ב-`/authorize {user_id}` כדי לאשר אותו קודם.",
        'cannot_remove_admin': "❌ **לא ניתן להסיר מנהל**\n\n👤 {user_name} הוא מנהל ולא ניתן להסיר אותו.\n\nהשתמש ב-`/addadmin` כדי לנהל הרשאות מנהל.",
        'access_revoked': "❌ **הגישה בוטלה**\n\nהגישה שלך לבוט רשימת הקניות המשפחתית בוטלה על ידי מנהל.\n\nצור קשר עם מנהל אם אתה צריך לשחזר את הגישה.",
        'error_removing_user': "❌ שגיאה בהסרת הרשאת המשתמש. אנא נסה שוב.",
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
        'recently_category': "🕒 שימוש אחרון",
        'recently_items_title': "פריטים ששומשו ב-7 הימים האחרונים:",
        'btn_back_menu': "🔙 חזרה לתפריט",
        'btn_cancel': "❌ ביטול",
        # Multi-list messages in Hebrew
        'btn_supermarket_list': "🛒 רשימת סופר",
        'supermarket_list': "רשימת סופר",
        'btn_new_list': "➕ רשימה חדשה",
        'btn_my_lists': "📋 הרשימות שלי",
        'btn_custom_shared_list': "🤝 רשימה משותפת",
        'custom_shared_lists_title': "🤝 רשימות משותפת מותאמות",
        'custom_shared_lists_empty': "🤝 **רשימות משותפת מותאמות**\n\nאין רשימות משותפות זמינות.\n\nהשתמש ב-'רשימה חדשה' → 'רשימה משותפת מותאמת' ליצירת אחת!",
        'custom_shared_lists_available': "🤝 **רשימות משותפת מותאמות**\n\nרשימות משותפות הנגישות לך:",
        'create_custom_shared_list_prompt': "🤝 **צור רשימה משותפת מותאמת**\n\nהכנס שם לרשימה המשותפת המותאמת שלך:",
        'share_custom_shared_list_title': "🤝 **שתף רשימה משותפת מותאמת**",
        'share_custom_shared_list_message': "בחר משתמשים לשתף את הרשימה '{list_name}' איתם:\n\nמשתמשים זמינים: {user_count}\n\nלחץ על משתמשים לבחירה/ביטול הבחירה, ואז לחץ 'המשך'.",
        'btn_continue_with_selected': "✅ המשך עם הנבחרים",
        'btn_select_all': "🚫 בחר הכל",
        'custom_shared_list_created': "✅ **רשימה משותפת מותאמת נוצרה!**\n\n📋 **{list_name}** נוצרה ושותפה עם {user_count} משתמשים.",
        'new_custom_shared_list_notification': "🤝 **רשימה משותפת מותאמת חדשה**\n\n📋 **{list_name}** שותפה איתך על ידי {creator_name}!",
        'finalize_list_title': "🔒 סגירת רשימה",
        'finalize_list_confirm': "🔒 **סגירת רשימה**\n\nרשימה: {list_name}\nפריטים: {item_count}\n\n⚠️ **פעולה זו תקפיא את הרשימה!**\n\nלאחר הסגירה:\n• ✅ ניתן לסמן פריטים כ'נקנו' או 'לא נמצאו'\n• ❌ לא ניתן להוסיף או להסיר פריטים\n• 📋 הרשימה הופכת לרשימת מכולת\n\n**פעולה זו דורשת הרשאות מנהל.**\n\nהאם אתה בטוח שברצונך לסגור את הרשימה?",
        'list_finalized': "✅ **רשימה נסגרה בהצלחה!**\n\n🔒 **{list_name}** הוקפאה.\n\n📋 הרשימה עכשיו במצב רשימת מכולת:\n• ✅ סמן פריטים כ'נקנו' או 'לא נמצאו'\n• ❌ לא ניתן להוסיף או להסיר פריטים\n• 📤 כל המשתמשים יכולים לצפות ולסמן פריטים",
        'list_unfrozen': "🔓 **רשימה נפתחה בהצלחה!**\n\n📋 **{list_name}** הוחזרה למצב רגיל.\n\n✅ משתמשים יכולים כעת להוסיף ולהסיר פריטים שוב.",
        'list_is_frozen': "🔒 **רשימה קפואה**\n\nרשימה זו נסגרה והיא כעת במצב קפוא.\n\n✅ **פעולות זמינות:**\n• סמן פריטים כ'נקנו' או 'לא נמצאו'\n• צפה ברשימת המכולת\n\n❌ **לא זמין:**\n• הוספת פריטים חדשים\n• הסרת פריטים\n\n📋 השתמש בזה כרשימת המכולת שלך!",
        'btn_mark_bought': "✅ נקנה",
        'btn_mark_not_found': "❌ לא נמצא",
        'item_marked_bought': "✅ '{item_name}' סומן כנקנה!",
        'item_marked_not_found': "❌ '{item_name}' סומן כלא נמצא!",
        'frozen_mode_action_denied': "🔒 **רשימה קפואה**\n\n❌ רשימה זו נסגרה.\n\n✅ **אתה יכול רק:**\n• לסמן פריטים כ'נקנו' או 'לא נמצאו'\n• לצפות ברשימת המכולת\n\n❌ **אתה לא יכול:**\n• להוסיף פריטים חדשים\n• להסיר פריטים",
        'finalize_permission_denied': "❌ **הרשאה נדחתה**\n\nרק הדברים הבאים יכולים לסגור רשימה זו:\n• מנהלי מערכת (עבור רשימות משותפות)\n• בעל/יוצר הרשימה (עבור הרשימות האישיות/המשותפות המותאמות)",
        'btn_manage_lists': "📂 נהל רשימות",
        'btn_manage_my_lists': "📂 נהל את הרשימות שלי",
        'admin_controls_title': "⚙️ בקרות מנהל\n\nבחר פעולת מנהל:",
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
        'bought_items_reset_notification': "🔄 פריטים שנקנו אופסו על ידי {reset_by}\n\n✅ {count} פריטים שנקנו אופסו לסטטוס 'ממתין'.\n\n📋 עכשיו תוכל לסמן אותם שוב כנקנו או לא נמצאו!",
        'maintenance_disabled': "❌ מצב התחזוקה הושבת\n\nלא יישלחו עוד תזכורות אוטומטיות.",
        'maintenance_time_over': "⏰ זמן התחזוקה הסתיים\n\nזה {day} {time} - זמן התחזוקה המתוכנן שלך עבר!\n\n🛒 האם סיימת את הקניות? האם לאפס את הרשימה עכשיו?",
        'maintenance_notification_sent': "📢 הודעת תחזוקה נשלחה לכל המנהלים.",
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
        'select_multiple_items': "בחר פריטים מרובים",
        'select_multiple_instructions': "לחץ על פריטים לבחירה/ביטול בחירה, ואז לחץ על 'הסר נבחרים' כשסיימת.",
        'items_selected': "{count} פריטים נבחרו",
        'remove_selected': "הסר נבחרים",
        'clear_selection': "נקה בחירה",
        'no_items_selected': "לא נבחרו פריטים להסרה.",
        'selected_items_not_found': "הפריטים הנבחרים לא נמצאו.",
        'successfully_removed_multiple': "הוסרו בהצלחה {count} פריטים מהרשימה.",
        # Main menu buttons
        'btn_new_list': "➕ רשימה חדשה",
        'btn_admin': "⚙️ מנהל",
        'btn_admin_management': "⚙️ ניהול",
        'btn_user_management': "👥 הצעות",
        'btn_broadcast': "📢 שידור",
        # List menu buttons
        'btn_add_item': "➕ הוסף פריט",
        'btn_search': "🔍🎤 חיפוש",
        'btn_view_items': "📖 צפה בפריטים",
        'btn_summary': "📊 סיכום",
        'btn_my_items': "👤 הפריטים שלי",
        'btn_export': "📤 ייצא",
        'btn_manage_suggestions': "💡 נהל הצעות",
        'btn_edit_name': "✏️ ערוך שם",
        'btn_remove_items': "🗑️ הסר פריטים",
        'btn_reset_items': "🔄 אפס פריטים/רשימה",
        'reset_options_title': "🔄 אפשרויות איפוס",
        'reset_options_message': "🔧 **אפשרויות איפוס עבור {list_name}**\n\nפריטים: {item_count}\n\nבחר מה לאיפוס:",
        'btn_remove_specific_items': "🎯 הסר פריטים ספציפיים",
        'btn_reset_bought_items': "✅ אפס רק פריטים 'נקנו'", 
        'btn_reset_whole_list': "🔄 אפס את כל הרשימה",
        'btn_cancel_reset': "❌ ביטול",
        'remove_item_confirmation': "❓ **אישור הסרת פריט**\n\n📦 **{item_name}**\n📋 מתוך: **{list_name}**\n\nלמה אתה מסיר את הפריט הזה?",
        'btn_bought': "✅ נקנה",
        'btn_not_found_button': "❌ לא נמצא",
        'btn_just_remove': "🗑️ רק הסר",
        'btn_cancel_button': "❌ ביטול",
        'item_removed_with_status': "✅ הסרת '{item_name}' בוצעה בהצלחה מתוך '{list_name}' - סומן כ{status}.",
        'item_removed_direct': "✅ הסרת '{item_name}' בוצעה בהצלחה מתוך '{list_name}'.",
        'frozen_list_summary_title': "🔒 **סיכום רשימה קפואה**",
        'finalized_on': "📅 נסגר ב: {timestamp}",
        'your_progress': "📊 **ההתקדמות שלך**: {bought}/{total} פריטים ({percent}%)",
        'status_summary': "✅ נקנו: {bought} | ❌ לא נמצאו: {not_found}",
        'category_complete': "✓ **הושלם**",
        'category_progress': "{bought}/{total} פריטים",
        'mark_item_status_title': "🔍 **סמן סטטוס פריט**",
        'mark_item_status_message': "📦 **{item_name}**\n\nאיך תרצה לסמן את הפריט הזה?",
        'found_and_bought': "✅ נמצא ונקנה",
        'not_found_in_store': "❌ לא נמצא בחנות",
        'change_item_status_title': "🔄 **שנה סטטוס פריט**",
        'change_item_status_message': "📦 **{item_name}**\n\nסטטוס נוכחי: {current_status}\n\nמה הסטטוס החדש?",
        'status_bought_by': "✅ נקנה על ידי {user_name}",
        'status_not_found_by': "❌ לא נמצא על ידי {user_name}",
        'btn_maintenance_mode': "⏰ מצב תחזוקה",
        'btn_delete_list': "🗑️ מחק רשימה",
        'btn_back_to_main_menu': "🏠 חזרה לתפריט הראשי",
        'btn_back_to_list': "🏠 חזרה לרשימה",
        'btn_yes': "✅ כן",
        'btn_no': "❌ לא",
        'btn_edit_description': "📝 ערוך תיאור",
        'btn_view_statistics': "📊 צפה בסטטיסטיקות",
        'btn_export_list': "📤 ייצא רשימה",
        'btn_finalize_list': "🔒 סגור רשימה",
        'btn_unfreeze_list': "🔓 פתח רשימה",
        'supermarket_protected': "🛡️ רשימה מוגנת\n\n❌ {supermarket_list} לא ניתן למחיקה.\n\nזוהי הרשימה המרכזית של הבוט וחייבת להישאר פעילה תמיד.",
        'supermarket_core_purpose': "זוהי הרשימה המרכזית של הבוט וחייבת להישאר פעילה תמיד.",
        'btn_new_category': "➕ קטגוריה חדשה",
        'btn_manage_categories': "📂 ניהול קטגוריות",
        'new_category_title': "➕ צור קטגוריה חדשה\n\nהזן שם לקטגוריה החדשה:",
        'new_category_emoji': "🎨 בחר אמוג'י עבור \"{category_name}\":\n\nהקלד אמוג'י או בחר מהנפוצים:",
        'new_category_hebrew': "🇮🇱 הזן תרגום עברי עבור \"{category_name}\":",
        'category_created_success': "✅ הקטגוריה \"{category_name}\" נוצרה בהצלחה!\n\nאמוג'י: {emoji}\nאנגלית: {name_en}\nעברית: {name_he}",
        'category_already_exists': "❌ הקטגוריה \"{category_name}\" כבר קיימת!",
        'category_creation_cancelled': "❌ יצירת הקטגוריה בוטלה.",
        'manage_categories_title': "📂 ניהול קטגוריות\n\nקטגוריות מותאמות אישית:",
        'btn_delete_category': "🗑️ מחק קטגוריה",
        'confirm_delete_category': "⚠️ האם אתה בטוח שברצונך למחוק את הקטגוריה \"{category_name}\"?\n\nזה יסיר אותה מכל הרשימות ולא ניתן לבטל!",
        'category_deleted_success': "✅ הקטגוריה \"{category_name}\" נמחקה בהצלחה!",
        'no_custom_categories': "📂 לא נמצאו קטגוריות מותאמות אישית.\n\nהשתמש ב-/newcategory כדי ליצור את הקטגוריה המותאמת הראשונה שלך!",
        'btn_suggest_category': "💡 הצע קטגוריה",
        'suggest_category_title': "💡 הצע קטגוריה חדשה\n\nהזן שם לקטגוריה החדשה:",
        'suggest_category_emoji': "🎨 בחר אמוג'י עבור \"{category_name}\":\n\nהקלד אמוג'י או בחר מהנפוצים:",
        'suggest_category_hebrew': "🇮🇱 הזן תרגום עברי עבור \"{category_name}\":",
        'category_suggestion_submitted': "✅ הצעת הקטגוריה \"{category_name}\" נשלחה בהצלחה!\n\n📋 **מה קורה הלאה:**\n• מנהלים יעיינו בהצעה שלך\n• תתעדכן כשתאושר או תידחה\n• אם תאושר, הקטגוריה תהיה זמינה לכולם",
        'category_suggestion_already_exists': "❌ הקטגוריה \"{category_name}\" כבר קיימת או הוצעה!",
        'category_suggestion_cancelled': "❌ הצעת הקטגוריה בוטלה.",
        'manage_category_suggestions_title': "💡 ניהול הצעות קטגוריות\n\nהצעות ממתינות:",
        'btn_approve_category': "✅ אשר קטגוריה",
        'btn_reject_category': "❌ דחה קטגוריה",
        'category_suggestion_approved': "✅ הצעת הקטגוריה \"{category_name}\" אושרה!\n\nהקטגוריה החדשה זמינה כעת לכל המשתמשים.",
        'category_suggestion_rejected': "❌ הצעת הקטגוריה \"{category_name}\" נדחתה.",
        'no_category_suggestions': "💡 לא נמצאו הצעות קטגוריות ממתינות.",
        # Rename functionality
        'rename_items_title': "✏️ **שנה שם פריטים (מנהל)**\n\nבחר קטגוריה לשינוי שם פריטים:",
        'rename_categories_title': "✏️ **שנה שם קטגוריות (מנהל)**\n\nבחר קטגוריה לשינוי שם:",
        'rename_items_category_title': "✏️ **שנה שם פריטים - {category_name}**\n\nבחר פריט לשינוי שם:",
        'rename_items_category_empty': "📝 **שנה שם פריטים - {category_name}**\n\n❌ לא נמצאו פריטים בקטגוריה זו.",
        'rename_categories_empty': "📂 **שנה שם קטגוריות (מנהל)**\n\n❌ לא נמצאו קטגוריות מותאמות אישית לשינוי שם.",
        'rename_item_prompt': "✏️ **שנה שם פריט**\n\n**קטגוריה:** {category_name}\n**שם נוכחי:** {item_name}\n\nאנא שלח את השם החדש באנגלית:",
        'rename_item_hebrew_prompt': "🇮🇱 **תרגום עברי**\n\n**פריט:** {item_name_en}\n**קטגוריה:** {category_name}\n\nאנא שלח את התרגום העברי:",
        'rename_category_prompt': "✏️ **שנה שם קטגוריה**\n\n**שם נוכחי:** {category_name_en} ({category_name_he})\n\nאנא שלח את השם החדש באנגלית:",
        'rename_category_hebrew_prompt': "🇮🇱 **תרגום עברי**\n\n**קטגוריה:** {category_name_en}\n**אנגלית:** {category_name_en}\n\nאנא שלח את התרגום העברי:",
        'item_renamed_success': "✅ **שם הפריט שונה בהצלחה!**\n\n**קטגוריה:** {category_name}\n**שם ישן:** {old_name}\n**שם חדש:** {new_name}",
        'category_renamed_success': "✅ **שם הקטגוריה שונה בהצלחה!**\n\n**שם ישן:** {old_name_en} ({old_name_he})\n**שם חדש:** {new_name_en} ({new_name_he})",
        'rename_error': "❌ שגיאה: נכשל בשינוי השם.",
        'rename_duplicate_item': "❌ שגיאה: הפריט '{new_name}' כבר קיים בקטגוריה זו.",
        'rename_duplicate_category': "❌ שגיאה: הקטגוריה '{new_name}' כבר קיימת.",
        'rename_missing_data': "❌ שגיאה: נתוני שינוי שם חסרים.",
        'rename_cancelled': "❌ שינוי השם בוטל.",
        'btn_back_to_management': "🔙 חזרה לניהול",
        # Additional button translations
        'btn_select_multiple_items': "🎯 בחר פריטים מרובים",
        'btn_add_to_current_list': "📝 הוסף לרשימה הנוכחית",
        'btn_add_to_category_permanently': "➕ הוסף לקטגוריה לצמיתות",
        'btn_suggest_for_category': "💡 הצע לקטגוריה",
        'btn_back_to_category': "🏠 חזרה לקטגוריה",
        'btn_manage_items': "📝 נהל פריטים",
        'btn_manage_categories': "🗂️ נהל קטגוריות",
        'btn_manage_templates': "📋 נהל תבניות",
        'btn_templates': "📝 תבניות",
        'btn_manage_lists': "📂 נהל רשימות",
        'btn_new_item': "➕ פריט חדש",
        'btn_rename_items': "✏️ שנה שמות פריטים",
        'btn_delete_items': "🗑️ מחק פריטים",
        'btn_new_category': "📂 קטגוריה חדשה",
        'btn_rename_categories': "✏️ שנה שמות קטגוריות",
        # Additional translations for hard-coded strings
        'search_again': "חפש שוב",
        'restore_original_item': "שחזר פריט מקורי",
        'supermarket_list_name': "רשימת סופר",
        'weekly_family_shopping_list': "רשימת קניות משפחתית שבועית",
        'friday': "יום שישי",
        'unknown': "לא ידוע",
        
        # Bot Commands Hebrew translations
        'cmd_start_hebrew': "🚀 התחל להשתמש בבוט",
        'cmd_menu_hebrew': "📱 הצג תפריט ראשי",
        'cmd_help_hebrew': "❓ הצג מדריך עזרה",
        'cmd_categories_hebrew': "📋 עיין בקטגוריות פריטים",
        'cmd_add_hebrew': "➕ הוסף פריט מותאם אישית",
        'cmd_list_hebrew': "📝 צפה ברשימת קניות",
        'cmd_summary_hebrew': "📊 צור דוח סיכום",
        'cmd_myitems_hebrew': "👤 צפה בפריטים שהוספתי",
        'cmd_language_hebrew': "🌍 שנה שפה",
        'cmd_users_hebrew': "👥 נהל משתמשים (מנהל)",
        'cmd_authorize_hebrew': "✅ אשר משתמש (מנהל)",
        'cmd_addadmin_hebrew': "👑 קדם למנהל (מנהל)",
        'cmd_removeuser_hebrew': "❌ הסר הרשאות משתמש (מנהל)",
        'cmd_broadcast_hebrew': "📢 שלח הודעה לכולם (מנהל)",
        'cmd_suggest_hebrew': "💡 הצע פריט חדש",
        'cmd_newcategory_hebrew': "➕ צור קטגוריה חדשה (מנהל)",
        'cmd_managecategories_hebrew': "📂 נהל קטגוריות (מנהל)",
        'cmd_suggestcategory_hebrew': "💡 הצע קטגוריה חדשה",
        'cmd_managecategorysuggestions_hebrew': "💡 נהל הצעות קטגוריות (מנהל)",
        'cmd_managesuggestions_hebrew': "📝 נהל הצעות (מנהל)",
        'cmd_newitem_hebrew': "🆕 הוסף פריט חדש לקטגוריה (מנהל)",
        'cmd_reset_hebrew': "🔄 אפס רשימה (מנהל)",
        'cmd_search_hebrew': "🔍 חפש פריטים",
        
        # Hard-coded button text Hebrew translations
        'btn_supermarket_list_hebrew': "🛒 רשימת סופר",
        'btn_new_list_hebrew': "➕ רשימה חדשה", 
        'btn_suggest_category_hebrew': "💡 הצע קטגוריה",
        'btn_my_lists_hebrew': "📋 הרשימות שלי",
        'btn_admin_management_hebrew': "⚙️ ניהול",
        'btn_user_management_hebrew': "👥 הצעות",
        'btn_broadcast_hebrew': "📢 שידור",
        'btn_help_hebrew': "❓ עזרה",
        'btn_categories_hebrew': "📋 קטגוריות",
        'btn_add_item_hebrew': "➕ הוסף פריט",
        'btn_view_list_hebrew': "📝 צפה ברשימה",
        'btn_summary_hebrew': "📊 סיכום",
        'btn_manage_users_hebrew': "👥 נהל משתמשים",
        'btn_suggest_item_hebrew': "💡 הצע פריט",
        'btn_new_item_hebrew': "➕ פריט חדש",
        'btn_search_hebrew': "🔍🎤 חיפוש",
        'btn_admin_hebrew': "⚙️ מנהל",
        
        # Critical notification messages Hebrew translations
        'create_new_list_title_hebrew': "📋 **צור רשימה חדשה**",
        'create_new_list_message_hebrew': "📋 **צור רשימה חדשה**\n\nבחר את סוג הרשימה שברצונך ליצור:\n\n🌐 **רשימה משותפת** - נראית לכל המנהלים והמשתמשים המורשים\n👤 **הרשימות שלי** - נראית רק לך\n🤝 **רשימה משותפת מותאמת** - שתף עם משתמשים ומנהלים ספציפיים",
        'list_frozen_notification_hebrew': "🔒 **רשימה נסגרה**",
        'list_frozen_message_hebrew': "📋 **{list_name}** נסגרה על ידי **{finalizer_name}**.\n\nהרשימה כעת במצב רשימת מכולת - סמן פריטים כנקנו או לא נמצאו!",
        'no_lists_found_hebrew': "❌ לא נמצאו רשימות.",
        'template_management_title_hebrew': "📋 **ניהול תבניות**",
        'template_management_message_hebrew': "בחר רשימה לניהול תבניות:",
        'manage_system_templates_hebrew': "🏛️ נהל תבניות מערכת",
        'list_reset_notification_hebrew': "🔄 **רשימה אופסה**",
        'list_reset_message_hebrew': "הרשימה **{list_name}** אופסה על ידי מנהל.\nכל הפריטים הוסרו מהרשימה.",
        'item_approved_notification_hebrew': "✅ **פריט אושר**",
        'item_approved_message_hebrew': "הפריט **{item_name}** שהוצע על ידי **{suggested_by_name}** אושר על ידי **{admin_name}**.\nהפריט זמין כעת לכל המשתמשים!",
        'category_approved_notification_hebrew': "✅ **קטגוריה אושרה**",
        'category_approved_message_hebrew': "הקטגוריה **{category_name}** שהוצעה על ידי **{suggested_by_name}** אושרה על ידי **{admin_name}**.\nהקטגוריה זמינה כעת לכל המשתמשים!",
        
        # UI buttons and navigation Hebrew translations  
        'back_to_management_hebrew': "🔙 חזור לניהול",
        'back_to_list_hebrew': "🔙 חזור לרשימה",
        'templates_for_list_hebrew': "📝 **תבניות עבור {list_name}**",
        'no_templates_available_hebrew': "אין תבניות זמינות לסוג רשימה זה עדיין.",
        'template_preview_hebrew': "📋 תצוגה מקדימה של תבנית {template_name}",
        'choose_template_usage_hebrew': "💡 בחר איך להשתמש בתבנית זו:",
        'add_all_items_hebrew': "✅ הוסף את כל הפריטים",
        'select_items_hebrew': "🎯 בחר פריטים", 
        'replace_list_hebrew': "🔄 החלף רשימה",
        'back_to_templates_hebrew': "🔙 חזור לתבניות",
        'my_templates_hebrew': "📝 **התבניות שלך**",
        'my_templates_none_hebrew': "עדיין לא נוצרו.",
        'my_template_stats_hebrew': "📊 סטטיסטיקות התבניות שלי",
        'manage_my_templates_hebrew': "⚙️ נהל את התבניות שלי",
        'create_from_current_list_hebrew': "➕ צור מהרשימה הנוכחית",
        'create_empty_template_hebrew': "➕ צור תבנית ריקה",
        'create_from_list_hebrew': "➕ צור מרשימה",
        
        # Maintenance mode Hebrew translations
        'maintenance_reset_whole_hebrew': "🔄 אפס את כל הרשימה",
        'maintenance_reset_bought_hebrew': "✅ אפס רק פריטים שנקנו",
        'maintenance_not_yet_hebrew': "❌ עדיין לא",
        
        # Additional button text checks Hebrew translations
        'btn_custom_shared_list_hebrew': "🤝 רשימה משותפת",
        'btn_manage_my_lists_hebrew': "📂 נהל את הרשימות שלי",
        
        # Template management UI Hebrew translations  
        'no_lists_found_template_hebrew': "❌ לא נמצאו רשימות.",
        'back_to_management_template_hebrew': "🔙 חזור לניהול",
        'template_management_global_hebrew': "📋 **ניהול תבניות**",
        'template_management_message_hebrew': "בחר רשימה לניהול תבניות:",
        'my_template_stats_hebrew': "📊 סטטיסטיקות התבניות שלי",
        'manage_my_templates_button_hebrew': "⚙️ נהל את התבניות שלי",
        'create_from_current_list_button_hebrew': "➕ צור מהרשימה הנוכחית", 
        'create_empty_template_button_hebrew': "➕ צור תבנית ריקה",
        'create_from_list_global_hebrew': "➕ צור מרשימה",
        'back_to_template_management_hebrew': "🔙 חזור לניהול תבניות",
        'back_to_template_management_menu_hebrew': "🔙 חזור לניהול תבניות",
        'template_preview_title_hebrew': "📋 תצוגה מקדימה של תבנית {template_name}",
        'choose_template_usage_hebrew': "💡 בחר איך להשתמש בתבנית זו:",
        'add_all_items_button_hebrew': "✅ הוסף את כל הפריטים",
        'select_items_button_hebrew': "🎯 בחר פריטים",
        'replace_list_button_hebrew': "🔄 החלף רשימה", 
        'back_to_templates_button_hebrew': "🔙 חזור לתבניות"
    }
}
