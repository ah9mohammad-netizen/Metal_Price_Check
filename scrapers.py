"""
Price fetching from various sources - FIXED VERSION
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
        return f"❌ خطا"

def clean_number(text):
    """Extract numbers from Persian/English text"""
    if not text:
        return None
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

# ============================================
# USD TO TOMAN
# ============================================

def fetch_usd_price():
    """Fetch USD to Toman from TGJU"""
    try:
        url = "https://www.tgju.org/profile/price_dollar_rl"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try different selectors
        price = None
        
        # Method 1: data-col attribute
        price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
        if price_elem:
            price = clean_number(price_elem.text)
        
        # Method 2: Look for high price value in page
        if not price:
            # Find all spans with numbers
            all_spans = soup.find_all('span')
            for span in all_spans:
                text = span.get_text()
                num = clean_number(text)
                if num and float(num) > 50000 and float(num) < 100000:  # USD price range
                    price = num
                    break
        
        if price:
            return f"💵 **دلار آمریکا:** {format_price(price, 'تومان', 0)}"
        
        return "💵 **دلار آمریکا:** در حال بروزرسانی..."
    except Exception as e:
        logger.error(f"USD error: {e}")
        raise

def get_usd_price():
    return get_cached_or_fetch('usd', fetch_usd_price)

# ============================================
# GOLD & SILVER - BOTH USD AND TOMAN
# ============================================

def fetch_gold_prices():
    """Fetch Gold price in both USD and Toman"""
    try:
        result = ""
        
        # 1. Get international gold price (USD per ounce)
        try:
            url = "https://www.gold.org/goldhub/data/gold-price"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for price element
            price_elem = soup.find('span', class_='price')
            if not price_elem:
                # Alternative: scrape from goldprice.org
                url = "https://goldprice.org/"
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                price_elem = soup.find('td', {'id': 'gm'})
            
            if price_elem:
                usd_price = clean_number(price_elem.text)
                if usd_price:
                    result += f"🥇 **طلا (جهانی):** ${format_price(usd_price, 'USD/اونس', 2)}\n"
        except:
            pass
        
        # 2. Get Iran gold price (Toman per gram)
        try:
            url = "https://www.tgju.org/profile/geram18"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
            if not price_elem:
                # Alternative selector
                price_elem = soup.find('span', class_='price')
            
            if price_elem:
                price = clean_number(price_elem.text)
                if price:
                    result += f"🥇 **طلای ۱۸ عیار (ایران):** {format_price(price, 'تومان/گرم', 0)}"
        except:
            pass
        
        return result if result else "🥇 **طلا:** N/A"
    except Exception as e:
        logger.error(f"Gold error: {e}")
        raise

def get_gold_price():
    return get_cached_or_fetch('gold', fetch_gold_prices)

def fetch_silver_prices():
    """Fetch Silver price in both USD and Toman"""
    try:
        result = ""
        
        # 1. Get international silver price (USD per ounce)
        try:
            url = "https://www.silverprice.org/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_elem = soup.find('td', {'id': 'sm'})
            if price_elem:
                usd_price = clean_number(price_elem.text)
                if usd_price:
                    result += f"⚪ **نقره (جهانی):** ${format_price(usd_price, 'USD/اونس', 2)}\n"
        except:
            pass
        
        # 2. Get Iran silver price (Toman per ounce)
        try:
            url = "https://www.tgju.org/profile/silver"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
            if price_elem:
                price = clean_number(price_elem.text)
                if price:
                    result += f"⚪ **نقره (ایران):** {format_price(price, 'تومان/اونس', 0)}"
        except:
            pass
        
        return result if result else "⚪ **نقره:** N/A"
    except Exception as e:
        logger.error(f"Silver error: {e}")
        raise

def get_silver_price():
    return get_cached_or_fetch('silver', fetch_silver_prices)

# ============================================
# INDUSTRIAL METALS - FIXED SCRAPING
# ============================================

def fetch_lme_metal(name_fa, symbol):
    """Fetch LME metal prices from multiple sources"""
    try:
        # Source 1: Try Investing.com
        url_map = {
            'copper': 'https://www.investing.com/commodities/copper',
            'nickel': 'https://www.investing.com/commodities/nickel',
            'zinc': 'https://www.investing.com/commodities/zinc',
            'aluminum': 'https://www.investing.com/commodities/aluminum',
            'iron': 'https://www.investing.com/commodities/iron-ore-62-cfr-futures'
        }
        
        if symbol not in url_map:
            return f"❌ {name_fa}: N/A"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url_map[symbol], headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple selectors
        price = None
        
        # Selector 1: data-test attribute
        price_elem = soup.find('span', {'data-test': 'instrument-price-last'})
        if price_elem:
            price = clean_number(price_elem.text)
        
        # Selector 2: class-based
        if not price:
            price_elem = soup.find('span', class_='text-2xl')
            if price_elem:
                price = clean_number(price_elem.text)
        
        # Selector 3: Look for large price number
        if not price:
            all_text = soup.get_text()
            numbers = re.findall(r'\b\d{1,2},?\d{3}\.\d{2}\b', all_text)
            if numbers:
                price = clean_number(numbers[0])
        
        emoji_map = {
            'copper': '🔶',
            'nickel': '🔘',
            'zinc': '⚫',
            'aluminum': '⚪',
            'iron': '🟤'
        }
        
        emoji = emoji_map.get(symbol, '•')
        
        if price:
            return f"{emoji} **{name_fa}:** ${format_price(price, 'USD/ton', 2)}"
        else:
            return f"{emoji} **{name_fa}:** در حال بروزرسانی..."
            
    except Exception as e:
        logger.error(f"{name_fa} error: {e}")
        return f"❌ **{name_fa}:** خطا"

def get_copper_price():
    return get_cached_or_fetch('copper', lambda: fetch_lme_metal('مس', 'copper'))

def get_nickel_price():
    return get_cached_or_fetch('nickel', lambda: fetch_lme_metal('نیکل', 'nickel'))

def get_zinc_price():
    return get_cached_or_fetch('zinc', lambda: fetch_lme_metal('روی', 'zinc'))

def get_aluminum_price():
    return get_cached_or_fetch('aluminum', lambda: fetch_lme_metal('آلومینیوم', 'aluminum'))

def get_iron_ore_price():
    return get_cached_or_fetch('iron', lambda: fetch_lme_metal('سنگ آهن (CFR چین)', 'iron'))

# ============================================
# IME PRICES - FIXED BrsApi Integration
# ============================================

def fetch_ime_prices():
    """Fetch Iran Mercantile Exchange prices from BrsApi"""
    try:
        # Try BrsApi endpoint
        url = f"{config.BRSAPI_BASE_URL}/commodity"
        headers = {
            'Authorization': f'Bearer {config.IME_API_KEY}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        
        logger.info(f"Calling BrsApi: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        logger.info(f"BrsApi status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"BrsApi response type: {type(data)}")
            logger.info(f"BrsApi response sample: {str(data)[:200]}")
            
            result = "📊 **بورس کالای ایران (IME):**\n\n"
            
            # Parse the response based on actual structure
            items = []
            if isinstance(data, dict):
                # Check common API response structures
                items = (data.get('data') or 
                        data.get('items') or 
                        data.get('commodities') or 
                        data.get('results') or 
                        [])
                
                # If data itself contains the items
                if not items and 'name' in data:
                    items = [data]
            elif isinstance(data, list):
                items = data
            
            products_found = []
            
            # Search keywords in Persian
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
            
            for item in items:
                # Get item name and price
                name = str(item.get('name', '') or 
                          item.get('title', '') or 
                          item.get('commodity_name', '') or 
                          item.get('symbol', ''))
                
                price = (item.get('last_price') or 
                        item.get('price') or 
                        item.get('close_price') or 
                        item.get('final_price') or 
                        0)
                
                # Check if name matches any keyword
                for keyword, (display_name, category) in keywords.items():
                    if keyword in name:
                        # Convert Rials to Tomans
                        price_toman = int(price) / 10 if price else 0
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
                result += "در حال بروزرسانی اطلاعات...\n"
                result += f"(API Response: {len(items)} items)\n"
            
            result += f"\n⏰ {datetime.now().strftime('%H:%M')}"
            return result
        
        elif response.status_code == 401:
            return "📊 **بورس کالا:** ❌ خطای احراز هویت API"
        elif response.status_code == 403:
            return "📊 **بورس کالا:** ❌ دسترسی غیرمجاز"
        else:
            return f"📊 **بورس کالا:** ❌ خطای سرور ({response.status_code})"
            
    except requests.exceptions.Timeout:
        return "📊 **بورس کالا:** ❌ timeout"
    except requests.exceptions.RequestException as e:
        logger.error(f"IME request error: {e}")
        return f"📊 **بورس کالا:** ❌ خطای ارتباط"
    except Exception as e:
        logger.error(f"IME error: {e}", exc_info=True)
        return f"📊 **بورس کالا:** ❌ خطا"

def get_ime_prices():
    return get_cached_or_fetch('ime', fetch_ime_prices)

# ============================================
# ALL PRICES
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
    """
    
    return message
