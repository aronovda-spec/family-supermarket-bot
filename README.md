# Family Shopping List Telegram Bot 🛒

A comprehensive Telegram bot for managing family shopping lists with multiple users, categories, and admin controls.

## Features ✨

### Core Functionality
- **Pre-defined Categories**: 12 categories with common items for quick selection
- **Custom Items**: Add any item not in the predefined lists
- **Notes System**: Optional quantity, brand, and priority notes
- **Duplicate Handling**: Smart merging of duplicate items with combined notes
- **User Management**: Admin and authorized user system
- **Real-time Notifications**: Users get notified of additions and deletions

### Categories Included
- 🥛 Dairy
- 🥦🍎 Fruits & Vegetables  
- 🍗🐟 Meat & Fish
- 🍞🍝 Staples (bread, pasta, rice)
- 🍫 Snacks
- 🧴🧻 Cleaning & Household
- 🥤 Beverages
- 🧊 Frozen Foods
- 🧂 Condiments & Spices
- 👶🐕 Baby & Pet
- 💊 Pharmacy & Health
- 🥐 Bakery

### Admin Features
- Item deletion with user notifications
- Complete list reset functionality
- User management and authorization

### Reports & Views
- **Current List**: Categorized view with notes and contributors
- **Summary Report**: Clean, printable shopping list
- **My Items**: Personal view of items you've added
- **By Category**: Organized shopping experience

## Setup Instructions 🚀

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Admin Telegram User IDs

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd family-shopping-bot
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   ADMIN_IDS=123456789,987654321
   DATABASE_PATH=shopping_bot.db
   ```

3. **Get Your Bot Token**
   - Message @BotFather on Telegram
   - Create a new bot with `/newbot`
   - Copy the token to your `.env` file

4. **Get Admin User IDs**
   - Message @userinfobot on Telegram to get your user ID
   - Add all admin user IDs to the `.env` file (comma-separated)

5. **Run the Bot**
   ```bash
   python bot.py
   ```

## Usage Guide 📱

### Getting Started
1. Start the bot with `/start`
2. Admins are auto-registered, others need admin approval
3. Use `/help` to see all available commands

### Adding Items
- **From Categories**: Use `/categories` or "📋 Categories" button
- **Custom Items**: Use `/add` or "➕ Add Item" button
- **With Notes**: Add quantity, brand, or priority when prompted

### Managing the List
- **View List**: `/list` or "📝 View List" - see all items with notes
- **Summary**: `/summary` or "📊 Summary" - clean report for shopping
- **My Items**: `/myitems` or "👤 My Items" - items you've added
- **Reset**: `/reset` or "🗑️ Reset List" (admin only)

### Admin Functions
- Delete items: Use `/delete_[item_id]` shown in the list view
- Reset entire list: Use `/reset` command
- All actions notify other users automatically

## Bot Commands 🤖

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Register and start using the bot | All |
| `/help` | Show help and commands | All |
| `/categories` | Browse items by category | All |
| `/add` | Add custom item | All |
| `/list` | View current shopping list | All |
| `/summary` | Generate shopping report | All |
| `/myitems` | View your added items | All |
| `/reset` | Reset entire list | Admin only |

## Database Schema 📊

The bot uses SQLite with the following tables:
- **users**: User registration and admin status
- **shopping_items**: Main shopping list items
- **item_notes**: Additional notes from multiple users

## Architecture 🏗️

- **bot.py**: Main bot logic and handlers
- **database.py**: Database operations and schema
- **config.py**: Configuration and categories
- **requirements.txt**: Python dependencies

## Workflow Example 📋

1. **Family Setup**: Dad and Mom are admins, kids are authorized users
2. **Weekly Planning**: Someone starts adding items from categories
3. **Collaboration**: Family members add items and notes throughout the week
4. **Shopping Day**: Generate summary report, shop, then reset list
5. **Repeat**: Clean slate for next week's planning

## Security Features 🔒

- **User Authorization**: Only registered users can access
- **Admin Controls**: Sensitive operations restricted to admins
- **Data Privacy**: Local SQLite database, no external data sharing
- **Input Validation**: Proper handling of user inputs and edge cases

## Customization 🎨

### Adding Categories
Edit the `CATEGORIES` dictionary in `config.py`:
```python
'new_category': {
    'name': 'Category Name', 
    'emoji': '🔥', 
    'items': ['Item 1', 'Item 2', 'Item 3']
}
```

### Modifying Messages
Update the `MESSAGES` dictionary in `config.py` to customize bot responses.

### Database Customization
Extend the database schema in `database.py` for additional features like:
- Item priorities
- Shopping history
- Store locations
- Price tracking

## Troubleshooting 🔧

### Common Issues

**Bot not responding**
- Check if BOT_TOKEN is correct
- Ensure bot is running and not crashed
- Check logs for error messages

**Users can't access**
- Verify user IDs in ADMIN_IDS
- Check if users are properly registered
- Admin needs to authorize new users

**Database errors**
- Check file permissions for database file
- Ensure SQLite is properly installed
- Delete database file to reset (loses data)

### Logs
The bot logs important events and errors. Check console output for debugging information.

## Contributing 🤝

Feel free to contribute by:
- Adding new categories and items
- Improving the user interface
- Adding new features (shopping history, price tracking, etc.)
- Fixing bugs and improving error handling
- Enhancing documentation

## License 📄

This project is open source. Feel free to modify and distribute according to your needs.

---

**Happy Shopping!** 🛒✨
