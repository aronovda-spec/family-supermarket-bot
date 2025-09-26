import logging
import asyncio
import sqlite3
import io
import os
from datetime import datetime
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, ADMIN_IDS, CATEGORIES, MESSAGES, LANGUAGES
from database import Database

# Try to import speech recognition for voice search
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    try:
        import SpeechRecognition as sr
        SPEECH_RECOGNITION_AVAILABLE = True
    except ImportError:
        SPEECH_RECOGNITION_AVAILABLE = False

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShoppingBot:
    def __init__(self):
        self.db = Database()
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()

        # Initialize admin users - DISABLED to prevent overwriting database
        # Admins should be set up manually or via permanent_admin_fix.py
        # for admin_id in ADMIN_IDS:
        #     self.db.add_user(admin_id, username=None, first_name=None, last_name=None, is_admin=True)

    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        return self.db.get_user_language(user_id)

    def get_message(self, user_id: int, key: str, **kwargs) -> str:
        """Get localized message for user"""
        lang = self.get_user_language(user_id)
        message = MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, key))
        if kwargs:
            try:
                return message.format(**kwargs)
            except:
                return message
        return message

    def get_category_name(self, user_id: int, category_key: str) -> str:
        """Get localized category name"""
        lang = self.get_user_language(user_id)
        
        # Check predefined categories first
        category = CATEGORIES.get(category_key, {})
        if category:
            return category.get('name', {}).get(lang, category.get('name', {}).get('en', category_key))
        
        # Check custom categories
        custom_category = self.db.get_custom_category(category_key)
        if custom_category:
            if lang == 'he':
                return custom_category['name_he']
            else:
                return custom_category['name_en']
        
        return category_key

    def get_category_items(self, user_id: int, category_key: str) -> List[str]:
        """Get localized category items (excluding deleted items)"""
        lang = self.get_user_language(user_id)
        
        # Check predefined categories first
        category = CATEGORIES.get(category_key, {})
        if category:
            # Get static items in user's language
            static_items = category.get('items', {}).get(lang, category.get('items', {}).get('en', []))
            
            # Filter out deleted items
            deleted_items = self.db.get_deleted_items_by_category(category_key)
            filtered_items = [item for item in static_items if item not in deleted_items]
            
            # Add dynamic items, checking for duplicates against BOTH static items and already added dynamic items
            dynamic_items = self.db.get_dynamic_category_items(category_key)
            for dynamic_item in dynamic_items:
                dynamic_item_name = dynamic_item.get(lang, dynamic_item.get('en', ''))
                if dynamic_item_name:
                    # Check if item already exists (case-insensitive) in filtered_items
                    item_exists = any(item.lower() == dynamic_item_name.lower() for item in filtered_items)
                    if not item_exists:
                        filtered_items.append(dynamic_item_name)
            
            return sorted(filtered_items)
        
        # For custom categories, return dynamic items only
        dynamic_items = self.db.get_dynamic_category_items(category_key)
        return sorted([item.get(lang, item.get('en', '')) for item in dynamic_items if item.get(lang, item.get('en', ''))])

    def setup_handlers(self):
        """Set up command and callback handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("categories", self.categories_command))
        self.application.add_handler(CommandHandler("add", self.add_item_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("summary", self.summary_command))
        self.application.add_handler(CommandHandler("myitems", self.my_items_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("users", self.users_command))
        self.application.add_handler(CommandHandler("authorize", self.authorize_command))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin_command))
        self.application.add_handler(CommandHandler("removeuser", self.remove_user_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("suggest", self.suggest_item_command))
        self.application.add_handler(CommandHandler("newcategory", self.new_category_command))
        self.application.add_handler(CommandHandler("managecategories", self.manage_categories_command))
        self.application.add_handler(CommandHandler("suggestcategory", self.suggest_category_command))
        self.application.add_handler(CommandHandler("managecategorysuggestions", self.manage_category_suggestions_command))
        self.application.add_handler(CommandHandler("managesuggestions", self.manage_suggestions_command))
        self.application.add_handler(CommandHandler("newitem", self.new_item_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        # Multi-list commands
        self.application.add_handler(CommandHandler("supermarket", self.supermarket_list_command))
        self.application.add_handler(CommandHandler("newlist", self.new_list_command))
        self.application.add_handler(CommandHandler("mylists", self.my_lists_command))
        self.application.add_handler(CommandHandler("managelists", self.manage_lists_command))
        self.application.add_handler(CommandHandler("maintenance", self.maintenance_mode_command))
        self.application.add_handler(CommandHandler("testmaintenance", self.test_maintenance_notification_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Add handler for delete commands (delete_11, delete_25, etc.) - BEFORE general text handler
        self.application.add_handler(MessageHandler(filters.Regex(r'^/delete_\d+$'), self.delete_item_command))
        
        # Message handler for text and voice messages
        self.application.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, self.handle_message))

    async def setup_bot_commands(self):
        """Set up bot commands menu for Telegram command suggestions"""
        from telegram import BotCommand
        
        # Define bot commands with descriptions (English)
        commands = [
            BotCommand("start", "🚀 Start using the bot"),
            BotCommand("menu", "📱 Show main menu"),
            BotCommand("help", "❓ Show help guide"),
            BotCommand("categories", "📋 Browse item categories"),
            BotCommand("add", "➕ Add custom item"),
            BotCommand("list", "📝 View shopping list"),
            BotCommand("summary", "📊 Generate summary report"),
            BotCommand("myitems", "👤 View my added items"),
            BotCommand("search", "🔍 Search for items"),
            BotCommand("language", "🌍 Change language"),
            BotCommand("users", "👥 Manage users (Admin)"),
            BotCommand("authorize", "✅ Authorize user (Admin)"),
            BotCommand("addadmin", "👑 Promote to admin (Admin)"),
            BotCommand("removeuser", "❌ Remove user authorization (Admin)"),
            BotCommand("broadcast", "📢 Send message to all (Admin)"),
            BotCommand("suggest", "💡 Suggest new item"),
            BotCommand("newcategory", "➕ Create new category (Admin)"),
            BotCommand("managecategories", "📂 Manage categories (Admin)"),
            BotCommand("suggestcategory", "💡 Suggest new category"),
            BotCommand("managecategorysuggestions", "💡 Manage category suggestions (Admin)"),
            BotCommand("managesuggestions", "📝 Manage suggestions (Admin)"),
            BotCommand("newitem", "🆕 Add new item to category (Admin)"),
            BotCommand("reset", "🔄 Reset list (Admin)")
        ]
        
        # Define Hebrew commands
        hebrew_commands = [
            BotCommand("start", "🚀 התחל להשתמש בבוט"),
            BotCommand("menu", "📱 הצג תפריט ראשי"),
            BotCommand("help", "❓ הצג מדריך עזרה"),
            BotCommand("categories", "📋 עיין בקטגוריות פריטים"),
            BotCommand("add", "➕ הוסף פריט מותאם אישית"),
            BotCommand("list", "📝 צפה ברשימת קניות"),
            BotCommand("summary", "📊 צור דוח סיכום"),
            BotCommand("myitems", "👤 צפה בפריטים שהוספתי"),
            BotCommand("search", "🔍 חפש פריטים"),
            BotCommand("language", "🌍 שנה שפה"),
            BotCommand("users", "👥 נהל משתמשים (מנהל)"),
            BotCommand("authorize", "✅ אשר משתמש (מנהל)"),
            BotCommand("addadmin", "👑 קדם למנהל (מנהל)"),
            BotCommand("removeuser", "❌ הסר הרשאות משתמש (מנהל)"),
            BotCommand("broadcast", "📢 שלח הודעה לכולם (מנהל)"),
            BotCommand("suggest", "💡 הצע פריט חדש"),
            BotCommand("newcategory", "➕ צור קטגוריה חדשה (מנהל)"),
            BotCommand("managecategories", "📂 נהל קטגוריות (מנהל)"),
            BotCommand("suggestcategory", "💡 הצע קטגוריה חדשה"),
            BotCommand("managecategorysuggestions", "💡 נהל הצעות קטגוריות (מנהל)"),
            BotCommand("managesuggestions", "📝 נהל הצעות (מנהל)"),
            BotCommand("newitem", "🆕 הוסף פריט חדש לקטגוריה (מנהל)"),
            BotCommand("reset", "🔄 אפס רשימה (מנהל)")
        ]
        
        try:
            # Set English commands (default)
            await self.application.bot.set_my_commands(commands)
            
            # Set Hebrew commands for Hebrew language
            await self.application.bot.set_my_commands(hebrew_commands, language_code="he")
            
            logger.info("Bot commands menu set up successfully (English + Hebrew)")
        except Exception as e:
            logger.error(f"Error setting up bot commands: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Clear all waiting states when using /start command
        self.clear_all_waiting_states(context)
        
        # Check if user is already registered
        if not self.db.is_user_authorized(user.id):
            # Auto-register if admin, otherwise require manual approval
            if user.id in ADMIN_IDS:
                self.db.add_user(user.id, user.username, user.first_name, user.last_name, is_admin=True)
                await update.message.reply_text(
                    f"🔑 Welcome Admin {user.first_name}!\n\n" + self.get_message(user.id, 'welcome')
                )
            else:
                # Add user to database but not authorized yet
                self.db.add_user(user.id, user.username, user.first_name, user.last_name, is_admin=False)
                # Update database to mark as unauthorized
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET is_authorized = FALSE WHERE user_id = ?', (user.id,))
                    conn.commit()
                
                await update.message.reply_text(
                    f"👋 Hi {user.first_name}!\n\n"
                    f"🔒 Your access request has been submitted to the family admins.\n\n"
                    f"📧 An admin will authorize you soon, and you'll get a notification when you can start using the bot.\n\n"
                    f"⏳ Please wait for approval..."
                )
                
                # Notify admins about new user request
                await self.notify_admins_new_user(update, context, user)
                return
        else:
            # Update user info - preserve admin status
            existing_user = self.db.get_user_info(user.id)
            is_existing_admin = existing_user['is_admin'] if existing_user else False
            self.db.add_user(user.id, user.username, user.first_name, user.last_name, is_admin=is_existing_admin)
            await update.message.reply_text(self.get_message(user.id, 'welcome'))

        # Show main menu
        await self.show_main_menu(update, context)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - show main menu"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        # Clear all waiting states when using /menu command
        self.clear_all_waiting_states(context)
        await self.show_main_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        # Clear all waiting states when using /help command
        self.clear_all_waiting_states(context)
        help_text = self.get_message(update.effective_user.id, 'help')
        await update.message.reply_text(help_text)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show dynamic main menu with list buttons"""
        user_id = update.effective_user.id
        
        # Check if user is authorized
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return
        
        # Get all active lists
        all_lists = self.db.get_all_lists()
        
        # Create keyboard with list buttons
        keyboard = []
        
        # Add list buttons (max 2 per row)
        list_buttons = []
        for list_info in all_lists:
            list_name = list_info['name']
            if list_info['list_type'] == 'supermarket':
                list_buttons.append(f"🛒 {list_name}")
            else:
                list_buttons.append(f"📋 {list_name}")
        
        # Add list buttons in rows of 2
        for i in range(0, len(list_buttons), 2):
            row = [list_buttons[i]]
            if i + 1 < len(list_buttons):
                row.append(list_buttons[i + 1])
            keyboard.append(row)
        
        # Add action buttons
        keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_new_list'))])
        
        # Add management buttons
        if self.db.is_user_admin(user_id):
            # Get pending count for admin management badge
            total_pending = self.db.get_total_pending_suggestions_count()
            admin_management_text = f"{self.get_message(user_id, 'btn_admin_management')} ({total_pending})"
            keyboard.append([KeyboardButton(admin_management_text)])
            keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_admin')), KeyboardButton(self.get_message(user_id, 'btn_broadcast'))])
        elif self.db.is_user_authorized(user_id):
            keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_user_management'))])
            keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_broadcast'))])
        
        keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_language'))])
        keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_help'))])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        
        main_menu_text = self.get_message(user_id, 'main_menu')
        
        if update.message:
            await update.message.reply_text(main_menu_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(main_menu_text, reply_markup=reply_markup)

    def clear_all_waiting_states(self, context: ContextTypes.DEFAULT_TYPE):
        """Clear all waiting states and temporary data"""
        # Clear all waiting states
        waiting_states = [
            'waiting_for_item', 'waiting_for_note', 'waiting_for_broadcast',
            'waiting_for_suggestion_item', 'waiting_for_suggestion', 'waiting_for_suggestion_translation',
            'waiting_for_new_item', 'waiting_for_add_to_list', 'waiting_for_new_item_translation',
            'waiting_for_search', 'waiting_for_list_name', 'waiting_for_list_description',
            'waiting_for_edit_list_name', 'waiting_for_edit_list_description',
            'waiting_for_voice_search', 'waiting_for_voice_text'
        ]
        
        for state in waiting_states:
            context.user_data.pop(state, None)
        
        # Clear temporary data
        temp_data = [
            'item_info', 'suggestion_item_name', 'suggestion_category', 'new_item_name',
            'new_item_category', 'add_to_list_category', 'target_list_id', 'search_list_id',
            'new_list_name', 'suggestion_from_search'
        ]
        
        for data in temp_data:
            context.user_data.pop(data, None)

    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command - show category selection"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /categories command
        self.clear_all_waiting_states(context)
        await self.show_categories(update, context)

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show categories for selection"""
        user_id = update.effective_user.id
        keyboard = []
        
        # Add SEARCH button first for easy access
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_search'), 
            callback_data="search"
        )])
        
        # Add RECENTLY category second (if there are recent items)
        recent_items = self.db.get_recently_used_items()
        if recent_items:
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'recently_category'), 
                callback_data="category_recently"
            )])
        
        # Add predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}", 
                callback_data=f"category_{category_key}"
            )])
        
        # Add custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category_name}", 
                callback_data=f"category_{category['category_key']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'), 
            callback_data="main_menu"
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = self.get_message(user_id, 'categories_title')
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def show_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show items in a specific category"""
        user_id = update.effective_user.id
        
        # Check if it's a predefined category
        category_data = CATEGORIES.get(category_key)
        if category_data:
            # Handle predefined category
            await self.show_predefined_category_items(update, context, category_key, category_data)
        else:
            # Handle custom category
            await self.show_custom_category_items(update, context, category_key)
    
    async def show_predefined_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, category_data: dict):
        """Show items in a predefined category"""
        user_id = update.effective_user.id
        if not category_data:
            return

        keyboard = []
        category_items = self.get_category_items(user_id, category_key)
        
        # Add multi-select option if there are items
        if category_items:
            keyboard.append([InlineKeyboardButton(
                "🎯 Select Multiple Items", 
                callback_data=f"category_select_{category_key}"
            )])
        
        # Add existing items
        for item in category_items:
            keyboard.append([InlineKeyboardButton(
                f"✅ {item}", 
                callback_data=f"add_item_{category_key}_{item}"
            )])
        
        # Add "ADD NEW ITEM" button if no items exist or always show it
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_add_new_item'),
            callback_data=f"add_new_item_{category_key}"
        )])

        keyboard.append([
            InlineKeyboardButton(self.get_message(user_id, 'btn_back_categories'), callback_data="categories"),
            InlineKeyboardButton(self.get_message(user_id, 'btn_main_menu'), callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        category_name = self.get_category_name(user_id, category_key)
        text = f"{category_data['emoji']} {category_name}\n\nTap ✅ to add items to your shopping list:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_custom_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show items in a custom category"""
        user_id = update.effective_user.id
        
        # Get custom category info
        custom_category = self.db.get_custom_category(category_key)
        if not custom_category:
            await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'category_not_found'))
            return
        
        keyboard = []
        
        # Get dynamic items for this custom category
        category_items = self.get_category_items(user_id, category_key)
        
        # Add multi-select option if there are items
        if category_items:
            keyboard.append([InlineKeyboardButton(
                "🎯 Select Multiple Items", 
                callback_data=f"category_select_{category_key}"
            )])
            
            # Add existing items
            for item in category_items:
                keyboard.append([InlineKeyboardButton(
                    f"✅ {item}", 
                    callback_data=f"add_item_{category_key}_{item}"
                )])
        
        # Custom categories don't have predefined items, so just show the "ADD NEW ITEM" button
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_add_new_item'),
            callback_data=f"add_new_item_{category_key}"
        )])

        keyboard.append([
            InlineKeyboardButton(self.get_message(user_id, 'btn_back_categories'), callback_data="categories"),
            InlineKeyboardButton(self.get_message(user_id, 'btn_main_menu'), callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        category_name = self.get_category_name(user_id, category_key)
        
        if category_items:
            text = f"{custom_category['emoji']} {category_name}\n\nTap ✅ to add items to your shopping list:"
        else:
            text = f"{custom_category['emoji']} {category_name}\n\nThis is a custom category. Tap ➕ to add new items:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def show_recently_used_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recently used items (past 7 days)"""
        user_id = update.effective_user.id
        recent_items = self.db.get_recently_used_items()
        
        if not recent_items:
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_categories'), 
                callback_data="categories"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"{self.get_message(user_id, 'recently_category')}\n\nNo items used in the past 7 days."
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            return
        
        keyboard = []
        
        # Add multi-select option
        keyboard.append([InlineKeyboardButton(
            "🎯 Select Multiple Items", 
            callback_data="recently_select"
        )])
        
        # Add recent items with usage count
        for item in recent_items:
            usage_text = f" ({item['usage_count']}x)" if item['usage_count'] > 1 else ""
            keyboard.append([InlineKeyboardButton(
                f"✅ {item['name']}{usage_text}", 
                callback_data=f"add_item_recently_{item['name']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_categories'), 
            callback_data="categories"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"{self.get_message(user_id, 'recently_category')}\n\n{self.get_message(user_id, 'recently_items_title')}"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def show_add_new_item_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show options for adding a new item"""
        user_id = update.effective_user.id
        category_data = CATEGORIES.get(category_key)
        if not category_data:
            return
        
        category_name = self.get_category_name(user_id, category_key)
        
        keyboard = []
        
        # Option 1: Add to current list only (no approval needed)
        keyboard.append([InlineKeyboardButton(
            "📝 Add to Current List",
            callback_data=f"add_to_list_{category_key}"
        )])
        
        # Option 2: Add permanently to category (requires approval for non-admins)
        if self.db.is_user_admin(user_id):
            keyboard.append([InlineKeyboardButton(
                "➕ Add to Category Permanently",
                callback_data=f"new_item_direct_{category_key}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                "💡 Suggest for Category",
                callback_data=f"suggest_new_{category_key}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "🏠 Back to Category",
            callback_data=f"category_{category_key}"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"➕ **Add New Item to {category_data['emoji']} {category_name}**\n\n"
        message += "**📝 Add to Current List** - Adds item only to your current shopping list (no approval needed)\n\n"
        if self.db.is_user_admin(user_id):
            message += "**➕ Add to Category Permanently** - Adds item to category for future use (admin only)"
        else:
            message += "**💡 Suggest for Category** - Suggests item for permanent addition to category (requires admin approval)"
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_suggestion_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Start the suggestion process for a specific category"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, category_key)
        
        # Store the category for the suggestion
        context.user_data['suggestion_category'] = category_key
        context.user_data['waiting_for_suggestion'] = True
        
        # Set target list_id (default to 1 for supermarket list)
        if 'target_list_id' not in context.user_data:
            context.user_data['target_list_id'] = 1
        
        input_prompt = self.get_message(user_id, 'suggest_item_input').format(category=category_name)
        await update.callback_query.edit_message_text(input_prompt)


    async def start_new_item_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Start the new item process for a specific category (admin only)"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, category_key)
        
        # Store the category for the new item
        context.user_data['new_item_category'] = category_key
        context.user_data['waiting_for_new_item'] = True
        
        message = self.get_message(user_id, 'add_new_item_to_category', category=category_name)
        
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

    async def start_add_to_list_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Start the process to add a new item directly to the current list"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, category_key)
        
        # Store the category for the new item
        context.user_data['add_to_list_category'] = category_key
        context.user_data['waiting_for_add_to_list'] = True
        
        message = self.get_message(user_id, 'add_new_item_to_list', category=category_name)
        
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

    async def process_add_to_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process adding a new item directly to the current list"""
        user_id = update.effective_user.id
        
        if not item_name.strip():
            await update.message.reply_text("❌ Please enter a valid item name.")
            return
        
        # Get the target list and category
        target_list_id = context.user_data.get('target_list_id', 1)  # Default to supermarket list
        category_key = context.user_data.get('add_to_list_category')
        
        if not category_key:
            await update.message.reply_text(self.get_message(user_id, 'error_category_not_found'))
            return
        
        # Add the item directly to the current list
        item_id = self.db.add_item_to_list(
            list_id=target_list_id,
            item_name=item_name.strip(),
            category=category_key,
            notes=None,
            added_by=user_id
        )
        
        if item_id:
            # Get list info for confirmation
            list_info = self.db.get_list_by_id(target_list_id)
            list_name = list_info['name'] if list_info else self.get_message(user_id, 'shopping_list_default')
            
            # Get category name for display
            category_name = self.get_category_name(user_id, category_key)
            
            success_message = f"✅ **Item Added Successfully!**\n\n"
            success_message += f"📝 **Item:** {item_name.strip()}\n"
            success_message += f"📂 **Category:** {category_name}\n"
            success_message += f"📋 **List:** {list_name}\n\n"
            success_message += self.get_message(user_id, 'item_added_to_list')
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            # Notify all users about the new item
            await self.notify_users_item_added(update, context, item_name.strip(), category_name, list_name, user_id)
        else:
            await update.message.reply_text(self.get_message(user_id, 'failed_to_add_item'))
        
        # Clear waiting states
        context.user_data.pop('waiting_for_add_to_list', None)
        context.user_data.pop('add_to_list_category', None)

    async def add_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - prompt for custom item"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /add command
        self.clear_all_waiting_states(context)
        context.user_data['waiting_for_item'] = True
        user_id = update.effective_user.id
        await update.message.reply_text(
            f"✏️ **{self.get_message(user_id, 'btn_add_item')}**\n\n"
            f"{self.get_message(user_id, 'add_custom_item_prompt')}",
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and voice messages"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Debug: Log all message types
        logging.info(f"Message received - Type: {type(update.message)}, Content: {update.message.content_type if hasattr(update.message, 'content_type') else 'unknown'}")
        logging.info(f"Voice: {update.message.voice}, Audio: {update.message.audio}, Text: {update.message.text}")
        logging.info(f"Message ID: {update.message.message_id}, User ID: {update.effective_user.id}")
        logging.info(f"All message attributes: {[attr for attr in dir(update.message) if not attr.startswith('_')]}")
        
        # Handle voice messages for voice search
        if update.message.voice:
            logging.info(f"Voice message received. waiting_for_voice_search: {context.user_data.get('waiting_for_voice_search')}")
            if context.user_data.get('waiting_for_voice_search'):
                await self.process_voice_search(update, context)
                return
            else:
                logging.info("Voice message received but not waiting for voice search")
                await update.message.reply_text("🎤 Voice message received, but I'm not expecting voice input right now.")
                return

        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Handle menu buttons FIRST (to cancel previous operations)
        if (text == self.get_message(user_id, 'btn_supermarket_list') or 
              text == "🛒 Supermarket List" or text == "🛒 רשימת סופר"):
            await self.supermarket_list_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_new_list') or 
              text == "➕ New List" or text == "➕ רשימה חדשה"):
            await self.new_list_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_suggest_category') or 
              text == "💡 Suggest Category" or text == "💡 הצע קטגוריה"):
            await self.suggest_category_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_my_lists') or 
              text == "📋 My Lists" or text == "📋 הרשימות שלי"):
            await self.my_lists_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_manage_lists') or 
              text == "📂 Manage Lists" or text == "📂 נהל רשימות"):
            await self.manage_lists_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_admin_management') or 
              text == "⚙️ Management" or text == "⚙️ ניהול" or
              text.startswith(self.get_message(user_id, 'btn_admin_management') + " (") or
              text.startswith("⚙️ Management (") or text.startswith("⚙️ ניהול (")):
            await self.show_admin_management_menu(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_user_management') or 
              text == "👥 Suggestions" or text == "👥 הצעות"):
            await self.show_user_management_menu(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_language') or 
              text == "🌐 Language" or text == "🌐 שפה"):
            await self.language_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_broadcast') or 
              text == "📢 Broadcast" or text == "📢 שידור"):
            await self.broadcast_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_help') or 
              text == "❓ Help" or text == "❓ עזרה"):
            await self.help_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_search') or 
              text == "🔍🎤 Search" or text == "🔍🎤 חיפוש"):
            await self.search_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_admin') or 
              text == "⚙️ Admin" or text == "⚙️ מנהל"):
            await self.show_admin_menu(update, context)
            return
        
        # Handle dynamic list buttons
        elif text.startswith("🛒 ") or text.startswith("📋 "):
            list_name = text[2:]  # Remove emoji prefix
            await self.show_list_menu(update, context, list_name)
            return
        
        # Handle voice search text input
        if context.user_data.get('waiting_for_voice_text'):
            context.user_data.pop('waiting_for_voice_text', None)
            await self.process_search(update, context, text)
            return
        
        # Handle category creation text input
        if context.user_data.get('creating_category'):
            if context.user_data.get('category_name') is None:
                # User is entering category name
                await self.process_category_name(update, context, text)
                return
            elif context.user_data.get('category_emoji') is None:
                # User is entering custom emoji (not from buttons)
                await self.process_category_emoji(update, context, text)
                return
            elif context.user_data.get('category_hebrew') is None:
                # User is entering Hebrew translation
                await self.process_category_hebrew(update, context, text)
                return
        
        # Handle category suggestion text input
        if context.user_data.get('suggesting_category'):
            if context.user_data.get('suggest_category_name') is None:
                # User is entering category name
                await self.process_suggest_category_name(update, context, text)
                return
            elif context.user_data.get('suggest_category_emoji') is None:
                # User is entering custom emoji (not from buttons)
                await self.process_suggest_category_emoji(update, context, text)
                return
            elif context.user_data.get('suggest_category_hebrew') is None:
                # User is entering Hebrew translation
                await self.process_suggest_category_hebrew(update, context, text)
                return
        
        # Handle main menu buttons - check both English and Hebrew
        if (text == self.get_message(user_id, 'btn_categories') or 
            text == "📋 Categories" or text == "📋 קטגוריות"):
            await self.show_categories(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_add_item') or 
              text == "➕ Add Item" or text == "➕ הוסף פריט"):
            await self.add_item_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_view_list') or 
              text == "📝 View List" or text == "📝 צפה ברשימה"):
            await self.list_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_summary') or 
              text == "📊 Summary" or text == "📊 סיכום"):
            await self.summary_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_my_items') or 
              text == "👤 My Items" or text == "👤 הפריטים שלי"):
            await self.my_items_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_help') or 
              text == "❓ Help" or text == "❓ עזרה"):
            await self.help_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_language') or 
              text == "🌐 Language" or text == "🌐 שפה"):
            await self.language_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_reset_list') or 
              text == "🗑️ Reset List" or text == "🗑️ אפס רשימה"):
            await self.reset_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_manage_users') or 
              text == "👥 Manage Users" or text == "👥 נהל משתמשים"):
            await self.users_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_broadcast') or 
              text == "📢 Broadcast" or text == "📢 שידור"):
            await self.broadcast_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_suggest_item') or 
              text == "💡 Suggest Item" or text == "💡 הצע פריט"):
            await self.suggest_item_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_new_item') or 
              text == "➕ New Item" or text == "➕ פריט חדש"):
            await self.new_item_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_search') or 
              text == "🔍🎤 Search" or text == "🔍🎤 חיפוש"):
            await self.search_command(update, context)
            return
        elif text == self.get_message(user_id, 'btn_help'):
            await self.help_command(update, context)
            return

        # Handle custom item addition
        if context.user_data.get('waiting_for_item'):
            await self.process_custom_item(update, context, text)
            return
        
        # Handle note addition
        if context.user_data.get('waiting_for_note'):
            item_info = context.user_data.get('item_info')
            if item_info:
                await self.process_item_with_note(update, context, item_info, text)
            return
        
        # Handle broadcast message
        if context.user_data.get('waiting_for_broadcast'):
            await self.process_broadcast_message(update, context, text)
            return
        
        # Handle suggestion input
        if context.user_data.get('waiting_for_suggestion_item'):
            await self.process_suggestion_item(update, context, text)
            return
        
        # Handle suggestion input (from category)
        if context.user_data.get('waiting_for_suggestion'):
            await self.process_suggestion_item(update, context, text)
            return
        
        # Handle suggestion translation
        if context.user_data.get('waiting_for_suggestion_translation'):
            await self.process_suggestion_translation(update, context, text)
            return
        
        # Handle new item input (admin only)
        if context.user_data.get('waiting_for_new_item'):
            await self.process_new_item(update, context, text)
            return
        
        # Handle add to list input
        if context.user_data.get('waiting_for_add_to_list'):
            await self.process_add_to_list(update, context, text)
            return
        
        # Handle new item translation (admin only)
        if context.user_data.get('waiting_for_new_item_translation'):
            await self.process_new_item_translation(update, context, text)
            return
        
        # Handle search input (after all button commands)
        if context.user_data.get('waiting_for_search'):
            await self.process_search(update, context, text)
            return
        
        # Handle multi-list input states
        if context.user_data.get('waiting_for_list_name'):
            await self.process_list_name(update, context, text)
            return
        
        if context.user_data.get('waiting_for_list_description'):
            await self.process_list_description(update, context, text)
            return
        
        if context.user_data.get('waiting_for_edit_list_name'):
            await self.process_edit_list_name(update, context, text)
            return
        
        if context.user_data.get('waiting_for_edit_list_description'):
            await self.process_edit_list_description(update, context, text)
            return
        
        # Handle item rename
        if context.user_data.get('renaming_item'):
            await self.process_item_rename(update, context, text)
            return
        
        # Handle category rename
        if context.user_data.get('renaming_category'):
            await self.process_category_rename(update, context, text)
            return
        
        # Handle template creation
        if context.user_data.get('creating_template') or context.user_data.get('creating_system_template'):
            await self.process_template_creation(update, context, text)
            return

    async def process_custom_item_from_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process custom item addition from search results - show ADD/NOTES/BACK TO CATEGORIES options directly"""
        # Ask for optional note
        context.user_data['waiting_for_note'] = True
        context.user_data['item_info'] = {
            'name': item_name,
            'category': 'custom',
            'user_id': update.effective_user.id,
            'list_id': 1  # Default to supermarket list
        }
        
        user_id = update.effective_user.id
        keyboard = [
            [
                InlineKeyboardButton(self.get_message(user_id, 'btn_add'), callback_data="skip_note"),
                InlineKeyboardButton(self.get_message(user_id, 'btn_notes'), callback_data="add_note")
            ],
            [
                InlineKeyboardButton(self.get_message(user_id, 'btn_back_categories'), callback_data="categories")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        adding_text = self.get_message(user_id, 'adding_item', item=item_name)
        prompt_text = self.get_message(user_id, 'add_notes_prompt')

        await update.callback_query.edit_message_text(
            f"{adding_text}\n\n{prompt_text}",
            reply_markup=reply_markup
        )

    async def process_custom_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process custom item addition"""
        context.user_data['waiting_for_item'] = False
        
        # Ask for optional note
        context.user_data['waiting_for_note'] = True
        context.user_data['item_info'] = {
            'name': item_name,
            'category': 'custom',
            'user_id': update.effective_user.id,
            'list_id': 1  # Default to supermarket list
        }
        
        user_id = update.effective_user.id
        keyboard = [
            [
                InlineKeyboardButton(self.get_message(user_id, 'btn_add'), callback_data="skip_note"),
                InlineKeyboardButton(self.get_message(user_id, 'btn_notes'), callback_data="add_note")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        adding_text = self.get_message(user_id, 'adding_item', item=item_name)
        prompt_text = self.get_message(user_id, 'add_notes_prompt')

        await update.message.reply_text(
            f"{adding_text}\n\n{prompt_text}",
            reply_markup=reply_markup
        )

    async def process_item_with_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_info: Dict, note: str = None):
        """Process item addition with optional note"""
        context.user_data['waiting_for_note'] = False
        context.user_data.pop('item_info', None)
        # Clear search context if this was from a search
        context.user_data.pop('current_search_query', None)
        
        # Get the target list ID
        list_id = item_info.get('list_id', 1)  # Default to supermarket list
        
        if list_id == 1:
            # Use the original method for supermarket list
            item_id = self.db.add_item(
                item_name=item_info['name'],
                category=item_info['category'],
                notes=note,
                added_by=item_info['user_id']
            )
        else:
            # Use the new method for custom lists
            item_id = self.db.add_item_to_list(
                list_id=list_id,
                item_name=item_info['name'],
                category=item_info['category'],
                notes=note,
                added_by=item_info['user_id']
            )
        
        user_id = item_info['user_id']
        if item_id:
            note_text = f"\n📝 Note: {note}" if note else ""
            success_message = self.get_message(user_id, 'item_added', item=item_info['name'], note=note_text)
            
            # Create keyboard with BACK TO CATEGORIES button for quick continuation
            # If category is 'custom' (from search), go to main categories menu
            if item_info['category'] == 'custom':
                callback_data = "categories"
            else:
                callback_data = f"category_{item_info['category']}"
            
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_categories'), 
                callback_data=callback_data
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Check if it's from callback query (Add button) or text message (typed note)
            if update.callback_query:
                await update.callback_query.edit_message_text(success_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text(success_message, reply_markup=reply_markup)
            
            # Notify other users
            await self.notify_users_item_added(update, context, item_info['name'], note)
        else:
            error_message = self.get_message(user_id, 'error_adding')
            if update.callback_query:
                await update.callback_query.edit_message_text(error_message)
            else:
                await update.message.reply_text(error_message)

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show current shopping list"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /list command
        self.clear_all_waiting_states(context)
        items = self.db.get_shopping_list()
        
        if not items:
            await update.message.reply_text(self.get_message(update.effective_user.id, 'list_empty'))
            return

        # Group items by category
        categorized_items = {}
        for item in items:
            category = item['category'] or 'Other'
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)

        # Build message
        message_parts = ["🛒 Current Shopping List:\n"]
        
        user_id = update.effective_user.id
        for category, category_items in categorized_items.items():
            # Get category emoji and localized name
            category_emoji = "📦"
            category_display_name = category
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category:
                    category_emoji = cat_data['emoji']
                    category_display_name = self.get_category_name(user_id, cat_key)
                    break
            
            message_parts.append(f"\n{category_emoji} {category_display_name}:")
            
            for item in category_items:
                item_text = f"• {item['name']}"
                
                # Add notes
                all_notes = []
                if item['notes']:
                    all_notes.append(item['notes'])
                for note_info in item['item_notes']:
                    all_notes.append(f"{note_info['note']} ({note_info['user_name']})")
                
                if all_notes:
                    item_text += f"\n  📝 {' | '.join(all_notes)}"
                
                # Add who added it
                item_text += f"\n  👤 Added by: {item['added_by_name']}"
                
                # Add delete button for admins
                if self.db.is_user_admin(update.effective_user.id):
                    item_text += f"\n  🗑️ /delete_{item['id']}"
                
                message_parts.append(item_text)

        message_parts.append(f"\n📊 Total items: {len(items)}")
        
        full_message = "\n".join(message_parts)
        
        # Split message if too long
        if len(full_message) > 4000:
            # Send in chunks
            current_chunk = "🛒 Current Shopping List:\n"
            for part in message_parts[1:]:
                if len(current_chunk + part) > 4000:
                    await update.message.reply_text(current_chunk)
                    current_chunk = part
                else:
                    current_chunk += "\n" + part
            
            if current_chunk:
                await update.message.reply_text(current_chunk)
        else:
            await update.message.reply_text(full_message)

    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command - generate formatted shopping report"""
        if not self.db.is_user_authorized(update.effective_user.id):
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /summary command
        self.clear_all_waiting_states(context)
        items = self.db.get_shopping_list()
        
        if not items:
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'list_empty'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'list_empty'))
            return

        # Group items by category
        categorized_items = {}
        for item in items:
            category = item['category'] or 'Other'
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)

        # Build clean summary
        summary_parts = [
            self.get_message(user_id, 'shopping_summary_report'),
            f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"📋 Total Items: {len(items)}",
            "─" * 30
        ]
        
        user_id = update.effective_user.id
        for category, category_items in categorized_items.items():
            # Get category emoji and localized name
            category_emoji = "📦"
            category_display_name = category
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category:
                    category_emoji = cat_data['emoji']
                    category_display_name = self.get_category_name(user_id, cat_key)
                    break
            
            summary_parts.append(f"\n{category_emoji} {category_display_name.upper()} ({len(category_items)} items)")
            
            for i, item in enumerate(category_items, 1):
                item_line = f"{i:2d}. {item['name']}"
                
                # Add consolidated notes
                all_notes = []
                if item['notes']:
                    all_notes.append(item['notes'])
                for note_info in item['item_notes']:
                    all_notes.append(note_info['note'])
                
                if all_notes:
                    item_line += f" ({' | '.join(all_notes)})"
                
                summary_parts.append(f"    {item_line}")

        summary_parts.append("\n" + "─" * 30)
        summary_parts.append("🛒 Happy Shopping! 🛒")
        
        full_summary = "\n".join(summary_parts)
        
        # Send summary
        if len(full_summary) > 4000:
            # Send in chunks
            current_chunk = ""
            for part in summary_parts:
                if len(current_chunk + part) > 4000:
                    await update.message.reply_text(current_chunk)
                    current_chunk = part
                else:
                    current_chunk += "\n" + part if current_chunk else part
            
            if current_chunk:
                if update.message:
                    await update.message.reply_text(current_chunk)
                elif update.callback_query:
                    await update.callback_query.edit_message_text(current_chunk)
        else:
            if update.message:
                await update.message.reply_text(full_summary)
            elif update.callback_query:
                # Add back button for callback queries
                keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data="list_menu_1")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(full_summary, reply_markup=reply_markup)

    async def my_items_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int = None):
        """Handle /myitems command - show items added by current user"""
        if not self.db.is_user_authorized(update.effective_user.id):
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /myitems command
        self.clear_all_waiting_states(context)
        # If list_id is provided, get items for that specific list, otherwise get all items
        if list_id:
            user_items = self.db.get_items_by_user_in_list(update.effective_user.id, list_id)
        else:
            user_items = self.db.get_items_by_user(update.effective_user.id)
        
        if not user_items:
            if update.message:
                await update.message.reply_text(
                    self.get_message(update.effective_user.id, 'my_items_empty')
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    self.get_message(update.effective_user.id, 'my_items_empty')
                )
            return

        # Group by category
        categorized_items = {}
        for item in user_items:
            category = item['category'] or 'Other'
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)

        # Build message
        message_parts = [f"👤 Your Items ({len(user_items)} total):\n"]
        
        user_id = update.effective_user.id
        for category, category_items in categorized_items.items():
            # Get category emoji and localized name
            category_emoji = "📦"
            category_display_name = category
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category:
                    category_emoji = cat_data['emoji']
                    category_display_name = self.get_category_name(user_id, cat_key)
                    break
            
            message_parts.append(f"\n{category_emoji} {category_display_name}:")
            
            for item in category_items:
                item_text = f"• {item['name']}"
                
                # Add notes
                all_notes = []
                if item['notes']:
                    all_notes.append(item['notes'])
                for note_info in item['item_notes']:
                    all_notes.append(f"{note_info['note']} ({note_info['user_name']})")
                
                if all_notes:
                    item_text += f"\n  📝 {' | '.join(all_notes)}"
                
                message_parts.append(item_text)

        full_message = "\n".join(message_parts)
        
        # Add back button if called from callback
        if update.callback_query:
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data="list_menu_1")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(full_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(full_message)

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command - reset shopping list (admin only)"""
        user_id = update.effective_user.id
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        # Confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Reset List", callback_data="confirm_reset"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🗑️ **Reset Shopping List**\n\n"
            f"⚠️ This will permanently delete ALL items from the shopping list.\n\n"
            f"{self.get_message(user_id, 'are_you_sure_continue')}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        if not self.db.is_user_authorized(update.effective_user.id):
            await query.edit_message_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        data = query.data

        if data == "main_menu":
            # Clear all waiting states when going back to main menu
            self.clear_all_waiting_states(context)
            await query.delete_message()
            await self.show_main_menu(update, context)
        
        elif data.startswith("my_items_"):
            list_id = int(data.replace("my_items_", ""))
            await self.my_items_command(update, context, list_id)
        
        elif data == "my_summary":
            await self.summary_command(update, context)
        
        elif data == "manage_users":
            await self.users_command(update, context)
        
        elif data == "categories":
            # Clear waiting states when going back to categories
            self.clear_all_waiting_states(context)
            await self.show_categories(update, context)
        
        elif data == "search":
            # Clear waiting states when starting search
            self.clear_all_waiting_states(context)
            await self.search_command(update, context)
        
        # Category creation callbacks
        elif data == "cancel_category_creation":
            await self.cancel_category_creation(update, context)
        
        elif data.startswith("emoji_"):
            emoji = data.replace("emoji_", "")
            await self.process_category_emoji(update, context, emoji)
        
        elif data == "skip_hebrew_translation":
            await self.create_custom_category(update, context)
        
        elif data.startswith("view_category_"):
            category_key = data.replace("view_category_", "")
            await self.show_category_details(update, context, category_key)
        
        elif data.startswith("delete_category_"):
            category_key = data.replace("delete_category_", "")
            await self.confirm_delete_category(update, context, category_key)
        
        elif data.startswith("confirm_delete_category_"):
            category_key = data.replace("confirm_delete_category_", "")
            await self.delete_custom_category(update, context, category_key)
        
        elif data == "new_category":
            # Show immediate feedback
            await query.answer("📂 Starting new category creation...")
            await self.start_category_creation(update, context)
        
        elif data == "new_category_admin":
            # Show immediate feedback
            await query.answer("📂 Starting new category creation...")
            await self.start_category_creation(update, context)
        
        elif data == "manage_categories":
            # Show immediate feedback
            await query.answer("🗂️ Loading category management options...")
            await self.show_manage_categories(update, context, back_to="admin_management")
        
        elif data == "new_item_admin":
            # Show immediate feedback
            await query.answer("➕ Starting new item creation process...")
            await self.show_categories_for_new_item(update, context)
        
        elif data == "manage_items_admin":
            # Show immediate feedback
            await query.answer("📝 Loading item management options...")
            await self.show_manage_items_admin(update, context)
        
        elif data == "rename_items_admin":
            # Show immediate feedback
            await query.answer("✏️ Loading item rename options...")
            await self.show_rename_items_admin(update, context)
        
        elif data == "rename_categories_admin":
            # Show immediate feedback
            await query.answer("✏️ Loading category rename options...")
            await self.show_rename_categories_admin(update, context)
        
        
        
        elif data == "suggest_item_user":
            # Show immediate feedback
            await query.answer("💡 Starting item suggestion process...")
            await self.show_categories_for_suggestion(update, context)
        
        elif data == "suggest_category_user":
            # Show immediate feedback
            await query.answer("📂 Starting category suggestion process...")
            await self.suggest_category_command(update, context)
        
        elif data == "admin_management":
            # Clear all waiting states when opening admin management
            self.clear_all_waiting_states(context)
            await self.show_admin_management_menu(update, context)
        
        elif data == "user_management":
            await self.show_user_management_menu(update, context)
        
        elif data == "manage_category_suggestions":
            # Show immediate feedback
            await query.answer("💭 Loading category suggestions for review...")
            await self.show_manage_category_suggestions(update, context)
        
        elif data == "manage_suggestions":
            # Show immediate feedback
            await query.answer("💡 Loading item suggestions for review...")
            await self.manage_suggestions_command(update, context)
        
        # Category suggestion callbacks
        elif data == "cancel_category_suggestion":
            await self.cancel_category_suggestion(update, context)
        
        elif data.startswith("suggest_emoji_"):
            emoji = data.replace("suggest_emoji_", "")
            await self.process_suggest_category_emoji(update, context, emoji)
        
        elif data == "skip_suggest_hebrew_translation":
            await self.submit_category_suggestion(update, context)
        
        elif data.startswith("review_category_suggestion_"):
            suggestion_id = int(data.replace("review_category_suggestion_", ""))
            await self.show_category_suggestion_review(update, context, suggestion_id)
        
        elif data.startswith("approve_category_suggestion_"):
            suggestion_id = int(data.replace("approve_category_suggestion_", ""))
            await self.approve_category_suggestion(update, context, suggestion_id)
        
        elif data.startswith("reject_category_suggestion_"):
            suggestion_id = int(data.replace("reject_category_suggestion_", ""))
            await self.reject_category_suggestion(update, context, suggestion_id)
        
        # Category multi-select callback handlers (MUST come before generic category_ handler)
        elif data.startswith("category_select_"):
            category_key = data.replace("category_select_", "")
            logging.info(f"Category select callback - data: '{data}', category_key: '{category_key}'")
            logging.info(f"About to call show_category_item_selection with category_key: '{category_key}'")
            await self.show_category_item_selection(update, context, category_key)
        
        elif data.startswith("category_toggle_"):
            parts = data.replace("category_toggle_", "").split("_")
            category_key = parts[0]
            item_index = int(parts[1])
            await self.toggle_category_item_selection(update, context, category_key, item_index)
        
        elif data.startswith("category_add_selected_"):
            category_key = data.replace("category_add_selected_", "")
            await self.add_selected_category_items(update, context, category_key)
        
        elif data.startswith("category_"):
            category_key = data.replace("category_", "")
            if category_key == "recently":
                await self.show_recently_used_items(update, context)
            else:
                await self.show_category_items(update, context, category_key)
        
        elif data.startswith("add_item_"):
            # Parse: add_item_categorykey_itemname
            # We need to be careful with category keys that contain underscores
            remaining = data.replace("add_item_", "")
            
            # Check for recently used items first
            if remaining.startswith("recently_"):
                item_name = remaining[9:]  # Remove "recently_" prefix
                # Get the original category for this item
                recent_items = self.db.get_recently_used_items()
                category_key = None
                for item in recent_items:
                    if item['name'] == item_name:
                        category_key = item['category']
                        break
                
                if category_key:
                    await self.process_category_item_selection(update, context, category_key, item_name)
                return
            
            # Find the category key by checking against known categories
            category_key = None
            item_name = None
            
            for cat_key in CATEGORIES.keys():
                if remaining.startswith(cat_key + "_"):
                    category_key = cat_key
                    item_name = remaining[len(cat_key) + 1:]  # +1 for the underscore
                    break
            
            if category_key and item_name:
                await self.process_category_item_selection(update, context, category_key, item_name)
        
        elif data.startswith("restore_item_"):
            # Handle "Restore Original Item" from restoration options
            parts = data.replace("restore_item_", "").split("_", 1)
            if len(parts) == 2:
                category_key, item_name = parts
                await self.handle_restore_item(update, context, category_key, item_name)
        
        elif data.startswith("add_new_item_"):
            # Handle "Add as New Item" from restoration options OR "ADD NEW ITEM" from category
            if "_" in data.replace("add_new_item_", ""):  # This has category_key_item_name format (restoration)
                parts = data.replace("add_new_item_", "").split("_", 1)
                if len(parts) == 2:
                    category_key, item_name = parts
                    await self.handle_add_as_new_item(update, context, category_key, item_name)
            else:
                # Handle "ADD NEW ITEM" button from category (original flow)
                category_key = data.replace("add_new_item_", "")
                await self.show_add_new_item_options(update, context, category_key)
        
        elif data == "add_to_list_from_search":
            # Handle "Add to List" from search results - use search query directly
            user_id = update.effective_user.id
            search_query = context.user_data.get('current_search_query', '')
            
            if not search_query:
                await update.callback_query.edit_message_text(
                    self.get_message(user_id, 'error_search_query_not_found'),
                    parse_mode='Markdown'
                )
                return
            
            # Go directly to ADD/NOTES/BACK TO CATEGORIES options
            await self.process_custom_item_from_search(update, context, search_query)
        
        elif data == "suggest_from_search":
            # Handle "Suggest for Category" from search results - show category selection
            await self.show_suggestion_categories(update, context)
        
        elif data == "search_again":
            # Handle "Search Again" button
            await self.show_search_prompt(update, context)
        
        elif data == "text_search":
            # Handle text search option
            context.user_data['waiting_for_search'] = True
            user_id = update.effective_user.id
            prompt_text = self.get_message(user_id, 'search_prompt')
            await update.callback_query.edit_message_text(prompt_text)
        
        elif data == "voice_search":
            # Handle voice search option
            try:
                await self.show_voice_search_prompt(update, context)
            except Exception as e:
                logging.error(f"Error in voice search: {e}")
                user_id = update.effective_user.id
                await update.callback_query.edit_message_text(self.get_message(user_id, 'error_opening_voice_search'))
        
        elif data.startswith("text_search_list_"):
            # Handle text search for specific list
            list_id = int(data.replace("text_search_list_", ""))
            context.user_data['waiting_for_search'] = True
            context.user_data['search_list_id'] = list_id
            user_id = update.effective_user.id
            list_info = self.db.get_list_by_id(list_id)
            list_name = list_info['name'] if list_info else f"List {list_id}"
            prompt_text = self.get_message(user_id, 'search_prompt')
            await update.callback_query.edit_message_text(
                f"🔍 **Search in {list_name}**\n\n{prompt_text}"
            )
        
        elif data.startswith("voice_search_list_"):
            # Handle voice search for specific list
            list_id = int(data.replace("voice_search_list_", ""))
            context.user_data['search_list_id'] = list_id
            await self.show_voice_search_prompt(update, context)
        
        elif data == "start_voice_recording":
            # Handle voice recording start
            await self.start_voice_recording(update, context)
        
        elif data == "stop_voice_recording":
            # Handle stop voice recording
            context.user_data.pop('waiting_for_voice_search', None)
            await self.show_voice_search_prompt(update, context)
        
        elif data.startswith("add_to_list_"):
            # Handle "Add to Current List" button
            category_key = data.replace("add_to_list_", "")
            await self.start_add_to_list_process(update, context, category_key)
        
        elif data == "skip_note":
            item_info = context.user_data.get('item_info')
            if item_info:
                await self.process_item_with_note(update, context, item_info)
        
        elif data == "add_note":
            item_info = context.user_data.get('item_info')
            if item_info:
                context.user_data['waiting_for_note'] = True
                user_id = update.effective_user.id
                input_text = self.get_message(user_id, 'add_notes_input', item=item_info['name'])
                await query.edit_message_text(input_text)
        
        elif data == "confirm_reset":
            await self.confirm_reset(update, context)
        
        elif data == "cancel_reset":
            await query.edit_message_text("❌ Reset cancelled.")
        
        elif data.startswith("set_language_"):
            language = data.replace("set_language_", "")
            user_id = update.effective_user.id
            
            if self.db.set_user_language(user_id, language):
                success_text = self.get_message(user_id, 'language_selected')
                await query.edit_message_text(success_text)
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text(self.get_message(user_id, 'error_changing_language'))
        
        elif data.startswith("suggest_category_"):
            category_key = data.replace("suggest_category_", "")
            user_id = update.effective_user.id
            
            # Store category and start suggestion process
            context.user_data['suggestion_category'] = category_key
            context.user_data['waiting_for_suggestion_item'] = True
            
            category_name = self.get_category_name(user_id, category_key)
            input_prompt = self.get_message(user_id, 'suggest_item_input').format(category=category_name)
            await query.edit_message_text(input_prompt)
        
        elif data.startswith("approve_suggestion_"):
            suggestion_id = int(data.replace("approve_suggestion_", ""))
            user_id = update.effective_user.id
            
            if self.db.approve_suggestion(suggestion_id, user_id):
                suggestion = self.db.get_suggestion_by_id(suggestion_id)
                if suggestion:
                    # Notify the user who suggested the item
                    await self.notify_suggestion_result(update, context, suggestion, 'approved')
                    # Notify all authorized users and admins about the approval
                    await self.notify_all_users_item_approved(suggestion, user_id)
                
                await query.edit_message_text("✅ Suggestion approved!")
                await self.show_admin_management_menu(update, context)
                # Also update the main menu to refresh the badge
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text(self.get_message(user_id, 'error_approving_suggestion'))
        
        elif data.startswith("reject_suggestion_"):
            suggestion_id = int(data.replace("reject_suggestion_", ""))
            user_id = update.effective_user.id
            
            if self.db.reject_suggestion(suggestion_id, user_id):
                suggestion = self.db.get_suggestion_by_id(suggestion_id)
                if suggestion:
                    # Notify the user who suggested the item
                    await self.notify_suggestion_result(update, context, suggestion, 'rejected')
                
                await query.edit_message_text("❌ Suggestion rejected.")
                await self.show_admin_management_menu(update, context)
                # Also update the main menu to refresh the badge
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ Error rejecting suggestion.")
        
        elif data.startswith("next_suggestion_"):
            current_index = int(data.replace("next_suggestion_", ""))
            suggestions = self.db.get_pending_suggestions()
            
            if current_index < len(suggestions):
                await self.show_suggestion_review(update, context, suggestions[current_index], current_index, len(suggestions))
            else:
                await query.edit_message_text("✅ No more suggestions to review.")
                await self.show_main_menu(update, context)
        
        elif data.startswith("next_suggestion_list_"):
            # Parse: next_suggestion_list_listid_index
            parts = data.replace("next_suggestion_list_", "").split("_")
            if len(parts) == 2:
                list_id = int(parts[0])
                current_index = int(parts[1])
                suggestions = self.db.get_pending_suggestions(list_id)
                
                if current_index < len(suggestions):
                    await self.show_suggestion_review_for_list(update, context, suggestions[current_index], current_index, len(suggestions), list_id)
                else:
                    await query.edit_message_text("✅ No more suggestions to review.")
                    await self.show_list_menu(update, context, f"list_menu_{list_id}")
        
        elif data.startswith("new_item_category_"):
            category_key = data.replace("new_item_category_", "")
            user_id = update.effective_user.id
            
            # Store category and start new item process
            context.user_data['new_item_category'] = category_key
            context.user_data['waiting_for_new_item'] = True
            
            category_name = self.get_category_name(user_id, category_key)
            input_prompt = f"{self.get_message(user_id, 'add_new_item_admin_title')}\n\nCategory: {category_name}\n\n{self.get_message(user_id, 'add_new_item_prompt')}\n\n{self.get_message(user_id, 'add_new_item_tips')}\n\n{self.get_message(user_id, 'type_item_name')}"
            await query.edit_message_text(input_prompt)
        
        elif data.startswith("search_add_list_"):
            # Add existing item to specific list
            import urllib.parse
            parts = data.replace("search_add_list_", "").split("_", 2)
            if len(parts) == 3:
                list_id = int(parts[0])
                category_key = parts[1]
                item_name = urllib.parse.unquote(parts[2])
                # Set target list and process item selection
                context.user_data['target_list_id'] = list_id
                await self.process_category_item_selection(update, context, category_key, item_name)
            else:
                await query.edit_message_text("❌ Error processing search result.")
        
        elif data.startswith("search_add_"):
            # Add existing item to shopping list (general search)
            import urllib.parse
            parts = data.replace("search_add_", "").split("_", 1)
            if len(parts) == 2:
                category_key = parts[0]
                item_name = urllib.parse.unquote(parts[1])
                await self.process_category_item_selection(update, context, category_key, item_name)
            else:
                await query.edit_message_text("❌ Error processing search result.")
        
        elif data.startswith("search_select_list_"):
            # Show selected item with action buttons (list-specific)
            import urllib.parse
            parts = data.replace("search_select_list_", "").split("_", 2)
            if len(parts) == 3:
                list_id = int(parts[0])
                category_key = parts[1]
                item_name = urllib.parse.unquote(parts[2])
                
                # Get item details
                category_data = CATEGORIES.get(category_key, {})
                category_name = self.get_category_name(user_id, category_key)
                
                # Find the item
                items_en = category_data.get('items', {}).get('en', [])
                items_he = category_data.get('items', {}).get('he', [])
                
                try:
                    item_index = items_en.index(item_name)
                    hebrew_name = items_he[item_index] if item_index < len(items_he) else item_name
                except ValueError:
                    hebrew_name = item_name
                
                message = self.get_message(user_id, 'search_item_found').format(
                    item_name=item_name,
                    category=f"{category_data.get('emoji', '📦')} {category_name}",
                    hebrew_name=hebrew_name
                )
                
                import urllib.parse
                keyboard = [
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_add_to_the_list'),
                        callback_data=f"search_add_list_{list_id}_{category_key}_{urllib.parse.quote(item_name)}"
                    )],
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_back_to_list'),
                        callback_data=f"list_menu_{list_id}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Error processing search selection.")
        
        elif data.startswith("search_select_"):
            # Show selected item with action buttons (general search)
            import urllib.parse
            parts = data.replace("search_select_", "").split("_", 1)
            if len(parts) == 2:
                category_key = parts[0]
                item_name = urllib.parse.unquote(parts[1])
                
                # Get item details
                category_data = CATEGORIES.get(category_key, {})
                category_name = self.get_category_name(user_id, category_key)
                
                # Find the item
                items_en = category_data.get('items', {}).get('en', [])
                items_he = category_data.get('items', {}).get('he', [])
                
                try:
                    item_index = items_en.index(item_name)
                    hebrew_name = items_he[item_index] if item_index < len(items_he) else item_name
                except ValueError:
                    hebrew_name = item_name
                
                message = self.get_message(user_id, 'search_item_found').format(
                    item_name=item_name,
                    category=f"{category_data.get('emoji', '📦')} {category_name}",
                    hebrew_name=hebrew_name
                )
                
                import urllib.parse
                keyboard = [
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_add_to_the_list'),
                        callback_data=f"search_add_{category_key}_{urllib.parse.quote(item_name)}"
                    )],
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_back_menu'),
                        callback_data="main_menu"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Error processing search selection.")
        
        elif data.startswith("search_suggest_"):
            # Start suggestion process for category
            category_key = data.replace("search_suggest_", "")
            context.user_data['suggestion_category'] = category_key
            context.user_data['waiting_for_suggestion_item'] = True
            
            category_name = self.get_category_name(user_id, category_key)
            input_prompt = self.get_message(user_id, 'suggest_item_input').format(category=category_name)
            await query.edit_message_text(input_prompt)
        
        elif data == "search_suggest_new":
            # Show category selection for new suggestion
            await self.show_suggestion_categories(update, context)
        
        elif data.startswith("suggest_new_"):
            # Handle suggest new item from specific category
            category_key = data.replace("suggest_new_", "")
            await self.start_suggestion_process(update, context, category_key)
        
        elif data.startswith("new_item_direct_"):
            # Handle direct add new item from specific category (admin)
            category_key = data.replace("new_item_direct_", "")
            await self.start_new_item_process(update, context, category_key)
        
        elif data == "new_item_direct":
            # Show category selection for new item (admin)
            await self.show_new_item_categories(update, context)
        
        # Multi-list callback handlers
        elif data == "supermarket_list":
            # Clear all waiting states when opening supermarket menu
            self.clear_all_waiting_states(context)
            await self.show_supermarket_list(update, context)
        
        elif data == "new_list":
            # Clear all waiting states when creating new list
            self.clear_all_waiting_states(context)
            await self.show_create_list_prompt(update, context)
        
        elif data == "my_lists":
            # Clear waiting states when going back to lists
            self.clear_all_waiting_states(context)
            await self.show_my_lists(update, context)
        
        elif data == "manage_lists":
            await self.show_manage_lists(update, context)
        
        elif data.startswith("manage_suggestions_"):
            list_id = int(data.replace("manage_suggestions_", ""))
            # Show immediate feedback
            await query.answer("💡 Loading suggestions for review...")
            await self.show_manage_suggestions_for_list(update, context, list_id)
        
        elif data.startswith("manage_item_suggestions_"):
            list_id = int(data.replace("manage_item_suggestions_", ""))
            await self.show_item_suggestions_for_list(update, context, list_id)
        
        elif data.startswith("list_actions_"):
            list_id = int(data.replace("list_actions_", ""))
            await self.show_list_actions(update, context, list_id)
        
        elif data.startswith("edit_list_name_"):
            list_id = int(data.replace("edit_list_name_", ""))
            await self.show_edit_list_name(update, context, list_id)
        
        elif data.startswith("edit_list_description_"):
            list_id = int(data.replace("edit_list_description_", ""))
            await self.show_edit_list_description(update, context, list_id)
        
        elif data.startswith("list_statistics_"):
            list_id = int(data.replace("list_statistics_", ""))
            await self.show_list_statistics(update, context, list_id)
        
        elif data.startswith("confirm_delete_list_"):
            list_id = int(data.replace("confirm_delete_list_", ""))
            await self.confirm_delete_list(update, context, list_id)
        
        
        elif data == "delete_permanent_items":
            await self.show_delete_permanent_items_menu(update, context)
        
        elif data.startswith("delete_permanent_items_"):
            category_key = data.replace("delete_permanent_items_", "")
            await self.show_permanent_items_in_category(update, context, category_key)
        
        elif data.startswith("confirm_delete_permanent_item_"):
            # Format: confirm_delete_permanent_item_{category_key}_{item_name}
            parts = data.replace("confirm_delete_permanent_item_", "").split("_", 1)
            if len(parts) == 2:
                category_key = parts[0]
                item_name = parts[1]
                await self.confirm_delete_permanent_item(update, context, category_key, item_name)
        
        elif data.startswith("rename_items_category_"):
            category_key = data.replace("rename_items_category_", "")
            await self.show_items_to_rename(update, context, category_key)
        
        elif data.startswith("rename_item_"):
            # Format: rename_item_{category_key}_{item_name}
            parts = data.replace("rename_item_", "").split("_", 1)
            if len(parts) == 2:
                category_key = parts[0]
                item_name = parts[1]
                await self.start_item_rename(update, context, category_key, item_name)
        
        elif data.startswith("rename_category_"):
            category_key = data.replace("rename_category_", "")
            await self.start_category_rename(update, context, category_key)
        
        elif data == "cancel_rename":
            await self.cancel_rename(update, context)
        
        elif data.startswith("delete_permanent_item_"):
            # Format: delete_permanent_item_{category_key}_{item_name}
            parts = data.replace("delete_permanent_item_", "").split("_", 1)
            if len(parts) == 2:
                category_key = parts[0]
                item_name = parts[1]
                await self.delete_permanent_item(update, context, category_key, item_name)
        
        elif data.startswith("remove_items_"):
            list_id = int(data.replace("remove_items_", ""))
            await self.show_remove_items_menu(update, context, list_id)
        
        elif data.startswith("remove_category_"):
            # Check if it's a permanent category removal (no list_id)
            if len(data.split('_')) == 3:  # remove_category_{category_key}
                category_key = data.replace("remove_category_", "")
                await self.confirm_remove_permanent_category(update, context, category_key)
            else:  # remove_category_{list_id}_{category} - existing functionality
                parts = data.split('_')
                list_id = int(parts[2])
                category = '_'.join(parts[3:])  # In case category has underscores
                await self.confirm_remove_category(update, context, list_id, category)
        
        elif data.startswith("remove_individual_"):
            list_id = int(data.replace("remove_individual_", ""))
            await self.show_individual_items_removal(update, context, list_id)
        
        elif data.startswith("confirm_remove_category_"):
            parts = data.split('_')
            list_id = int(parts[3])
            category = '_'.join(parts[4:])  # In case category has underscores
            await self.remove_category_items(update, context, list_id, category)
        
        elif data.startswith("confirm_remove_permanent_category_"):
            category_key = data.replace("confirm_remove_permanent_category_", "")
            await self.remove_permanent_category(update, context, category_key)
        
        elif data.startswith("remove_item_"):
            parts = data.split('_')
            list_id = int(parts[2])
            item_id = int(parts[3])
            await self.remove_individual_item(update, context, list_id, item_id)
        
        
        
        
        elif data.startswith("confirm_reset_list_"):
            list_id = int(data.replace("confirm_reset_list_", ""))
            await self.confirm_reset_list_items(update, context, list_id)
        
        elif data.startswith("export_list_"):
            list_id = int(data.replace("export_list_", ""))
            await self.export_list(update, context, list_id)
        
        elif data.startswith("summary_list_"):
            list_id = int(data.replace("summary_list_", ""))
            await self.show_list_summary(update, context, list_id)
        
        elif data.startswith("list_menu_"):
            list_id = int(data.replace("list_menu_", ""))
            # Clear any pending item info when going back to list menu
            context.user_data.pop('item_info', None)
            context.user_data.pop('waiting_for_note', None)
            list_info = self.db.get_list_by_id(list_id)
            if list_info:
                await self.show_list_menu(update, context, list_info['name'])
        
        elif data.startswith("select_list_"):
            list_id = int(data.replace("select_list_", ""))
            await self.select_list(update, context, list_id)
        
        elif data.startswith("add_to_list_"):
            list_id = int(data.replace("add_to_list_", ""))
            await self.show_categories_for_list(update, context, list_id)
        
        elif data.startswith("categories_list_"):
            list_id = int(data.replace("categories_list_", ""))
            await self.show_categories_for_list(update, context, list_id)
        
        elif data.startswith("search_list_"):
            list_id = int(data.replace("search_list_", ""))
            await self.show_search_for_list(update, context, list_id)
        
        elif data == "add_description":
            context.user_data['waiting_for_list_description'] = True
            list_name = context.user_data.get('new_list_name')
            prompt_text = self.get_message(update.effective_user.id, 'create_list_description_input').format(list_name=list_name)
            await query.edit_message_text(prompt_text)
        
        elif data == "skip_description":
            await self.process_list_description(update, context, None)
        
        elif data.startswith("view_list_"):
            list_id = int(data.replace("view_list_", ""))
            await self.view_list_items(update, context, list_id)
        
        elif data.startswith("edit_list_name_"):
            list_id = int(data.replace("edit_list_name_", ""))
            await self.show_edit_list_name(update, context, list_id)
        
        elif data.startswith("edit_list_description_"):
            list_id = int(data.replace("edit_list_description_", ""))
            await self.show_edit_list_description(update, context, list_id)
        
        elif data.startswith("delete_list_"):
            list_id = int(data.replace("delete_list_", ""))
            result = self.db.delete_list(list_id)
            
            if result == "PROTECTED":
                # Supermarket list protection triggered
                protected_message = self.get_message(update.effective_user.id, 'supermarket_protected').format(
                    supermarket_list=self.get_message(update.effective_user.id, 'supermarket_list')
                )
                await query.edit_message_text(protected_message)
            elif result:
                # Successful deletion
                message = self.get_message(update.effective_user.id, 'list_deleted').format(list_name=result)
                await query.edit_message_text(message)
                
                # Notify all authorized users about list deletion
                await self.notify_list_deletion(result, list_id)
                
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ Error deleting list.")
        
        elif data.startswith("reset_list_"):
            list_id = int(data.replace("reset_list_", ""))
            if self.db.reset_list(list_id):
                list_info = self.db.get_list_by_id(list_id)
                list_name = list_info['name'] if list_info else self.get_message(update.effective_user.id, 'list_fallback').format(list_id=list_id)
                message = self.get_message(update.effective_user.id, 'list_reset_items').format(list_name=list_name)
                await query.edit_message_text(message)
                
                # Notify all authorized users about list reset
                await self.notify_list_reset(list_name, list_id)
                
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ Error resetting list.")
        
        # Maintenance mode callback handlers
        elif data == "maintenance_mode":
            await self.show_maintenance_mode(update, context)
        
        elif data == "set_maintenance_schedule":
            await self.show_set_maintenance_schedule(update, context)
        
        elif data == "view_maintenance_schedule":
            await self.show_maintenance_schedule(update, context)
        
        elif data == "disable_maintenance":
            await self.disable_maintenance_mode(update, context)
        
        elif data.startswith("maintenance_day_"):
            day = data.replace("maintenance_day_", "")
            context.user_data['maintenance_day'] = day
            await self.show_maintenance_time_selection(update, context)
        
        elif data.startswith("maintenance_time_"):
            time = data.replace("maintenance_time_", "")
            await self.confirm_maintenance_schedule(update, context, time)
        
        elif data == "confirm_maintenance_schedule":
            await self.save_maintenance_schedule(update, context)
        
        elif data == "cancel_maintenance_schedule":
            await self.show_maintenance_mode(update, context)
        
        elif data == "maintenance_reset_confirm":
            await self.confirm_maintenance_reset(update, context)
        
        elif data == "maintenance_reset_decline":
            await self.decline_maintenance_reset(update, context)
        
        # Template callback handlers
        elif data.startswith("templates_list_"):
            list_id = int(data.replace("templates_list_", ""))
            await self.show_templates_menu(update, context, list_id)
        
        elif data.startswith("template_preview_"):
            parts = data.replace("template_preview_", "").split("_")
            template_id = int(parts[0])
            list_id = int(parts[1])
            await self.show_template_preview(update, context, template_id, list_id)
        
        elif data.startswith("template_add_all_"):
            parts = data.replace("template_add_all_", "").split("_")
            template_id = int(parts[0])
            list_id = int(parts[1])
            await self.add_template_items(update, context, template_id, list_id)
        
        elif data.startswith("template_select_"):
            parts = data.replace("template_select_", "").split("_")
            template_id = int(parts[0])
            list_id = int(parts[1])
            await self.show_template_item_selection(update, context, template_id, list_id)
        
        elif data.startswith("template_replace_"):
            parts = data.replace("template_replace_", "").split("_")
            template_id = int(parts[0])
            list_id = int(parts[1])
            # Reset list first, then add all template items
            self.db.reset_list(list_id)
            await self.add_template_items(update, context, template_id, list_id)
        
        elif data.startswith("template_toggle_"):
            parts = data.replace("template_toggle_", "").split("_")
            template_id = int(parts[0])
            item_index = int(parts[1])
            await self.toggle_template_item_selection(update, context, template_id, item_index)
        
        elif data.startswith("template_add_selected_"):
            parts = data.replace("template_add_selected_", "").split("_")
            template_id = int(parts[0])
            list_id = int(parts[1])
            # Get selected items from user data
            selection_key = f'template_selection_{template_id}'
            selected_items = context.user_data.get(selection_key, {}).get('selected_items', [])
            await self.add_template_items(update, context, template_id, list_id, selected_items)
        
        elif data.startswith("save_template_"):
            list_id = int(data.replace("save_template_", ""))
            await self.save_current_list_as_template(update, context, list_id)
        
        elif data.startswith("template_management_"):
            list_id = int(data.replace("template_management_", ""))
            await self.show_template_management(update, context, list_id)
        
        elif data.startswith("system_template_management_"):
            list_id = int(data.replace("system_template_management_", ""))
            await self.show_system_template_management(update, context, list_id)
        
        elif data.startswith("create_system_template_"):
            list_id = int(data.replace("create_system_template_", ""))
            await self.create_system_template_from_list(update, context, list_id)
        
        elif data.startswith("edit_system_template_"):
            template_id = int(data.replace("edit_system_template_", ""))
            await self.edit_system_template(update, context, template_id)
        
        elif data.startswith("delete_system_template_"):
            template_id = int(data.replace("delete_system_template_", ""))
            await self.delete_system_template(update, context, template_id)
        
        elif data.startswith("confirm_delete_system_template_"):
            template_id = int(data.replace("confirm_delete_system_template_", ""))
            await self.confirm_delete_system_template(update, context, template_id)
        
        elif data.startswith("template_remove_item_"):
            parts = data.replace("template_remove_item_", "").split("_")
            template_id = int(parts[0])
            item_index = int(parts[1])
            await self.remove_template_item(update, context, template_id, item_index)
        
        elif data.startswith("template_add_items_"):
            template_id = int(data.replace("template_add_items_", ""))
            await self.add_items_to_template(update, context, template_id)
        
        elif data.startswith("template_save_changes_"):
            template_id = int(data.replace("template_save_changes_", ""))
            await self.save_template_changes(update, context, template_id)
        
        elif data.startswith("template_cancel_edit_"):
            template_id = int(data.replace("template_cancel_edit_", ""))
            await self.cancel_template_edit(update, context, template_id)
        
        elif data.startswith("template_category_"):
            parts = data.replace("template_category_", "").split("_")
            category_key = parts[0]
            template_id = int(parts[1])
            await self.show_template_category_items(update, context, category_key, template_id)
        
        elif data.startswith("template_add_item_"):
            # Parse callback data with pipe separator
            callback_parts = data.replace("template_add_item_", "").split("|")
            if len(callback_parts) == 3:
                category_key = callback_parts[0]
                item_name = callback_parts[1]
                template_id = int(callback_parts[2])
                await self.add_item_to_template(update, context, category_key, item_name, template_id)
            else:
                await update.callback_query.edit_message_text("❌ Invalid callback data.")
        
        elif data.startswith("recently_select"):
            await self.show_category_item_selection(update, context, "recently")

    async def process_category_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            category_key: str, item_name: str):
        """Process item selection from category"""
        # Check if we're adding to a specific list
        target_list_id = context.user_data.get('target_list_id')
        
        # Ask for optional note
        context.user_data['waiting_for_note'] = True
        context.user_data['item_info'] = {
            'name': item_name,
            'category': category_key,
            'user_id': update.effective_user.id,
            'list_id': target_list_id or 1  # Default to supermarket list
        }
        
        user_id = update.effective_user.id
        keyboard = [
            [
                InlineKeyboardButton(self.get_message(user_id, 'btn_add'), callback_data="skip_note"),
                InlineKeyboardButton(self.get_message(user_id, 'btn_notes'), callback_data="add_note")
            ],
            [
                InlineKeyboardButton(self.get_message(user_id, 'btn_back_categories'), callback_data="categories")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        adding_text = self.get_message(user_id, 'adding_item', item=item_name)
        prompt_text = self.get_message(user_id, 'add_notes_prompt')
        
        await update.callback_query.edit_message_text(
            f"{adding_text}\n\n{prompt_text}",
            reply_markup=reply_markup
        )

    async def confirm_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute list reset"""
        user_id = update.effective_user.id
        if self.db.reset_shopping_list():
            await update.callback_query.edit_message_text(
                f"✅ **Shopping list has been reset!**\n\n"
                f"{self.get_message(user_id, 'all_items_cleared')}"
            )
            
            # Notify all users
            await self.notify_users_list_reset(update, context)
        else:
            await update.callback_query.edit_message_text(
                "❌ Error resetting the shopping list. Please try again."
            )

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command - show user management (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        users = self.db.get_all_users()
        
        if not users:
            if update.message:
                await update.message.reply_text("👥 No users registered yet.")
            elif update.callback_query:
                await update.callback_query.edit_message_text("👥 No users registered yet.")
            return

        # Build user list message
        message_parts = ["👥 **Suggestions**\n"]
        
        admins = [u for u in users if u['is_admin']]
        authorized = [u for u in users if u['is_authorized'] and not u['is_admin']]
        unauthorized = [u for u in users if not u['is_authorized']]

        if admins:
            message_parts.append("👑 **Admins:**")
            for user in admins:
                name = user['first_name'] or user['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user['user_id'])
                message_parts.append(f"• {name} (ID: {user['user_id']})")

        if authorized:
            message_parts.append("\n✅ **Authorized Users:**")
            for user in authorized:
                name = user['first_name'] or user['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user['user_id'])
                message_parts.append(f"• {name} (ID: {user['user_id']})")

        if unauthorized:
            message_parts.append("\n⏳ **Pending Authorization:**")
            for user in unauthorized:
                name = user['first_name'] or user['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user['user_id'])
                message_parts.append(f"• {name} (ID: {user['user_id']})")
                message_parts.append(f"  `/authorize {user['user_id']}`")

        message_parts.append(f"\n📊 **Total Users:** {len(users)}")
        message_parts.append("\n💡 **Commands:**")
        message_parts.append("• `/authorize <user_id>` - Authorize a regular user")
        message_parts.append("• `/removeuser <user_id>` - Remove user authorization")
        message_parts.append("• `/addadmin <user_id>` - Promote user to admin")
        message_parts.append("• `/users` - Show this list")

        full_message = "\n".join(message_parts)
        
        # Add back button for callback queries
        if update.callback_query:
            keyboard = [[InlineKeyboardButton(self.get_message(update.effective_user.id, 'btn_back_menu'), callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(full_message, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text(full_message, parse_mode='Markdown')

    async def authorize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /authorize command - authorize a user (admin only)"""
        user_id = update.effective_user.id
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                f"❌ **Usage:** `/authorize <user_id>`\n\n"
                f"{self.get_message(user_id, 'authorize_example')}",
                parse_mode='Markdown'
            )
            return

        try:
            user_id_to_authorize = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
            return

        # Check if user exists in database
        user_info = self.db.get_user_info(user_id_to_authorize)
        if not user_info:
            await update.message.reply_text(
                f"❌ User ID `{user_id_to_authorize}` not found.\n\n"
                f"{self.get_message(user_id, 'users_must_start_first')}",
                parse_mode='Markdown'
            )
            return

        if user_info['is_authorized']:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_authorize)
            await update.message.reply_text(f"✅ {user_name} is already authorized!")
            return

        # Authorize the user
        success = self.db.add_user(
            user_id_to_authorize,
            user_info['username'],
            user_info['first_name'],
            user_info['last_name'],
            is_admin=False  # Regular authorization, not admin
        )

        if success:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_authorize)
            admin_name = update.effective_user.first_name or update.effective_user.username or self.get_message(update.effective_user.id, 'admin_fallback')
            
            await update.message.reply_text(
                f"✅ **User Authorized!**\n\n"
                f"👤 {user_name} can now use the shopping bot.\n\n"
                f"{self.get_message(user_id, 'will_be_notified_features')}",
                parse_mode='Markdown'
            )

            # Notify the authorized user
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_authorize,
                    text=f"🎉 **{self.get_message(user_id_to_authorize, 'user_authorized_message', admin_name=admin_name)}**",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not notify authorized user {user_id_to_authorize}: {e}")

        else:
            await update.message.reply_text("❌ Error authorizing user. Please try again.")

    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addadmin command - promote user to admin (admin only)"""
        user_id = update.effective_user.id
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                f"❌ **Usage:** `/addadmin <user_id>`\n\n"
                f"{self.get_message(update.effective_user.id, 'addadmin_example')}",
                parse_mode='Markdown'
            )
            return

        try:
            user_id_to_promote = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
            return

        # Check if user exists in database
        user_info = self.db.get_user_info(user_id_to_promote)
        if not user_info:
            await update.message.reply_text(
                f"❌ User ID `{user_id_to_promote}` not found.\n\n"
                f"{self.get_message(user_id, 'users_must_start_first_promote')}",
                parse_mode='Markdown'
            )
            return

        if user_info['is_admin']:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_promote)
            await update.message.reply_text(f"✅ {user_name} is already an admin!")
            return

        # Promote user to admin (this also authorizes them if they weren't already)
        success = self.db.add_user(
            user_id_to_promote,
            user_info['username'],
            user_info['first_name'],
            user_info['last_name'],
            is_admin=True  # Promote to admin
        )

        if success:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_promote)
            admin_name = update.effective_user.first_name or update.effective_user.username or self.get_message(update.effective_user.id, 'admin_fallback')
            
            await update.message.reply_text(
                f"👑 **User Promoted to Admin!**\n\n"
                f"👤 {user_name} is now a family admin.\n\n"
                f"🔑 **New Admin Privileges:**\n"
                f"• Authorize/manage users\n"
                f"• Delete items from shopping list\n"
                f"• Reset shopping list\n"
                f"• Promote other users to admin\n\n"
                f"{self.get_message(user_id, 'will_be_notified_admin')}",
                parse_mode='Markdown'
            )

            # Notify the new admin
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_promote,
                    text=self.get_message(user_id_to_promote, 'user_promoted_message', admin_name=admin_name),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not notify new admin {user_id_to_promote}: {e}")

            # Notify other admins
            await self.notify_admins_promotion(update, context, user_name, user_id_to_promote)

        else:
            await update.message.reply_text("❌ Error promoting user to admin. Please try again.")

    async def remove_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removeuser command - remove user authorization (admin only)"""
        user_id = update.effective_user.id
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return

        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                self.get_message(update.effective_user.id, 'usage_removeuser'),
                parse_mode='Markdown'
            )
            return

        try:
            user_id_to_remove = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid user ID. Please provide a valid number.\n\n"
                f"**Example:** `/removeuser 123456789`",
                parse_mode='Markdown'
            )
            return

        # Check if trying to remove self
        if user_id_to_remove == user_id:
            await update.message.reply_text("❌ You cannot remove yourself!")
            return

        # Check if user exists in database
        user_info = self.db.get_user_info(user_id_to_remove)
        if not user_info:
            await update.message.reply_text(
                f"❌ User ID `{user_id_to_remove}` not found.\n\n"
                f"{self.get_message(user_id, 'users_must_start_first')}",
                parse_mode='Markdown'
            )
            return

        if not user_info['is_authorized']:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_remove)
            await update.message.reply_text(
                self.get_message(update.effective_user.id, 'user_not_authorized').format(
                    user_name=user_name, 
                    user_id=user_id_to_remove
                ),
                parse_mode='Markdown'
            )
            return

        # Check if trying to remove an admin
        if user_info['is_admin']:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_remove)
            await update.message.reply_text(
                self.get_message(update.effective_user.id, 'cannot_remove_admin').format(user_name=user_name),
                parse_mode='Markdown'
            )
            return

        # Remove user authorization
        success = self.db.remove_user_authorization(user_id_to_remove)
        
        if success:
            user_name = user_info['first_name'] or user_info['username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_to_remove)
            admin_name = update.effective_user.first_name or update.effective_user.username or self.get_message(update.effective_user.id, 'admin_fallback')
            
            await update.message.reply_text(
                f"✅ **User Authorization Removed**\n\n"
                f"👤 {user_name} can no longer use the shopping bot.\n\n"
                f"🔑 **What happens:**\n"
                f"• User loses access to all bot features\n"
                f"• Must be re-authorized to use the bot\n"
                f"• Their shopping items remain in the database",
                parse_mode='Markdown'
            )
            
            # Notify the removed user
            try:
                await self.application.bot.send_message(
                    chat_id=user_id_to_remove,
                    text=f"❌ **Access Revoked**\n\n"
                         f"Your access to the Family Shopping List Bot has been revoked by an admin.\n\n"
                         f"Contact an admin if you need access restored.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.warning(f"Could not notify removed user {user_id_to_remove}: {e}")

        else:
            await update.message.reply_text("❌ Error removing user authorization. Please try again.")

    async def notify_admins_promotion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    promoted_user_name: str, promoted_user_id: int):
        """Notify other admins about user promotion"""
        user_id = update.effective_user.id
        promoter_name = update.effective_user.first_name or update.effective_user.username or self.get_message(update.effective_user.id, 'admin_fallback')
        message = (
            f"👑 **New Admin Promoted**\n\n"
            f"👤 **{promoted_user_name}** (ID: `{promoted_user_id}`)\n"
            f"🔑 Promoted by: {promoter_name}\n\n"
            f"{self.get_message(user_id, 'now_have_privileges')}"
        )
        
        # Get all admin users
        all_users = self.db.get_all_users()
        for db_user in all_users:
            if (db_user['is_admin'] and 
                db_user['user_id'] != update.effective_user.id and 
                db_user['user_id'] != promoted_user_id):
                try:
                    await context.bot.send_message(
                        chat_id=db_user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not notify admin {db_user['user_id']}: {e}")

    async def notify_admins_new_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Notify admins about new user request"""
        user_name = user.first_name or user.username or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user.id)
        username_display = f"@{user.username}" if user.username else self.get_message(update.effective_user.id, 'none_fallback')
        message = (
            f"👤 <b>New User Request</b>\n\n"
            f"Name: {user_name}\n"
            f"Username: {username_display}\n"
            f"ID: <code>{user.id}</code>\n\n"
            f"🔧 <b>Admin Commands:</b>\n"
            f"• /authorize {user.id} - Authorize this user\n"
            f"• /removeuser {user.id} - Remove user authorization\n"
            f"• /addadmin {user.id} - Promote to admin\n"
            f"• /users - View all users"
        )
        
        # Get all admin users
        all_users = self.db.get_all_users()
        for db_user in all_users:
            if db_user['is_admin'] and db_user['user_id'] != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=db_user['user_id'],
                        text=message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Could not notify admin {db_user['user_id']}: {e}")

    async def notify_users_item_added(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    item_name: str, note: str = None):
        """Notify other users when an item is added"""
        user = update.effective_user
        user_name = user.first_name or user.username or self.get_message(update.effective_user.id, 'someone_fallback')
        
        note_text = f" (Note: {note})" if note else ""
        message = f"🔔 {user_name} added: **{item_name}**{note_text}"
        
        # Get all users except the one who added the item
        all_users = self.db.get_all_users()
        for db_user in all_users:
            if db_user['user_id'] != user.id and db_user['is_authorized']:
                try:
                    await context.bot.send_message(
                        chat_id=db_user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {db_user['user_id']}: {e}")

    async def notify_users_list_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Notify all users when list is reset"""
        user = update.effective_user
        user_name = user.first_name or user.username or self.get_message(update.effective_user.id, 'admin_fallback')
        
        message = f"🗑️ **Shopping list reset by {user_name}**\n\nThe list is now empty and ready for new items!"
        
        # Get all users except the admin who reset
        all_users = self.db.get_all_users()
        for db_user in all_users:
            if db_user['user_id'] != user.id and db_user['is_authorized']:
                try:
                    await context.bot.send_message(
                        chat_id=db_user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {db_user['user_id']}: {e}")

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - send message to all authorized users"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        # Clear all waiting states when using broadcast command
        self.clear_all_waiting_states(context)

        # Check if user is admin or authorized
        if not (self.db.is_user_admin(update.effective_user.id) or self.db.is_user_authorized(update.effective_user.id)):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        # Set waiting for broadcast message
        context.user_data['waiting_for_broadcast'] = True
        
        prompt_text = self.get_message(update.effective_user.id, 'broadcast_prompt')
        await update.message.reply_text(prompt_text)

    async def process_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Process broadcast message and send to all authorized users"""
        user_id = update.effective_user.id
        
        if not message_text.strip():
            await update.message.reply_text(self.get_message(user_id, 'broadcast_empty'))
            return

        # Get all authorized users
        users = self.db.get_all_authorized_users()
        
        if not users:
            await update.message.reply_text(self.get_message(user_id, 'broadcast_no_users'))
            return

        # Get sender info
        sender_info = self.db.get_user_info(user_id)
        sender_name = sender_info.get('first_name', '') or sender_info.get('username', '') or self.get_message(user_id, 'user_fallback').format(user_id=user_id)
        
        # Send to all users
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                # Skip sending to self
                if user['user_id'] == user_id:
                    continue
                    
                # Format message based on user's language
                user_lang = user.get('language', 'en')
                broadcast_text = MESSAGES.get(user_lang, MESSAGES['en'])['broadcast_received'].format(
                    sender=sender_name,
                    message=message_text
                )
                
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=broadcast_text
                )
                sent_count += 1
                
            except Exception as e:
                logging.warning(f"Could not send broadcast to user {user['user_id']}: {e}")
                failed_count += 1

        # Save broadcast to history
        self.db.save_broadcast_message(user_id, message_text, sent_count)
        
        # Send confirmation to sender
        success_text = self.get_message(user_id, 'broadcast_sent').format(
            count=sent_count,
            message=message_text[:100] + "..." if len(message_text) > 100 else message_text
        )
        await update.message.reply_text(success_text)
        
        # Clear waiting state
        context.user_data['waiting_for_broadcast'] = False

    async def suggest_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /suggest command - show category selection for suggesting new items"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        await self.show_suggestion_categories(update, context)

    async def show_suggestion_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show category selection for item suggestions"""
        user_id = update.effective_user.id
        
        # Set search context if this is from search results
        if update.callback_query and update.callback_query.data == "suggest_from_search":
            context.user_data['suggestion_from_search'] = True
            context.user_data['target_list_id'] = context.user_data.get('search_list_id', 1)
        
        keyboard = []
        
        # Create category buttons
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"suggest_category_{category_key}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'),
            callback_data="main_menu"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        prompt_text = self.get_message(user_id, 'suggest_item_prompt')
        
        if update.message:
            await update.message.reply_text(prompt_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(prompt_text, reply_markup=reply_markup)

    async def process_suggestion_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process suggestion item name input"""
        user_id = update.effective_user.id
        
        if not item_name.strip():
            await update.message.reply_text(self.get_message(user_id, 'suggestion_empty'))
            return
        
        # Store the item name and ask for Hebrew translation
        context.user_data['suggestion_item_name'] = item_name.strip()
        context.user_data['waiting_for_suggestion_item'] = False
        context.user_data['waiting_for_suggestion'] = False  # Clear the new state too
        context.user_data['waiting_for_suggestion_translation'] = True
        
        category_key = context.user_data.get('suggestion_category')
        category_name = self.get_category_name(user_id, category_key)
        
        translation_prompt = self.get_message(user_id, 'suggest_item_translation').format(
            item_name=item_name.strip(),
            category=category_name
        )
        
        await update.message.reply_text(translation_prompt)

    async def process_suggestion_translation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hebrew_translation: str):
        """Process suggestion Hebrew translation input"""
        user_id = update.effective_user.id
        
        if not hebrew_translation.strip():
            await update.message.reply_text(self.get_message(user_id, 'suggestion_translation_empty'))
            return
        
        # Get stored data
        item_name_en = context.user_data.get('suggestion_item_name')
        category_key = context.user_data.get('suggestion_category')
        
        if not item_name_en or not category_key:
            await update.message.reply_text(self.get_message(user_id, 'suggestion_error'))
            return
        
        # Get the target list_id (default to 1 for supermarket list)
        target_list_id = context.user_data.get('target_list_id', 1)
        
        # Save suggestion to database
        success = self.db.add_item_suggestion(user_id, category_key, item_name_en, hebrew_translation.strip(), target_list_id)
        
        if success:
            category_name = self.get_category_name(user_id, category_key)
            success_message = self.get_message(user_id, 'suggestion_submitted').format(
                item_name_en=item_name_en,
                item_name_he=hebrew_translation.strip(),
                category=category_name
            )
            
            # Check if this came from search and add navigation button
            if context.user_data.get('suggestion_from_search'):
                keyboard = [[InlineKeyboardButton(
                    "🔍 Search Again",
                    callback_data="search_again"
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(success_message, reply_markup=reply_markup)
                context.user_data.pop('suggestion_from_search', None)
            else:
                await update.message.reply_text(success_message)
            
            # Notify admins about new suggestion
            await self.notify_admins_new_suggestion(update, context, item_name_en, hebrew_translation.strip(), category_name)
        else:
            # Check if it's a duplicate
            if self.db.is_item_in_category(category_key, item_name_en):
                category_name = self.get_category_name(user_id, category_key)
                duplicate_message = f"❌ **Item Already Exists**\n\nThe item **{item_name_en}** already exists in the **{category_name}** category.\n\nPlease suggest a different item."
                await update.message.reply_text(duplicate_message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **Suggestion Failed**\n\nThis item may have already been suggested or there was an error. Please try again.")
        
        # Clear waiting states
        context.user_data.pop('waiting_for_suggestion_translation', None)
        context.user_data.pop('suggestion_item_name', None)
        context.user_data.pop('suggestion_category', None)

    async def notify_admins_new_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         item_name_en: str, item_name_he: str, category_name: str):
        """Notify admins about new item suggestion"""
        admins = self.db.get_admin_users()
        
        for admin in admins:
            try:
                notification = f"💡 NEW ITEM SUGGESTION\n\n📝 Item: {item_name_en}\n🌐 Hebrew: {item_name_he}\n📂 Category: {category_name}\n\nUse 'Manage Suggestions' to review."
                await context.bot.send_message(
                    chat_id=admin['user_id'],
                    text=notification
                )
            except Exception as e:
                logging.warning(f"Could not notify admin {admin['user_id']}: {e}")

    async def manage_suggestions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /managesuggestions command - show pending suggestions for admin review"""
        user_id = update.effective_user.id
        if not self.db.is_user_authorized(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            if update.message:
                await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        suggestions = self.db.get_pending_suggestions()
        
        if not suggestions:
            # Show "no suggestions found" message with back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Management", callback_data="admin_management")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = "💡 **Manage Items Suggested**\n\n✅ No pending item suggestions found.\n\nAll suggestions have been reviewed."
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        # Show first suggestion for review
        await self.show_suggestion_review(update, context, suggestions[0], 0, len(suggestions))

    async def show_manage_suggestions_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show consolidated suggestions management (items + categories)"""
        user_id = update.effective_user.id
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return

        list_info = self.db.get_list_by_id(list_id)
        list_name = list_info['name'] if list_info else self.get_message(update.effective_user.id, 'list_fallback').format(list_id=list_id)
        
        # Get pending item suggestions for this list
        item_suggestions = self.db.get_pending_suggestions(list_id)
        
        # Get pending category suggestions
        category_suggestions = self.db.get_pending_category_suggestions()
        
        message = f"💡 **Manage Suggestions - {list_name}**\n\n"
        
        if not item_suggestions and not category_suggestions:
            message += "📝 No pending suggestions."
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]]
        else:
            message += f"📊 **Pending Suggestions:**\n"
            if item_suggestions:
                message += f"• 📦 Items: {len(item_suggestions)}\n"
            if category_suggestions:
                message += f"• 📂 Categories: {len(category_suggestions)}\n"
            
            keyboard = []
            if item_suggestions:
                keyboard.append([InlineKeyboardButton("📦 Manage Item Suggestions", callback_data=f"manage_item_suggestions_{list_id}")])
            if category_suggestions:
                keyboard.append([InlineKeyboardButton("📂 Manage Category Suggestions", callback_data="manage_category_suggestions")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_item_suggestions_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show item suggestions for a specific list"""
        user_id = update.effective_user.id
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return

        suggestions = self.db.get_pending_suggestions(list_id)
        
        if not suggestions:
            list_info = self.db.get_list_by_id(list_id)
            list_name = list_info['name'] if list_info else self.get_message(update.effective_user.id, 'list_fallback').format(list_id=list_id)
            
            keyboard = [[InlineKeyboardButton("🏠 Back to Suggestions", callback_data=f"manage_suggestions_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"📦 **Item Suggestions for {list_name}**\n\n"
            message += self.get_message(user_id, 'no_pending_suggestions')
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        # Show first suggestion for review
        await self.show_suggestion_review_for_list(update, context, suggestions[0], 0, len(suggestions), list_id)

    async def show_suggestion_review_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  suggestion: Dict, current_index: int, total_count: int, list_id: int):
        """Show suggestion for admin review (list-specific)"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, suggestion['category_key'])
        list_info = self.db.get_list_by_id(list_id)
        list_name = list_info['name'] if list_info else self.get_message(update.effective_user.id, 'list_fallback').format(list_id=list_id)
        
        message = f"{self.get_message(user_id, 'suggestion_review')} ({current_index + 1}/{total_count})\n\n"
        message += f"📋 List: {list_name}\n"
        message += f"📝 Item: {suggestion['item_name_en']}\n"
        message += f"🌐 Hebrew: {suggestion['item_name_he']}\n"
        message += f"📂 Category: {category_name}\n"
        message += f"👤 Suggested by: {suggestion['suggested_by_first_name'] or suggestion['suggested_by_username'] or 'Unknown'}\n"
        message += f"📅 Date: {suggestion['created_at']}\n\n"
        message += self.get_message(user_id, 'choose_action')
        
        keyboard = [
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_approve'),
                callback_data=f"approve_suggestion_{suggestion['id']}"
            ), InlineKeyboardButton(
                self.get_message(user_id, 'btn_reject'),
                callback_data=f"reject_suggestion_{suggestion['id']}"
            )]
        ]
        
        if total_count > 1:
            keyboard.append([InlineKeyboardButton(
                "⏭️ Next",
                callback_data=f"next_suggestion_list_{list_id}_{current_index + 1}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_to_list'),
            callback_data=f"list_menu_{list_id}"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    async def show_suggestion_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  suggestion: Dict, current_index: int, total_count: int):
        """Show suggestion for admin review"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, suggestion['category_key'])
        
        message = f"{self.get_message(user_id, 'suggestion_review')} ({current_index + 1}/{total_count})\n\n"
        message += f"📝 Item: {suggestion['item_name_en']}\n"
        message += f"🌐 Hebrew: {suggestion['item_name_he']}\n"
        message += f"📂 Category: {category_name}\n"
        message += f"👤 Suggested by: {suggestion['suggested_by_first_name'] or suggestion['suggested_by_username'] or 'Unknown'}\n"
        message += f"📅 Date: {suggestion['created_at']}\n\n"
        message += self.get_message(user_id, 'choose_action')
        
        keyboard = [
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_approve'),
                callback_data=f"approve_suggestion_{suggestion['id']}"
            ), InlineKeyboardButton(
                self.get_message(user_id, 'btn_reject'),
                callback_data=f"reject_suggestion_{suggestion['id']}"
            )]
        ]
        
        if total_count > 1:
            keyboard.append([InlineKeyboardButton(
                "⏭️ Next",
                callback_data=f"next_suggestion_{current_index + 1}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_main_menu'),
            callback_data="main_menu"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    async def notify_suggestion_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     suggestion: Dict, result: str):
        """Notify user about suggestion approval/rejection"""
        try:
            # Get the user who made the suggestion
            suggested_by = suggestion.get('suggested_by_first_name') or suggestion.get('suggested_by_username')
            
            # For now, we'll need to get the user_id from the suggestion
            # This would require modifying the database query to include user_id
            # For simplicity, we'll skip individual notifications for now
            # In a full implementation, you'd store the user_id and send them a message
            
            logging.info(f"Suggestion {suggestion['id']} {result} - Item: {suggestion['item_name_en']}")
            
        except Exception as e:
            logging.error(f"Error notifying suggestion result: {e}")

    async def new_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /newitem command - admin can add items directly to categories"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        await self.show_new_item_categories(update, context)

    async def show_new_item_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show category selection for adding new items directly (admin only)"""
        user_id = update.effective_user.id
        keyboard = []
        
        # Create category buttons
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"new_item_category_{category_key}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'),
            callback_data="main_menu"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        prompt_text = "➕ ADD NEW ITEM (ADMIN)\n\nChoose a category to add a new item directly:"
        
        if update.message:
            await update.message.reply_text(prompt_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(prompt_text, reply_markup=reply_markup)

    async def process_new_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process new item name input (admin only)"""
        user_id = update.effective_user.id
        
        if not item_name.strip():
            await update.message.reply_text("❌ Please provide an item name.")
            return
        
        category_key = context.user_data.get('new_item_category')
        category_name = self.get_category_name(user_id, category_key)
        
        # Check if item was previously deleted (restoration detection)
        if self.db.is_item_deleted(category_key, item_name.strip()):
            await self.show_restoration_options(update, context, category_key, item_name.strip())
            return
        
        # Store the item name and ask for Hebrew translation
        context.user_data['new_item_name'] = item_name.strip()
        context.user_data['waiting_for_new_item'] = False
        context.user_data['waiting_for_new_item_translation'] = True
        
        translation_prompt = f"{self.get_message(user_id, 'translation_required_admin')}\n\nItem: {item_name.strip()}\nCategory: {category_name}\n\n{self.get_message(user_id, 'provide_hebrew_translation')}\n\n{self.get_message(user_id, 'hebrew_translation_tips')}\n\n{self.get_message(user_id, 'type_hebrew_translation')}"
        
        await update.message.reply_text(translation_prompt)

    async def process_new_item_translation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hebrew_translation: str):
        """Process new item Hebrew translation input (admin only)"""
        user_id = update.effective_user.id
        
        if not hebrew_translation.strip():
            await update.message.reply_text(self.get_message(user_id, 'please_provide_hebrew'))
            return
        
        # Get stored data
        item_name_en = context.user_data.get('new_item_name')
        category_key = context.user_data.get('new_item_category')
        
        if not item_name_en or not category_key:
            await update.message.reply_text(self.get_message(user_id, 'error_processing_new_item'))
            return
        
        # Add item directly to the category (admin privilege)
        result = self.add_item_to_category(category_key, item_name_en, hebrew_translation.strip())
        if result:
            category_name = self.get_category_name(user_id, category_key)
            success_message = self.get_message(user_id, 'item_added_as_new_success').format(
                item_name=item_name_en, 
                category_name=category_name
            ) + f"\n\n🌐 Hebrew: {hebrew_translation.strip()}\n\nThis item is now available for everyone!"
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            # Notify all users about the new item
            await self.notify_users_new_item(update, context, item_name_en, hebrew_translation.strip(), category_name)
        else:
            # Check if it's a duplicate
            if self.db.is_item_in_category(category_key, item_name_en):
                await update.message.reply_text(self.get_message(user_id, 'error_adding_new_item_duplicate').format(
                    item_name=item_name_en, 
                    category_name=self.get_category_name(user_id, category_key)
                ), parse_mode='Markdown')
            else:
                await update.message.reply_text(self.get_message(user_id, 'error_adding_new_item'))
        
        # Clear waiting states
        context.user_data.pop('waiting_for_new_item_translation', None)
        context.user_data.pop('new_item_name', None)
        context.user_data.pop('new_item_category', None)

    def add_item_to_category(self, category_key: str, item_name_en: str, item_name_he: str) -> bool:
        """Add item directly to category (admin only)"""
        try:
            # Check if item already exists (static or dynamic)
            if self.db.is_item_in_category(category_key, item_name_en):
                return False  # Item already exists
            
            # Add to dynamic category items table
            return self.db.add_dynamic_category_item(category_key, item_name_en, item_name_he)
        except Exception as e:
            logging.error(f"Error adding item to category: {e}")
            return False

    async def show_restoration_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     category_key: str, item_name: str):
        """Show restoration options for deleted items"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, category_key)
        
        message = self.get_message(user_id, 'item_restoration_detected').format(
            item_name=item_name, 
            category_name=category_name
        )
        
        keyboard = [
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_restore_original_item'), 
                callback_data=f"restore_item_{category_key}_{item_name}"
            )],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_add_as_new_item'), 
                callback_data=f"add_new_item_{category_key}_{item_name}"
            )],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_cancel_restoration'), 
                callback_data=f"category_{category_key}"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_restore_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                category_key: str, item_name: str):
        """Handle restoring a deleted item"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, category_key)
        
        # Restore the item by removing it from deleted_items table
        success = self.db.restore_deleted_item(category_key, item_name)
        
        if success:
            message = self.get_message(user_id, 'item_restored_success').format(
                item_name=item_name, 
                category_name=category_name
            )
            
            # Show success message with back button
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_categories'), 
                callback_data="categories"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'failed_to_restore_item'))

    async def handle_add_as_new_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   category_key: str, item_name: str):
        """Handle adding a deleted item as a new item"""
        user_id = update.effective_user.id
        
        # Store the item name and proceed with normal new item flow
        context.user_data['new_item_name'] = item_name
        context.user_data['new_item_category'] = category_key
        context.user_data['waiting_for_new_item_translation'] = True
        
        category_name = self.get_category_name(user_id, category_key)
        
        translation_prompt = f"{self.get_message(user_id, 'translation_required_admin')}\n\nItem: {item_name}\nCategory: {category_name}\n\n{self.get_message(user_id, 'provide_hebrew_translation')}\n\n{self.get_message(user_id, 'hebrew_translation_tips')}\n\n{self.get_message(user_id, 'type_hebrew_translation')}"
        
        await update.callback_query.edit_message_text(translation_prompt)

    async def notify_users_new_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  item_name_en: str, item_name_he: str, category_name: str):
        """Notify all users about new item added by admin"""
        users = self.db.get_all_authorized_users()
        
        for user in users:
            try:
                notification = f"🆕 NEW ITEM ADDED!\n\n📝 Item: {item_name_en}\n🌐 Hebrew: {item_name_he}\n📂 Category: {category_name}\n\nThis item is now available in the categories menu!"
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=notification
                )
            except Exception as e:
                logging.warning(f"Could not notify user {user['user_id']}: {e}")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command - search for items in categories"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        # Clear all waiting states when using /search command
        self.clear_all_waiting_states(context)
        await self.show_search_prompt(update, context)

    async def show_search_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show search prompt with text and voice options"""
        user_id = update.effective_user.id
        
        # Create keyboard with text and voice search options
        keyboard = [
            [InlineKeyboardButton(self.get_message(user_id, 'btn_text_search'), callback_data="text_search")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_voice_search'), callback_data="voice_search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        prompt_text = self.get_message(user_id, 'search_prompt')
        
        if update.message:
            await update.message.reply_text(
                f"{prompt_text}\n\nChoose search method:",
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                f"{prompt_text}\n\nChoose search method:",
                reply_markup=reply_markup
            )

    async def show_voice_search_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show voice search prompt"""
        try:
            user_id = update.effective_user.id
            
            # Create keyboard with voice recording option
            keyboard = [
                [InlineKeyboardButton(self.get_message(user_id, 'btn_start_voice_recording'), callback_data="start_voice_recording")],
                [InlineKeyboardButton(self.get_message(user_id, 'btn_switch_to_text_search'), callback_data="text_search")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            prompt_text = self.get_message(user_id, 'voice_search_prompt')
            await update.callback_query.edit_message_text(
                prompt_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error in show_voice_search_prompt: {e}")
            await update.callback_query.edit_message_text("❌ Error loading voice search. Please try again.")

    async def start_voice_recording(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start voice recording for search"""
        user_id = update.effective_user.id
        
        # Show listening message without stop button (automatic stop when releasing microphone)
        prompt_text = self.get_message(user_id, 'voice_search_listening')
        await update.callback_query.edit_message_text(
            prompt_text
        )
        
        # Set waiting for voice message
        context.user_data['waiting_for_voice_search'] = True
        logging.info("Voice recording started, waiting_for_voice_search set to True")

    async def process_voice_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process voice message for search"""
        user_id = update.effective_user.id
        
        # Clear voice search waiting state
        context.user_data.pop('waiting_for_voice_search', None)
        
        try:
            # Show processing message
            processing_msg = await update.message.reply_text(
                self.get_message(user_id, 'voice_search_processing')
            )
            
            # Get the voice file
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            logging.info(f"Voice file downloaded: {voice_file.file_id}")
            
            if SPEECH_RECOGNITION_AVAILABLE:
                # Try to transcribe the voice
                transcribed_text = await self.transcribe_voice(voice_file)
                
                if transcribed_text:
                    await processing_msg.edit_text(
                        f"🎤 Voice transcribed: **{transcribed_text}**\n\nSearching..."
                    )
                    # Process the search with transcribed text
                    await self.process_search(update, context, transcribed_text)
                else:
                    await processing_msg.edit_text(
                        "🎤 Voice recognition failed!\n\n"
                        "Please type what you said so I can search for it:\n\n"
                        "💡 Example: 'milk', 'חלב', 'bread', 'לחם'"
                    )
                    context.user_data['waiting_for_voice_text'] = True
            else:
                # Speech recognition not available
                await processing_msg.edit_text(
                    "🎤 Voice received!\n\n"
                    "⚠️ Voice-to-text requires additional setup.\n"
                    "Please type what you said:"
                )
                context.user_data['waiting_for_voice_text'] = True
            
        except Exception as e:
            logging.error(f"Voice search processing error: {e}")
            await update.message.reply_text(
                self.get_message(user_id, 'voice_search_error')
            )

    async def transcribe_voice(self, voice_file) -> str:
        """Transcribe voice file to text"""
        try:
            # Download voice file
            voice_data = await voice_file.download_as_bytearray()
            logging.info(f"Voice data downloaded: {len(voice_data)} bytes")
            
            # Initialize speech recognizer
            recognizer = sr.Recognizer()
            
            # Try direct recognition (works with some OGG files)
            try:
                audio_io = io.BytesIO(voice_data)
                with sr.AudioFile(audio_io) as source:
                    audio = recognizer.record(source)
                    
                    # Try English first
                    try:
                        text = recognizer.recognize_google(audio, language='en-US')
                        logging.info(f"Voice transcribed (English): {text}")
                        return text
                    except sr.UnknownValueError:
                        # Try Hebrew if English fails
                        try:
                            text = recognizer.recognize_google(audio, language='he-IL')
                            logging.info(f"Voice transcribed (Hebrew): {text}")
                            return text
                        except sr.UnknownValueError:
                            # Try auto-detect
                            try:
                                text = recognizer.recognize_google(audio)
                                logging.info(f"Voice transcribed (auto-detect): {text}")
                                return text
                            except sr.UnknownValueError:
                                logging.error("Could not understand voice message")
                                return None
                                
            except Exception as e:
                logging.error(f"Voice recognition failed: {e}")
                return None
                
        except Exception as e:
            logging.error(f"Voice transcription error: {e}")
            return None

    async def process_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_query: str):
        """Process search query"""
        user_id = update.effective_user.id
        
        if not search_query.strip():
            await update.message.reply_text(self.get_message(user_id, 'search_empty'))
            return
        
        context.user_data['waiting_for_search'] = False
        
        # Get target list ID (default to supermarket list if not specified)
        target_list_id = context.user_data.get('search_list_id', 1)
        list_info = self.db.get_list_by_id(target_list_id)
        list_name = list_info['name'] if list_info else self.get_message(user_id, 'list_fallback').format(list_id=target_list_id)
        
        # Search in both categories and current list
        category_results = self.search_items(search_query.strip(), user_id)
        list_results = self.search_items_in_list(search_query.strip(), target_list_id, user_id)
        
        # Store search query for later use
        context.user_data['current_search_query'] = search_query.strip()
        
        # Show comprehensive search results
        await self.show_comprehensive_search_results(update, context, search_query.strip(), category_results, list_results, list_name, target_list_id)
        
        # Clear search context
        context.user_data.pop('search_list_id', None)

    def search_items(self, query: str, user_id: int) -> List[Dict]:
        """Search for items in all categories"""
        results = []
        query_lower = query.lower()
        
        # Search in predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            
            # Search in English items
            for i, item_en in enumerate(category_data['items']['en']):
                if query_lower in item_en.lower():
                    item_he = category_data['items']['he'][i] if i < len(category_data['items']['he']) else item_en
                    results.append({
                        'item_name': item_en,
                        'hebrew_name': item_he,
                        'category': category_name,
                        'category_key': category_key,
                        'category_emoji': category_data['emoji']
                    })
            
            # Search in Hebrew items
            for i, item_he in enumerate(category_data['items']['he']):
                if query_lower in item_he.lower():
                    item_en = category_data['items']['en'][i] if i < len(category_data['items']['en']) else item_he
                    results.append({
                        'item_name': item_en,
                        'hebrew_name': item_he,
                        'category': category_name,
                        'category_key': category_key,
                        'category_emoji': category_data['emoji']
                    })
            
            # Search in dynamic items for this category
            dynamic_items = self.db.get_dynamic_category_items(category_key)
            for item in dynamic_items:
                lang = self.get_user_language(user_id)
                item_name = item.get(lang, item.get('en', ''))
                if item_name and query_lower in item_name.lower():
                    # Get both English and Hebrew names
                    item_en = item.get('en', item_name)
                    item_he = item.get('he', item_name)
                    results.append({
                        'item_name': item_en,
                        'hebrew_name': item_he,
                        'category': category_name,
                        'category_key': category_key,
                        'category_emoji': category_data['emoji']
                    })
        
        # Search in custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            # Custom categories don't have predefined items, but they might have dynamic items
            dynamic_items = self.db.get_dynamic_category_items(category['category_key'])
            for item in dynamic_items:
                lang = self.get_user_language(user_id)
                item_name = item.get(lang, item.get('en', ''))
                if item_name and query_lower in item_name.lower():
                    item_en = item.get('en', item_name)
                    item_he = item.get('he', item_name)
                    results.append({
                        'item_name': item_en,
                        'hebrew_name': item_he,
                        'category': category_name,
                        'category_key': category['category_key'],
                        'category_emoji': category['emoji']
                    })
        
        # Remove duplicates
        unique_results = []
        seen = set()
        for result in results:
            key = (result['item_name'], result['category_key'])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results

    async def show_comprehensive_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                              query: str, category_results: List[Dict], list_results: List[Dict], 
                                              list_name: str, target_list_id: int):
        """Show comprehensive search results from both categories and list"""
        user_id = update.effective_user.id
        
        # Create message
        message = f"🔍 **Search Results for '{query}'**\n\n"
        
        # Show items found in categories (available to add)
        if category_results:
            message += f"📂 **Available in Categories:**\n"
            for result in category_results:
                message += f"• {result['category_emoji']} {result['item_name']} ({result['hebrew_name']}) - {result['category']}\n"
            message += "\n"
        
        # Show items found in current list (already added)
        if list_results:
            message += f"📋 **Already in {list_name}:**\n"
            for result in list_results:
                notes_text = f" - {result['notes']}" if result.get('notes') else ""
                message += f"• ✅ {result['item_name']}{notes_text}\n"
            message += "\n"
        
        # Create keyboard based on what was found
        keyboard = []
        
        if category_results:
            # Add buttons for items found in categories
            for result in category_results[:5]:  # Limit to 5 items to avoid too many buttons
                keyboard.append([InlineKeyboardButton(
                    f"➕ Add {result['item_name']}",
                    callback_data=f"add_item_{result['category_key']}_{result['item_name']}"
                )])
        
        if list_results:
            # Add buttons for items found in list (to remove)
            for result in list_results[:3]:  # Limit to 3 items
                keyboard.append([InlineKeyboardButton(
                    f"❌ Remove {result['item_name']}",
                    callback_data=f"remove_item_{target_list_id}_{result['item_name']}"
                )])
        
        # Add action buttons
        if not category_results and not list_results:
            # No results found - offer two options
            keyboard.append([
                InlineKeyboardButton(
                    "➕ Add to List",
                    callback_data="add_to_list_from_search"
                ),
                InlineKeyboardButton(
                    "💡 Suggest for Category",
                    callback_data="suggest_from_search"
                )
            ])
            message += "❌ **No items found**\n\nChoose how to add this item:"
        else:
            # Results found - add navigation buttons
            if category_results:
                keyboard.append([InlineKeyboardButton(
                    "📂 Browse Categories",
                    callback_data="categories"
                )])
            keyboard.append([InlineKeyboardButton(
                "📋 Back to List",
                callback_data=f"list_menu_{target_list_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    def search_items_in_list(self, query: str, list_id: int, user_id: int) -> List[Dict]:
        """Search for items within a specific list"""
        results = []
        query_lower = query.lower()
        
        # Get items from the specific list
        list_items = self.db.get_shopping_list_by_id(list_id)
        
        for item in list_items:
            item_name = item['name'].lower()
            if query_lower in item_name:
                # Format results to match the expected structure for show_search_results
                results.append({
                    'item_name': item['name'],  # Use 'item_name' for compatibility
                    'hebrew_name': item['name'],  # Same as English for now
                    'category': item['category'] or 'Other',
                    'category_key': item['category'] or 'other',
                    'category_emoji': '📦',  # Default emoji
                    'notes': item['notes'],
                    'added_by': item['added_by'],
                    'list_id': list_id
                })
        
        return results

    async def show_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, results: List[Dict], list_name: str = None):
        """Show search results"""
        user_id = update.effective_user.id
        
        if len(results) == 1:
            # Single result - show directly with action buttons
            result = results[0]
            message = self.get_message(user_id, 'search_item_found').format(
                item_name=result['item_name'],
                category=f"{result['category_emoji']} {result['category']}",
                hebrew_name=result['hebrew_name']
            )
            
            import urllib.parse
            # Check if this is a list-specific search
            list_id = result.get('list_id')
            if list_id:
                # For list-specific search, add to that specific list
                keyboard = [
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_add_to_the_list'),
                        callback_data=f"search_add_list_{list_id}_{result['category_key']}_{urllib.parse.quote(result['item_name'])}"
                    )],
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_back_to_list'),
                        callback_data=f"list_menu_{list_id}"
                    )]
                ]
            else:
                # For general search, use the old method
                keyboard = [
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_add_to_the_list'),
                        callback_data=f"search_add_{result['category_key']}_{urllib.parse.quote(result['item_name'])}"
                    )],
                    [InlineKeyboardButton(
                        self.get_message(user_id, 'btn_back_menu'),
                        callback_data="main_menu"
                    )]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)
            
        else:
            # Multiple results - show list with selection
            message = self.get_message(user_id, 'search_results').format(
                count=len(results),
                query=query
            )
            
            keyboard = []
            import urllib.parse
            for result in results[:10]:  # Limit to 10 results
                # Check if this is a list-specific search
                list_id = result.get('list_id')
                if list_id:
                    # For list-specific search, include list context in callback
                    keyboard.append([InlineKeyboardButton(
                        f"{result['category_emoji']} {result['item_name']} ({result['category']})",
                        callback_data=f"search_select_list_{list_id}_{result['category_key']}_{urllib.parse.quote(result['item_name'])}"
                    )])
                else:
                    # For general search, use the old method
                    keyboard.append([InlineKeyboardButton(
                        f"{result['category_emoji']} {result['item_name']} ({result['category']})",
                        callback_data=f"search_select_{result['category_key']}_{urllib.parse.quote(result['item_name'])}"
                    )])
            
            # Add back button - check if any result has list_id to determine context
            list_id = results[0].get('list_id') if results else None
            if list_id:
                keyboard.append([InlineKeyboardButton(
                    self.get_message(user_id, 'btn_back_to_list'),
                    callback_data=f"list_menu_{list_id}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    self.get_message(user_id, 'btn_back_menu'),
                    callback_data="main_menu"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def show_no_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, list_name: str = None):
        """Show no results message with options"""
        user_id = update.effective_user.id
        
        # Debug: Check if message exists
        try:
            message = self.get_message(user_id, 'search_no_results').format(query=query)
        except Exception as e:
            message = f"🔍 NO RESULTS FOUND in {list_name}\n\nNo items found matching '{query}'.\n\nWould you like to:"
            logging.error(f"Error getting search_no_results message: {e}")
        
        keyboard = []
        
        if not self.db.is_user_admin(user_id):
            keyboard.append([InlineKeyboardButton(
                "💡 Suggest New Item",
                callback_data="search_suggest_new"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'btn_add_new_item'),
                callback_data="new_item_direct"
            )])
        
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'),
            callback_data="main_menu"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /language command - show language selection"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        # Clear all waiting states when using language command
        self.clear_all_waiting_states(context)

        await self.show_language_selection(update, context)

    async def show_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show language selection menu"""
        user_id = update.effective_user.id
        current_lang = self.get_user_language(user_id)
        
        keyboard = []
        for lang_code, lang_info in LANGUAGES.items():
            current_marker = " ✅" if lang_code == current_lang else ""
            keyboard.append([InlineKeyboardButton(
                f"{lang_info['emoji']} {lang_info['name']}{current_marker}",
                callback_data=f"set_language_{lang_code}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        select_text = self.get_message(user_id, 'select_language')
        
        if update.message:
            await update.message.reply_text(select_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(select_text, reply_markup=reply_markup)

    # Multi-list functionality methods
    async def supermarket_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle supermarket list button/command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        # Clear all waiting states when opening supermarket menu
        self.clear_all_waiting_states(context)
        await self.show_supermarket_list(update, context)
    
    async def show_supermarket_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show supermarket list with actions"""
        # Use the new list menu system
        await self.show_list_menu(update, context, self.get_message(update.effective_user.id, 'supermarket_list'))
    
    async def new_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new list button/command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        await self.show_create_list_prompt(update, context)
    
    async def show_create_list_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show create list prompt"""
        user_id = update.effective_user.id
        context.user_data['waiting_for_list_name'] = True
        
        prompt_text = self.get_message(user_id, 'create_list_prompt')
        
        if update.message:
            await update.message.reply_text(prompt_text)
        elif update.callback_query:
            await update.callback_query.edit_message_text(prompt_text)
    
    async def process_list_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_name: str):
        """Process list name input"""
        context.user_data['waiting_for_list_name'] = False
        
        if not list_name.strip():
            await update.message.reply_text(self.get_message(update.effective_user.id, 'list_name_empty'))
            return
        
        # Check if list name already exists
        all_lists = self.db.get_all_lists()
        for existing_list in all_lists:
            if existing_list['name'].lower() == list_name.lower():
                await update.message.reply_text(self.get_message(update.effective_user.id, 'list_name_exists'))
                return
        
        context.user_data['new_list_name'] = list_name.strip()
        
        # Ask for description
        keyboard = [
            [InlineKeyboardButton(self.get_message(update.effective_user.id, 'btn_yes'), callback_data="add_description")],
            [InlineKeyboardButton(self.get_message(update.effective_user.id, 'btn_no'), callback_data="skip_description")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        prompt_text = self.get_message(update.effective_user.id, 'create_list_description').format(list_name=list_name)
        await update.message.reply_text(prompt_text, reply_markup=reply_markup)
    
    async def process_list_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
        """Process list description input"""
        context.user_data['waiting_for_list_description'] = False
        
        list_name = context.user_data.get('new_list_name')
        description = description.strip() if description else None
        
        # Create the list
        list_id = self.db.create_list(
            name=list_name,
            description=description,
            created_by=update.effective_user.id,
            list_type='custom'
        )
        
        if list_id:
            success_text = self.get_message(update.effective_user.id, 'list_created').format(
                list_name=list_name,
                description=description or 'No description'
            )
            # Handle both message and callback query cases
            if update.message:
                await update.message.reply_text(success_text)
            elif update.callback_query:
                await update.callback_query.message.reply_text(success_text)
            await self.show_main_menu(update, context)
        else:
            error_text = self.get_message(update.effective_user.id, 'list_creation_error')
            if update.message:
                await update.message.reply_text(error_text)
            elif update.callback_query:
                await update.callback_query.message.reply_text(error_text)
    
    async def my_lists_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle my lists button/command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        await self.show_my_lists(update, context)
    
    async def show_my_lists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's lists"""
        user_id = update.effective_user.id
        user_lists = self.db.get_user_lists(user_id)
        
        if not user_lists:
            message = self.get_message(user_id, 'my_lists_empty')
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]]
        else:
            message = self.get_message(user_id, 'my_lists_title')
            keyboard = []
            
            for list_info in user_lists:
                keyboard.append([InlineKeyboardButton(
                    f"📋 {list_info['name']}",
                    callback_data=f"list_actions_{list_info['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def manage_lists_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manage lists button/command (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return
        
        await self.show_manage_lists(update, context)
    
    async def show_manage_lists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all lists for admin management"""
        user_id = update.effective_user.id
        all_lists = self.db.get_all_lists()
        
        if not all_lists:
            message = self.get_message(user_id, 'manage_lists_empty')
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]]
        else:
            message = self.get_message(user_id, 'manage_lists_title')
            keyboard = []
            
            for list_info in all_lists:
                # Get item count
                items = self.db.get_shopping_list_by_id(list_info['id'])
                item_count = len(items)
                
                creator_name = list_info.get('creator_first_name') or list_info.get('creator_username') or 'Unknown'
                
                if list_info['description']:
                    list_text = self.get_message(user_id, 'list_info').format(
                        list_name=list_info['name'],
                        description=list_info['description'],
                        creator=creator_name,
                        created_at=list_info['created_at'][:10],  # Just the date
                        item_count=item_count
                    )
                else:
                    list_text = self.get_message(user_id, 'list_info_no_description').format(
                        list_name=list_info['name'],
                        creator=creator_name,
                        created_at=list_info['created_at'][:10],
                        item_count=item_count
                    )
                
                keyboard.append([InlineKeyboardButton(
                    list_text,
                    callback_data=f"list_actions_{list_info['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_list_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show actions for a specific list"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get item count
        items = self.db.get_shopping_list_by_id(list_id)
        item_count = len(items)
        
        # Admin-only actions (no basic user actions in admin menu)
        keyboard = [
            [InlineKeyboardButton(self.get_message(user_id, 'btn_edit_name'), callback_data=f"edit_list_name_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_edit_description'), callback_data=f"edit_list_description_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_view_statistics'), callback_data=f"list_statistics_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_export_list'), callback_data=f"export_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_reset_items'), callback_data=f"confirm_reset_list_{list_id}")]
        ]
        
        # Only allow deletion for custom lists (not supermarket list)
        if list_info['list_type'] != 'supermarket':
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_delete_list'), callback_data=f"confirm_delete_list_{list_id}")])
        
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_lists'), callback_data="my_lists")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = self.get_message(user_id, 'list_actions').format(list_name=list_info['name'])
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_categories_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show categories for adding items to a specific list"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Store the target list in context
        context.user_data['target_list_id'] = list_id
        
        keyboard = []
        
        # Add SEARCH button first for easy access
        keyboard.append([InlineKeyboardButton(
            self.get_message(user_id, 'btn_search'), 
            callback_data=f"search_list_{list_id}"
        )])
        
        # Add RECENTLY category second (if there are recent items)
        recent_items = self.db.get_recently_used_items()
        if recent_items:
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'recently_category'), 
                callback_data="category_recently"
            )])
        
        # Add predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"category_{category_key}"
            )])
        
        # Add custom categories from database
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category_name}",
                callback_data=f"category_{category['category_key']}"
            )])
        
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_lists'), callback_data="my_lists")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"📋 Add items to: {list_info['name']}\n\n" + self.get_message(user_id, 'categories_title')
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def select_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Select a list for adding items"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Store the selected list
        context.user_data['selected_list_id'] = list_id
        
        message = self.get_message(user_id, 'list_selected').format(list_name=list_info['name'])
        await update.callback_query.edit_message_text(message)
        await self.show_main_menu(update, context)
    
    async def view_list_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """View items in a specific list"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        
        if not items:
            message = f"📝 {list_info['name']}\n\n{self.get_message(user_id, 'list_empty')}"
        else:
            message = f"📝 {list_info['name']}\n\n"
            current_category = None
            
            for item in items:
                if item['category'] != current_category:
                    current_category = item['category']
                    category_name = self.get_category_name(user_id, current_category) if current_category else 'Custom'
                    message += f"\n{category_name}:\n"
                
                message += f"• {item['name']}"
                if item['notes']:
                    message += f" ({item['notes']})"
                if item['item_notes']:
                    for note_info in item['item_notes']:
                        message += f"\n  📝 {note_info['note']} - {note_info['user_name']}"
                message += "\n"
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_lists'), callback_data="my_lists")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_edit_list_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show edit list name prompt"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        context.user_data['waiting_for_edit_list_name'] = True
        context.user_data['editing_list_id'] = list_id
        
        prompt_text = self.get_message(user_id, 'edit_list_name_prompt').format(current_name=list_info['name'])
        await update.callback_query.edit_message_text(prompt_text)
    
    async def process_edit_list_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_name: str):
        """Process edit list name input"""
        context.user_data['waiting_for_edit_list_name'] = False
        list_id = context.user_data.pop('editing_list_id')
        
        if not new_name.strip():
            await update.message.reply_text(self.get_message(update.effective_user.id, 'list_name_empty'))
            return
        
        if self.db.update_list_name(list_id, new_name.strip()):
            success_text = self.get_message(update.effective_user.id, 'list_name_updated').format(new_name=new_name.strip())
            await update.message.reply_text(success_text)
            await self.show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ Error updating list name.")
    
    async def show_edit_list_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show edit list description prompt"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        context.user_data['waiting_for_edit_list_description'] = True
        context.user_data['editing_list_id'] = list_id
        
        current_description = list_info.get('description') or 'No description'
        prompt_text = self.get_message(user_id, 'edit_list_description_prompt').format(
            list_name=list_info['name'],
            current_description=current_description
        )
        await update.callback_query.edit_message_text(prompt_text)
    
    async def process_edit_list_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_description: str):
        """Process edit list description input"""
        context.user_data['waiting_for_edit_list_description'] = False
        list_id = context.user_data.pop('editing_list_id')
        
        # Update description in database (you'll need to add this method to database.py)
        # For now, just show success message
        success_text = self.get_message(update.effective_user.id, 'list_description_updated')
        await update.message.reply_text(success_text)
        await self.show_main_menu(update, context)
    
    async def show_list_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show detailed statistics for a list"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get all items in the list
        items = self.db.get_shopping_list_by_id(list_id)
        
        # Calculate statistics
        total_items = len(items)
        items_with_notes = len([item for item in items if item.get('notes')])
        items_without_notes = total_items - items_with_notes
        
        # Count items by category
        category_counts = {}
        user_counts = {}
        
        for item in items:
            category = item.get('category', 'Other')
            category_counts[category] = category_counts.get(category, 0) + 1
            
            added_by = item.get('added_by', 'Unknown')
            user_counts[added_by] = user_counts.get(added_by, 0) + 1
        
        # Create statistics message
        stats_message = f"📊 **{list_info['name']} Statistics**\n\n"
        stats_message += f"📈 **Overview:**\n"
        stats_message += f"• Total Items: {total_items}\n"
        stats_message += f"• With Notes: {items_with_notes}\n"
        stats_message += f"• Without Notes: {items_without_notes}\n\n"
        
        if category_counts:
            stats_message += f"📂 **By Category:**\n"
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                category_name = self.get_category_name(user_id, category)
                stats_message += f"• {category_name}: {count}\n"
            stats_message += "\n"
        
        if user_counts:
            stats_message += f"👥 **By User:**\n"
            for user_id_val, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True):
                # Get user name from database
                user_info = self.db.get_user_by_id(user_id_val)
                user_name = user_info.get('first_name') or user_info.get('username') or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=user_id_val)
                stats_message += f"• {user_name}: {count}\n"
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list_actions'), callback_data=f"list_actions_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(stats_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_remove_items_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show menu for removing items from list or categories"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get items in the list
        items = self.db.get_shopping_list_by_id(list_id)
        
        if not items:
            message = f"📋 **{list_info['name']}**\n\n📝 This list is empty. Nothing to remove from the list."
            
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        # Group items by category for easier removal
        grouped_items = {}
        for item in items:
            category = item.get('category', 'Other')
            if category not in grouped_items:
                grouped_items[category] = []
            grouped_items[category].append(item)
        
        message = f"🗑️ **Remove Items from {list_info['name']}**\n\n"
        message += self.get_message(user_id, 'choose_what_remove')
        
        keyboard = []
        
        # Add buttons for each category
        for category, category_items in grouped_items.items():
            category_name = self.get_category_name(user_id, category)
            keyboard.append([InlineKeyboardButton(
                f"📂 {category_name} ({len(category_items)} items)", 
                callback_data=f"remove_category_{list_id}_{category}"
            )])
        
        # Add individual item removal option
        keyboard.append([InlineKeyboardButton(
            "🔍 Remove Individual Items", 
            callback_data=f"remove_individual_{list_id}"
        )])
        
        # Add back button
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def confirm_remove_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, category: str):
        """Confirm removal of all items from a category"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get items in this category
        items = self.db.get_shopping_list_by_id(list_id)
        category_items = [item for item in items if item.get('category') == category]
        
        if not category_items:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'no_items_found_category'))
            return
        
        category_name = self.get_category_name(user_id, category)
        
        message = f"🗑️ **Confirm Category Removal**\n\n"
        message += f"**Category:** {category_name}\n"
        message += f"**Items to remove:** {len(category_items)}\n\n"
        message += "**Items:**\n"
        for item in category_items[:10]:  # Show first 10 items
            message += f"• {item['name']}\n"
        if len(category_items) > 10:
            message += f"... and {len(category_items) - 10} more items\n"
        
        message += f"\n⚠️ This will remove ALL items from the {category_name} category."
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Remove All", callback_data=f"confirm_remove_category_{list_id}_{category}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"remove_items_{list_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_individual_items_removal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show individual items for removal"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get items in the list
        items = self.db.get_shopping_list_by_id(list_id)
        
        if not items:
            message = f"📋 **{list_info['name']}**\n\n📝 This list is empty. Nothing to remove."
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        message = f"🔍 **Remove Individual Items from {list_info['name']}**\n\n"
        message += self.get_message(user_id, 'select_items_remove')
        
        keyboard = []
        
        # Add items in groups of 2 for better layout
        for i in range(0, len(items), 2):
            row = []
            for j in range(2):
                if i + j < len(items):
                    item = items[i + j]
                    item_name = item['name'][:20] + "..." if len(item['name']) > 20 else item['name']
                    row.append(InlineKeyboardButton(
                        f"🗑️ {item_name}", 
                        callback_data=f"remove_item_{list_id}_{item['id']}"
                    ))
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🏠 Back to Remove Menu", callback_data=f"remove_items_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def remove_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, category: str):
        """Remove all items from a category"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get items in this category
        items = self.db.get_shopping_list_by_id(list_id)
        category_items = [item for item in items if item.get('category') == category]
        
        if not category_items:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'no_items_found_category'))
            return
        
        # Remove all items from this category
        removed_count = 0
        for item in category_items:
            if self.db.delete_item(item['id']):
                removed_count += 1
        
        category_name = self.get_category_name(user_id, category)
        
        # Notify all users about the removal
        authorized_users = self.db.get_all_authorized_users()
        for auth_user in authorized_users:
            try:
                user_lang = self.db.get_user_language(auth_user['user_id'])
                if user_lang == 'he':
                    notification = f"🗑️ מנהל הסיר {removed_count} פריטים מהקטגוריה '{category_name}' ברשימה '{list_info['name']}'"
                else:
                    notification = f"🗑️ Admin removed {removed_count} items from '{category_name}' category in '{list_info['name']}' list"
                
                await self.application.bot.send_message(chat_id=auth_user['user_id'], text=notification)
            except Exception as e:
                logging.error(f"Error sending removal notification to user {auth_user['user_id']}: {e}")
        
        success_message = f"✅ Successfully removed {removed_count} items from {category_name} category."
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(success_message, reply_markup=reply_markup)
    
    async def remove_individual_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, item_id: int):
        """Remove an individual item"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get the item to remove
        items = self.db.get_shopping_list_by_id(list_id)
        item_to_remove = None
        for item in items:
            if item['id'] == item_id:
                item_to_remove = item
                break
        
        if not item_to_remove:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'item_not_found'))
            return
        
        # Remove the item
        if self.db.delete_item(item_id):
            # Notify all users about the removal
            authorized_users = self.db.get_all_authorized_users()
            for auth_user in authorized_users:
                try:
                    user_lang = self.db.get_user_language(auth_user['user_id'])
                    if user_lang == 'he':
                        notification = f"🗑️ מנהל הסיר את הפריט '{item_to_remove['name']}' מהרשימה '{list_info['name']}'"
                    else:
                        notification = f"🗑️ Admin removed item '{item_to_remove['name']}' from '{list_info['name']}' list"
                    
                    await self.application.bot.send_message(chat_id=auth_user['user_id'], text=notification)
                except Exception as e:
                    logging.error(f"Error sending removal notification to user {auth_user['user_id']}: {e}")
            
            success_message = f"✅ Successfully removed '{item_to_remove['name']}' from the list."
            keyboard = [[InlineKeyboardButton("🏠 Back to Remove Menu", callback_data=f"remove_items_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(success_message, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'remove_item_failed'))
    
    
    
    
    
    async def confirm_delete_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show delete list confirmation (with supermarket list protection)"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # PROTECTION: Never allow deletion of supermarket list
        if list_info['list_type'] == 'supermarket':
            protected_message = self.get_message(user_id, 'supermarket_protected').format(
                supermarket_list=self.get_message(user_id, 'supermarket_list')
            )
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_lists'), callback_data="my_lists")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(protected_message, reply_markup=reply_markup)
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        item_count = len(items)
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete_list_{list_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"list_actions_{list_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = self.get_message(user_id, 'confirm_delete_list').format(
            list_name=list_info['name'],
            item_count=item_count
        )
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def confirm_reset_list_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show reset list items confirmation"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        item_count = len(items)
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Reset", callback_data=f"reset_list_{list_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"list_actions_{list_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = self.get_message(user_id, 'confirm_reset_list').format(
            list_name=list_info['name'],
            item_count=item_count
        )
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def export_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Export list items and send to all admins and authorized users"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        
        # Get current date/time
        from datetime import datetime
        export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not items:
            message = self.get_message(user_id, 'list_export_empty').format(
                list_name=list_info['name'],
                export_date=export_date
            )
        else:
            items_text = ""
            current_category = None
            
            for item in items:
                if item['category'] != current_category:
                    current_category = item['category']
                    category_name = self.get_category_name(user_id, current_category) if current_category else 'Custom'
                    items_text += f"\n{category_name}:\n"
                
                items_text += f"• {item['name']}"
                if item['notes']:
                    items_text += f" ({item['notes']})"
                if item['item_notes']:
                    for note_info in item['item_notes']:
                        items_text += f"\n  📝 {note_info['note']} - {note_info['user_name']}"
                items_text += "\n"
            
            message = self.get_message(user_id, 'list_export').format(
                list_name=list_info['name'],
                export_date=export_date,
                items_text=items_text
            )
        
        # Send export to all admins and authorized users
        all_users = self.db.get_all_authorized_users()
        sent_count = 0
        
        for user in all_users:
            try:
                user_lang = self.get_user_language(user['user_id'])
                if user_lang == 'he':
                    # Send Hebrew version
                    if not items:
                        user_message = self.get_message(user['user_id'], 'list_export_empty').format(
                            list_name=list_info['name'],
                            export_date=export_date
                        )
                    else:
                        user_message = self.get_message(user['user_id'], 'list_export').format(
                            list_name=list_info['name'],
                            export_date=export_date,
                            items_text=items_text
                        )
                else:
                    # Send English version
                    user_message = message
                
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=user_message
                )
                sent_count += 1
            except Exception as e:
                logging.error(f"Failed to send export to user {user['user_id']}: {e}")
        
        # Confirm to the user who requested the export
        confirm_message = f"📤 Export sent to {sent_count} users successfully!"
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_lists'), callback_data="my_lists")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(confirm_message, reply_markup=reply_markup)
    
    async def show_list_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_name: str):
        """Show menu for a specific list with relevant options"""
        user_id = update.effective_user.id
        
        # Find the list by name - with special handling for supermarket list
        all_lists = self.db.get_all_lists()
        target_list = None
        
        # Special handling for supermarket list (by name or by type)
        if list_name == self.get_message(user_id, 'supermarket_list') or list_name == self.get_message(user_id, 'supermarket_list_en'):
            # Find supermarket list by type (more reliable than name)
            for list_info in all_lists:
                if list_info['list_type'] == 'supermarket':
                    target_list = list_info
                    break
        else:
            # Regular list lookup by name
            for list_info in all_lists:
                if list_info['name'] == list_name:
                    target_list = list_info
                    break
        
        if not target_list:
            if update.message:
                await update.message.reply_text("❌ List not found.")
            elif update.callback_query:
                await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        list_id = target_list['id']
        
        # Create keyboard with list-specific options
        keyboard = [
            [InlineKeyboardButton("📝 Templates", callback_data=f"templates_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_add_item'), callback_data=f"categories_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_search'), callback_data=f"search_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_my_items'), callback_data=f"my_items_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_view_items'), callback_data=f"view_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_summary'), callback_data=f"summary_list_{list_id}")]
        ]
        
        # Add admin-only options (only list-specific functions)
        if self.db.is_user_admin(user_id):
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_export'), callback_data=f"export_list_{list_id}")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_reset_items'), callback_data=f"confirm_reset_list_{list_id}")])
            keyboard.append([InlineKeyboardButton("🗑️ Remove Items", callback_data=f"remove_items_{list_id}")])
            
            # Add maintenance mode only for supermarket list
            if target_list['list_type'] == 'supermarket':
                keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_maintenance_mode'), callback_data="maintenance_mode")])
            
            # Only allow deletion for custom lists (not supermarket list)
            if target_list['list_type'] != 'supermarket':
                keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_delete_list'), callback_data=f"confirm_delete_list_{list_id}")])
        
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_main_menu'), callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get item count for display
        items = self.db.get_shopping_list_by_id(list_id)
        item_count = len(items)
        
        message = f"📋 **{list_name}**\n\n"
        message += self.get_message(user_id, 'items_count').format(count=item_count) + "\n"
        message += self.get_message(user_id, 'list_type').format(type=target_list['list_type'].title()) + "\n\n"
        message += self.get_message(user_id, 'choose_action')
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_list_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show summary for a specific list"""
        user_id = update.effective_user.id
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        
        if not items:
            message = f"📋 {list_info['name']}\n\nNo items in this list yet."
        else:
            # Group items by category
            categories = {}
            for item in items:
                category = item['category'] or 'Other'
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)
            
            message = f"📋 {list_info['name']} Summary\n\n"
            message += self.get_message(user_id, 'total_items').format(count=len(items)) + "\n\n"
            
            for category, category_items in categories.items():
                message += f"{category} {self.get_message(user_id, 'items_count_inline').format(count=len(category_items))}:\n"
                for item in category_items:
                    message += f"• {item['name']}"
                    if item['notes']:
                        message += f" ({item['notes']})"
                    message += "\n"
                message += "\n"
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_search_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show search interface for a specific list with method selection"""
        user_id = update.effective_user.id
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        # Set the target list for search
        context.user_data['search_list_id'] = list_id
        
        # Create keyboard with text and voice search options
        keyboard = [
            [InlineKeyboardButton(self.get_message(user_id, 'btn_text_search'), callback_data=f"text_search_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_voice_search'), callback_data=f"voice_search_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_list'), callback_data=f"list_menu_{list_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🔍 **Search in {list_info['name']}**\n\n"
        message += self.get_message(user_id, 'search_prompt')
        message += "\n\nChoose search method:"
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin menu with all admin controls"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return
        
        keyboard = [
            [InlineKeyboardButton(self.get_message(user_id, 'btn_manage_users'), callback_data="manage_users")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_manage_lists'), callback_data="manage_lists")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = self.get_message(user_id, 'admin_controls_title')
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    # Maintenance mode methods
    async def maintenance_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle maintenance mode button/command (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
        
        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return
        
        await self.show_maintenance_mode(update, context)

    async def show_admin_management_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin management menu with all management functions"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Get pending counts for badges
        total_pending = self.db.get_total_pending_suggestions_count()
        item_suggestions_pending = self.db.get_pending_item_suggestions_count()
        category_suggestions_pending = self.db.get_pending_category_suggestions_count()
        
        # Create buttons with badges
        keyboard = [
            [InlineKeyboardButton("➕ New Item", callback_data="new_item_admin")],
            [InlineKeyboardButton("📝 Manage Items", callback_data="manage_items_admin")],
            [InlineKeyboardButton(f"💡 Manage Items Suggested ({item_suggestions_pending})", callback_data="manage_suggestions")],
            [InlineKeyboardButton("📂 New Category", callback_data="new_category_admin")],
            [InlineKeyboardButton("🗂️ Manage Categories", callback_data="manage_categories")],
            [InlineKeyboardButton(f"💭 Manage Categories Suggested ({category_suggestions_pending})", callback_data="manage_category_suggestions")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"⚙️ **Management** ({total_pending})\n\nChoose what you want to manage:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_user_management_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user management menu with suggestion functions"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_authorized(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'not_registered'))
            return
        
        keyboard = [
            [InlineKeyboardButton("💡 Suggest New Item", callback_data="suggest_item_user")],
            [InlineKeyboardButton("📂 Suggest New Category", callback_data="suggest_category_user")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "👥 **Suggestions**\n\nChoose what you want to suggest:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_categories_for_new_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show categories for admin to add new items"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        keyboard = []
        
        # Add predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"new_item_category_{category_key}"
            )])
        
        # Add custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category_name}",
                callback_data=f"new_item_category_{category['category_key']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Management", callback_data="admin_management")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "➕ **Add New Item (Admin)**\n\nSelect a category to add a new item:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_manage_items_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin item management options"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        keyboard = [
            [InlineKeyboardButton("✏️ Rename Items", callback_data="rename_items_admin")],
            [InlineKeyboardButton("🗑️ Delete Permanent Items", callback_data="delete_permanent_items")],
            [InlineKeyboardButton("🔙 Back to Management", callback_data="admin_management")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "📝 **Manage Items (Admin)**\n\nChoose what you want to manage:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_categories_for_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show categories for user to suggest new items"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_authorized(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'not_registered'))
            return
        
        keyboard = []
        
        # Add predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"suggest_category_{category_key}"
            )])
        
        # Add custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category_name}",
                callback_data=f"suggest_category_{category['category_key']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Suggestions", callback_data="user_management")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "💡 **Suggest New Item**\n\nSelect a category to suggest a new item:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')



    async def show_delete_permanent_items_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show menu to select which category to delete permanent items from"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        keyboard = []
        
        # Add predefined categories
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"delete_permanent_items_{category_key}"
            )])
        
        # Add custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_name = self.get_category_name(user_id, category['category_key'])
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category_name}",
                callback_data=f"delete_permanent_items_{category['category_key']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Management", callback_data="admin_management")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "🗑️ **Delete Permanent Items**\n\nSelect a category to permanently delete items from:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_permanent_items_in_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show predefined items in a category for deletion"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Get predefined items from the category
        if category_key not in CATEGORIES:
            message = "❌ Category not found."
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.edit_message_text(message)
            return
        
        category_data = CATEGORIES[category_key]
        category_name = self.get_category_name(user_id, category_key)
        
        # Get items in user's language (show all items, including deleted ones for admin deletion)
        items = category_data['items'][self.get_user_language(user_id)]
        
        # Filter out already deleted items to avoid duplicates
        deleted_items = self.db.get_deleted_items_by_category(category_key)
        available_items = [item for item in items if item not in deleted_items]
        
        if not available_items:
            message = f"📂 **{category_name}**\n\nAll items in this category have already been deleted."
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Delete Permanent Items", callback_data="delete_permanent_items")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        keyboard = []
        
        for item in available_items:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {item}",
                callback_data=f"confirm_delete_permanent_item_{category_key}_{item}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Delete Permanent Items", callback_data="delete_permanent_items")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"🗑️ **Delete Items from {category_name}**\n\nSelect an item to permanently remove from this category:"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def confirm_delete_permanent_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, item_name: str):
        """Confirm deletion of a predefined item from category"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        category_name = self.get_category_name(user_id, category_key)
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete Permanently", callback_data=f"delete_permanent_item_{category_key}_{item_name}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"delete_permanent_items_{category_key}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"⚠️ **Confirm Permanent Deletion**\n\nAre you sure you want to permanently remove:\n\n**{item_name}**\n\nfrom the **{category_name}** category?\n\nThis item will no longer appear in the 'Add Item' options!"
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def delete_permanent_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, item_name: str):
        """Delete a predefined item from category"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            if update.message:
                await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            elif update.callback_query:
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Check if category exists
        if category_key not in CATEGORIES:
            message = "❌ Category not found."
            if update.message:
                await update.message.reply_text(message)
            elif update.callback_query:
                await update.callback_query.edit_message_text(message)
            return
        
        category_name = self.get_category_name(user_id, category_key)
        
        # Add the item to deleted items list (we'll store this in the database)
        success = self.db.add_deleted_item(category_key, item_name, user_id)
        
        if success:
            message = f"✅ **Item Deleted Successfully**\n\n**{item_name}** has been permanently removed from the **{category_name}** category.\n\nThis item will no longer appear in the 'Add Item' options!"
            
            # Notify all authorized users
            await self.notify_item_deletion(item_name, category_name)
        else:
            message = "❌ Failed to delete item. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Delete Permanent Items", callback_data="delete_permanent_items")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def notify_item_deletion(self, item_name: str, category: str):
        """Notify all authorized users about item deletion"""
        try:
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            for user in users:
                try:
                    message = f"🗑️ **Item Deleted**\n\n**{item_name}** has been permanently deleted from the **{category}** category."
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about item deletion: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about item deletion: {e}")

    async def notify_list_reset(self, list_name: str, list_id: int):
        """Notify all authorized users about list reset"""
        try:
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"🔄 **רשימה אופסה**\n\nהרשימה **{list_name}** אופסה על ידי מנהל.\nכל הפריטים הוסרו מהרשימה."
                    else:
                        message = f"🔄 **List Reset**\n\nThe **{list_name}** list has been reset by an admin.\nAll items have been removed from the list."
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about list reset: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about list reset: {e}")

    async def notify_list_deletion(self, list_name: str, list_id: int):
        """Notify all authorized users about list deletion"""
        try:
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"🗑️ **רשימה נמחקה**\n\nהרשימה **{list_name}** נמחקה על ידי מנהל.\nהרשימה לא קיימת יותר."
                    else:
                        message = f"🗑️ **List Deleted**\n\nThe **{list_name}** list has been deleted by an admin.\nThe list no longer exists."
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about list deletion: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about list deletion: {e}")


    async def confirm_remove_permanent_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Confirm removal of a permanent category"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Get category info
        category_info = self.db.get_custom_category(category_key)
        if not category_info:
            await update.callback_query.edit_message_text("❌ Category not found.")
            return
        
        category_name = self.get_category_name(user_id, category_key)
        
        # Check if category has items in any lists
        items_count = self.db.count_items_in_category(category_key)
        
        message = f"🗑️ **Remove Category Permanently**\n\n"
        message += f"📂 Category: {category_info['emoji']} {category_name}\n"
        message += f"📊 Items in lists: {items_count}\n\n"
        
        if items_count > 0:
            message += f"⚠️ **WARNING:** This category has {items_count} items in shopping lists.\n"
            message += f"Removing this category will also remove all these items from all lists.\n\n"
        
        message += "Are you sure you want to permanently remove this category?"
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Remove Permanently", callback_data=f"confirm_remove_permanent_category_{category_key}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="remove_categories_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def remove_permanent_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Remove a category permanently"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Get category info before deletion
        category_info = self.db.get_custom_category(category_key)
        if not category_info:
            await update.callback_query.edit_message_text("❌ Category not found.")
            return
        
        category_name = self.get_category_name(user_id, category_key)
        
        # Remove the category
        success = self.db.delete_custom_category(category_key)
        
        if success:
            message = f"✅ **Category Removed Successfully**\n\n"
            message += f"📂 Category: {category_info['emoji']} {category_name}\n"
            message += f"🗑️ All items from this category have been removed from all lists.\n\n"
            message += f"The category has been permanently deleted."
            
            # Notify all users about the category removal
            await self.notify_category_removal(category_name, category_info['emoji'])
        else:
            message = "❌ Error removing category. Please try again."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin Management", callback_data="admin_management")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def notify_category_removal(self, category_name: str, emoji: str):
        """Notify all users about category removal"""
        try:
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            message = f"📢 **Category Removed**\n\n"
            message += f"🗑️ Category: {emoji} {category_name}\n"
            message += f"👤 Removed by: Admin\n\n"
            message += f"All items from this category have been removed from all shopping lists."
            
            for user in users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']}: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about category removal: {e}")
    
    async def show_maintenance_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show maintenance mode options"""
        user_id = update.effective_user.id
        maintenance = self.db.get_maintenance_mode(1)  # Supermarket list
        
        keyboard = []
        
        if maintenance:
            # Show current schedule and options
            schedule_text = f"{maintenance['scheduled_day']} at {maintenance['scheduled_time']}"
            message = self.get_message(user_id, 'maintenance_mode_enabled').format(
                schedule=schedule_text,
                next_reset=f"{maintenance['scheduled_day']} {maintenance['scheduled_time']}"
            )
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_view_schedule'), callback_data="view_maintenance_schedule")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_disable_maintenance'), callback_data="disable_maintenance")])
        else:
            # Show setup option
            message = self.get_message(user_id, 'maintenance_mode_disabled')
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_set_schedule'), callback_data="set_maintenance_schedule")])
        
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_set_maintenance_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show day selection for maintenance schedule"""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton(self.get_message(user_id, "day_monday"), callback_data="maintenance_day_Monday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_tuesday"), callback_data="maintenance_day_Tuesday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_wednesday"), callback_data="maintenance_day_Wednesday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_thursday"), callback_data="maintenance_day_Thursday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_friday"), callback_data="maintenance_day_Friday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_saturday"), callback_data="maintenance_day_Saturday")],
            [InlineKeyboardButton(self.get_message(user_id, "day_sunday"), callback_data="maintenance_day_Sunday")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = self.get_message(user_id, 'set_maintenance_schedule')
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_maintenance_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show time selection for maintenance schedule"""
        user_id = update.effective_user.id
        
        # Common shopping times
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
        
        keyboard = []
        for i in range(0, len(times), 3):
            row = []
            for j in range(3):
                if i + j < len(times):
                    row.append(InlineKeyboardButton(times[i + j], callback_data=f"maintenance_time_{times[i + j]}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="set_maintenance_schedule")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        day = context.user_data.get('maintenance_day', 'Unknown')
        message = f"⏰ Select time for {day}:\n\nChoose when you typically go shopping:"
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def confirm_maintenance_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE, time: str):
        """Confirm maintenance schedule"""
        user_id = update.effective_user.id
        day = context.user_data.get('maintenance_day', 'Unknown')
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data="confirm_maintenance_schedule")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_maintenance_schedule")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"📅 Confirm Maintenance Schedule\n\nDay: {day}\nTime: {time}\n\nThis will remind you to reset the supermarket list every {day} at {time}."
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        
        # Store the time in context
        context.user_data['maintenance_time'] = time
    
    async def save_maintenance_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save the maintenance schedule"""
        user_id = update.effective_user.id
        day = context.user_data.get('maintenance_day')
        time = context.user_data.get('maintenance_time')
        
        if not day or not time:
            await update.callback_query.edit_message_text("❌ Error: Missing schedule information.")
            return
        
        success = self.db.set_maintenance_mode(1, day, time, user_id)  # Supermarket list
        
        if success:
            message = self.get_message(user_id, 'maintenance_schedule_set').format(
                schedule=f"{day} at {time}",
                next_reminder=f"{day} {time}"
            )
            # Clear context data
            context.user_data.pop('maintenance_day', None)
            context.user_data.pop('maintenance_time', None)
        else:
            message = self.get_message(user_id, 'maintenance_schedule_error')
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_maintenance_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current maintenance schedule details"""
        user_id = update.effective_user.id
        maintenance = self.db.get_maintenance_mode(1)
        
        if not maintenance:
            message = self.get_message(user_id, 'maintenance_mode_disabled')
        else:
            last_reminder = maintenance['last_reminder'] or 'Never'
            message = f"📅 Current Maintenance Schedule\n\nDay: {maintenance['scheduled_day']}\nTime: {maintenance['scheduled_time']}\nLast reminder: {last_reminder}\nReminders sent: {maintenance['reminder_count']}"
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def disable_maintenance_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disable maintenance mode"""
        user_id = update.effective_user.id
        
        success = self.db.deactivate_maintenance_mode(1)  # Supermarket list
        
        if success:
            message = self.get_message(user_id, 'maintenance_disabled')
        else:
            message = "❌ Error disabling maintenance mode."
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def confirm_maintenance_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm maintenance reset"""
        user_id = update.effective_user.id
        
        # Reset the supermarket list
        if self.db.reset_list(1):  # Supermarket list
            message = self.get_message(user_id, 'maintenance_reset_confirmed').format(supermarket_list=self.get_message(user_id, 'supermarket_list'))
            # Update maintenance reminder
            maintenance = self.db.get_maintenance_mode(1)
            if maintenance:
                self.db.update_maintenance_reminder(maintenance['id'])
            # Notify all users
            await self.notify_users_list_reset(update, context, self.get_message(update.effective_user.id, 'supermarket_list'))
        else:
            message = "❌ Error resetting list."
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def decline_maintenance_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Decline maintenance reset"""
        user_id = update.effective_user.id
        
        message = self.get_message(user_id, 'maintenance_reset_declined')
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="maintenance_mode")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def test_maintenance_notification_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test maintenance notification system (admin only)"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text("❌ Only admins can test maintenance notifications.")
            return
        
        # Send test notification to all admins
        await self.send_maintenance_notification_to_admins(context, "Friday", "14:00")
        
        message = self.get_message(user_id, 'maintenance_notification_sent')
        await update.message.reply_text(message)
    
    async def delete_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete commands like /delete_11, /delete_25, etc."""
        user_id = update.effective_user.id
        command_text = update.message.text
        
        # Debug logging
        logging.info(f"Delete command received: {command_text} from user {user_id}")
        
        # Check if user is admin
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text("❌ Only admins can delete items.")
            return
        
        # Extract item ID from command
        try:
            item_id = int(command_text.replace('/delete_', ''))
        except ValueError:
            await update.message.reply_text("❌ Invalid delete command format.")
            return
        
        # Get item info before deletion for notification
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT item_name, category FROM shopping_items WHERE id = ?', (item_id,))
                result = cursor.fetchone()
                if not result:
                    await update.message.reply_text("❌ Item not found.")
                    return
                item_name, category = result
        except Exception as e:
            logging.error(f"Error getting item info: {e}")
            await update.message.reply_text("❌ Error getting item information.")
            return
        
        # Delete the item
        deleted_item_name = self.db.delete_item(item_id)
        
        if deleted_item_name:
            # Notify all users about the deletion
            await self.notify_item_deletion(item_name, category or 'Unknown')
            await update.message.reply_text(f"✅ Item '{item_name}' deleted successfully.")
        else:
            await update.message.reply_text("❌ Failed to delete item.")
    
    # Category Creation Methods
    async def new_category_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /newcategory command - Create a new custom category (admin only)"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text("❌ Only admins can create new categories.")
            return
        
        await self.start_category_creation(update, context)
    
    async def manage_categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /managecategories command - Manage custom categories (admin only)"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text("❌ Only admins can manage categories.")
            return
        
        await self.show_manage_categories(update, context, back_to="main_menu")
    
    async def start_category_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the category creation process"""
        user_id = update.effective_user.id
        
        # Clear any previous category creation data
        context.user_data.pop('creating_category', None)
        context.user_data.pop('category_name', None)
        context.user_data.pop('category_emoji', None)
        context.user_data.pop('category_hebrew', None)
        
        # Set flag to indicate we're creating a category
        context.user_data['creating_category'] = True
        
        message = self.get_message(user_id, 'new_category_title')
        
        # Add cancel button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_cancel'),
            callback_data="cancel_category_creation"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_name: str):
        """Process category name input"""
        user_id = update.effective_user.id
        
        if not category_name.strip():
            await update.message.reply_text("❌ Please provide a category name.")
            return
        
        # Check if category already exists (in predefined or custom)
        category_key = category_name.lower().replace(' ', '_').replace('-', '_')
        
        # Check predefined categories
        if category_key in CATEGORIES:
            await update.message.reply_text(
                self.get_message(user_id, 'category_already_exists').format(category_name=category_name)
            )
            return
        
        # Check custom categories
        if self.db.get_custom_category(category_key):
            await update.message.reply_text(
                self.get_message(user_id, 'category_already_exists').format(category_name=category_name)
            )
            return
        
        # Store category name and ask for emoji
        context.user_data['category_name'] = category_name.strip()
        context.user_data['category_key'] = category_key
        
        await self.ask_for_category_emoji(update, context)
    
    async def ask_for_category_emoji(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user to choose an emoji for the category"""
        user_id = update.effective_user.id
        category_name = context.user_data.get('category_name', '')
        
        message = self.get_message(user_id, 'new_category_emoji').format(category_name=category_name)
        
        # Add common emoji buttons
        keyboard = [
            [InlineKeyboardButton("📱", callback_data="emoji_📱"),
             InlineKeyboardButton("💻", callback_data="emoji_💻"),
             InlineKeyboardButton("🎮", callback_data="emoji_🎮"),
             InlineKeyboardButton("📚", callback_data="emoji_📚")],
            [InlineKeyboardButton("🏠", callback_data="emoji_🏠"),
             InlineKeyboardButton("🚗", callback_data="emoji_🚗"),
             InlineKeyboardButton("✈️", callback_data="emoji_✈️"),
             InlineKeyboardButton("🎉", callback_data="emoji_🎉")],
            [InlineKeyboardButton("🎨", callback_data="emoji_🎨"),
             InlineKeyboardButton("🎵", callback_data="emoji_🎵"),
             InlineKeyboardButton("🏃", callback_data="emoji_🏃"),
             InlineKeyboardButton("🍽️", callback_data="emoji_🍽️")],
            [InlineKeyboardButton("📦", callback_data="emoji_📦"),
             InlineKeyboardButton("🔧", callback_data="emoji_🔧"),
             InlineKeyboardButton("💡", callback_data="emoji_💡"),
             InlineKeyboardButton("⭐", callback_data="emoji_⭐")],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_cancel'),
                callback_data="cancel_category_creation"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_category_emoji(self, update: Update, context: ContextTypes.DEFAULT_TYPE, emoji: str):
        """Process emoji selection"""
        user_id = update.effective_user.id
        
        # Store emoji and ask for Hebrew translation
        context.user_data['category_emoji'] = emoji
        
        await self.ask_for_category_hebrew(update, context)
    
    async def ask_for_category_hebrew(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user for Hebrew translation"""
        user_id = update.effective_user.id
        category_name = context.user_data.get('category_name', '')
        
        message = self.get_message(user_id, 'new_category_hebrew').format(category_name=category_name)
        
        # Add skip button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_skip'),
            callback_data="skip_hebrew_translation"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_category_hebrew(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hebrew_name: str):
        """Process Hebrew translation input"""
        user_id = update.effective_user.id
        
        # Store Hebrew translation and create category
        context.user_data['category_hebrew'] = hebrew_name.strip()
        
        await self.create_custom_category(update, context)
    
    async def create_custom_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create the custom category in database"""
        user_id = update.effective_user.id
        
        category_name = context.user_data.get('category_name', '')
        category_key = context.user_data.get('category_key', '')
        emoji = context.user_data.get('category_emoji', '📦')
        hebrew_name = context.user_data.get('category_hebrew', category_name)
        
        # Create category in database
        success = self.db.add_custom_category(category_key, emoji, category_name, hebrew_name, user_id)
        
        if success:
            # Clear creation data
            context.user_data.pop('creating_category', None)
            context.user_data.pop('category_name', None)
            context.user_data.pop('category_key', None)
            context.user_data.pop('category_emoji', None)
            context.user_data.pop('category_hebrew', None)
            
            # Send success message
            message = self.get_message(user_id, 'category_created_success').format(
                category_name=category_name,
                emoji=emoji,
                name_en=category_name,
                name_he=hebrew_name
            )
            
            # Add back to categories button so user can see their new category
            keyboard = [[InlineKeyboardButton(
                "📂 View Categories",
                callback_data="categories"
            )]]
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="main_menu"
            )])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                self.get_message(user_id, 'category_already_exists').format(category_name=category_name)
            )
    
    async def show_manage_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE, back_to: str = "main_menu"):
        """Show manage categories interface"""
        user_id = update.effective_user.id
        
        # Get custom categories
        custom_categories = self.db.get_custom_categories()
        
        if not custom_categories:
            message = self.get_message(user_id, 'no_custom_categories')
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data=back_to
            )]]
        else:
            message = self.get_message(user_id, 'manage_categories_title')
            keyboard = [
                [InlineKeyboardButton("✏️ Rename Categories", callback_data="rename_categories_admin")]
            ]
            
            for category in custom_categories:
                keyboard.append([InlineKeyboardButton(
                    f"{category['emoji']} {category['name_en']} ({category['name_he']})",
                    callback_data=f"view_category_{category['category_key']}"
                )])
            
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data=back_to
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def cancel_category_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel category creation"""
        user_id = update.effective_user.id
        
        # Clear creation data
        context.user_data.pop('creating_category', None)
        context.user_data.pop('category_name', None)
        context.user_data.pop('category_key', None)
        context.user_data.pop('category_emoji', None)
        context.user_data.pop('category_hebrew', None)
        
        message = self.get_message(user_id, 'category_creation_cancelled')
        
        # Add back to menu button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_category_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show category details and management options"""
        user_id = update.effective_user.id
        
        category = self.db.get_custom_category(category_key)
        if not category:
            await update.callback_query.answer(self.get_message(update.effective_user.id, 'category_not_found'))
            return
        
        message = f"📂 **{category['name_en']}** ({category['name_he']})\n\n"
        message += f"Emoji: {category['emoji']}\n"
        message += f"Created: {category['created_at']}\n"
        message += f"Key: `{category['category_key']}`"
        
        keyboard = [
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_delete_category'),
                callback_data=f"delete_category_{category_key}"
            )],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="manage_categories"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def confirm_delete_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Confirm category deletion"""
        user_id = update.effective_user.id
        
        category = self.db.get_custom_category(category_key)
        if not category:
            await update.callback_query.answer(self.get_message(update.effective_user.id, 'category_not_found'))
            return
        
        message = self.get_message(user_id, 'confirm_delete_category').format(
            category_name=category['name_en']
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "✅ Yes, Delete",
                callback_data=f"confirm_delete_category_{category_key}"
            )],
            [InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"view_category_{category_key}"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def delete_custom_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Delete custom category"""
        user_id = update.effective_user.id
        
        category = self.db.get_custom_category(category_key)
        if not category:
            await update.callback_query.answer(self.get_message(update.effective_user.id, 'category_not_found'))
            return
        
        success = self.db.delete_custom_category(category_key)
        
        if success:
            message = self.get_message(user_id, 'category_deleted_success').format(
                category_name=category['name_en']
            )
            
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="manage_categories"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.callback_query.answer("Failed to delete category!")
    
    # Category Suggestion Methods
    async def suggest_category_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /suggestcategory command - Suggest a new category (all users)"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_authorized(user_id):
            await update.message.reply_text(self.get_message(user_id, 'not_registered'))
            return
        
        await self.start_category_suggestion(update, context)
    
    async def manage_category_suggestions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /managecategorysuggestions command - Manage category suggestions (admin only)"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return
        
        await self.show_manage_category_suggestions(update, context)
    
    async def start_category_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the category suggestion process"""
        user_id = update.effective_user.id
        
        # Clear any previous suggestion data
        context.user_data.pop('suggesting_category', None)
        context.user_data.pop('suggest_category_name', None)
        context.user_data.pop('suggest_category_emoji', None)
        context.user_data.pop('suggest_category_hebrew', None)
        
        # Set flag to indicate we're suggesting a category
        context.user_data['suggesting_category'] = True
        
        message = self.get_message(user_id, 'suggest_category_title')
        
        # Add cancel button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_cancel'),
            callback_data="cancel_category_suggestion"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_suggest_category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_name: str):
        """Process category name input for suggestion"""
        user_id = update.effective_user.id
        
        if not category_name.strip():
            await update.message.reply_text("❌ Please provide a category name.")
            return
        
        # Check if category already exists (in predefined or custom)
        category_key = category_name.lower().replace(' ', '_').replace('-', '_')
        
        # Check predefined categories
        if category_key in CATEGORIES:
            await update.message.reply_text(
                self.get_message(user_id, 'category_suggestion_already_exists').format(category_name=category_name)
            )
            return
        
        # Check custom categories
        if self.db.get_custom_category(category_key):
            await update.message.reply_text(
                self.get_message(user_id, 'category_suggestion_already_exists').format(category_name=category_name)
            )
            return
        
        # Check pending suggestions
        pending_suggestions = self.db.get_pending_category_suggestions()
        for suggestion in pending_suggestions:
            if suggestion['category_key'] == category_key:
                await update.message.reply_text(
                    self.get_message(user_id, 'category_suggestion_already_exists').format(category_name=category_name)
                )
                return
        
        # Store category name and ask for emoji
        context.user_data['suggest_category_name'] = category_name.strip()
        context.user_data['suggest_category_key'] = category_key
        
        await self.ask_for_suggest_category_emoji(update, context)
    
    async def ask_for_suggest_category_emoji(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user to choose an emoji for the category suggestion"""
        user_id = update.effective_user.id
        category_name = context.user_data.get('suggest_category_name', '')
        
        message = self.get_message(user_id, 'suggest_category_emoji').format(category_name=category_name)
        
        # Add common emoji buttons
        keyboard = [
            [InlineKeyboardButton("📱", callback_data="suggest_emoji_📱"),
             InlineKeyboardButton("💻", callback_data="suggest_emoji_💻"),
             InlineKeyboardButton("🎮", callback_data="suggest_emoji_🎮"),
             InlineKeyboardButton("📚", callback_data="suggest_emoji_📚")],
            [InlineKeyboardButton("🏠", callback_data="suggest_emoji_🏠"),
             InlineKeyboardButton("🚗", callback_data="suggest_emoji_🚗"),
             InlineKeyboardButton("✈️", callback_data="suggest_emoji_✈️"),
             InlineKeyboardButton("🎉", callback_data="suggest_emoji_🎉")],
            [InlineKeyboardButton("🎨", callback_data="suggest_emoji_🎨"),
             InlineKeyboardButton("🎵", callback_data="suggest_emoji_🎵"),
             InlineKeyboardButton("🏃", callback_data="suggest_emoji_🏃"),
             InlineKeyboardButton("🍽️", callback_data="suggest_emoji_🍽️")],
            [InlineKeyboardButton("📦", callback_data="suggest_emoji_📦"),
             InlineKeyboardButton("🔧", callback_data="suggest_emoji_🔧"),
             InlineKeyboardButton("💡", callback_data="suggest_emoji_💡"),
             InlineKeyboardButton("⭐", callback_data="suggest_emoji_⭐")],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_cancel'),
                callback_data="cancel_category_suggestion"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_suggest_category_emoji(self, update: Update, context: ContextTypes.DEFAULT_TYPE, emoji: str):
        """Process emoji selection for category suggestion"""
        user_id = update.effective_user.id
        
        # Store emoji and ask for Hebrew translation
        context.user_data['suggest_category_emoji'] = emoji
        
        await self.ask_for_suggest_category_hebrew(update, context)
    
    async def ask_for_suggest_category_hebrew(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user for Hebrew translation for category suggestion"""
        user_id = update.effective_user.id
        category_name = context.user_data.get('suggest_category_name', '')
        
        message = self.get_message(user_id, 'suggest_category_hebrew').format(category_name=category_name)
        
        # Add skip button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_skip'),
            callback_data="skip_suggest_hebrew_translation"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def process_suggest_category_hebrew(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hebrew_name: str):
        """Process Hebrew translation input for category suggestion"""
        user_id = update.effective_user.id
        
        # Store Hebrew translation and submit suggestion
        context.user_data['suggest_category_hebrew'] = hebrew_name.strip()
        
        await self.submit_category_suggestion(update, context)
    
    async def submit_category_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Submit the category suggestion"""
        user_id = update.effective_user.id
        
        category_name = context.user_data.get('suggest_category_name', '')
        category_key = context.user_data.get('suggest_category_key', '')
        emoji = context.user_data.get('suggest_category_emoji', '📦')
        hebrew_name = context.user_data.get('suggest_category_hebrew', category_name)
        
        # Submit suggestion to database
        success = self.db.add_category_suggestion(user_id, category_key, emoji, category_name, hebrew_name)
        
        if success:
            # Clear suggestion data
            context.user_data.pop('suggesting_category', None)
            context.user_data.pop('suggest_category_name', None)
            context.user_data.pop('suggest_category_key', None)
            context.user_data.pop('suggest_category_emoji', None)
            context.user_data.pop('suggest_category_hebrew', None)
            
            # Send success message
            message = self.get_message(user_id, 'category_suggestion_submitted').format(
                category_name=category_name
            )
            
            # Add back to menu button
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Notify admins
            await self.notify_admins_category_suggestion(user_id, category_name, emoji, hebrew_name)
        else:
            await update.message.reply_text(
                self.get_message(user_id, 'category_suggestion_already_exists').format(category_name=category_name)
            )
    
    async def show_manage_category_suggestions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show manage category suggestions interface"""
        user_id = update.effective_user.id
        
        # Get pending category suggestions
        suggestions = self.db.get_pending_category_suggestions()
        
        if not suggestions:
            message = self.get_message(user_id, 'no_category_suggestions')
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="main_menu"
            )]]
        else:
            message = self.get_message(user_id, 'manage_category_suggestions_title')
            keyboard = []
            
            for suggestion in suggestions:
                suggested_by = suggestion['suggested_by_first_name'] or suggestion['suggested_by_username'] or self.get_message(update.effective_user.id, 'user_fallback').format(user_id=suggestion['suggested_by'])
                keyboard.append([InlineKeyboardButton(
                    f"{suggestion['emoji']} {suggestion['name_en']} ({suggestion['name_he']}) - by {suggested_by}",
                    callback_data=f"review_category_suggestion_{suggestion['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="main_menu"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def cancel_category_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel category suggestion"""
        user_id = update.effective_user.id
        
        # Clear suggestion data
        context.user_data.pop('suggesting_category', None)
        context.user_data.pop('suggest_category_name', None)
        context.user_data.pop('suggest_category_key', None)
        context.user_data.pop('suggest_category_emoji', None)
        context.user_data.pop('suggest_category_hebrew', None)
        
        message = self.get_message(user_id, 'category_suggestion_cancelled')
        
        # Add back to menu button
        keyboard = [[InlineKeyboardButton(
            self.get_message(user_id, 'btn_back_menu'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    
    async def notify_admins_category_suggestion(self, suggested_by: int, category_name: str, emoji: str, hebrew_name: str):
        """Notify admins about new category suggestion"""
        admins = self.db.get_admin_users()
        
        for admin in admins:
            try:
                admin_name = admin['first_name'] or admin['username'] or self.get_message(admin['user_id'], 'admin_fallback')
                suggested_by_name = self.db.get_user_info(suggested_by)
                suggested_by_display = suggested_by_name['first_name'] if suggested_by_name else self.get_message(admin['user_id'], 'user_fallback').format(user_id=suggested_by)
                
                notification = f"💡 **New Category Suggestion**\n\n"
                notification += f"**Category:** {emoji} {category_name} ({hebrew_name})\n"
                notification += f"**Suggested by:** {suggested_by_display}\n\n"
                notification += f"Use /managecategorysuggestions to review and approve."
                
                await self.application.bot.send_message(
                    chat_id=admin['user_id'],
                    text=notification,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.warning(f"Could not notify admin {admin['user_id']} about category suggestion: {e}")
    
    async def show_category_suggestion_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE, suggestion_id: int):
        """Show category suggestion for review"""
        user_id = update.effective_user.id
        
        suggestion = self.db.get_category_suggestion_by_id(suggestion_id)
        if not suggestion:
            await update.callback_query.answer("Suggestion not found!")
            return
        
        message = f"💡 **Category Suggestion Review**\n\n"
        message += f"**Category:** {suggestion['emoji']} {suggestion['name_en']} ({suggestion['name_he']})\n"
        message += f"**Suggested by:** {suggestion['suggested_by_first_name'] or suggestion['suggested_by_username'] or f'User {suggestion['suggested_by']}'}\n"
        message += f"**Date:** {suggestion['created_at']}\n\n"
        message += f"**Key:** `{suggestion['category_key']}`"
        
        keyboard = [
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_approve_category'),
                callback_data=f"approve_category_suggestion_{suggestion_id}"
            )],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_reject_category'),
                callback_data=f"reject_category_suggestion_{suggestion_id}"
            )],
            [InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="manage_category_suggestions"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def approve_category_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, suggestion_id: int):
        """Approve a category suggestion"""
        user_id = update.effective_user.id
        
        suggestion = self.db.get_category_suggestion_by_id(suggestion_id)
        if not suggestion:
            await update.callback_query.answer("Suggestion not found!")
            return
        
        success = self.db.approve_category_suggestion(suggestion_id, user_id)
        
        if success:
            message = self.get_message(user_id, 'category_suggestion_approved').format(
                category_name=suggestion['name_en']
            )
            
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="admin_management"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            
            # Notify the user who suggested it
            await self.notify_user_category_suggestion_result(suggestion['suggested_by'], suggestion['name_en'], 'approved')
            # Notify all authorized users and admins about the approval
            await self.notify_all_users_category_approved(suggestion, user_id)
            
            # Also update the main menu to refresh the badge
            await self.show_main_menu(update, context)
        else:
            await update.callback_query.answer("Failed to approve suggestion!")
    
    async def reject_category_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, suggestion_id: int):
        """Reject a category suggestion"""
        user_id = update.effective_user.id
        
        suggestion = self.db.get_category_suggestion_by_id(suggestion_id)
        if not suggestion:
            await update.callback_query.answer("Suggestion not found!")
            return
        
        success = self.db.reject_category_suggestion(suggestion_id, user_id)
        
        if success:
            message = self.get_message(user_id, 'category_suggestion_rejected').format(
                category_name=suggestion['name_en']
            )
            
            keyboard = [[InlineKeyboardButton(
                self.get_message(user_id, 'btn_back_menu'),
                callback_data="admin_management"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            
            # Notify the user who suggested it
            await self.notify_user_category_suggestion_result(suggestion['suggested_by'], suggestion['name_en'], 'rejected')
            
            # Also update the main menu to refresh the badge
            await self.show_main_menu(update, context)
        else:
            await update.callback_query.answer("Failed to reject suggestion!")
    
    async def notify_user_category_suggestion_result(self, user_id: int, category_name: str, result: str):
        """Notify user about their category suggestion result"""
        try:
            if result == 'approved':
                message = f"✅ **Category Approved!**\n\nYour suggestion \"{category_name}\" has been approved and is now available to all users!"
            else:
                message = f"❌ **Category Rejected**\n\nYour suggestion \"{category_name}\" was not approved at this time."
            
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.warning(f"Could not notify user {user_id} about category suggestion result: {e}")

    async def notify_all_users_item_approved(self, suggestion: Dict, approved_by_user_id: int):
        """Notify all authorized users and admins about item approval"""
        try:
            # Get admin info who approved
            admin_info = self.db.get_user_info(approved_by_user_id)
            admin_name = admin_info.get('first_name', 'Admin') if admin_info else 'Admin'
            
            # Get user info who suggested
            suggested_by_info = self.db.get_user_info(suggestion['suggested_by'])
            suggested_by_name = suggested_by_info.get('first_name', 'User') if suggested_by_info else 'User'
            
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"✅ **פריט אושר**\n\nהפריט **{suggestion['item_name_en']}** שהוצע על ידי **{suggested_by_name}** אושר על ידי **{admin_name}**.\nהפריט זמין כעת לכל המשתמשים!"
                    else:
                        message = f"✅ **Item Approved**\n\nThe item **{suggestion['item_name_en']}** suggested by **{suggested_by_name}** has been approved by **{admin_name}**.\nThe item is now available to all users!"
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about item approval: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about item approval: {e}")

    async def notify_all_users_category_approved(self, suggestion: Dict, approved_by_user_id: int):
        """Notify all authorized users and admins about category approval"""
        try:
            # Get admin info who approved
            admin_info = self.db.get_user_info(approved_by_user_id)
            admin_name = admin_info.get('first_name', 'Admin') if admin_info else 'Admin'
            
            # Get user info who suggested
            suggested_by_info = self.db.get_user_info(suggestion['suggested_by'])
            suggested_by_name = suggested_by_info.get('first_name', 'User') if suggested_by_info else 'User'
            
            # Get all authorized users
            users = self.db.get_all_authorized_users()
            
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"✅ **קטגוריה אושרה**\n\nהקטגוריה **{suggestion['name_en']}** שהוצעה על ידי **{suggested_by_name}** אושרה על ידי **{admin_name}**.\nהקטגוריה זמינה כעת לכל המשתמשים!"
                    else:
                        message = f"✅ **Category Approved**\n\nThe category **{suggestion['name_en']}** suggested by **{suggested_by_name}** has been approved by **{admin_name}**.\nThe category is now available to all users!"
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about category approval: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about category approval: {e}")

    async def show_rename_items_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show rename items interface for admins"""
        user_id = update.effective_user.id
        
        try:
            if not self.db.is_user_admin(user_id):
                if update.message:
                    await update.message.reply_text(self.get_message(user_id, 'admin_only'))
                elif update.callback_query:
                    await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
                return
        
            # Get all categories with their items
            keyboard = []
            
            # Add predefined categories
            for category_key, category_data in CATEGORIES.items():
                category_name = self.get_category_name(user_id, category_key)
                keyboard.append([InlineKeyboardButton(
                    f"{category_data['emoji']} {category_name}",
                    callback_data=f"rename_items_category_{category_key}"
                )])
            
            # Add custom categories
            custom_categories = self.db.get_custom_categories()
            for category in custom_categories:
                keyboard.append([InlineKeyboardButton(
                    f"{category['emoji']} {category['name_en']} ({category['name_he']})",
                    callback_data=f"rename_items_category_{category['category_key']}"
                )])
            
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_management'), callback_data="admin_management")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = self.get_message(user_id, 'rename_items_title')
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            error_message = f"❌ Error loading rename interface: {str(e)}"
            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.edit_message_text(error_message)

    async def show_rename_categories_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show rename categories interface for admins"""
        user_id = update.effective_user.id
        
        try:
            if not self.db.is_user_admin(user_id):
                if update.message:
                    await update.message.reply_text(self.get_message(user_id, 'admin_only'))
                elif update.callback_query:
                    await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
                return
            
            # Get custom categories
            custom_categories = self.db.get_custom_categories()
            
            if not custom_categories:
                message = self.get_message(user_id, 'rename_categories_empty')
                keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_management'), callback_data="admin_management")]]
            else:
                message = self.get_message(user_id, 'rename_categories_title')
                keyboard = []
                
                for category in custom_categories:
                    keyboard.append([InlineKeyboardButton(
                        f"{category['emoji']} {category['name_en']} ({category['name_he']})",
                        callback_data=f"rename_category_{category['category_key']}"
                    )])
                
                keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_management'), callback_data="admin_management")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            elif update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            
        except Exception as e:
            error_message = f"❌ Error loading category rename options: {str(e)}"
            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.edit_message_text(error_message)

    async def show_items_to_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show items in a category for renaming"""
        user_id = update.effective_user.id
        
        try:
            if not self.db.is_user_admin(user_id):
                await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
                return
            
            # Get category items
            items = self.get_category_items(user_id, category_key)
            category_name = self.get_category_name(user_id, category_key)
            
            if not items:
                message = self.get_message(user_id, 'rename_items_category_empty').format(category_name=category_name)
                keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_management'), callback_data="admin_management")]]
            else:
                message = self.get_message(user_id, 'rename_items_category_title').format(category_name=category_name)
                keyboard = []
                
                for item in items:
                    keyboard.append([InlineKeyboardButton(
                        f"✏️ {item}",
                        callback_data=f"rename_item_{category_key}_{item}"
                    )])
                
                keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_back_to_management'), callback_data="admin_management")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            print(f"ERROR in show_items_to_rename: {e}")
            error_message = f"❌ Error loading items for renaming: {str(e)}"
            await update.callback_query.edit_message_text(error_message)

    async def start_item_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, item_name: str):
        """Start the item rename process"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Store rename data
        context.user_data['renaming_item'] = True
        context.user_data['rename_category'] = category_key
        context.user_data['rename_old_name'] = item_name
        context.user_data['rename_step'] = 'english'
        
        category_name = self.get_category_name(user_id, category_key)
        message = self.get_message(user_id, 'rename_item_prompt').format(category_name=category_name, item_name=item_name)
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_cancel'), callback_data="cancel_rename")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_category_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Start the category rename process"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Get category info
        category = self.db.get_category_by_key(category_key)
        if not category:
            await update.callback_query.edit_message_text("❌ Category not found.")
            return
        
        # Store rename data
        context.user_data['renaming_category'] = True
        context.user_data['rename_category_key'] = category_key
        context.user_data['rename_old_name_en'] = category['name_en']
        context.user_data['rename_old_name_he'] = category['name_he']
        
        message = self.get_message(user_id, 'rename_category_prompt').format(
            category_name_en=category['name_en'], 
            category_name_he=category['name_he']
        )
        
        keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_cancel'), callback_data="cancel_rename")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def cancel_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the rename process"""
        user_id = update.effective_user.id
        
        # Clear rename data
        context.user_data.pop('renaming_item', None)
        context.user_data.pop('renaming_category', None)
        context.user_data.pop('rename_category', None)
        context.user_data.pop('rename_category_key', None)
        context.user_data.pop('rename_old_name', None)
        context.user_data.pop('rename_old_name_en', None)
        context.user_data.pop('rename_old_name_he', None)
        context.user_data.pop('rename_new_name_en', None)
        context.user_data.pop('rename_step', None)
        
        await update.callback_query.edit_message_text(self.get_message(user_id, 'rename_cancelled'))
        
        # Return to admin management menu
        await self.show_admin_management_menu(update, context)

    async def process_item_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Process item rename"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return
        
        category_key = context.user_data.get('rename_category')
        old_name = context.user_data.get('rename_old_name')
        
        if not category_key or not old_name:
            await update.message.reply_text(self.get_message(user_id, 'rename_missing_data'))
            return
        
        # Check current step
        rename_step = context.user_data.get('rename_step', 'english')
        
        if rename_step == 'english':
            # User entered English name
            new_name_en = text.strip()
            
            # Check if new name already exists in category
            if self.db.is_item_in_category(new_name_en, category_key):
                await update.message.reply_text(self.get_message(user_id, 'rename_duplicate_item').format(new_name=new_name_en))
                return
            
            # Store English name and ask for Hebrew
            context.user_data['rename_new_name_en'] = new_name_en
            context.user_data['rename_step'] = 'hebrew'
            
            category_name = self.get_category_name(user_id, category_key)
            message = self.get_message(user_id, 'rename_item_hebrew_prompt').format(
                item_name_en=new_name_en,
                category_name=category_name
            )
            
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_cancel'), callback_data="cancel_rename")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        elif rename_step == 'hebrew':
            # User entered Hebrew name
            new_name_he = text.strip()
            new_name_en = context.user_data.get('rename_new_name_en')
            
            # Rename the item in the database
            success = self.db.rename_item(old_name, new_name_en, category_key, new_name_he)
            
            if success:
                category_name = self.get_category_name(user_id, category_key)
                await update.message.reply_text(self.get_message(user_id, 'item_renamed_success').format(
                    category_name=category_name, 
                    old_name=old_name, 
                    new_name=new_name_en
                ))
                
                # Notify all users about the rename
                await self.notify_item_rename(old_name, new_name_en, category_name)
            else:
                await update.message.reply_text(self.get_message(user_id, 'rename_error'))
            
            # Clear rename data
            context.user_data.pop('renaming_item', None)
            context.user_data.pop('rename_category', None)
            context.user_data.pop('rename_old_name', None)
            context.user_data.pop('rename_new_name_en', None)
            context.user_data.pop('rename_step', None)

    async def process_category_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Process category rename"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return
        
        category_key = context.user_data.get('rename_category_key')
        old_name_en = context.user_data.get('rename_old_name_en')
        old_name_he = context.user_data.get('rename_old_name_he')
        
        if not category_key or not old_name_en:
            await update.message.reply_text(self.get_message(user_id, 'rename_missing_data'))
            return
        
        # Check current step
        rename_step = context.user_data.get('rename_step', 'english')
        
        if rename_step == 'english':
            # User entered English name
            new_name_en = text.strip()
            
            # Check if category name already exists
            if self.db.is_category_name_exists(new_name_en):
                await update.message.reply_text(self.get_message(user_id, 'rename_duplicate_category').format(new_name=new_name_en))
                return
            
            # Store English name and ask for Hebrew
            context.user_data['rename_new_name_en'] = new_name_en
            context.user_data['rename_step'] = 'hebrew'
            
            message = self.get_message(user_id, 'rename_category_hebrew_prompt').format(
                category_name_en=new_name_en
            )
            
            keyboard = [[InlineKeyboardButton(self.get_message(user_id, 'btn_cancel'), callback_data="cancel_rename")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        elif rename_step == 'hebrew':
            # User entered Hebrew name
            new_name_he = text.strip()
            new_name_en = context.user_data.get('rename_new_name_en')
            
            # Rename the category in the database
            success = self.db.rename_category(category_key, new_name_en, new_name_he)
            
            if success:
                await update.message.reply_text(self.get_message(user_id, 'category_renamed_success').format(
                    old_name_en=old_name_en,
                    old_name_he=old_name_he,
                    new_name_en=new_name_en,
                    new_name_he=new_name_he
                ))
                
                # Notify all users about the rename
                await self.notify_category_rename(old_name_en, new_name_en)
            else:
                await update.message.reply_text(self.get_message(user_id, 'rename_error'))
            
            # Clear rename data
            context.user_data.pop('renaming_category', None)
            context.user_data.pop('rename_category_key', None)
            context.user_data.pop('rename_old_name_en', None)
            context.user_data.pop('rename_old_name_he', None)
            context.user_data.pop('rename_new_name_en', None)
            context.user_data.pop('rename_step', None)

    async def notify_item_rename(self, old_name: str, new_name: str, category_name: str):
        """Notify all users about item rename"""
        try:
            users = self.db.get_all_users()
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"✏️ **פריט שונה שם**\n\nהפריט **{old_name}** בקטגוריה **{category_name}** שונה ל-**{new_name}**."
                    else:
                        message = f"✏️ **Item Renamed**\n\nThe item **{old_name}** in category **{category_name}** has been renamed to **{new_name}**."
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about item rename: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about item rename: {e}")

    async def notify_category_rename(self, old_name: str, new_name: str):
        """Notify all users about category rename"""
        try:
            users = self.db.get_all_users()
            for user in users:
                try:
                    user_lang = self.db.get_user_language(user['user_id'])
                    if user_lang == 'he':
                        message = f"✏️ **קטגוריה שונה שם**\n\nהקטגוריה **{old_name}** שונה ל-**{new_name}**."
                    else:
                        message = f"✏️ **Category Renamed**\n\nThe category **{old_name}** has been renamed to **{new_name}**."
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not notify user {user['user_id']} about category rename: {e}")
        except Exception as e:
            logging.error(f"Error notifying users about category rename: {e}")

    # Template Methods
    async def show_templates_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show templates menu for a specific list"""
        user_id = update.effective_user.id
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        list_type = list_info['list_type']
        templates = self.db.get_templates_by_list_type(list_type, user_id)
        
        if not templates:
            message = f"📝 **Templates for {list_info['name']}**\n\nNo templates available for this list type yet."
            keyboard = [[InlineKeyboardButton("🔙 Back to List", callback_data=f"list_menu_{list_id}")]]
        else:
            message = f"📝 **Templates for {list_info['name']}**\n\n"
            message += f"Available templates ({len(templates)}):\n\n"
            
            keyboard = []
            for template in templates[:10]:  # Limit to 10 templates
                template_name = template['name']
                item_count = len(template['items'])
                usage_count = template['usage_count']
                
                # Add usage info
                usage_info = f" ({usage_count} uses)" if usage_count > 0 else ""
                
                # System template indicator
                if template['is_system_template']:
                    template_name = f"⭐ {template_name}"
                
                button_text = f"{template_name} ({item_count} items){usage_info}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"template_preview_{template['id']}_{list_id}")])
            
            # Add template management options
            keyboard.append([InlineKeyboardButton("💾 Save Current List as Template", callback_data=f"save_template_{list_id}")])
            keyboard.append([InlineKeyboardButton("⚙️ Template Management", callback_data=f"template_management_{list_id}")])
            keyboard.append([InlineKeyboardButton("🔙 Back to List", callback_data=f"list_menu_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_template_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int, list_id: int):
        """Show template preview with customization options"""
        user_id = update.effective_user.id
        
        template = self.db.get_template_by_id(template_id)
        if not template:
            await update.callback_query.edit_message_text("❌ Template not found.")
            return
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        # Track preview usage
        self.db.increment_template_usage(template_id, user_id, 'preview')
        
        message = f"📋 **{template['name']}** Template Preview\n\n"
        if template['description']:
            message += f"_{template['description']}_\n\n"
        
        message += f"Items ({len(template['items'])}):\n"
        for i, item in enumerate(template['items'], 1):
            category_info = f" ({item['category']})" if item.get('category') else ""
            notes_info = f" - {item['notes']}" if item.get('notes') else ""
            message += f"{i}. {item['name']}{category_info}{notes_info}\n"
        
        message += f"\n💡 **Choose how to use this template:**"
        
        keyboard = [
            [InlineKeyboardButton("✅ Add All Items", callback_data=f"template_add_all_{template_id}_{list_id}")],
            [InlineKeyboardButton("🎯 Select Items", callback_data=f"template_select_{template_id}_{list_id}")],
            [InlineKeyboardButton("🔄 Replace List", callback_data=f"template_replace_{template_id}_{list_id}")],
            [InlineKeyboardButton("🔙 Back to Templates", callback_data=f"templates_list_{list_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_template_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int, list_id: int, selected_items: List[str] = None):
        """Add template items to a list"""
        user_id = update.effective_user.id
        
        items_added = self.db.add_template_items_to_list(template_id, list_id, selected_items, user_id)
        
        list_info = self.db.get_list_by_id(list_id)
        template = self.db.get_template_by_id(template_id)
        
        if items_added > 0:
            message = f"✅ **Template Applied Successfully!**\n\n"
            message += f"Added {items_added} items from **{template['name']}** to **{list_info['name']}**.\n\n"
            
            if selected_items:
                message += "Selected items:\n"
                for item in selected_items:
                    message += f"• {item}\n"
            else:
                message += "All template items were added."
        else:
            message = f"⚠️ **No items added**\n\n"
            message += f"All items from **{template['name']}** already exist in **{list_info['name']}**."
        
        keyboard = [
            [InlineKeyboardButton("📋 View List", callback_data=f"view_list_{list_id}")],
            [InlineKeyboardButton("🔙 Back to Templates", callback_data=f"templates_list_{list_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_template_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int, list_id: int):
        """Show template item selection interface"""
        user_id = update.effective_user.id
        
        template = self.db.get_template_by_id(template_id)
        if not template:
            await update.callback_query.edit_message_text("❌ Template not found.")
            return
        
        # Store template selection state
        context.user_data[f'template_selection_{template_id}'] = {
            'template_id': template_id,
            'list_id': list_id,
            'selected_items': []
        }
        
        message = f"🎯 **Select Items from {template['name']}**\n\n"
        message += "Choose which items to add to your list:\n\n"
        
        keyboard = []
        for i, item in enumerate(template['items']):
            category_info = f" ({item['category']})" if item.get('category') else ""
            notes_info = f" - {item['notes']}" if item.get('notes') else ""
            item_text = f"{item['name']}{category_info}{notes_info}"
            
            keyboard.append([InlineKeyboardButton(f"☐ {item_text}", callback_data=f"template_toggle_{template_id}_{i}")])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Add Selected Items", callback_data=f"template_add_selected_{template_id}_{list_id}")],
            [InlineKeyboardButton("🔙 Back to Preview", callback_data=f"template_preview_{template_id}_{list_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def toggle_template_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int, item_index: int):
        """Toggle item selection in template"""
        user_id = update.effective_user.id
        
        template = self.db.get_template_by_id(template_id)
        if not template or item_index >= len(template['items']):
            await update.callback_query.answer("❌ Invalid item selection")
            return
        
        # Get or create selection state
        selection_key = f'template_selection_{template_id}'
        if selection_key not in context.user_data:
            context.user_data[selection_key] = {
                'template_id': template_id,
                'list_id': None,
                'selected_items': []
            }
        
        selected_items = context.user_data[selection_key]['selected_items']
        item_name = template['items'][item_index]['name']
        
        # Toggle selection
        if item_name in selected_items:
            selected_items.remove(item_name)
        else:
            selected_items.append(item_name)
        
        # Update button text
        item = template['items'][item_index]
        category_info = f" ({item['category']})" if item.get('category') else ""
        notes_info = f" - {item['notes']}" if item.get('notes') else ""
        item_text = f"{item['name']}{category_info}{notes_info}"
        
        is_selected = item_name in selected_items
        button_text = f"{'☑️' if is_selected else '☐'} {item_text}"
        
        # Update the specific button
        keyboard = []
        for i, template_item in enumerate(template['items']):
            category_info = f" ({template_item['category']})" if template_item.get('category') else ""
            notes_info = f" - {template_item['notes']}" if template_item.get('notes') else ""
            template_item_text = f"{template_item['name']}{category_info}{notes_info}"
            
            is_item_selected = template_item['name'] in selected_items
            button_text = f"{'☑️' if is_item_selected else '☐'} {template_item_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"template_toggle_{template_id}_{i}")])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Add Selected Items", callback_data=f"template_add_selected_{template_id}_{context.user_data[selection_key]['list_id']}")],
            [InlineKeyboardButton("🔙 Back to Preview", callback_data=f"template_preview_{template_id}_{context.user_data[selection_key]['list_id']}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)

    async def save_current_list_as_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Save current list as a template"""
        user_id = update.effective_user.id
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        items = self.db.get_shopping_list_by_id(list_id)
        if not items:
            await update.callback_query.edit_message_text("❌ Cannot save empty list as template.")
            return
        
        # Store template creation state
        context.user_data['creating_template'] = {
            'list_id': list_id,
            'list_name': list_info['name'],
            'list_type': list_info['list_type'],
            'items': items
        }
        
        message = f"💾 **Save Template from {list_info['name']}**\n\n"
        message += f"Current list has {len(items)} items:\n"
        for item in items[:5]:  # Show first 5 items
            message += f"• {item['name']}\n"
        if len(items) > 5:
            message += f"... and {len(items) - 5} more items\n"
        
        message += "\nEnter a name for this template:"
        
        # Set waiting state for template creation
        context.user_data['creating_template'] = True
        
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

    async def show_template_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show template management options"""
        user_id = update.effective_user.id
        is_admin = self.db.is_user_admin(user_id)
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        list_type = list_info['list_type']
        
        # Get user templates
        user_templates = self.db.get_user_templates(user_id)
        user_templates_for_type = [t for t in user_templates if t['list_type'] == list_type]
        
        # Get system templates for admins
        system_templates_for_type = []
        if is_admin:
            all_templates = self.db.get_templates_by_list_type(list_type)
            system_templates_for_type = [t for t in all_templates if t['is_system_template']]
        
        message = f"⚙️ **Template Management for {list_info['name']}**\n\n"
        
        # Show user templates
        if user_templates_for_type:
            message += f"📝 **Your Templates** ({len(user_templates_for_type)}):\n"
            for template in user_templates_for_type:
                usage_info = f" ({template['usage_count']} uses)" if template['usage_count'] > 0 else ""
                message += f"• {template['name']} ({len(template['items'])} items){usage_info}\n"
            message += "\n"
        else:
            message += "📝 **Your Templates**: None created yet.\n\n"
        
        # Show system templates for admins
        if is_admin and system_templates_for_type:
            message += f"🏛️ **System Templates** ({len(system_templates_for_type)}):\n"
            for template in system_templates_for_type:
                usage_info = f" ({template['usage_count']} uses)" if template['usage_count'] > 0 else ""
                creator_info = f" by {template.get('first_name', 'Unknown')}" if template.get('first_name') else ""
                message += f"• {template['name']} ({len(template['items'])} items){usage_info}{creator_info}\n"
            message += "\n"
        elif is_admin:
            message += "🏛️ **System Templates**: None created yet.\n\n"
        
        keyboard = []
        
        # User template management
        if user_templates_for_type:
            keyboard.append([InlineKeyboardButton("📊 My Template Statistics", callback_data=f"template_stats_{list_id}")])
            keyboard.append([InlineKeyboardButton("🗑️ Delete My Templates", callback_data=f"template_delete_menu_{list_id}")])
        
        # Admin system template management
        if is_admin and system_templates_for_type:
            keyboard.append([InlineKeyboardButton("🏛️ Manage System Templates", callback_data=f"system_template_management_{list_id}")])
        
        # Admin can create system templates
        if is_admin:
            keyboard.append([InlineKeyboardButton("➕ Create System Template", callback_data=f"create_system_template_{list_id}")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 Back to Templates", callback_data=f"templates_list_{list_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_system_template_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show system template management for admins"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        list_type = list_info['list_type']
        all_templates = self.db.get_templates_by_list_type(list_type)
        system_templates = [t for t in all_templates if t['is_system_template']]
        
        message = f"🏛️ **System Template Management for {list_info['name']}**\n\n"
        
        if system_templates:
            message += f"**System Templates** ({len(system_templates)}):\n\n"
            for template in system_templates:
                usage_info = f" ({template['usage_count']} uses)" if template['usage_count'] > 0 else ""
                creator_info = f" by {template.get('first_name', 'Unknown')}" if template.get('first_name') else ""
                created_date = template['created_at'][:10] if template['created_at'] else "Unknown"
                message += f"**{template['name']}**{usage_info}{creator_info}\n"
                message += f"• Items: {len(template['items'])}\n"
                message += f"• Created: {created_date}\n"
                if template['description']:
                    message += f"• Description: {template['description']}\n"
                message += "\n"
        else:
            message += "No system templates found for this list type.\n\n"
        
        keyboard = []
        
        if system_templates:
            for template in system_templates:
                keyboard.append([
                    InlineKeyboardButton(f"✏️ Edit {template['name']}", callback_data=f"edit_system_template_{template['id']}"),
                    InlineKeyboardButton(f"🗑️ Delete", callback_data=f"delete_system_template_{template['id']}")
                ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Create System Template", callback_data=f"create_system_template_{list_id}")],
            [InlineKeyboardButton("🔙 Back to Template Management", callback_data=f"template_management_{list_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def create_system_template_from_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Create a system template from current list"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        # Get current list items
        items = self.db.get_shopping_list_by_id(list_id)
        if not items:
            await update.callback_query.edit_message_text("❌ List is empty. Cannot create template from empty list.")
            return
        
        # Store template creation data
        context.user_data['creating_system_template'] = {
            'list_id': list_id,
            'list_name': list_info['name'],
            'list_type': list_info['list_type'],
            'items': items
        }
        
        message = f"🏛️ **Create System Template from {list_info['name']}**\n\n"
        message += f"**Current List Items** ({len(items)}):\n"
        for item in items[:10]:  # Show first 10 items
            message += f"• {item['name']}"
            if item['notes']:
                message += f" ({item['notes']})"
            message += "\n"
        
        if len(items) > 10:
            message += f"... and {len(items) - 10} more items\n"
        
        message += "\n**System templates are available to all users.**\n\n"
        message += "Please enter a name for this system template:"
        
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

    async def edit_system_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Edit a system template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        template = self.db.get_template_by_id(template_id)
        if not template or not template['is_system_template']:
            await update.callback_query.edit_message_text("❌ System template not found.")
            return
        
        # Store template editing state
        # Debug: Check template items structure
        print(f"DEBUG: Template items type: {type(template['items'])}")
        print(f"DEBUG: Template items: {template['items']}")
        
        context.user_data['editing_template'] = {
            'template_id': template_id,
            'template_name': template['name'],
            'list_type': template['list_type'],
            'current_items': template['items'].copy()
        }
        
        message = f"✏️ **Edit Template: {template['name']}**\n"
        message += f"Items: {len(template['items'])}\n\n"
        
        keyboard = []
        
        # Show items with delete buttons (simplified)
        for i, item in enumerate(template['items']):
            item_name = item['name'][:25]  # Truncate to 25 chars
            button_text = f"🗑️ {item_name}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"template_remove_item_{template_id}_{i}")
            ])
        
        # Add new item options
        keyboard.extend([
            [InlineKeyboardButton("➕ Add Items from Categories", callback_data=f"template_add_items_{template_id}")],
            [InlineKeyboardButton("💾 Save Changes", callback_data=f"template_save_changes_{template_id}")],
            [InlineKeyboardButton("❌ Cancel Editing", callback_data=f"template_cancel_edit_{template_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Always send a new message to avoid 400 errors
        try:
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            await update.callback_query.answer("✅ Template editing")
        except Exception as e:
            print(f"ERROR in edit_system_template: {e}")
            await update.callback_query.answer("❌ Error showing template")

    async def remove_template_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int, item_index: int):
        """Remove an item from template being edited"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        editing_data = context.user_data.get('editing_template')
        print(f"DEBUG: Editing data: {editing_data}")
        print(f"DEBUG: Template ID: {template_id}")
        print(f"DEBUG: Item index: {item_index}")
        
        if not editing_data or editing_data['template_id'] != template_id:
            # Try to recreate the editing session from the template
            template = self.db.get_template_by_id(template_id)
            if template and template['is_system_template']:
                editing_data = {
                    'template_id': template_id,
                    'template_name': template['name'],
                    'list_type': template['list_type'],
                    'current_items': template['items'].copy()
                }
                context.user_data['editing_template'] = editing_data
                print(f"DEBUG: Recreated editing session: {editing_data}")
            else:
                await update.callback_query.edit_message_text("❌ Template editing session not found.")
                return
        
        # Remove item from current items
        if 0 <= item_index < len(editing_data['current_items']):
            removed_item = editing_data['current_items'].pop(item_index)
            
            # Update the editing data in context
            context.user_data['editing_template'] = editing_data
            
            # Show confirmation and refresh the edit interface
            await update.callback_query.answer(f"✅ Removed: {removed_item['name']}")
            
            # Send a new message with updated template instead of editing
            message = f"✏️ **Edit Template: {editing_data['template_name']}**\n"
            message += f"Items: {len(editing_data['current_items'])}\n\n"
            
            keyboard = []
            
            # Show remaining items with delete buttons
            for i, item in enumerate(editing_data['current_items']):
                item_name = item['name'][:25]  # Truncate to 25 chars
                button_text = f"🗑️ {item_name}"
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=f"template_remove_item_{template_id}_{i}")
                ])
            
            # Add new item options
            keyboard.extend([
                [InlineKeyboardButton("➕ Add Items from Categories", callback_data=f"template_add_items_{template_id}")],
                [InlineKeyboardButton("💾 Save Changes", callback_data=f"template_save_changes_{template_id}")],
                [InlineKeyboardButton("❌ Cancel Editing", callback_data=f"template_cancel_edit_{template_id}")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send new message
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text("❌ Invalid item index.")

    async def add_items_to_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Show categories to add items to template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        editing_data = context.user_data.get('editing_template')
        if not editing_data or editing_data['template_id'] != template_id:
            await update.callback_query.edit_message_text("❌ Template editing session not found.")
            return
        
        # Store template context for adding items
        context.user_data['adding_to_template'] = template_id
        
        message = f"➕ **Add Items to Template: {editing_data['template_name']}**\n\n"
        message += f"**Current Items**: {len(editing_data['current_items'])}\n\n"
        message += "Choose a category to add items from:"
        
        keyboard = []
        
        # Add predefined categories
        from config import CATEGORIES
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            emoji = category_data.get('emoji', '📦')
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {category_name}", callback_data=f"template_category_{category_key}_{template_id}")
            ])
        
        # Add custom categories
        custom_categories = self.db.get_custom_categories()
        for category in custom_categories:
            category_key = category['category_key']
            category_name = self.get_category_name(user_id, category_key)
            emoji = category['emoji']
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {category_name}", callback_data=f"template_category_{category_key}_{template_id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 Back to Template Edit", callback_data=f"edit_system_template_{template_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def save_template_changes(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Save changes to template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        editing_data = context.user_data.get('editing_template')
        if not editing_data or editing_data['template_id'] != template_id:
            await update.callback_query.edit_message_text("❌ Template editing session not found.")
            return
        
        # Update template in database
        success = self.db.update_template(
            template_id=template_id,
            items=editing_data['current_items']
        )
        
        if success:
            message = f"✅ **Template Updated Successfully!**\n\n"
            message += f"Template: **{editing_data['template_name']}**\n"
            message += f"Items: {len(editing_data['current_items'])}\n"
            message += f"Type: System Template\n\n"
            message += "Changes have been saved and are now available to all users."
            
            # Get list_id for navigation
            all_lists = self.db.get_all_lists()
            matching_lists = [l for l in all_lists if l['list_type'] == editing_data['list_type']]
            list_id = matching_lists[0]['id'] if matching_lists else 1
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to System Templates", callback_data=f"system_template_management_{list_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Clear editing state
            context.user_data.pop('editing_template', None)
            context.user_data.pop('adding_to_template', None)
        else:
            await update.callback_query.edit_message_text("❌ Failed to save template changes. Please try again.")

    async def cancel_template_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Cancel template editing"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        # Clear editing state
        context.user_data.pop('editing_template', None)
        context.user_data.pop('adding_to_template', None)
        
        # Get list_id for navigation
        template = self.db.get_template_by_id(template_id)
        if template:
            all_lists = self.db.get_all_lists()
            matching_lists = [l for l in all_lists if l['list_type'] == template.get('list_type', 'supermarket')]
            list_id = matching_lists[0]['id'] if matching_lists else 1
            
            message = "❌ **Template editing cancelled.**\n\nNo changes were saved."
            keyboard = [
                [InlineKeyboardButton("🔙 Back to System Templates", callback_data=f"system_template_management_{list_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text("❌ Template not found.")

    async def show_template_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, template_id: int):
        """Show category items for adding to template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        editing_data = context.user_data.get('editing_template')
        if not editing_data or editing_data['template_id'] != template_id:
            await update.callback_query.edit_message_text("❌ Template editing session not found.")
            return
        
        # Get category items
        category_items = self.get_category_items(user_id, category_key)
        if not category_items:
            await update.callback_query.edit_message_text("❌ No items available in this category.")
            return
        
        category_name = self.get_category_name(user_id, category_key)
        category_emoji = "📦"
        
        # Get emoji for predefined categories
        from config import CATEGORIES
        if category_key in CATEGORIES:
            category_emoji = CATEGORIES[category_key].get('emoji', '📦')
        else:
            # Get emoji for custom categories
            custom_category = self.db.get_custom_category(category_key)
            if custom_category:
                category_emoji = custom_category['emoji']
        
        message = f"➕ **Add to: {editing_data['template_name']}**\n"
        message += f"{category_emoji} {category_name} ({len(category_items)} items)\n\n"
        message += "Tap ✅ to add:"
        
        keyboard = []
        
        # Show items with add buttons
        for item in category_items:
            # Check if item already exists in template
            item_exists = any(existing_item['name'].lower() == item.lower() for existing_item in editing_data['current_items'])
            print(f"DEBUG: Checking item '{item}' - exists: {item_exists}")
            print(f"DEBUG: Current template items: {[i['name'] for i in editing_data['current_items']]}")
            button_text = f"✅ {item}" if not item_exists else f"🔄 {item} (already added)"
            # Use a separator that's less likely to appear in item names
            callback_data = f"template_add_item_{category_key}|{item}|{template_id}"
            
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=callback_data)
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 Back to Add Items", callback_data=f"template_add_items_{template_id}")],
            [InlineKeyboardButton("🔙 Back to Template Edit", callback_data=f"edit_system_template_{template_id}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_item_to_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, item_name: str, template_id: int):
        """Add an item to template being edited"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        editing_data = context.user_data.get('editing_template')
        if not editing_data or editing_data['template_id'] != template_id:
            # Try to recreate the editing session from the template
            template = self.db.get_template_by_id(template_id)
            if template and template['is_system_template']:
                editing_data = {
                    'template_id': template_id,
                    'template_name': template['name'],
                    'list_type': template['list_type'],
                    'current_items': template['items'].copy()
                }
                context.user_data['editing_template'] = editing_data
                print(f"DEBUG: Recreated editing session for add_item: {editing_data}")
            else:
                await update.callback_query.edit_message_text("❌ Template editing session not found.")
                return
        
        # Check if item already exists
        item_exists = any(existing_item['name'].lower() == item_name.lower() for existing_item in editing_data['current_items'])
        
        if not item_exists:
            # Add new item to template
            new_item = {
                'name': item_name,
                'category': category_key,
                'notes': ''
            }
            editing_data['current_items'].append(new_item)
            
            # Update the editing data in context
            context.user_data['editing_template'] = editing_data
            
            # Show confirmation and refresh the category items view
            await update.callback_query.answer(f"✅ Added: {item_name}")
            
            # Send new message with updated category items
            await self.show_template_category_items(update, context, category_key, template_id)
        else:
            # Item already exists, just show a brief message
            await update.callback_query.answer(f"ℹ️ {item_name} is already in the template")

    async def delete_system_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Delete a system template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        template = self.db.get_template_by_id(template_id)
        if not template or not template['is_system_template']:
            await update.callback_query.edit_message_text("❌ System template not found.")
            return
        
        # Confirm deletion
        message = f"🗑️ **Delete System Template: {template['name']}**\n\n"
        message += f"**Template Details:**\n"
        message += f"• Items: {len(template['items'])}\n"
        message += f"• Usage Count: {template['usage_count']}\n"
        message += f"• Created: {template['created_at'][:10] if template['created_at'] else 'Unknown'}\n\n"
        message += "⚠️ **This action cannot be undone!**\n\n"
        message += "Are you sure you want to delete this system template?"
        
        # Get list_id from template's list_type
        all_lists = self.db.get_all_lists()
        matching_lists = [l for l in all_lists if l['list_type'] == template.get('list_type', 'supermarket')]
        list_id = matching_lists[0]['id'] if matching_lists else 1  # Fallback to list 1
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_system_template_{template_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"system_template_management_{list_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def confirm_delete_system_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_id: int):
        """Confirm deletion of a system template"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.callback_query.edit_message_text(self.get_message(user_id, 'admin_only'))
            return
        
        template = self.db.get_template_by_id(template_id)
        if not template or not template['is_system_template']:
            await update.callback_query.edit_message_text("❌ System template not found.")
            return
        
        # Delete the template
        success = self.db.delete_template(template_id, user_id)
        
        if success:
            message = f"✅ **System Template Deleted Successfully!**\n\n"
            message += f"Template: **{template['name']}**\n"
            message += f"Items: {len(template['items'])}\n"
            message += f"Usage Count: {template['usage_count']}\n\n"
            message += "The template has been permanently removed from the system."
            
            # Get list_id from template's list_type
            all_lists = self.db.get_all_lists()
            matching_lists = [l for l in all_lists if l['list_type'] == template.get('list_type', 'supermarket')]
            list_id = matching_lists[0]['id'] if matching_lists else 1  # Fallback to list 1
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to System Templates", callback_data=f"system_template_management_{list_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text("❌ Failed to delete system template. Please try again.")

    async def process_template_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template_name: str):
        """Process template creation from user input"""
        user_id = update.effective_user.id
        
        # Check if creating regular template or system template
        template_data = context.user_data.get('creating_template')
        system_template_data = context.user_data.get('creating_system_template')
        
        if not template_data and not system_template_data:
            await update.message.reply_text("❌ Template creation data not found.")
            return
        
        # Determine template type
        is_system_template = system_template_data is not None
        data = system_template_data if is_system_template else template_data
        
        # Create template
        template_id = self.db.create_template(
            name=template_name.strip(),
            description=f"Template created from {data['list_name']}",
            list_type=data['list_type'],
            items=[{
                'name': item['name'],
                'category': item['category'],
                'notes': item['notes']
            } for item in data['items']],
            created_by=user_id,
            is_system_template=is_system_template
        )
        
        if template_id:
            template_type = "System Template" if is_system_template else "Template"
            message = f"✅ **{template_type} Created Successfully!**\n\n"
            message += f"Template: **{template_name}**\n"
            message += f"Items: {len(data['items'])}\n"
            message += f"List Type: {data['list_type']}\n"
            if is_system_template:
                message += f"Type: System Template (available to all users)\n"
            message += "\nYou can now use this template in the Templates menu!"
            
            keyboard = [
                [InlineKeyboardButton("📝 View Templates", callback_data=f"templates_list_{data['list_id']}")],
                [InlineKeyboardButton("📋 Back to List", callback_data=f"list_menu_{data['list_id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to create template. Please try again.")
        
        # Clear template creation state
        context.user_data.pop('creating_template', None)
        context.user_data.pop('creating_system_template', None)

    # Category Multi-Select Methods
    async def show_category_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show category item selection interface"""
        user_id = update.effective_user.id
        
        logging.info(f"show_category_item_selection called with category_key: '{category_key}'")
        
        # Get category items
        category_items = self.get_category_items(user_id, category_key)
        logging.info(f"Category items found: {len(category_items) if category_items else 0}")
        
        # Debug: Check if category exists in CATEGORIES
        from config import CATEGORIES
        logging.info(f"Category '{category_key}' exists in CATEGORIES: {category_key in CATEGORIES}")
        if category_key in CATEGORIES:
            logging.info(f"Category data: {CATEGORIES[category_key]}")
        
        # Debug: Check if it's a custom category
        custom_category = self.db.get_custom_category(category_key)
        logging.info(f"Custom category found: {custom_category is not None}")
        if custom_category:
            logging.info(f"Custom category data: {custom_category}")
        
        if not category_items:
            await update.callback_query.edit_message_text("❌ No items available in this category.")
            return
        
        # Store category selection state
        context.user_data[f'category_selection_{category_key}'] = {
            'category_key': category_key,
            'selected_items': []
        }
        
        # Get category name and emoji
        if category_key == 'recently':
            category_name = self.get_message(user_id, 'recently_category')
            category_emoji = "🕒"
        else:
            from config import CATEGORIES
            category_data = CATEGORIES.get(category_key, {})
            
            # Check if it's a custom category
            if not category_data:
                custom_category = self.db.get_custom_category(category_key)
                if custom_category:
                    category_name = self.get_category_name(user_id, category_key)
                    category_emoji = custom_category['emoji']
                else:
                    # Fallback for unknown categories
                    category_name = category_key
                    category_emoji = "📦"
            else:
                category_name = self.get_category_name(user_id, category_key)
                category_emoji = category_data.get('emoji', '📦')
        
        message = f"🎯 **Select Items from {category_emoji} {category_name}**\n\n"
        message += "Choose which items to add to your shopping list:\n\n"
        
        keyboard = []
        for i, item in enumerate(category_items):
            keyboard.append([InlineKeyboardButton(f"☐ {item}", callback_data=f"category_toggle_{category_key}_{i}")])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Add Selected Items", callback_data=f"category_add_selected_{category_key}")],
            [InlineKeyboardButton("🔙 Back to Category", callback_data=f"category_{category_key}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def toggle_category_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str, item_index: int):
        """Toggle item selection in category"""
        user_id = update.effective_user.id
        
        # Get category items
        category_items = self.get_category_items(user_id, category_key)
        if not category_items or item_index >= len(category_items):
            await update.callback_query.answer("❌ Invalid item selection")
            return
        
        # Get or create selection state
        selection_key = f'category_selection_{category_key}'
        if selection_key not in context.user_data:
            context.user_data[selection_key] = {
                'category_key': category_key,
                'selected_items': []
            }
        
        selected_items = context.user_data[selection_key]['selected_items']
        item_name = category_items[item_index]
        
        # Toggle selection
        if item_name in selected_items:
            selected_items.remove(item_name)
        else:
            selected_items.append(item_name)
        
        # Update button text
        is_selected = item_name in selected_items
        button_text = f"{'☑️' if is_selected else '☐'} {item_name}"
        
        # Update the specific button
        keyboard = []
        for i, category_item in enumerate(category_items):
            is_item_selected = category_item in selected_items
            button_text = f"{'☑️' if is_item_selected else '☐'} {category_item}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"category_toggle_{category_key}_{i}")])
        
        keyboard.extend([
            [InlineKeyboardButton("✅ Add Selected Items", callback_data=f"category_add_selected_{category_key}")],
            [InlineKeyboardButton("🔙 Back to Category", callback_data=f"category_{category_key}")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)

    async def add_selected_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Add selected category items to the shopping list"""
        user_id = update.effective_user.id
        
        # Get selected items from user data
        selection_key = f'category_selection_{category_key}'
        selected_items = context.user_data.get(selection_key, {}).get('selected_items', [])
        
        if not selected_items:
            await update.callback_query.edit_message_text("❌ No items selected.")
            return
        
        # Get target list ID
        target_list_id = context.user_data.get('target_list_id', 1)  # Default to supermarket list
        
        items_added = 0
        failed_items = []
        
        for item_name in selected_items:
            # Determine category for the item
            if category_key == 'recently':
                # For recently used items, we need to find the original category
                recent_items = self.db.get_recently_used_items()
                item_category = None
                for recent_item in recent_items:
                    if recent_item['name'] == item_name:
                        item_category = recent_item['category']
                        break
            else:
                item_category = category_key
            
            # Add item to list
            success = self.db.add_item_to_list(target_list_id, item_name, item_category, None, user_id)
            if success:
                items_added += 1
            else:
                failed_items.append(item_name)
        
        # Create success message
        if items_added > 0:
            message = f"✅ **Items Added Successfully!**\n\n"
            message += f"Added {items_added} items to your shopping list.\n\n"
            
            if failed_items:
                message += f"⚠️ Failed to add: {', '.join(failed_items)}\n\n"
            
            message += "Selected items:\n"
            for item in selected_items:
                if item not in failed_items:
                    message += f"• {item}\n"
        else:
            message = f"❌ **Failed to add items**\n\n"
            message += "All selected items could not be added to your shopping list."
        
        keyboard = [
            [InlineKeyboardButton("📋 View Shopping List", callback_data=f"view_list_{target_list_id}")],
            [InlineKeyboardButton("🔙 Back to Category", callback_data=f"category_{category_key}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Clear selection state
        context.user_data.pop(selection_key, None)

    async def send_maintenance_notification_to_admins(self, context: ContextTypes.DEFAULT_TYPE, day: str, time: str):
        """Send maintenance notification to all admins when scheduled time is over"""
        try:
            # Get all admin users
            admins = self.db.get_admin_users()
            
            if not admins:
                logger.warning("No admin users found for maintenance notification")
                return
            
            # Create notification message with reset options
            for admin in admins:
                try:
                    # Get admin's language preference
                    admin_lang = self.get_user_language(admin['user_id'])
                    
                    # Create message based on language
                    if admin_lang == 'he':
                        message = self.get_message(admin['user_id'], 'maintenance_time_over').format(day=day, time=time)
                    else:
                        message = self.get_message(admin['user_id'], 'maintenance_time_over').format(day=day, time=time)
                    
                    # Create inline keyboard with reset options
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "✅ Reset List Now" if admin_lang != 'he' else "✅ אפס רשימה עכשיו",
                                callback_data="maintenance_reset_confirm"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "❌ Not Yet" if admin_lang != 'he' else "❌ עדיין לא",
                                callback_data="maintenance_reset_decline"
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send notification to admin
                    await context.bot.send_message(
                        chat_id=admin['user_id'],
                        text=message,
                        reply_markup=reply_markup
                    )
                    
                    logger.info(f"Maintenance notification sent to admin {admin['user_id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to send maintenance notification to admin {admin['user_id']}: {e}")
            
            logger.info(f"Maintenance notifications sent to {len(admins)} admins")
            
        except Exception as e:
            logger.error(f"Error sending maintenance notifications: {e}")

    async def check_maintenance_schedule(self, context: ContextTypes.DEFAULT_TYPE):
        """Check if it's time to send maintenance notifications"""
        try:
            # Get active maintenance mode
            maintenance = self.db.get_maintenance_mode(1)  # Supermarket list
            
            if not maintenance:
                return  # No active maintenance mode
            
            # Get current time
            now = datetime.now()
            current_day = now.strftime('%A').lower()
            current_time = now.strftime('%H:%M')
            
            # Check if it's the scheduled day and time has passed
            scheduled_day = maintenance['scheduled_day'].lower()
            scheduled_time = maintenance['scheduled_time']
            
            # Convert day names to lowercase for comparison
            day_mapping = {
                'monday': 'monday',
                'tuesday': 'tuesday', 
                'wednesday': 'wednesday',
                'thursday': 'thursday',
                'friday': 'friday',
                'saturday': 'saturday',
                'sunday': 'sunday'
            }
            
            if current_day == day_mapping.get(scheduled_day, scheduled_day):
                # Check if current time is past scheduled time
                try:
                    scheduled_hour, scheduled_minute = map(int, scheduled_time.split(':'))
                    current_hour, current_minute = map(int, current_time.split(':'))
                    
                    scheduled_total_minutes = scheduled_hour * 60 + scheduled_minute
                    current_total_minutes = current_hour * 60 + current_minute
                    
                    # Check if we're past the scheduled time (with 1 minute tolerance)
                    if current_total_minutes >= scheduled_total_minutes:
                        # Check if we haven't sent a notification today
                        last_reminder = maintenance.get('last_reminder')
                        if last_reminder:
                            try:
                                # Handle different datetime formats
                                if 'T' in last_reminder:
                                    last_reminder_date = datetime.fromisoformat(last_reminder.replace('Z', '+00:00'))
                                else:
                                    last_reminder_date = datetime.fromisoformat(last_reminder)
                                
                                if last_reminder_date.date() == now.date():
                                    return  # Already sent today
                            except ValueError:
                                # If we can't parse the date, proceed with sending notification
                                pass
                        
                        # Send notification to admins
                        await self.send_maintenance_notification_to_admins(context, scheduled_day.title(), scheduled_time)
                        
                        # Update reminder timestamp
                        self.db.update_maintenance_reminder(maintenance['id'])
                        
                        logger.info(f"Maintenance notification sent for {scheduled_day} {scheduled_time}")
                        
                except ValueError:
                    logger.error(f"Invalid time format in maintenance schedule: {scheduled_time}")
                    
        except Exception as e:
            logger.error(f"Error checking maintenance schedule: {e}")

    def run(self):
        """Run the bot"""
        logger.info("Starting Shopping Bot...")
        
        # Set up bot commands menu
        async def post_init(application):
            await self.setup_bot_commands()
            
            # Set up maintenance schedule checker (if JobQueue is available)
            job_queue = application.job_queue
            if job_queue is not None:
                # Check maintenance schedule every 30 minutes
                job_queue.run_repeating(
                    self.check_maintenance_schedule,
                    interval=1800,  # 30 minutes in seconds
                    first=10  # Start after 10 seconds
                )
                logger.info("Maintenance schedule checker started")
            else:
                logger.warning("JobQueue not available - maintenance notifications disabled. Install with: pip install python-telegram-bot[job-queue]")
        
        self.application.post_init = post_init
        self.application.run_polling()

if __name__ == "__main__":
    bot = ShoppingBot()
    bot.run()
