"""
Price fetching - VERIFIED WORKING SOURCES ONLY
===============================================
Data Sources:
- gold-api.com: Gold, Silver, Copper (FREE, no auth, no limits)
- Yahoo Finance: Zinc, Aluminum, Iron Ore, Copper (FREE, no auth)
- TGJU.org: Iran prices (may be geo-blocked from US servers)
- BrsApi.ir: IME prices (geo-blocked from US servers)
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import config
import re

logger = logging.getLogger(__name__)

# ============================================
# Cache System
# ============================================
price_cache = {}
CACHE_TIME = timedelta(seconds=config.CACHE_DURATION)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


def get_cached_or_fetch(key, fetch_function):
    """Cache mechanism to reduce API calls"""
    now = datetime.now()
    if key in price_cache:
        data, timestamp = price_cache[key]
        if now - timestamp < CACHE_TIME:
            return data

    logger.info(f"Fetching: {key}")
    try:
        data = fetch_function()
        price_cache[key] = (data, now)
        return data
    except Exception as e:
        logger.error(f"Error fetching {key}: {e}")
        if key in price_cache:
            data, _ = price_cache[key]
            return data + "\n_(cached)_"
        return "❌ خطا در دریافت اطلاعات"


def clean_number(text):
    """Extract numbers from text"""
    if not text:
        return None
    persian = '۰۱۲۳۴۵۶۷۸۹'
    english = '0123456789'
    trans = str.maketrans(persian, english)
    text = str(text).translate(trans).replace(',', '')
    numbers = re.findall(r'\d+\.?\d*', text)
    return numbers[0] if numbers else None


def fmt(price, currency='', decimals=2):
    """Format price with thousand separators"""
    try:
        num = float(price)
        if decimals == 0:
            return f"{num:,.0f} {currency}".strip()
        return f"{num:,.{decimals}f} {currency}".strip()
    except:
        return "N/A"


# ============================================
# HELPER: gold-api.com (VERIFIED WORKING)
# ============================================
def gold_api_price(symbol):
    """Fetch price from gold-api.com (free, no auth)"""
    r = requests.get(f'https://api.gold-api.com/price/{symbol}', timeout=10)
    if r.status_code == 200:
        return r.json().get('price', 0)
    return 0


# ============================================
# HELPER: Yahoo Finance (VERIFIED WORKING)
# ============================================
def yahoo_price(ticker):
    """Fetch price from Yahoo Finance (free, no auth)"""
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 200:
        data = r.json()
        result = data.get('chart', {}).get('result', [{}])[0]
        return result.get('meta', {}).get('regularMarketPrice', 0)
    return 0


# ============================================
# 1. USD TO TOMAN
# ============================================
def fetch_usd_price():
    """Fetch USD to Toman from TGJU"""
    try:
        r = requests.get('https://www.tgju.org/profile/price_dollar_rl',
                         headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if elem:
            price = clean_number(elem.text)
            if price and 40000 < float(price) < 150000:
                return f"💵 **دلار آمریکا:** {fmt(price, 'تومان', 0)}"
        return "💵 **دلار آمریکا:** در حال بروزرسانی..."
    except requests.exceptions.Timeout:
        return "💵 **دلار آمریکا:** ⏳ سرور در دسترس نیست"
    except Exception as e:
        logger.error(f"USD error: {e}")
        return "💵 **دلار آمریکا:** ❌ خطا"


def get_usd_price():
    return get_cached_or_fetch('usd', fetch_usd_price)


# ============================================
# 2. GOLD
# ============================================
def fetch_gold_price():
    """Gold: gold-api.com (USD) + TGJU (Toman)"""
    result = ""

    # International price
    try:
        price = gold_api_price('XAU')
        if price:
            result += f"🥇 **طلا (جهانی):** ${fmt(price, 'USD/اونس')}\n"
    except Exception as e:
        logger.error(f"Gold intl error: {e}")

    # Iran price
    try:
        r = requests.get('https://www.tgju.org/profile/geram18',
                         headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.content, 'html.parser')
        elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if elem:
            price = clean_number(elem.text)
            if price and float(price) > 1000000:
                result += f"🥇 **طلای ۱۸ عیار (ایران):** {fmt(price, 'تومان/گرم', 0)}"
    except:
        pass

    return result.strip() if result else "🥇 **طلا:** خطا در دریافت اطلاعات"


def get_gold_price():
    return get_cached_or_fetch('gold', fetch_gold_price)


# ============================================
# 3. SILVER
# ============================================
def fetch_silver_price():
    """Silver: gold-api.com (USD) + TGJU (Toman)"""
    result = ""

    # International price
    try:
        price = gold_api_price('XAG')
        if price:
            result += f"⚪ **نقره (جهانی):** ${fmt(price, 'USD/اونس')}\n"
    except Exception as e:
        logger.error(f"Silver intl error: {e}")

    # Iran price
    try:
        r = requests.get('https://www.tgju.org/profile/silver',
                         headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.content, 'html.parser')
        elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if elem:
            price = clean_number(elem.text)
            if price:
                result += f"⚪ **نقره (ایران):** {fmt(price, 'تومان/اونس', 0)}"
    except:
        pass

    return result.strip() if result else "⚪ **نقره:** خطا در دریافت اطلاعات"


def get_silver_price():
    return get_cached_or_fetch('silver', fetch_silver_price)


# ============================================
# 4. COPPER
# ============================================
def fetch_copper_price():
    """Copper: Yahoo Finance HG=F (per lb, convert to per ton)"""
    try:
        price = yahoo_price('HG=F')
        if price:
            price_per_ton = price * 2204.62  # lb -> ton
            return f"🔶 **مس:** ${fmt(price_per_ton, 'USD/ton')}"
        return "🔶 **مس:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"Copper error: {e}")
        return "🔶 **مس:** ❌ خطا"


def get_copper_price():
    return get_cached_or_fetch('copper', fetch_copper_price)


# ============================================
# 5. NICKEL
# ============================================
def fetch_nickel_price():
    """Nickel: Try multiple free sources"""
    # Source 1: Try fetching from a free financial data site
    try:
        r = requests.get(
            'https://www.google.com/finance/quote/NICKEL:CMX',
            headers=HEADERS, timeout=8
        )
        if r.status_code == 200:
            text = r.text
            # Look for price in response
            import re
            matches = re.findall(r'data-last-price="(\d+\.?\d*)"', text)
            if matches:
                price = float(matches[0])
                if price > 100:  # Likely per ton
                    return f"🔘 **نیکل:** ${fmt(price, 'USD/ton')}"
    except:
        pass

    # Source 2: NIY=F (CME Nickel in JPY) with proper conversion
    try:
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/NIY=F'
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            result = data.get('chart', {}).get('result', [{}])[0]
            meta = result.get('meta', {})
            price_jpy = meta.get('regularMarketPrice', 0)
            if price_jpy:
                # Get USD/JPY rate
                usdjpy = yahoo_price('JPY=X')
                if usdjpy and usdjpy > 0:
                    # NIY=F contract = 6 metric tons, price in JPY
                    # Total value = price * 6
                    # Per ton in JPY = price * 6
                    # Per ton in USD = price * 6 / usdjpy
                    price_usd_per_ton = (price_jpy * 6) / usdjpy
                    if 5000 < price_usd_per_ton < 50000:  # Sanity check
                        return f"🔘 **نیکل:** ${fmt(price_usd_per_ton, 'USD/ton')}"
    except Exception as e:
        logger.error(f"Nickel error: {e}")

    return "🔘 **نیکل:** در حال بروزرسانی..."


def get_nickel_price():
    return get_cached_or_fetch('nickel', fetch_nickel_price)


# ============================================
# 6. ZINC
# ============================================
def fetch_zinc_price():
    """Zinc: Yahoo Finance ZNC=F (per ton)"""
    try:
        price = yahoo_price('ZNC=F')
        if price:
            return f"⚫ **روی:** ${fmt(price, 'USD/ton')}"
        return "⚫ **روی:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"Zinc error: {e}")
        return "⚫ **روی:** ❌ خطا"


def get_zinc_price():
    return get_cached_or_fetch('zinc', fetch_zinc_price)


# ============================================
# 7. ALUMINUM
# ============================================
def fetch_aluminum_price():
    """Aluminum: Yahoo Finance ALI=F (per ton)"""
    try:
        price = yahoo_price('ALI=F')
        if price:
            return f"⚪ **آلومینیوم:** ${fmt(price, 'USD/ton')}"
        return "⚪ **آلومینیوم:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"Aluminum error: {e}")
        return "⚪ **آلومینیوم:** ❌ خطا"


def get_aluminum_price():
    return get_cached_or_fetch('aluminum', fetch_aluminum_price)


# ============================================
# 8. IRON ORE
# ============================================
def fetch_iron_ore_price():
    """Iron Ore: Yahoo Finance TIO=F (per ton)"""
    try:
        price = yahoo_price('TIO=F')
        if price:
            return f"🟤 **سنگ آهن (CFR چین):** ${fmt(price, 'USD/ton')}"
        return "🟤 **سنگ آهن:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"Iron ore error: {e}")
        return "🟤 **سنگ آهن:** ❌ خطا"


def get_iron_ore_price():
    return get_cached_or_fetch('iron', fetch_iron_ore_price)


# ============================================
# 9-10. IME PRICES (BrsApi)
# ============================================
def fetch_ime_prices():
    """Fetch IME prices from BrsApi"""
    if not config.IME_API_KEY:
        return "📊 **بورس کالای ایران:**\n⚠️ API key تنظیم نشده"

    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = (
            f"https://Api.BrsApi.ir/IME/Physical.php"
            f"?key={config.IME_API_KEY}"
            f"&date_start={today}&date_end={today}"
        )
        r = requests.get(url, headers={'Accept': 'application/json'}, timeout=20)

        if r.status_code == 200:
            data = r.json()
            return parse_ime_response(data)
        elif r.status_code == 401:
            return "📊 **بورس کالا:** ❌ خطای احراز هویت"
        else:
            return f"📊 **بورس کالا:** ❌ خطای {r.status_code}"

    except requests.exceptions.Timeout:
        return "📊 **بورس کالا:** ⏳ سرور در دسترس نیست\nممکن است محدودیت جغرافیایی باشد"
    except Exception as e:
        logger.error(f"IME error: {e}")
        return "📊 **بورس کالا:** ❌ خطا"


def parse_ime_response(data):
    """Parse IME API response"""
    result = "📊 **بورس کالای ایران (IME):**\n\n"

    items = []
    if isinstance(data, dict):
        items = (data.get('data') or data.get('items') or
                 data.get('commodities') or data.get('Physical') or [])
        if not items and 'name' in data:
            items = [data]
    elif isinstance(data, list):
        items = data

    if not items:
        return result + "📭 اطلاعاتی یافت نشد"

    keywords = {
        'کنسانتره': ('🔹 کنسانتره آهن', 'iron'),
        'گندله': ('🔹 گندله آهن', 'iron'),
        'اسفنجی': ('🔹 آهن اسفنجی', 'iron'),
        'شمش فولاد': ('🔸 شمش فولاد', 'steel'),
        'شمش': ('🔸 شمش فولاد', 'steel'),
        'میلگرد': ('🔸 میلگرد', 'steel'),
        'ورق گرم': ('🔸 ورق گرم', 'steel'),
        'ورق سرد': ('🔸 ورق سرد', 'steel'),
    }

    products = []
    for item in items:
        name = str(item.get('name', '') or item.get('title', '') or
                   item.get('commodity_name', '') or item.get('CommodityName', '') or
                   item.get('symbol', '') or item.get('Symbol', '') or '')
        price = (item.get('last_price') or item.get('price') or
                 item.get('close_price') or item.get('ClosePrice') or
                 item.get('final_price') or item.get('FinalPrice') or
                 item.get('LastPrice') or 0)

        for kw, (display, cat) in keywords.items():
            if kw in name:
                try:
                    pt = int(float(price)) / 10 if price else 0
                except:
                    pt = 0
                if pt > 0:
                    products.append({'name': display, 'price': fmt(pt, 'تومان/تن', 0), 'cat': cat})
                break

    if products:
        iron = [p for p in products if p['cat'] == 'iron']
        steel = [p for p in products if p['cat'] == 'steel']
        if iron:
            result += "**محصولات آهنی:**\n"
            for p in iron:
                result += f"{p['name']}: {p['price']}\n"
            result += "\n"
        if steel:
            result += "**محصولات فولادی:**\n"
            for p in steel:
                result += f"{p['name']}: {p['price']}\n"
    else:
        result += f"📭 محصولات مورد نظر یافت نشد ({len(items)} items)\n"

    result += f"\n⏰ {datetime.now().strftime('%H:%M')}"
    return result


def get_ime_prices():
    return get_cached_or_fetch('ime', fetch_ime_prices)


# ============================================
# ALL PRICES
# ============================================
def get_all_prices():
    """Get all prices in one message"""
    timestamp = datetime.now().strftime('%Y/%m/%d - %H:%M')
    return f"""
📊 **گزارش کامل قیمت‌ها**
🕐 {timestamp}

━━━━━━━━━━━━━━━━━━━━
**💱 نرخ ارز:**
{get_usd_price()}

━━━━━━━━━━━━━━━━━━━━
**✨ فلزات گرانبها:**
{get_gold_price()}

{get_silver_price()}

━━━━━━━━━━━━━━━━━━━━
**🏭 فلزات صنعتی (USD/ton):**
{get_copper_price()}
{get_nickel_price()}
{get_zinc_price()}
{get_aluminum_price()}
{get_iron_ore_price()}

━━━━━━━━━━━━━━━━━━━━
{get_ime_prices()}

━━━━━━━━━━━━━━━━━━━━
🔄 /all برای بروزرسانی
"""
