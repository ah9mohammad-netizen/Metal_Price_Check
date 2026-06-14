"""
Price fetching from various sources
"""
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import config
import re

logger = logging.getLogger(__name__)

# Cache
price_cache = {}
CACHE_TIME = timedelta(seconds=config.CACHE_DURATION)

def get_cached_or_fetch(key, fetch_function):
    """Cache mechanism to reduce API calls"""
    now = datetime.now()
    if key in price_cache:
        data, timestamp = price_cache[key]
        if now - timestamp < CACHE_TIME:
            logger.info(f"✅ Cache hit: {key}")
            return data
    
    logger.info(f"🔄 Fetching fresh data: {key}")
    try:
        data = fetch_function()
        price_cache[key] = (data, now)
        return data
    except Exception as e:
        logger.error(f"❌ Error fetching {key}: {e}")
        if key in price_cache:
            data, _ = price_cache[key]
            return data + " (cached)"
        return f"❌ خطا در دریافت {key}"

def clean_number(text):
    """Extract numbers from Persian/English text"""
    if not text:
        return None
    persian = '۰۱۲۳۴۵۶۷۸۹'
    english = '0123456789'
    trans = str.maketrans(persian, english)
    text = str(text).translate(trans)
    numbers = re.sub(r'[^\d.]', '', text)
    return numbers if numbers else None

def format_price(price, currency='', decimals=2):
    """Format price with thousand separators"""
    try:
        if isinstance(price, str):
            price = price.replace(',', '')
        num = float(price)
        if decimals == 0:
            formatted = f"{num:,.0f}"
        else:
            formatted = f"{num:,.{decimals}f}"
        return f"{formatted} {currency}".strip()
    except:
        return "N/A"

def fetch_usd_price():
    """Fetch USD to Toman from TGJU"""
    try:
        url = "https://www.tgju.org/profile/price_dollar_rl"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html5lib')
        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        
        if price_elem:
            price = clean_number(price_elem.text)
            if price:
                return f"💵 **دلار آمریکا:** {format_price(price, 'تومان', 0)}"
        
        return "💵 **دلار آمریکا:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"USD error: {e}")
        raise

def get_usd_price():
    return get_cached_or_fetch('usd', fetch_usd_price)

def fetch_gold_price():
    """Fetch Gold price"""
    try:
        url = "https://www.tgju.org/profile/geram18"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html5lib')
        
        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
            if price:
                return f"🥇 **طلای ۱۸ عیار:** {format_price(price, 'تومان/گرم', 0)}"
        return "🥇 **طلا:** N/A"
    except Exception as e:
        logger.error(f"Gold error: {e}")
        raise

def get_gold_price():
    return get_cached_or_fetch('gold', fetch_gold_price)

def fetch_silver_price():
    """Fetch Silver price"""
    try:
        url = "https://www.tgju.org/profile/silver"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html5lib')
        
        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
            if price:
                return f"⚪ **نقره:** {format_price(price, 'تومان/اونس', 0)}"
        return "⚪ **نقره:** N/A"
    except Exception as e:
        logger.error(f"Silver error: {e}")
        raise

def get_silver_price():
    return get_cached_or_fetch('silver', fetch_silver_price)

def fetch_metal_price(name_fa, name_en, slug, emoji):
    """Fetch metal price from Investing.com"""
    try:
        url = f"https://www.investing.com/commodities/{slug}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html5lib')
        
        price_elem = soup.find('span', {'data-test': 'instrument-price-last'})
        if not price_elem:
            price_elem = soup.find('span', class_='text-2xl')
        
        if price_elem:
            price = clean_number(price_elem.text)
            if price:
                return f"{emoji} **{name_fa}:** ${format_price(price, 'USD/ton', 2)}"
        
        return f"{emoji} **{name_fa}:** N/A"
    except Exception as e:
        logger.error(f"{name_en} error: {e}")
        raise

def get_copper_price():
    return get_cached_or_fetch('copper', lambda: fetch_metal_price('مس', 'Copper', 'copper', '🔶'))

def get_nickel_price():
    return get_cached_or_fetch('nickel', lambda: fetch_metal_price('نیکل', 'Nickel', 'nickel', '🔘'))

def get_zinc_price():
    return get_cached_or_fetch('zinc', lambda: fetch_metal_price('روی', 'Zinc', 'zinc', '⚫'))

def get_aluminum_price():
    return get_cached_or_fetch('aluminum', lambda: fetch_metal_price('آلومینیوم', 'Aluminum', 'aluminum', '⚪'))

def get_iron_ore_price():
    return get_cached_or_fetch('iron', lambda: fetch_metal_price('سنگ آهن', 'Iron Ore', 'iron-ore-62-cfr-futures', '🟤'))

def fetch_ime_prices():
    """Fetch Iran Mercantile Exchange prices"""
    try:
        url = f"{config.BRSAPI_BASE_URL}/market/commodity"
        headers = {
            'Authorization': f'Bearer {config.IME_API_KEY}',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            result = "📊 **بورس کالای ایران:**\n\n"
            result += "در حال بروزرسانی...\n"
            result += f"⏰ {datetime.now().strftime('%H:%M')}"
            return result
        else:
            return f"❌ خطای API: {response.status_code}"
            
    except Exception as e:
        logger.error(f"IME fetch error: {e}")
        raise

def get_ime_prices():
    return get_cached_or_fetch('ime', fetch_ime_prices)

def get_all_prices():
    """Get all prices in one message"""
    timestamp = datetime.now().strftime('%Y/%m/%d - %H:%M')
    
    message = f"""
📊 **گزارش کامل قیمت‌ها**
🕐 {timestamp}

━━━━━━━━━━━━━━━━━━━━
**💱 نرخ ارز:**
{get_usd_price()}

━━━━━━━━━━━━━━━━━━━━
**✨ فلزات گرانبها (ایران):**
{get_gold_price()}
{get_silver_price()}

━━━━━━━━━━━━━━━━━━━━
**🏭 فلزات صنعتی جهانی (USD):**
{get_copper_price()}
{get_nickel_price()}
{get_zinc_price()}
{get_aluminum_price()}
{get_iron_ore_price()}

━━━━━━━━━━━━━━━━━━━━
{get_ime_prices()}

━━━━━━━━━━━━━━━━━━━━
🔄 دستور /all برای بروزرسانی
    """
    
    return message
