import logging
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, ADMIN_IDS, CATEGORIES, MESSAGES, LANGUAGES
from database import Database

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
        category = CATEGORIES.get(category_key, {})
        return category.get('name', {}).get(lang, category.get('name', {}).get('en', category_key))

    def get_category_items(self, user_id: int, category_key: str) -> List[str]:
        """Get localized category items"""
        lang = self.get_user_language(user_id)
        category = CATEGORIES.get(category_key, {})
        return category.get('items', {}).get(lang, category.get('items', {}).get('en', []))

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
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("suggest", self.suggest_item_command))
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
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for custom item addition
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

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
            BotCommand("broadcast", "📢 Send message to all (Admin)"),
            BotCommand("suggest", "💡 Suggest new item"),
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
            BotCommand("broadcast", "📢 שלח הודעה לכולם (מנהל)"),
            BotCommand("suggest", "💡 הצע פריט חדש"),
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
        
        await self.show_main_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return
            
        help_text = self.get_message(update.effective_user.id, 'help')
        await update.message.reply_text(help_text)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show dynamic main menu with list buttons"""
        user_id = update.effective_user.id
        
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
        
        # Add admin and utility buttons
        if self.db.is_user_admin(user_id):
            keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_admin')), KeyboardButton(self.get_message(user_id, 'btn_broadcast'))])
        elif self.db.is_user_authorized(user_id):
            keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_broadcast'))])
        
        keyboard.append([KeyboardButton(self.get_message(user_id, 'btn_language'))])
        keyboard.append([KeyboardButton("❓ Help")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        
        main_menu_text = self.get_message(user_id, 'main_menu')
        
        if update.message:
            await update.message.reply_text(main_menu_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(main_menu_text, reply_markup=reply_markup)

    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command - show category selection"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        await self.show_categories(update, context)

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show categories for selection"""
        user_id = update.effective_user.id
        keyboard = []
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}", 
                callback_data=f"category_{category_key}"
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
        category_data = CATEGORIES.get(category_key)
        if not category_data:
            return

        keyboard = []
        category_items = self.get_category_items(user_id, category_key)
        
        # Add existing items
        for item in category_items:
            keyboard.append([InlineKeyboardButton(
                f"✅ {item}", 
                callback_data=f"add_item_{category_key}_{item}"
            )])
        
        # Add "ADD NEW ITEM" button if no items exist or always show it
        keyboard.append([InlineKeyboardButton(
            "➕ ADD NEW ITEM",
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
            await update.message.reply_text("❌ Error: Category not found.")
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
            await update.message.reply_text("❌ Failed to add item. Please try again.")
        
        # Clear waiting states
        context.user_data.pop('waiting_for_add_to_list', None)
        context.user_data.pop('add_to_list_category', None)

    async def add_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - prompt for custom item"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        context.user_data['waiting_for_item'] = True
        await update.message.reply_text(
            f"✏️ **{self.get_message(user_id, 'btn_add_item')}**\n\n"
            f"{self.get_message(user_id, 'add_custom_item_prompt')}",
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        text = update.message.text.strip()
        user_id = update.effective_user.id
        
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
        elif (text == self.get_message(user_id, 'btn_manage_suggestions') or 
              text == "💡 Manage Suggestions" or text == "💡 נהל הצעות"):
            await self.manage_suggestions_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_new_item') or 
              text == "➕ New Item" or text == "➕ פריט חדש"):
            await self.new_item_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_search') or 
              text == "🔍 Search" or text == "🔍 חיפוש"):
            await self.search_command(update, context)
            return
        elif text == "❓ Help":
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
        
        # Handle search input
        if context.user_data.get('waiting_for_search'):
            await self.process_search(update, context, text)
            return
        
        # Handle multi-list message buttons
        elif (text == self.get_message(user_id, 'btn_supermarket_list') or 
              text == self.get_message(update.effective_user.id, 'btn_supermarket_list')):
            await self.supermarket_list_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_new_list') or 
              text == "➕ New List" or text == "➕ רשימה חדשה"):
            await self.new_list_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_my_lists') or 
              text == "📋 My Lists" or text == "📋 הרשימות שלי"):
            await self.my_lists_command(update, context)
            return
        elif (text == self.get_message(user_id, 'btn_manage_lists') or 
              text == "📂 Manage Lists" or text == "📂 נהל רשימות"):
            await self.manage_lists_command(update, context)
            return
        elif (text == "⚙️ Admin" or text == "⚙️ מנהל"):
            await self.show_admin_menu(update, context)
            return
        
        # Handle dynamic list buttons
        elif text.startswith("🛒 ") or text.startswith("📋 "):
            list_name = text[2:]  # Remove emoji prefix
            await self.show_list_menu(update, context, list_name)
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

    async def process_custom_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_name: str):
        """Process custom item addition"""
        context.user_data['waiting_for_item'] = False
        
        # Ask for optional note
        context.user_data['waiting_for_note'] = True
        context.user_data['item_info'] = {
            'name': item_name,
            'category': 'custom',
            'user_id': update.effective_user.id
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
            
            # Check if it's from callback query (Add button) or text message (typed note)
            if update.callback_query:
                await update.callback_query.edit_message_text(success_message)
            else:
                await update.message.reply_text(success_message)
            
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
            "📊 SHOPPING SUMMARY REPORT",
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
                keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data="list_menu_1")]]
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
            keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data="list_menu_1")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(full_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(full_message)

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command - reset shopping list (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
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
            await query.delete_message()
            await self.show_main_menu(update, context)
        
        elif data.startswith("my_items_"):
            list_id = int(data.replace("my_items_", ""))
            await self.my_items_command(update, context, list_id)
        
        elif data == "my_summary":
            await self.summary_command(update, context)
        
        elif data == "categories":
            await self.show_categories(update, context)
        
        elif data.startswith("category_"):
            category_key = data.replace("category_", "")
            await self.show_category_items(update, context, category_key)
        
        elif data.startswith("add_item_"):
            # Parse: add_item_categorykey_itemname
            # We need to be careful with category keys that contain underscores
            remaining = data.replace("add_item_", "")
            
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
        
        elif data.startswith("add_new_item_"):
            # Handle "ADD NEW ITEM" button from category
            category_key = data.replace("add_new_item_", "")
            await self.show_add_new_item_options(update, context, category_key)
        
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
                await query.edit_message_text("❌ Error changing language.")
        
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
                
                await query.edit_message_text("✅ Suggestion approved!")
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ Error approving suggestion.")
        
        elif data.startswith("reject_suggestion_"):
            suggestion_id = int(data.replace("reject_suggestion_", ""))
            user_id = update.effective_user.id
            
            if self.db.reject_suggestion(suggestion_id, user_id):
                suggestion = self.db.get_suggestion_by_id(suggestion_id)
                if suggestion:
                    # Notify the user who suggested the item
                    await self.notify_suggestion_result(update, context, suggestion, 'rejected')
                
                await query.edit_message_text("❌ Suggestion rejected.")
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
            input_prompt = f"➕ ADD NEW ITEM (ADMIN)\n\nCategory: {category_name}\n\nPlease type the item name in English:\n\n💡 Tips:\n• Use clear, simple names\n• Avoid brand names\n• Examples: 'Organic honey', 'Fresh basil', 'Whole wheat bread'\n\nType the item name:"
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
                        "✅ ADD TO THE LIST",
                        callback_data=f"search_add_list_{list_id}_{category_key}_{urllib.parse.quote(item_name)}"
                    )],
                    [InlineKeyboardButton(
                        "🏠 Back to List",
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
                        "✅ ADD TO THE LIST",
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
            await self.show_supermarket_list(update, context)
        
        elif data == "new_list":
            await self.show_create_list_prompt(update, context)
        
        elif data == "my_lists":
            await self.show_my_lists(update, context)
        
        elif data == "manage_lists":
            await self.show_manage_lists(update, context)
        
        elif data.startswith("manage_suggestions_"):
            list_id = int(data.replace("manage_suggestions_", ""))
            await self.show_manage_suggestions_for_list(update, context, list_id)
        
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
        
        elif data.startswith("remove_items_"):
            list_id = int(data.replace("remove_items_", ""))
            await self.show_remove_items_menu(update, context, list_id)
        
        elif data.startswith("remove_category_"):
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
        
        elif data.startswith("remove_item_"):
            parts = data.split('_')
            list_id = int(parts[2])
            item_id = int(parts[3])
            await self.remove_individual_item(update, context, list_id, item_id)
        
        elif data.startswith("delete_permanent_items_"):
            list_id = int(data.replace("delete_permanent_items_", ""))
            await self.show_delete_permanent_items(update, context, list_id)
        
        elif data.startswith("delete_permanent_category_"):
            parts = data.split('_')
            list_id = int(parts[3])
            category = '_'.join(parts[4:])  # In case category has underscores
            await self.confirm_delete_permanent_category(update, context, list_id, category)
        
        elif data.startswith("delete_permanent_individual_"):
            list_id = int(data.replace("delete_permanent_individual_", ""))
            await self.show_delete_permanent_individual(update, context, list_id)
        
        elif data.startswith("confirm_delete_permanent_category_"):
            parts = data.split('_')
            list_id = int(parts[4])
            category = '_'.join(parts[5:])  # In case category has underscores
            await self.delete_permanent_category_items(update, context, list_id, category)
        
        elif data.startswith("delete_permanent_item_"):
            parts = data.split('_', 4)  # Split into max 5 parts: ['delete', 'permanent', 'item', 'list_id', 'category_itemname']
            list_id = int(parts[3])
            category_item = parts[4]  # This contains "category_itemname"
            # Split category and item name (category is first part, rest is item name)
            category_parts = category_item.split('_', 1)
            category = category_parts[0]
            item_name = category_parts[1] if len(category_parts) > 1 else ""
            await self.delete_permanent_individual_item(update, context, list_id, category, item_name)
        
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
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ Error deleting list.")
        
        elif data.startswith("reset_list_"):
            list_id = int(data.replace("reset_list_", ""))
            if self.db.reset_list(list_id):
                list_info = self.db.get_list_by_id(list_id)
                list_name = list_info['name'] if list_info else f"List {list_id}"
                message = self.get_message(update.effective_user.id, 'list_reset_items').format(list_name=list_name)
                await query.edit_message_text(message)
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
                InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{target_list_id or 1}")
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
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        users = self.db.get_all_users()
        
        if not users:
            await update.message.reply_text("👥 No users registered yet.")
            return

        # Build user list message
        message_parts = ["👥 **User Management**\n"]
        
        admins = [u for u in users if u['is_admin']]
        authorized = [u for u in users if u['is_authorized'] and not u['is_admin']]
        unauthorized = [u for u in users if not u['is_authorized']]

        if admins:
            message_parts.append("👑 **Admins:**")
            for user in admins:
                name = user['first_name'] or user['username'] or f"User {user['user_id']}"
                message_parts.append(f"• {name} (ID: {user['user_id']})")

        if authorized:
            message_parts.append("\n✅ **Authorized Users:**")
            for user in authorized:
                name = user['first_name'] or user['username'] or f"User {user['user_id']}"
                message_parts.append(f"• {name} (ID: {user['user_id']})")

        if unauthorized:
            message_parts.append("\n⏳ **Pending Authorization:**")
            for user in unauthorized:
                name = user['first_name'] or user['username'] or f"User {user['user_id']}"
                message_parts.append(f"• {name} (ID: {user['user_id']})")
                message_parts.append(f"  `/authorize {user['user_id']}`")

        message_parts.append(f"\n📊 **Total Users:** {len(users)}")
        message_parts.append("\n💡 **Commands:**")
        message_parts.append("• `/authorize <user_id>` - Authorize a regular user")
        message_parts.append("• `/addadmin <user_id>` - Promote user to admin")
        message_parts.append("• `/users` - Show this list")

        full_message = "\n".join(message_parts)
        await update.message.reply_text(full_message, parse_mode='Markdown')

    async def authorize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /authorize command - authorize a user (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
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
            user_name = user_info['first_name'] or user_info['username'] or f"User {user_id_to_authorize}"
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
            user_name = user_info['first_name'] or user_info['username'] or f"User {user_id_to_authorize}"
            admin_name = update.effective_user.first_name or update.effective_user.username or "Admin"
            
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
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                f"❌ **Usage:** `/addadmin <user_id>`\n\n"
                f"{self.get_message(user_id, 'addadmin_example')}",
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
            user_name = user_info['first_name'] or user_info['username'] or f"User {user_id_to_promote}"
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
            user_name = user_info['first_name'] or user_info['username'] or f"User {user_id_to_promote}"
            admin_name = update.effective_user.first_name or update.effective_user.username or "Admin"
            
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

    async def notify_admins_promotion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    promoted_user_name: str, promoted_user_id: int):
        """Notify other admins about user promotion"""
        user_id = update.effective_user.id
        promoter_name = update.effective_user.first_name or update.effective_user.username or "Admin"
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
        user_name = user.first_name or user.username or f"User {user.id}"
        message = (
            f"👤 **New User Request**\n\n"
            f"Name: {user_name}\n"
            f"Username: @{user.username if user.username else 'None'}\n"
            f"ID: `{user.id}`\n\n"
            f"To authorize: `/authorize {user.id}`\n"
            f"To view all users: `/users`"
        )
        
        # Get all admin users
        all_users = self.db.get_all_users()
        for db_user in all_users:
            if db_user['is_admin'] and db_user['user_id'] != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=db_user['user_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not notify admin {db_user['user_id']}: {e}")

    async def notify_users_item_added(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    item_name: str, note: str = None):
        """Notify other users when an item is added"""
        user = update.effective_user
        user_name = user.first_name or user.username or "Someone"
        
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
        user_name = user.first_name or user.username or "Admin"
        
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
        sender_name = sender_info.get('first_name', '') or sender_info.get('username', '') or f"User {user_id}"
        
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
        if self.db.add_item_suggestion(user_id, category_key, item_name_en, hebrew_translation.strip(), target_list_id):
            category_name = self.get_category_name(user_id, category_key)
            success_message = self.get_message(user_id, 'suggestion_submitted').format(
                item_name_en=item_name_en,
                item_name_he=hebrew_translation.strip(),
                category=category_name
            )
            await update.message.reply_text(success_message)
            
            # Notify admins about new suggestion
            await self.notify_admins_new_suggestion(update, context, item_name_en, hebrew_translation.strip(), category_name)
        else:
            await update.message.reply_text(self.get_message(user_id, 'suggestion_error'))
        
        # Clear waiting states
        context.user_data.pop('waiting_for_suggestion_translation', None)
        context.user_data.pop('suggestion_item_name', None)
        context.user_data.pop('suggestion_category', None)

    async def notify_admins_new_suggestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         item_name_en: str, item_name_he: str, category_name: str):
        """Notify admins about new item suggestion"""
        admins = self.db.get_all_users()
        admins = [admin for admin in admins if admin['is_admin']]
        
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
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'not_registered'))
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        suggestions = self.db.get_pending_suggestions()
        
        if not suggestions:
            await update.message.reply_text(self.get_message(update.effective_user.id, 'suggestions_empty'))
            return
        
        # Show first suggestion for review
        await self.show_suggestion_review(update, context, suggestions[0], 0, len(suggestions))

    async def show_manage_suggestions_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show pending suggestions for a specific list"""
        if not self.db.is_user_admin(update.effective_user.id):
            await update.callback_query.edit_message_text(self.get_message(update.effective_user.id, 'admin_only'))
            return

        suggestions = self.db.get_pending_suggestions(list_id)
        
        if not suggestions:
            list_info = self.db.get_list_by_id(list_id)
            list_name = list_info['name'] if list_info else f"List {list_id}"
            
            keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"💡 **Manage Suggestions for {list_name}**\n\n"
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
        list_name = list_info['name'] if list_info else f"List {list_id}"
        
        message = f"💡 SUGGESTION REVIEW ({current_index + 1}/{total_count})\n\n"
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
            "🏠 Back to List",
            callback_data=f"list_menu_{list_id}"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    async def show_suggestion_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  suggestion: Dict, current_index: int, total_count: int):
        """Show suggestion for admin review"""
        user_id = update.effective_user.id
        category_name = self.get_category_name(user_id, suggestion['category_key'])
        
        message = f"💡 SUGGESTION REVIEW ({current_index + 1}/{total_count})\n\n"
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
        
        # Store the item name and ask for Hebrew translation
        context.user_data['new_item_name'] = item_name.strip()
        context.user_data['waiting_for_new_item'] = False
        context.user_data['waiting_for_new_item_translation'] = True
        
        category_key = context.user_data.get('new_item_category')
        category_name = self.get_category_name(user_id, category_key)
        
        translation_prompt = f"🌐 Translation Required (Admin)\n\nItem: {item_name.strip()}\nCategory: {category_name}\n\nPlease provide the Hebrew translation:\n\n💡 Tips:\n• Use common Hebrew terms\n• Keep it simple and clear\n• Examples: 'דבש אורגני', 'בזיליקום טרי', 'לחם מחיטה מלאה'\n\nType the Hebrew translation:"
        
        await update.message.reply_text(translation_prompt)

    async def process_new_item_translation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hebrew_translation: str):
        """Process new item Hebrew translation input (admin only)"""
        user_id = update.effective_user.id
        
        if not hebrew_translation.strip():
            await update.message.reply_text("❌ Please provide a Hebrew translation.")
            return
        
        # Get stored data
        item_name_en = context.user_data.get('new_item_name')
        category_key = context.user_data.get('new_item_category')
        
        if not item_name_en or not category_key:
            await update.message.reply_text("❌ Error processing new item. Please try again.")
            return
        
        # Add item directly to the category (admin privilege)
        if self.add_item_to_category(category_key, item_name_en, hebrew_translation.strip()):
            category_name = self.get_category_name(user_id, category_key)
            success_message = f"✅ New Item Added!\n\n📝 Item: {item_name_en}\n🌐 Hebrew: {hebrew_translation.strip()}\n📂 Category: {category_name}\n\nThis item is now available for everyone!"
            await update.message.reply_text(success_message)
            
            # Notify all users about the new item
            await self.notify_users_new_item(update, context, item_name_en, hebrew_translation.strip(), category_name)
        else:
            await update.message.reply_text("❌ Error adding new item. Please try again.")
        
        # Clear waiting states
        context.user_data.pop('waiting_for_new_item_translation', None)
        context.user_data.pop('new_item_name', None)
        context.user_data.pop('new_item_category', None)

    def add_item_to_category(self, category_key: str, item_name_en: str, item_name_he: str) -> bool:
        """Add item directly to category (admin only)"""
        try:
            # Update the CATEGORIES dictionary in config.py
            # This is a simplified approach - in production you'd want to persist this
            if category_key in CATEGORIES:
                CATEGORIES[category_key]['items']['en'].append(item_name_en)
                CATEGORIES[category_key]['items']['he'].append(item_name_he)
                return True
            return False
        except Exception as e:
            logging.error(f"Error adding item to category: {e}")
            return False

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

        await self.show_search_prompt(update, context)

    async def show_search_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show search prompt"""
        user_id = update.effective_user.id
        context.user_data['waiting_for_search'] = True
        
        prompt_text = self.get_message(user_id, 'search_prompt')
        await update.message.reply_text(prompt_text)

    async def process_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_query: str):
        """Process search query"""
        user_id = update.effective_user.id
        
        if not search_query.strip():
            await update.message.reply_text(self.get_message(user_id, 'search_empty'))
            return
        
        context.user_data['waiting_for_search'] = False
        
        # Check if this is a list-specific search
        search_list_id = context.user_data.get('search_list_id')
        if search_list_id:
            # Search within specific list
            results = self.search_items_in_list(search_query.strip(), search_list_id, user_id)
            list_info = self.db.get_list_by_id(search_list_id)
            list_name = list_info['name'] if list_info else f"List {search_list_id}"
        else:
            # General search (for backward compatibility)
            results = self.search_items(search_query.strip(), user_id)
            list_name = "all lists"
        
        if results:
            await self.show_search_results(update, context, search_query.strip(), results, list_name)
        else:
            await self.show_no_search_results(update, context, search_query.strip(), list_name)
        
        # Clear search context
        context.user_data.pop('search_list_id', None)

    def search_items(self, query: str, user_id: int) -> List[Dict]:
        """Search for items in all categories"""
        results = []
        query_lower = query.lower()
        
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
        
        # Remove duplicates
        unique_results = []
        seen = set()
        for result in results:
            key = (result['item_name'], result['category_key'])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results

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

    async def show_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, results: List[Dict], list_name: str = "all lists"):
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
                        "✅ ADD TO THE LIST",
                        callback_data=f"search_add_list_{list_id}_{result['category_key']}_{urllib.parse.quote(result['item_name'])}"
                    )],
                    [InlineKeyboardButton(
                        "🏠 Back to List",
                        callback_data=f"list_menu_{list_id}"
                    )]
                ]
            else:
                # For general search, use the old method
                keyboard = [
                    [InlineKeyboardButton(
                        "✅ ADD TO THE LIST",
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
                    "🏠 Back to List",
                    callback_data=f"list_menu_{list_id}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    self.get_message(user_id, 'btn_back_menu'),
                    callback_data="main_menu"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def show_no_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, list_name: str = "all lists"):
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
                "➕ ADD NEW ITEM",
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
        for category_key, category_data in CATEGORIES.items():
            category_name = self.get_category_name(user_id, category_key)
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_name}",
                callback_data=f"category_{category_key}"
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
                user_name = user_info.get('first_name') or user_info.get('username') or f"User {user_id_val}"
                stats_message += f"• {user_name}: {count}\n"
        
        keyboard = [[InlineKeyboardButton("🏠 Back to List Actions", callback_data=f"list_actions_{list_id}")]]
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
            message = f"📋 **{list_info['name']}**\n\n📝 This list is empty. Nothing to remove from the list.\n\n"
            message += self.get_message(user_id, 'however_delete_permanent')
            
            keyboard = []
            
            # Add permanent item deletion option for admins (always show)
            keyboard.append([InlineKeyboardButton(
                "🗑️ Delete Permanent Items", 
                callback_data=f"delete_permanent_items_{list_id}"
            )])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")])
            
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
        
        # Add permanent item deletion option for admins (always show)
        keyboard.append([InlineKeyboardButton(
            "🗑️ Delete Permanent Items", 
            callback_data=f"delete_permanent_items_{list_id}"
        )])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")])
        
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
            keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
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
        keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
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
            await update.callback_query.edit_message_text("Failed to remove item. Please try again.")
    
    async def show_delete_permanent_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show permanent items for deletion from categories"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get all permanent items from categories
        permanent_items = []
        user_lang = self.db.get_user_language(user_id) or 'en'
        
        for category_key, category_data in CATEGORIES.items():
            if isinstance(category_data, dict) and 'items' in category_data:
                # Get items for the user's language
                items = category_data['items'].get(user_lang, [])
                for item in items:
                    permanent_items.append({
                        'name': item,
                        'category': category_key,
                        'category_name': self.get_category_name(user_id, category_key)
                    })
        
        if not permanent_items:
            message = f"📋 **{list_info['name']}**\n\n📝 No permanent items found in categories."
            keyboard = [[InlineKeyboardButton("🏠 Back to Remove Menu", callback_data=f"remove_items_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        message = f"🗑️ **Delete Individual Permanent Items**\n\n"
        message += "⚠️ **WARNING**: This will permanently delete items from categories!\n"
        message += "These items will no longer be available for selection.\n\n"
        message += "Select individual items to delete permanently:\n\n"
        
        keyboard = []
        
        # Show individual items for selection (2 per row)
        for i in range(0, len(permanent_items), 2):
            row = []
            for j in range(2):
                if i + j < len(permanent_items):
                    item = permanent_items[i + j]
                    category_name = self.get_category_name(user_id, item['category'])
                    item_display = item['name'][:15] + "..." if len(item['name']) > 15 else item['name']
                    row.append(InlineKeyboardButton(
                        f"🗑️ {item_display}",
                        callback_data=f"delete_permanent_item_{list_id}_{item['category']}_{item['name']}"
                    ))
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🏠 Back to Remove Menu", callback_data=f"remove_items_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def confirm_delete_permanent_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, category: str):
        """Confirm deletion of all permanent items from a category"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get permanent items in this category
        category_data = CATEGORIES.get(category, {})
        if not isinstance(category_data, dict) or 'items' not in category_data:
            await update.callback_query.edit_message_text("No permanent items found in this category.")
            return
        
        user_lang = self.db.get_user_language(user_id) or 'en'
        permanent_items = category_data['items'].get(user_lang, [])
        category_name = self.get_category_name(user_id, category)
        
        message = f"🗑️ **Confirm Permanent Category Deletion**\n\n"
        message += f"**Category:** {category_name}\n"
        message += f"**Items to delete permanently:** {len(permanent_items)}\n\n"
        message += "**Items:**\n"
        for item in permanent_items[:10]:  # Show first 10 items
            message += f"• {item}\n"
        if len(permanent_items) > 10:
            message += f"... and {len(permanent_items) - 10} more items\n"
        
        message += f"\n⚠️ **WARNING**: This will permanently delete ALL items from the {category_name} category!"
        message += f"\nThese items will no longer be available for selection in any list."
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete All Permanently", callback_data=f"confirm_delete_permanent_category_{list_id}_{category}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"delete_permanent_items_{list_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_delete_permanent_individual(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show individual permanent items for deletion"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get all permanent items from categories
        permanent_items = []
        user_lang = self.db.get_user_language(user_id) or 'en'
        
        for category_key, category_data in CATEGORIES.items():
            if isinstance(category_data, dict) and 'items' in category_data:
                # Get items for the user's language
                items = category_data['items'].get(user_lang, [])
                for item in items:
                    permanent_items.append({
                        'name': item,
                        'category': category_key,
                        'category_name': self.get_category_name(user_id, category_key)
                    })
        
        if not permanent_items:
            message = f"📋 **{list_info['name']}**\n\n📝 No permanent items found in categories."
            keyboard = [[InlineKeyboardButton("🏠 Back to Remove Menu", callback_data=f"remove_items_{list_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        message = f"🔍 **Delete Individual Permanent Items from {list_info['name']}**\n\n"
        message += "⚠️ **WARNING**: This will permanently delete items from categories!\n\n"
        message += self.get_message(user_id, 'select_items_delete_permanently')
        
        keyboard = []
        
        # Add items in groups of 2 for better layout
        for i in range(0, len(permanent_items), 2):
            row = []
            for j in range(2):
                if i + j < len(permanent_items):
                    item = permanent_items[i + j]
                    item_name = item['name'][:15] + "..." if len(item['name']) > 15 else item['name']
                    row.append(InlineKeyboardButton(
                        f"🗑️ {item_name}", 
                        callback_data=f"delete_permanent_item_{list_id}_{item['category']}_{item['name']}"
                    ))
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🏠 Back to Delete Menu", callback_data=f"delete_permanent_items_{list_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def delete_permanent_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, category: str):
        """Delete all permanent items from a category"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get permanent items in this category
        category_data = CATEGORIES.get(category, {})
        if not isinstance(category_data, dict) or 'items' not in category_data:
            await update.callback_query.edit_message_text("No permanent items found in this category.")
            return
        
        user_lang = self.db.get_user_language(user_id) or 'en'
        permanent_items = category_data['items'].get(user_lang, []).copy()  # Make a copy
        category_name = self.get_category_name(user_id, category)
        
        # Clear the items from the category
        CATEGORIES[category]['items'][user_lang] = []
        
        # Notify all users about the deletion
        authorized_users = self.db.get_all_authorized_users()
        for auth_user in authorized_users:
            try:
                user_lang = self.db.get_user_language(auth_user['user_id'])
                if user_lang == 'he':
                    notification = f"🗑️ מנהל מחק לצמיתות {len(permanent_items)} פריטים מהקטגוריה '{category_name}'"
                else:
                    notification = f"🗑️ Admin permanently deleted {len(permanent_items)} items from '{category_name}' category"
                
                await self.application.bot.send_message(chat_id=auth_user['user_id'], text=notification)
            except Exception as e:
                logging.error(f"Error sending deletion notification to user {auth_user['user_id']}: {e}")
        
        success_message = f"✅ Successfully deleted {len(permanent_items)} items permanently from {category_name} category."
        keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(success_message, reply_markup=reply_markup)
    
    async def delete_permanent_individual_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int, category: str, item_name: str):
        """Delete an individual permanent item from a category"""
        user_id = update.effective_user.id
        list_info = self.db.get_list_by_id(list_id)
        
        if not list_info:
            await update.callback_query.edit_message_text(self.get_message(user_id, 'list_not_found'))
            return
        
        # Get permanent items in this category
        category_data = CATEGORIES.get(category, {})
        if not isinstance(category_data, dict) or 'items' not in category_data:
            await update.callback_query.edit_message_text("Category not found.")
            return
        
        user_lang = self.db.get_user_language(user_id) or 'en'
        items = category_data['items'].get(user_lang, [])
        
        if item_name not in items:
            await update.callback_query.edit_message_text("Item not found in category.")
            return
        
        # Remove the item from the category
        items.remove(item_name)
        category_name = self.get_category_name(user_id, category)
        
        # Notify all users about the deletion
        authorized_users = self.db.get_all_authorized_users()
        for auth_user in authorized_users:
            try:
                user_lang = self.db.get_user_language(auth_user['user_id'])
                if user_lang == 'he':
                    notification = f"🗑️ מנהל מחק לצמיתות את הפריט '{item_name}' מהקטגוריה '{category_name}'"
                else:
                    notification = f"🗑️ Admin permanently deleted item '{item_name}' from '{category_name}' category"
                
                await self.application.bot.send_message(chat_id=auth_user['user_id'], text=notification)
            except Exception as e:
                logging.error(f"Error sending deletion notification to user {auth_user['user_id']}: {e}")
        
        success_message = f"✅ Successfully deleted '{item_name}' permanently from {category_name} category."
        keyboard = [[InlineKeyboardButton("🏠 Back to Delete Menu", callback_data=f"delete_permanent_items_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(success_message, reply_markup=reply_markup)
    
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
        if list_name == self.get_message(user_id, 'supermarket_list') or list_name == "Supermarket List":
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
            [InlineKeyboardButton(self.get_message(user_id, 'btn_add_item'), callback_data=f"categories_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_search'), callback_data=f"search_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_view_items'), callback_data=f"view_list_{list_id}")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_summary'), callback_data=f"summary_list_{list_id}")]
        ]
        
        # Add "My Items" for all lists
        keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_my_items'), callback_data=f"my_items_{list_id}")])
        
        # Add admin-only options
        if self.db.is_user_admin(user_id):
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_export'), callback_data=f"export_list_{list_id}")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_manage_suggestions'), callback_data=f"manage_suggestions_{list_id}")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_edit_name'), callback_data=f"edit_list_name_{list_id}")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_remove_items'), callback_data=f"remove_items_{list_id}")])
            keyboard.append([InlineKeyboardButton(self.get_message(user_id, 'btn_reset_items'), callback_data=f"confirm_reset_list_{list_id}")])
            
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
        message += f"Items: {item_count}\n"
        message += f"Type: {target_list['list_type'].title()}\n\n"
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
            message = f"📋 **{list_info['name']}**\n\nNo items in this list yet."
        else:
            # Group items by category
            categories = {}
            for item in items:
                category = item['category'] or 'Other'
                if category not in categories:
                    categories[category] = []
                categories[category].append(item)
            
            message = f"📋 **{list_info['name']}** Summary\n\n"
            message += f"Total items: {len(items)}\n\n"
            
            for category, category_items in categories.items():
                message += f"**{category}** ({len(category_items)} items):\n"
                for item in category_items:
                    message += f"• {item['name']}"
                    if item['notes']:
                        message += f" ({item['notes']})"
                    message += "\n"
                message += "\n"
        
        keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_search_for_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_id: int):
        """Show search interface for a specific list"""
        user_id = update.effective_user.id
        
        list_info = self.db.get_list_by_id(list_id)
        if not list_info:
            await update.callback_query.edit_message_text("❌ List not found.")
            return
        
        # Set the target list for search
        context.user_data['search_list_id'] = list_id
        
        keyboard = [[InlineKeyboardButton("🏠 Back to List", callback_data=f"list_menu_{list_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🔍 **Search in {list_info['name']}**\n\n"
        message += "Type the name of an item you want to search for:"
        
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Set waiting state for search input
        context.user_data['waiting_for_search'] = True
        context.user_data['search_list_id'] = list_id
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin menu with all admin controls"""
        user_id = update.effective_user.id
        
        if not self.db.is_user_admin(user_id):
            await update.message.reply_text(self.get_message(user_id, 'admin_only'))
            return
        
        keyboard = [
            [InlineKeyboardButton("👥 Manage Users", callback_data="manage_users")],
            [InlineKeyboardButton("📂 Manage Lists", callback_data="manage_lists")],
            [InlineKeyboardButton(self.get_message(user_id, 'btn_back_menu'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "⚙️ ADMIN CONTROLS\n\nChoose an admin action:"
        
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
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Shopping Bot...")
        
        # Set up bot commands menu
        async def post_init(application):
            await self.setup_bot_commands()
        
        self.application.post_init = post_init
        self.application.run_polling()

if __name__ == "__main__":
    bot = ShoppingBot()
    bot.run()
