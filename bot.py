"""
Telegram Metal & Currency Price Bot
===================================
Features:
- USD to Toman exchange rate
- Gold & Silver prices (International + Iran)
- Industrial metals (Copper, Nickel, Zinc, Aluminum, Iron Ore)
- Iran Mercantile Exchange (IME) prices
- Inline keyboard for easy navigation
- Caching to reduce API calls
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime
import config
import scrapers

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)


def get_main_keyboard():
    """Create the main inline keyboard"""
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
            InlineKeyboardButton("🔩 سرب", callback_data='lead')
        ],
        [
            InlineKeyboardButton("🪙 قلع", callback_data='tin'),
            InlineKeyboardButton("🟤 سنگ آهن", callback_data='iron')
        ],
        [
            InlineKeyboardButton("📊 بورس کالا ایران", callback_data='ime')
        ],
        [
            InlineKeyboardButton("📈 همه قیمت‌ها", callback_data='all')
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data='refresh')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_welcome_message():
    """Get the welcome message text"""
    return """
🤖 **ربات قیمت فلزات و ارز**

📊 **قیمت‌های لحظه‌ای:**

✅ دلار آمریکا (بازار آزاد ایران)
✅ طلا و نقره (بین‌المللی + ایران)
✅ فلزات صنعتی جهانی (USD/ton)
   • مس، نیکل، روی، آلومینیوم
   • سرب، قلع
✅ سنگ آهن CFR چین

📊 **بورس کالای ایران (IME):**
   • کنسانتره سنگ آهن (گهر زمین)
   • گندله سنگ آهن (گهر زمین)
   • شمش بلوم (فولاد خوزستان)
   • ورق گرم (فولاد مبارکه)
   • میلگرد ۱۸ (ذوب آهن اصفهان)

⏱ بروزرسانی: هر ۵ دقیقه (فلزات جهانی)
⏱ بورس کالا: هر روز ساعت ۱۳:۰۰ (تهران)

🔽 انتخاب کنید:
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with buttons"""
    user = update.effective_user
    logger.info(f"👤 User {user.id} (@{user.username}) started the bot")

    welcome = get_welcome_message()
    reply_markup = get_main_keyboard()

    await update.message.reply_text(
        welcome,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    choice = query.data
    user = update.effective_user
    logger.info(f"👤 User {user.id} requested: {choice}")

    # Show loading message
    loading = await query.message.reply_text("⏳ لطفا صبر کنید...")

    try:
        # Map choices to handler functions
        handlers = {
            'usd': scrapers.get_usd_price,
            'gold': scrapers.get_gold_price,
            'silver': scrapers.get_silver_price,
            'copper': scrapers.get_copper_price,
            'nickel': scrapers.get_nickel_price,
            'zinc': scrapers.get_zinc_price,
            'aluminum': scrapers.get_aluminum_price,
            'lead': scrapers.get_lead_price,
            'tin': scrapers.get_tin_price,
            'iron': scrapers.get_iron_ore_price,
            'ime': scrapers.get_ime_prices,
            'all': scrapers.get_all_prices,
            'refresh': scrapers.get_all_prices,
        }

        if choice in handlers:
            result = handlers[choice]()
        else:
            result = "❌ گزینه نامعتبر"

        # Add Tehran timestamp
        from datetime import timedelta, timezone
        tehran_tz = timezone(timedelta(hours=3, minutes=30))
        timestamp = datetime.now(tehran_tz).strftime('%Y/%m/%d - %H:%M')
        result += f"\n\n🕐 {timestamp} (تهران)"

        # Add back button for single metal views
        if choice not in ['all', 'refresh']:
            back_keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data='menu')]]
            reply_markup = InlineKeyboardMarkup(back_keyboard)
        else:
            reply_markup = get_main_keyboard()

        # Edit the loading message with the result
        await loading.edit_text(
            result,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"❌ Error in button handler: {e}", exc_info=True)
        await loading.edit_text(
            "❌ خطا در دریافت اطلاعات\nلطفا دوباره تلاش کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='menu')]
            ])
        )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu button to return to main menu"""
    query = update.callback_query
    await query.answer()

    welcome = get_welcome_message()
    reply_markup = get_main_keyboard()

    await query.message.edit_text(
        welcome,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all prices via /all command"""
    loading = await update.message.reply_text("⏳ در حال دریافت تمام قیمت‌ها...")

    try:
        result = scrapers.get_all_prices()

        await loading.edit_text(
            result,
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"All command error: {e}")
        await loading.edit_text("❌ خطا در دریافت اطلاعات")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help message"""
    help_text = """
📖 **راهنمای ربات**

**دستورات:**
/start - منوی اصلی با دکمه‌ها
/all - نمایش همه قیمت‌ها
/help - این راهنما

**منابع داده:**
• طلا و نقره: gold-api.com (رایگان)
• مس: gold-api.com (رایگان)
• ارز و طلای ایران: TGJU.org
• بورس کالا: BrsApi.ir

**واحدها:**
💱 دلار و طلای ایران: تومان
🌍 فلزات جهانی: دلار آمریکا (USD)
📊 بورس کالا: تومان/تن

**نکات:**
⏱ کش: {cache_min} دقیقه
🔄 بروزرسانی خودکار
💡 قیمت‌ها ممکن است کمی تأخیر داشته باشند

**پشتیبانی:**
در صورت بروز مشکل، دوباره تلاش کنید.
""".format(cache_min=config.CACHE_DURATION // 60)

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status (admin only)"""
    user = update.effective_user
    
    # Build status message
    status = "📊 **وضعیت ربات:**\n\n"
    
    # Data sources
    status += "✅ **منابع داده:**\n"
    status += "  • livedata.ir (فلزات + دلار)\n"
    status += "  • gold-api.com (پشتیبانی)\n"
    status += "  • TradingEconomics (سنگ آهن)\n\n"
    
    # IME status
    status += "📊 **بورس کالا (IME):**\n"
    if scrapers.ime_cache.get('prices'):
        status += f"  • {len(scrapers.ime_cache['prices'])} محصول ذخیره شده\n"
    if scrapers.ime_manual_prices:
        status += f"  • {len(scrapers.ime_manual_prices)} قیمت دستی\n"
    if scrapers.ime_cache.get('last_update'):
        status += f"  • آخرین بروزرسانی: {scrapers.ime_cache['last_update'].strftime('%H:%M')}\n"
    
    # Proxy status
    status += f"\n🌐 **پروکسی:**\n"
    status += f"  • {len(scrapers.IME_PROXIES)} پروکسی فعال\n"
    if scrapers.ime_cache.get('proxy_update_date'):
        status += f"  • بروزرسانی: {scrapers.ime_cache['proxy_update_date'].strftime('%Y/%m/%d')}\n"
    
    await update.message.reply_text(status, parse_mode=ParseMode.MARKDOWN)


async def update_proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually update proxy list"""
    loading = await update.message.reply_text("🔄 در حال بروزرسانی لیست پروکسی...")
    
    new_proxies = scrapers.update_proxy_list()
    if new_proxies:
        scrapers.IME_PROXIES = new_proxies
        await loading.edit_text(f"✅ {len(new_proxies)} پروکسی جدید ذخیره شد")
    else:
        await loading.edit_text("❌ خطا در دریافت پروکسی‌ها")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    # Try to notify user about the error
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ خطایی رخ داد. لطفا دوباره تلاش کنید."
            )
        except:
            pass


def main():
    """Start the bot"""
    logger.info("🚀 Starting Metal Price Bot...")

    # Create application
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("updateproxies", update_proxies_command))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(?!menu$)'))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern='^menu$'))
    app.add_error_handler(error_handler)

    logger.info("✅ Bot started successfully!")
    logger.info("📱 Send /start to your bot on Telegram")
    logger.info("Press Ctrl+C to stop")

    # Start polling
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # Ignore updates received while bot was offline
    )


if __name__ == '__main__':
    main()
