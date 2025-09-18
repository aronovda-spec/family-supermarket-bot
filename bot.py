import logging
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, ADMIN_IDS, CATEGORIES, MESSAGES
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
        
        # Initialize admin users
        for admin_id in ADMIN_IDS:
            self.db.add_user(admin_id, is_admin=True)

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
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for custom item addition
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Check if user is already registered
        if not self.db.is_user_authorized(user.id):
            # Auto-register if admin, otherwise require manual approval
            if user.id in ADMIN_IDS:
                self.db.add_user(user.id, user.username, user.first_name, user.last_name, is_admin=True)
                await update.message.reply_text(
                    f"🔑 Welcome Admin {user.first_name}!\n\n" + MESSAGES['welcome']
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
            # Update user info
            self.db.add_user(user.id, user.username, user.first_name, user.last_name)
            await update.message.reply_text(MESSAGES['welcome'])

        # Show main menu
        await self.show_main_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return
            
        await update.message.reply_text(MESSAGES['help'], parse_mode='Markdown')

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu with quick action buttons"""
        keyboard = [
            [KeyboardButton("📋 Categories"), KeyboardButton("➕ Add Item")],
            [KeyboardButton("📝 View List"), KeyboardButton("📊 Summary")],
            [KeyboardButton("👤 My Items"), KeyboardButton("❓ Help")]
        ]
        
        if self.db.is_user_admin(update.effective_user.id):
            keyboard.append([KeyboardButton("🗑️ Reset List"), KeyboardButton("👥 Manage Users")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if update.message:
            await update.message.reply_text(
                "🛒 What would you like to do?", 
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                "🛒 What would you like to do?", 
                reply_markup=reply_markup
            )

    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command - show category selection"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        await self.show_categories(update, context)

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show categories for selection"""
        keyboard = []
        for category_key, category_data in CATEGORIES.items():
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_data['name']}", 
                callback_data=f"category_{category_key}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🛒 **Select a category to browse items:**"
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category_key: str):
        """Show items in a specific category"""
        category_data = CATEGORIES.get(category_key)
        if not category_data:
            return

        keyboard = []
        for item in category_data['items']:
            keyboard.append([InlineKeyboardButton(
                f"✅ {item}", 
                callback_data=f"add_item_{category_key}_{item}"
            )])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Categories", callback_data="categories"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"{category_data['emoji']} **{category_data['name']}**\n\nTap ✅ to add items to your shopping list:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - prompt for custom item"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        context.user_data['waiting_for_item'] = True
        await update.message.reply_text(
            "✏️ **Add Custom Item**\n\n"
            "Please type the item name you want to add to the shopping list:\n\n"
            "_Example: Organic honey_",
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        text = update.message.text.strip()
        
        # Handle main menu buttons
        if text == "📋 Categories":
            await self.show_categories(update, context)
            return
        elif text == "➕ Add Item":
            await self.add_item_command(update, context)
            return
        elif text == "📝 View List":
            await self.list_command(update, context)
            return
        elif text == "📊 Summary":
            await self.summary_command(update, context)
            return
        elif text == "👤 My Items":
            await self.my_items_command(update, context)
            return
        elif text == "❓ Help":
            await self.help_command(update, context)
            return
        elif text == "🗑️ Reset List":
            await self.reset_command(update, context)
            return
        elif text == "👥 Manage Users":
            await self.users_command(update, context)
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
        
        keyboard = [[InlineKeyboardButton("Skip Notes", callback_data="skip_note")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Adding:** {item_name}\n\n"
            "📝 Would you like to add notes? (quantity, brand, priority, etc.)\n\n"
            "_Example: 2 bottles, organic brand_\n\n"
            "Or tap 'Skip Notes' to add without notes:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def process_item_with_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_info: Dict, note: str = None):
        """Process item addition with optional note"""
        context.user_data['waiting_for_note'] = False
        context.user_data.pop('item_info', None)
        
        item_id = self.db.add_item(
            item_name=item_info['name'],
            category=item_info['category'],
            notes=note,
            added_by=item_info['user_id']
        )
        
        if item_id:
            note_text = f"\n📝 Note: {note}" if note else ""
            await update.message.reply_text(
                f"✅ **Added to shopping list:**\n"
                f"🛒 {item_info['name']}{note_text}\n\n"
                f"Use /list to view the complete shopping list.",
                parse_mode='Markdown'
            )
            
            # Notify other users
            await self.notify_users_item_added(update, context, item_info['name'], note)
        else:
            await update.message.reply_text("❌ Error adding item. Please try again.")

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show current shopping list"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        items = self.db.get_shopping_list()
        
        if not items:
            await update.message.reply_text(MESSAGES['list_empty'])
            return

        # Group items by category
        categorized_items = {}
        for item in items:
            category = item['category'] or 'Other'
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)

        # Build message
        message_parts = ["🛒 **Current Shopping List:**\n"]
        
        for category, category_items in categorized_items.items():
            # Get category emoji
            category_emoji = "📦"
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category or cat_data['name'] == category:
                    category_emoji = cat_data['emoji']
                    break
            
            message_parts.append(f"\n{category_emoji} **{category}**")
            
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

        message_parts.append(f"\n📊 **Total items:** {len(items)}")
        
        full_message = "\n".join(message_parts)
        
        # Split message if too long
        if len(full_message) > 4000:
            # Send in chunks
            current_chunk = "🛒 **Current Shopping List:**\n"
            for part in message_parts[1:]:
                if len(current_chunk + part) > 4000:
                    await update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = part
                else:
                    current_chunk += "\n" + part
            
            if current_chunk:
                await update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(full_message, parse_mode='Markdown')

    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command - generate formatted shopping report"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        items = self.db.get_shopping_list()
        
        if not items:
            await update.message.reply_text(MESSAGES['list_empty'])
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
            "📊 **SHOPPING SUMMARY REPORT**",
            f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"📋 Total Items: {len(items)}",
            "─" * 30
        ]
        
        for category, category_items in categorized_items.items():
            # Get category emoji
            category_emoji = "📦"
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category or cat_data['name'] == category:
                    category_emoji = cat_data['emoji']
                    break
            
            summary_parts.append(f"\n{category_emoji} **{category.upper()}** ({len(category_items)} items)")
            
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
                    await update.message.reply_text(current_chunk, parse_mode='Markdown')
                    current_chunk = part
                else:
                    current_chunk += "\n" + part if current_chunk else part
            
            if current_chunk:
                await update.message.reply_text(current_chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(full_summary, parse_mode='Markdown')

    async def my_items_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /myitems command - show items added by current user"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        user_items = self.db.get_items_by_user(update.effective_user.id)
        
        if not user_items:
            await update.message.reply_text(
                "📝 You haven't added any items to the shopping list yet.\n\n"
                "Use /categories to browse items or /add to add custom items!"
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
        message_parts = [f"👤 **Your Items ({len(user_items)} total):**\n"]
        
        for category, category_items in categorized_items.items():
            # Get category emoji
            category_emoji = "📦"
            for cat_key, cat_data in CATEGORIES.items():
                if cat_key == category or cat_data['name'] == category:
                    category_emoji = cat_data['emoji']
                    break
            
            message_parts.append(f"\n{category_emoji} **{category}**")
            
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
        await update.message.reply_text(full_message, parse_mode='Markdown')

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command - reset shopping list (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['admin_only'])
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
            "🗑️ **Reset Shopping List**\n\n"
            "⚠️ This will permanently delete ALL items from the shopping list.\n\n"
            "Are you sure you want to continue?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        if not self.db.is_user_authorized(update.effective_user.id):
            await query.edit_message_text(MESSAGES['not_registered'])
            return

        data = query.data

        if data == "main_menu":
            await query.delete_message()
            await self.show_main_menu(update, context)
        
        elif data == "categories":
            await self.show_categories(update, context)
        
        elif data.startswith("category_"):
            category_key = data.replace("category_", "")
            await self.show_category_items(update, context, category_key)
        
        elif data.startswith("add_item_"):
            parts = data.replace("add_item_", "").split("_", 1)
            if len(parts) == 2:
                category_key, item_name = parts
                await self.process_category_item_selection(update, context, category_key, item_name)
        
        elif data == "skip_note":
            item_info = context.user_data.get('item_info')
            if item_info:
                await self.process_item_with_note(update, context, item_info)
        
        elif data == "confirm_reset":
            await self.confirm_reset(update, context)
        
        elif data == "cancel_reset":
            await query.edit_message_text("❌ Reset cancelled.")

    async def process_category_item_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            category_key: str, item_name: str):
        """Process item selection from category"""
        # Ask for optional note
        context.user_data['waiting_for_note'] = True
        context.user_data['item_info'] = {
            'name': item_name,
            'category': category_key,
            'user_id': update.effective_user.id
        }
        
        keyboard = [[InlineKeyboardButton("Skip Notes", callback_data="skip_note")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            f"✅ **Adding:** {item_name}\n\n"
            "📝 Would you like to add notes? (quantity, brand, priority, etc.)\n\n"
            "_Example: 2 bottles, organic brand_\n\n"
            "Type your note or tap 'Skip Notes':",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def confirm_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute list reset"""
        if self.db.reset_shopping_list():
            await update.callback_query.edit_message_text(
                "✅ **Shopping list has been reset!**\n\n"
                "All items have been cleared. You can start adding new items for your next shopping trip."
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
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['admin_only'])
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
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['admin_only'])
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/authorize <user_id>`\n\n"
                "Example: `/authorize 123456789`\n\n"
                "Use `/users` to see pending users and their IDs.",
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
                "Users must send `/start` to the bot first before they can be authorized.",
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
                f"They will be notified and can start using all bot features.",
                parse_mode='Markdown'
            )

            # Notify the authorized user
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_authorize,
                    text=f"🎉 **Great news!**\n\n"
                         f"You've been authorized by {admin_name} to use the Family Shopping List Bot!\n\n"
                         f"You can now:\n"
                         f"• Browse categories with /categories\n"
                         f"• Add custom items with /add\n"
                         f"• View the shopping list with /list\n"
                         f"• Get summaries with /summary\n\n"
                         f"Use /help to see all available commands. Happy shopping! 🛒",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not notify authorized user {user_id_to_authorize}: {e}")

        else:
            await update.message.reply_text("❌ Error authorizing user. Please try again.")

    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addadmin command - promote user to admin (admin only)"""
        if not self.db.is_user_authorized(update.effective_user.id):
            await update.message.reply_text(MESSAGES['not_registered'])
            return

        if not self.db.is_user_admin(update.effective_user.id):
            await update.message.reply_text(MESSAGES['admin_only'])
            return

        # Check if user_id was provided
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/addadmin <user_id>`\n\n"
                "Example: `/addadmin 123456789`\n\n"
                "⚠️ **Warning:** This gives the user full admin privileges including:\n"
                "• User management\n"
                "• Item deletion\n"
                "• List reset\n"
                "• Admin promotion\n\n"
                "Use `/users` to see user IDs.",
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
                "Users must send `/start` to the bot first before they can be promoted.",
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
                f"They will be notified of their new admin status.",
                parse_mode='Markdown'
            )

            # Notify the new admin
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_promote,
                    text=f"👑 **Congratulations!**\n\n"
                         f"You've been promoted to **Family Admin** by {admin_name}!\n\n"
                         f"🔑 **Your new admin privileges:**\n"
                         f"• `/users` - Manage family members\n"
                         f"• `/authorize <user_id>` - Authorize new users\n"
                         f"• `/addadmin <user_id>` - Promote users to admin\n"
                         f"• `/reset` - Reset shopping list\n"
                         f"• Delete items from shopping list\n\n"
                         f"🛒 You now have full control over the family shopping bot!\n\n"
                         f"Use `/help` to see all available commands.",
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
        promoter_name = update.effective_user.first_name or update.effective_user.username or "Admin"
        message = (
            f"👑 **New Admin Promoted**\n\n"
            f"👤 **{promoted_user_name}** (ID: `{promoted_user_id}`)\n"
            f"🔑 Promoted by: {promoter_name}\n\n"
            f"They now have full admin privileges."
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

    def run(self):
        """Run the bot"""
        logger.info("Starting Shopping Bot...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = ShoppingBot()
    bot.run()
