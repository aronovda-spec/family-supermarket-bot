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
        'help': """🛒 Family Shopping List Bot Commands

Main Commands:
/start - Start the bot and register
/help - Show this help message
/categories - Browse and add items by category
/add - Add a custom item to the list
/list - View current shopping list
/summary - Get formatted shopping report
/myitems - View items you've added

Admin Commands:
/reset - 🔴 Reset the entire list
/users - 👥 Manage users and view status
/authorize <user_id> - ✅ Authorize a regular user
/addadmin <user_id> - 👑 Promote user to admin

Quick Actions:
- Tap ✅ next to category items to add them
- Add notes when prompted (quantity, brand, etc.)
- Only admins can delete items and reset the list

Features:
✅ Pre-defined categories for quick selection
✅ Custom item addition
✅ Optional notes (quantity, brand, priority)
✅ Duplicate handling with note merging
✅ Admin controls for deletion and reset
✅ Summary reports by category and user
✅ User authorization system""",
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
        # Button texts
        'btn_categories': "📋 Categories",
        'btn_add_item': "➕ Add Item", 
        'btn_view_list': "📝 View List",
        'btn_summary': "📊 Summary",
        'btn_my_items': "👤 My Items",
        'btn_help': "❓ Help",
        'btn_reset_list': "🗑️ Reset List",
        'btn_manage_users': "👥 Manage Users",
        'btn_language': "🌐 Language",
        'btn_add': "✅ Add",
        'btn_notes': "📝 Notes",
        'btn_back_categories': "🔙 Back to Categories",
        'btn_main_menu': "🏠 Main Menu",
        'btn_back_menu': "🔙 Back to Menu"
    },
    'he': {
        'welcome': "🛒 ברוכים הבאים לבוט רשימת הקניות המשפחתית!\n\nהבוט עוזר לנהל את רשימת הקניות השבועית עם המשפחה.\n\nהשתמש ב-/help כדי לראות את כל הפקודות.",
        'help': """🛒 פקודות בוט רשימת הקניות המשפחתית

פקודות עיקריות:
/start - התחלת השימוש ברישום
/help - הצגת הודעת עזרה זו
/categories - עיון והוספת פריטים לפי קטגוריה
/add - הוספת פריט מותאם אישית
/list - הצגת רשימת הקניות הנוכחית
/summary - קבלת דוח קניות מעוצב
/myitems - הצגת הפריטים שהוספת

פקודות מנהל:
/reset - 🔴 איפוס רשימה מלא
/users - 👥 ניהול משתמשים והצגת סטטוס
/authorize <user_id> - ✅ אישור משתמש רגיל
/addadmin <user_id> - 👑 קידום משתמש למנהל

פעולות מהירות:
- לחץ על ✅ ליד פריטי הקטגוריות כדי להוסיף אותם
- הוסף הערות כשתתבקש (כמות, מותג, וכו')
- רק מנהלים יכולים למחוק פריטים ולאפס רשימות

תכונות:
✅ קטגוריות מוגדרות מראש לבחירה מהירה
✅ הוספת פריטים מותאמים אישית
✅ הערות אופציונליות (כמות, מותג, עדיפות)
✅ טיפול בכפילויות עם מיזוג הערות
✅ בקרות מנהל למחיקה ואיפוס
✅ דוחות סיכום לפי קטגוריה ומשתמש
✅ מערכת הרשאות משתמשים""",
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
        # Button texts in Hebrew
        'btn_categories': "📋 קטגוריות",
        'btn_add_item': "➕ הוסף פריט", 
        'btn_view_list': "📝 צפה ברשימה",
        'btn_summary': "📊 סיכום",
        'btn_my_items': "👤 הפריטים שלי",
        'btn_help': "❓ עזרה",
        'btn_reset_list': "🗑️ אפס רשימה",
        'btn_manage_users': "👥 נהל משתמשים",
        'btn_language': "🌐 שפה",
        'btn_add': "✅ הוסף",
        'btn_notes': "📝 הערות",
        'btn_back_categories': "🔙 חזרה לקטגוריות",
        'btn_main_menu': "🏠 תפריט ראשי",
        'btn_back_menu': "🔙 חזרה לתפריט"
    }
}
