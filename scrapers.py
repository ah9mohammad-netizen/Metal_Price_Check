"""
Price fetching from reliable FREE sources
==========================================
Data Sources:
- gold-api.com: Gold, Silver, Copper (FREE, no auth, no limits)
- TGJU.org: USD/Toman, Iran Gold, Iran Silver (web scraping)
- BrsApi.ir: Iran Mercantile Exchange prices (API key required)
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import config
import re
import json

logger = logging.getLogger(__name__)

# ============================================
# Cache System
# ============================================
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
        # Return cached data if available (even if expired)
        if key in price_cache:
            data, _ = price_cache[key]
            return data + "\n⚠️ (cached)"
        return f"❌ خطا در دریافت اطلاعات"


def clean_number(text):
    """Extract numbers from Persian/English text"""
    if not text:
        return None
    # Convert Persian numbers to English
    persian = '۰۱۲۳۴۵۶۷۸۹'
    english = '0123456789'
    trans = str.maketrans(persian, english)
    text = str(text).translate(trans)
    # Remove commas and keep only numbers and decimal point
    text = text.replace(',', '')
    numbers = re.findall(r'\d+\.?\d*', text)
    return numbers[0] if numbers else None


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


def get_headers():
    """Common headers for web requests"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }


# ============================================
# 1. USD TO TOMAN (from TGJU with timeout handling)
# ============================================
def fetch_usd_price():
    """Fetch USD to Toman from TGJU"""
    try:
        url = "https://www.tgju.org/profile/price_dollar_rl"
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Method 1: data-col attribute (most reliable)
        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
            if price and 40000 < float(price) < 150000:  # Valid USD/Toman range
                return f"💵 **دلار آمریکا:** {format_price(price, 'تومان', 0)}"

        # Method 2: Look for price in specific class
        price_elem = soup.find('span', class_='price')
        if price_elem:
            price = clean_number(price_elem.text)
            if price and 40000 < float(price) < 150000:
                return f"💵 **دلار آمریکا:** {format_price(price, 'تومان', 0)}"

        # Method 3: Search all spans for valid price range
        all_spans = soup.find_all('span')
        for span in all_spans:
            text = span.get_text()
            num = clean_number(text)
            if num and 40000 < float(num) < 150000:
                return f"💵 **دلار آمریکا:** {format_price(num, 'تومان', 0)}"

        return "💵 **دلار آمریکا:** در حال بروزرسانی..."
    except requests.exceptions.Timeout:
        logger.warning("TGJU timeout - may be geo-blocked")
        return "💵 **دلار آمریکا:** ⏳ سرور در دسترس نیست (تلاش مجدد...)"
    except Exception as e:
        logger.error(f"USD error: {e}")
        raise


def get_usd_price():
    return get_cached_or_fetch('usd', fetch_usd_price)


# ============================================
# 2. GOLD - International (gold-api.com) + Iran (TGJU)
# ============================================
def fetch_gold_price():
    """Fetch Gold price - International USD + Iran Toman"""
    result = ""

    # Part 1: International price from gold-api.com (FREE, reliable)
    try:
        url = "https://api.gold-api.com/price/XAU"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('price', 0)
            if price:
                result += f"🥇 **طلا (جهانی):** ${format_price(price, 'USD/اونس', 2)}\n"
    except Exception as e:
        logger.error(f"Gold international error: {e}")

    # Part 2: Iran gold price from TGJU (Toman per gram)
    try:
        url = "https://www.tgju.org/profile/geram18"
        response = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
            if price and float(price) > 1000000:  # Valid gold price range
                result += f"🥇 **طلای ۱۸ عیار (ایران):** {format_price(price, 'تومان/گرم', 0)}"
    except requests.exceptions.Timeout:
        logger.warning("TGJU timeout for gold - may be geo-blocked")
    except Exception as e:
        logger.error(f"Gold Iran error: {e}")

    return result.strip() if result else "🥇 **طلا:** خطا در دریافت اطلاعات"


def get_gold_price():
    return get_cached_or_fetch('gold', fetch_gold_price)


# ============================================
# 3. SILVER - International (gold-api.com) + Iran (TGJU)
# ============================================
def fetch_silver_price():
    """Fetch Silver price - International USD + Iran Toman"""
    result = ""

    # Part 1: International price from gold-api.com
    try:
        url = "https://api.gold-api.com/price/XAG"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('price', 0)
            if price:
                result += f"⚪ **نقره (جهانی):** ${format_price(price, 'USD/اونس', 2)}\n"
    except Exception as e:
        logger.error(f"Silver international error: {e}")

    # Part 2: Iran silver price from TGJU
    try:
        url = "https://www.tgju.org/profile/silver"
        response = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
            if price:
                result += f"⚪ **نقره (ایران):** {format_price(price, 'تومان/اونس', 0)}"
    except requests.exceptions.Timeout:
        logger.warning("TGJU timeout for silver - may be geo-blocked")
    except Exception as e:
        logger.error(f"Silver Iran error: {e}")

    return result.strip() if result else "⚪ **نقره:** خطا در دریافت اطلاعات"


def get_silver_price():
    return get_cached_or_fetch('silver', fetch_silver_price)


# ============================================
# 4. COPPER - from gold-api.com (FREE)
# ============================================
def fetch_copper_price():
    """Fetch Copper price from gold-api.com"""
    try:
        url = "https://api.gold-api.com/price/HG"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('price', 0)
            if price:
                # gold-api returns price per pound, convert to per ton
                price_per_ton = price * 2204.62
                return f"🔶 **مس:** ${format_price(price_per_ton, 'USD/ton', 2)}"
        return "🔶 **مس:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"Copper error: {e}")
        raise


def get_copper_price():
    return get_cached_or_fetch('copper', fetch_copper_price)


# ============================================
# 5-8. LME METALS - Using gold-api.com + fallbacks
# ============================================

# Metal emoji mapping
METAL_EMOJIS = {
    'nickel': '🔘',
    'zinc': '⚫',
    'aluminum': '⚪',
    'iron': '🟤'
}


def fetch_single_lme_metal(metal_name_fa, metal_key):
    """Fetch a single LME metal price with multiple fallback sources"""
    
    # Source 1: Try gold-api.com (only works for copper)
    if metal_key == 'copper':
        try:
            url = "https://api.gold-api.com/price/HG"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data.get('price', 0)
                if price:
                    price_per_ton = price * 2204.62
                    return f"🔶 **{metal_name_fa}:** ${format_price(price_per_ton, 'USD/ton', 2)}"
        except:
            pass

    # Source 2: Try alternative free sources for LME metals
    alternative_urls = {
        'nickel': [
            'https://www.barchart.com/futures/quotes/NID00/overview',
            'https://tradingeconomics.com/commodity/nickel',
        ],
        'zinc': [
            'https://www.barchart.com/futures/quotes/ZSD00/overview',
            'https://tradingeconomics.com/commodity/zinc',
        ],
        'aluminum': [
            'https://www.barchart.com/futures/quotes/AHD00/overview',
            'https://tradingeconomics.com/commodity/aluminum',
        ],
        'iron': [
            'https://www.barchart.com/futures/quotes/TIO00/overview',
            'https://tradingeconomics.com/commodity/iron-ore',
        ]
    }

    emoji = METAL_EMOJIS.get(metal_key, '•')

    # Try each alternative source
    if metal_key in alternative_urls:
        for url in alternative_urls[metal_key]:
            try:
                response = requests.get(url, headers=get_headers(), timeout=10)
                if response.status_code == 200:
                    text = response.text
                    # Look for price patterns
                    patterns = [
                        r'(\d{1,2},?\d{3}\.\d{2})',  # e.g., 19,274.25
                        r'(\d{2,3}\.\d{2})',          # e.g., 107.10
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, text)
                        if matches:
                            price = clean_number(matches[0])
                            if price and float(price) > 0:
                                return f"{emoji} **{metal_name_fa}:** ${format_price(price, 'USD/ton', 2)}"
            except:
                continue

    # If all sources fail, return placeholder
    return f"{emoji} **{metal_name_fa}:** در حال بروزرسانی..."


def get_nickel_price():
    return get_cached_or_fetch('nickel', lambda: fetch_single_lme_metal('نیکل', 'nickel'))


def get_zinc_price():
    return get_cached_or_fetch('zinc', lambda: fetch_single_lme_metal('روی', 'zinc'))


def get_aluminum_price():
    return get_cached_or_fetch('aluminum', lambda: fetch_single_lme_metal('آلومینیوم', 'aluminum'))


def get_iron_ore_price():
    return get_cached_or_fetch('iron', lambda: fetch_single_lme_metal('سنگ آهن (CFR چین)', 'iron'))


# ============================================
# 9-10. IRAN MERCANTILE EXCHANGE (IME) - BrsApi
# ============================================
def fetch_ime_prices():
    """Fetch Iran Mercantile Exchange prices from BrsApi"""
    if not config.IME_API_KEY:
        return "📊 **بورس کالای ایران:**\n⚠️ API key تنظیم نشده\nبرای فعال‌سازی، کلید API را در تنظیمات Railway وارد کنید."

    try:
        # Use the correct endpoint format provided by user
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://Api.BrsApi.ir/IME/Physical.php?key={config.IME_API_KEY}&date_start={today}&date_end={today}"
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }

        logger.info(f"Calling BrsApi for IME prices...")
        response = requests.get(url, headers=headers, timeout=20)
        logger.info(f"BrsApi status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            return parse_ime_response(data)

        elif response.status_code == 401:
            return "📊 **بورس کالا:** ❌ خطای احراز هویت API\nلطفاً کلید API را بررسی کنید"
        elif response.status_code == 403:
            return "📊 **بورس کالا:** ❌ دسترسی غیرمجاز"
        else:
            return f"📊 **بورس کالا:** ❌ خطای سرور ({response.status_code})"

    except requests.exceptions.Timeout:
        logger.warning("BrsApi timeout - API may be unreachable")
        return "📊 **بورس کالا:** ⏳ زمان انتظار تمام شد\nسرور ممکن است موقتاً در دسترس نباشد"
    except requests.exceptions.RequestException as e:
        logger.error(f"IME request error: {e}")
        return "📊 **بورس کالا:** ❌ خطای ارتباط با سرور"
    except Exception as e:
        logger.error(f"IME error: {e}", exc_info=True)
        return "📊 **بورس کالا:** ❌ خطا"


def parse_ime_response(data):
    """Parse IME API response and extract relevant products"""
    result = "📊 **بورس کالای ایران (IME):**\n\n"

    # Log the response structure for debugging
    logger.info(f"IME Response type: {type(data)}")
    logger.info(f"IME Response preview: {str(data)[:500]}")

    # Extract items from response
    items = []
    if isinstance(data, dict):
        items = (data.get('data') or
                 data.get('items') or
                 data.get('commodities') or
                 data.get('results') or
                 data.get('Physical') or [])
        if not items and 'name' in data:
            items = [data]
    elif isinstance(data, list):
        items = data

    if not items:
        return result + "📭 اطلاعاتی یافت نشد\n(API ممکن است نیاز به بررسی داشته باشد)"

    # Keywords to search for
    keywords = {
        # Iron products (9)
        'کنسانتره': ('🔹 کنسانتره آهن', 'iron'),
        'گندله': ('🔹 گندله آهن', 'iron'),
        'اسفنجی': ('🔹 آهن اسفنجی', 'iron'),
        # Steel products (10)
        'شمش فولاد': ('🔸 شمش فولاد', 'steel'),
        'شمش': ('🔸 شمش فولاد', 'steel'),
        'میلگرد': ('🔸 میلگرد', 'steel'),
        'ورق گرم': ('🔸 ورق گرم', 'steel'),
        'ورق سرد': ('🔸 ورق سرد', 'steel'),
    }

    products_found = []

    for item in items:
        # Get item name - try multiple possible field names
        name = str(item.get('name', '') or
                   item.get('title', '') or
                   item.get('commodity_name', '') or
                   item.get('CommodityName', '') or
                   item.get('symbol', '') or
                   item.get('Symbol', '') or '')

        # Get price - try multiple possible field names
        price = (item.get('last_price') or
                 item.get('price') or
                 item.get('close_price') or
                 item.get('final_price') or
                 item.get('ClosePrice') or
                 item.get('FinalPrice') or
                 item.get('LastPrice') or 0)

        # Check if name matches any keyword
        for keyword, (display_name, category) in keywords.items():
            if keyword in name:
                # Convert Rials to Tomans (divide by 10)
                try:
                    price_toman = int(float(price)) / 10 if price else 0
                except:
                    price_toman = 0
                    
                if price_toman > 0:
                    products_found.append({
                        'name': display_name,
                        'price': format_price(price_toman, 'تومان/تن', 0),
                        'category': category
                    })
                break

    if products_found:
        # Group by category
        iron_products = [p for p in products_found if p['category'] == 'iron']
        steel_products = [p for p in products_found if p['category'] == 'steel']

        if iron_products:
            result += "**محصولات آهنی:**\n"
            for p in iron_products:
                result += f"{p['name']}: {p['price']}\n"
            result += "\n"

        if steel_products:
            result += "**محصولات فولادی:**\n"
            for p in steel_products:
                result += f"{p['name']}: {p['price']}\n"
    else:
        result += "📭 محصولات مورد نظر یافت نشد\n"
        result += f"(تعداد کل اقلام: {len(items)})\n"

    result += f"\n⏰ {datetime.now().strftime('%H:%M')}"
    return result


def get_ime_prices():
    return get_cached_or_fetch('ime', fetch_ime_prices)


# ============================================
# ALL PRICES - Complete Report
# ============================================
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
**✨ فلزات گرانبها:**
{get_gold_price()}

{get_silver_price()}

━━━━━━━━━━━━━━━━━━━━
**🏭 فلزات صنعتی جهانی (LME):**
{get_copper_price()}
{get_nickel_price()}
{get_zinc_price()}
{get_aluminum_price()}
{get_iron_ore_price()}

━━━━━━━━━━━━━━━━━━━━
{get_ime_prices()}

━━━━━━━━━━━━━━━━━━━━
🔄 دستور /all برای بروزرسانی
💡 کش: {config.CACHE_DURATION // 60} دقیقه
"""

    return message
