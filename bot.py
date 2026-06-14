import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from data_fetcher import DataFetcher
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
fetcher = DataFetcher()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **ربات قیمت فلزات و ارز**\n\n"
        "دستور `/prices` را ارسال کنید تا تمام قیمت‌ها نمایش داده شود.\n"
        "قیمت فلزات پایه به **دلار** و محصولات بورسی به **تومان** نمایش داده می‌شود.",
        parse_mode="Markdown"
    )

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 در حال دریافت قیمت‌ها از منابع معتبر...")
    
    data = await fetcher.get_all_prices()
    
    ime = data["ime"]
    text = f"""🕒 **به‌روزرسانی:** {data['timestamp']}

💵 **دلار آزاد:** {data['dollar']} تومان

🏅 **فلزات گران‌بها (USD)**
• طلای جهانی: {data['gold']}
• نقره جهانی: {data['silver']}

⚙️ **فلزات پایه (USD)**
• مس: {data['copper']}
• نیکل: {data['nickel']}
• روی: {data['zinc']}
• آلومینیوم: {data['aluminum']}
• سنگ آهن (چین): {data['iron_ore']}

🏭 **بورس کالا ایران (تومان)**
• کنسانتره آهن: {ime.get('کنسانتره', '—')}
• گندله: {ime.get('گندله', '—')}
• آهن اسفنجی: {ime.get('آهن اسفنجی', '—')}
• شمش فولاد: {ime.get('شمش فولاد', '—')}
• میلگرد: {ime.get('میلگرد', '—')}
• ورق گرم: {ime.get('ورق گرم', '—')}
• ورق سرد: {ime.get('ورق سرد', '—')}

📉 فقط ۱۰ درخواست در روز مجاز است.
"""
    await msg.edit_text(text, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("prices", prices))
    
    print("✅ Bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
