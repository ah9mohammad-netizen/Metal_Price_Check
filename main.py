import logging
import os
import httpx
import time
from datetime import datetime
from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Load from Railway Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
IME_API_KEY = os.getenv("IME_API_KEY")
ALPHA_KEY = os.getenv("ALPHA_VANTAGE_KEY")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN is missing! Set it in Railway Variables.")
    raise ValueError("BOT_TOKEN environment variable is required")

PORT = int(os.getenv("PORT", 8080))

cache = {}
cache_time = {}
CACHE_DURATION = 1800  # 30 minutes

# ===================== DATA FUNCTIONS =====================
async def get_dollar_toman():
    if "dollar" in cache_time and time.time() - cache_time["dollar"] < CACHE_DURATION:
        return cache["dollar"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://www.tgju.org/json?type=dollar")
            price = r.json().get("price")
            result = f"{int(price):,}" if price else "N/A"
            cache["dollar"] = result
            cache_time["dollar"] = time.time()
            return result
    except Exception as e:
        logger.error(f"Dollar error: {e}")
        return "خطا"

async def get_alpha_price(symbol: str):
    key = f"alpha_{symbol}"
    if key in cache_time and time.time() - cache_time[key] < CACHE_DURATION:
        return cache[key]
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_KEY}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            price = r.json().get("Global Quote", {}).get("05. price")
            if price:
                result = f"${float(price):,.2f}"
                cache[key] = result
                cache_time[key] = time.time()
                return result
    except Exception as e:
        logger.error(f"Alpha Vantage error {symbol}: {e}")
    return "N/A"

async def get_ime_data():
    if "ime" in cache_time and time.time() - cache_time["ime"] < CACHE_DURATION:
        return cache["ime"]
    try:
        headers = {"X-API-KEY": IME_API_KEY}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://brsapi.ir/api/v1/ime", headers=headers)
            data = resp.json()
            logger.info(f"IME API Response: {data}")   # ← We need this in logs
            result = {
                "کنسانتره": data.get("concentrate") or data.get("کنسانتره") or "—",
                "گندله": data.get("pellet") or data.get("گندله") or "—",
                "آهن اسفنجی": data.get("sponge_iron") or data.get("آهن_اسفنجی") or "—",
                "شمش فولاد": data.get("billet") or data.get("شمش") or "—",
                "میلگرد": data.get("rebar") or data.get("میلگرد") or "—",
                "ورق گرم": data.get("hot_rolled") or data.get("ورق_گرم") or "—",
                "ورق سرد": data.get("cold_rolled") or data.get("ورق_سرد") or "—",
            }
            cache["ime"] = result
            cache_time["ime"] = time.time()
            return result
    except Exception as e:
        logger.error(f"IME Error: {e}")
        return {"error": "خطا در API IME"}

async def get_all_prices():
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dollar": await get_dollar_toman(),
        "gold": await get_alpha_price("XAUUSD"),
        "silver": await get_alpha_price("XAGUSD"),
        "copper": await get_alpha_price("HG=F"),
        "nickel": await get_alpha_price("NICKEL"),
        "zinc": await get_alpha_price("ZINC"),
        "aluminum": await get_alpha_price("ALUMINUM"),
        "iron_ore": await get_alpha_price("IRONORE"),
        "ime": await get_ime_data()
    }

# ===================== BOT HANDLERS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 ربات قیمت فلزات فعال است.\n\n/send `/prices`")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 در حال دریافت قیمت‌ها...")
    data = await get_all_prices()
    ime = data["ime"]
    
    text = f"""🕒 **به‌روزرسانی:** {data['timestamp']}

💵 **دلار:** {data['dollar']} تومان

🏅 **فلزات (USD)**
• طلا: {data['gold']}
• نقره: {data['silver']}
• مس: {data['copper']}
• نیکل: {data['nickel']}
• روی: {data['zinc']}
• آلومینیوم: {data['aluminum']}
• سنگ آهن: {data['iron_ore']}

🏭 **بورس کالا (تومان)**
• کنسانتره: {ime.get('کنسانتره','—')}
• گندله: {ime.get('گندله','—')}
• آهن اسفنجی: {ime.get('آهن اسفنجی','—')}
• شمش فولاد: {ime.get('شمش فولاد','—')}
• میلگرد: {ime.get('میلگرد','—')}
• ورق گرم: {ime.get('ورق گرم','—')}
• ورق سرد: {ime.get('ورق سرد','—')}
"""
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

# ===================== FASTAPI =====================
@app.get("/health")
async def health():
    return {"status": "Bot is running"}

@app.on_event("startup")
async def on_startup():
    logger.info("Bot is starting...")
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("prices", prices))
        webhook_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
        if webhook_url:
            await application.bot.set_webhook(f"https://{webhook_url}/webhook")
            logger.info(f"Webhook set to https://{webhook_url}/webhook")
    except Exception as e:
        logger.error(f"Startup error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
