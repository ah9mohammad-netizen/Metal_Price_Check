"""
Telegram Metal & Currency Price Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import config
import scrapers

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with buttons"""
    keyboard = [
        [
            InlineKeyboardButton("💵 دلار", callback_data='usd'),
            InlineKeyboardButton("🥇 طلا", callback_data='gold')
        ],
        [
            InlineKeyboardButton("⚪ نقره", callback_data='silver'),
            InlineKeyboardButton("🔶 مس", callback_data='copper')
        ],
        [
            InlineKeyboardButton("🔘 نیکل", callback_data='nickel'),
            InlineKeyboardButton("⚫ روی", callback_data='zinc')
        ],
        [
            InlineKeyboardButton("⚪ آلومینیوم", callback_data='aluminum'),
            InlineKeyboardButton("🟤 سنگ آهن", callback_data='iron')
        ],
        [
            InlineKeyboardButton("📊 بورس کالا ایران", callback_data='ime')
        ],
        [
            InlineKeyboardButton("📈 همه قیمت‌ها", callback_data='all')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = """
🤖 **ربات قیمت فلزات و ارز**

📊 **قیمت‌های لحظه‌ای:**

✅ دلار آمریکا (بازار آزاد ایران)
✅ طلا و نقره (بازار ایران - تومان)
✅ فلزات صنعتی جهانی (USD)
   • مس، نیکل، روی، آلومینیوم
✅ سنگ آهن CFR چین (USD)
✅ بورس کالای ایران (تومان)
   • کنسانتره، گندله، آهن اسفنجی
   • شمش فولاد، میلگرد، ورق

⏱ بروزرسانی هر ۵ دقیقه

🔽 انتخاب کنید:
    """
    
    user = update.effective_user
    logger.info(f"User {user.id} (@{user.username}) started")
    
    await update.message.reply_text(welcome, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    user = update.effective_user
    logger.info(f"User {user.id} requested: {choice}")
    
    loading = await query.message.reply_text("⏳ لطفا صبر کنید...")
    
    try:
        handlers = {
            'usd': scrapers.get_usd_price,
            'gold': scrapers.get_gold_price,
            'silver': scrapers.get_silver_price,
            'copper': scrapers.get_copper_price,
            'nickel': scrapers.get_nickel_price,
            'zinc': scrapers.get_zinc_price,
            'aluminum': scrapers.get_aluminum_price,
            'iron': scrapers.get_iron_ore_price,
            'ime': scrapers.get_ime_prices,
            'all': scrapers.get_all_prices
        }
        
        if choice in handlers:
            result = handlers[choice]()
        else:
            result = "❌ گزینه نامعتبر"
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        result += f"\n\n🕐 {timestamp}"
        
        await loading.edit_text(result)
        
    except Exception as e:
        logger.error(f"Error in button handler: {e}", exc_info=True)
        await loading.edit_text("❌ خطا در دریافت اطلاعات\nلطفا دوباره تلاش کنید")

async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all prices via /all command"""
    loading = await update.message.reply_text("⏳ در حال دریافت...")
    try:
        result = scrapers.get_all_prices()
        await loading.edit_text(result)
    except Exception as e:
        logger.error(f"All command error: {e}")
        await loading.edit_text("❌ خطا")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help message"""
    help_text = """
📖 **راهنمای ربات**

**دستورات:**
/start - منوی اصلی
/all - نمایش همه قیمت‌ها
/help - راهنما

**منابع:**
• ارز و طلا: TGJU.org
• فلزات جهانی: LME/Investing.com
• بورس کالا: BrsApi.ir

💡 فلزات جهانی به دلار
💡 محصولات ایران به تومان

⏱ کش: ۵ دقیقه
    """
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

def main():
    """Start the bot"""
    logger.info("🚀 Starting bot...")
    
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot started successfully!")
    logger.info("Press Ctrl+C to stop")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
