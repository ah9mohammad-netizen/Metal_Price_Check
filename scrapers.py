"""
Price fetching - ALL from livedata.ir + IME via SOCKS5 proxy
=============================================================
Primary Source: livedata.ir (Iranian site with all metals + USD/Toman)
IME Source: ime.co.ir via SOCKS5 proxies (unreliable but free)
Fallback: gold-api.com, TradingEconomics
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta, timezone
import config
import re
import random

logger = logging.getLogger(__name__)

# Cache
price_cache = {}
CACHE_TIME = timedelta(seconds=config.CACHE_DURATION)
IME_CACHE_TIME = timedelta(seconds=1800)  # 30 min cache for IME (longer due to proxy issues)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Tehran timezone (UTC+3:30)
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# SOCKS5 proxies for IME (auto-updated from hide.mn)
IME_PROXIES_FILE = 'ime_proxies.json'
IME_PROXIES = []

def load_proxies():
    """Load proxies from file"""
    try:
        import json
        with open(IME_PROXIES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_proxies(proxies):
    """Save proxies to file"""
    try:
        import json
        with open(IME_PROXIES_FILE, 'w') as f:
            json.dump(proxies, f)
    except Exception as e:
        logger.error(f"Failed to save proxies: {e}")

def fetch_proxies_from_hidemn():
    """Fetch fresh SOCKS5 proxies from hide.mn"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get('https://hide.mn/en/proxy-list/countries/iran/', 
                        headers=headers, timeout=15)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Find proxy table (first table on the page)
            proxies = []
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        ip = cells[0].get_text(strip=True)
                        port = cells[1].get_text(strip=True)
                        proxy_type = cells[4].get_text(strip=True)
                        
                        # Only get SOCKS5 and HTTP proxies
                        if 'SOCKS5' in proxy_type.upper():
                            proxies.append(f'socks5://{ip}:{port}')
                        elif 'HTTP' in proxy_type.upper():
                            proxies.append(f'http://{ip}:{port}')
                
                if proxies:  # Found proxies in first table
                    break
            
            if proxies:
                logger.info(f"Fetched {len(proxies)} proxies from hide.mn")
                return proxies
    except Exception as e:
        logger.error(f"Failed to fetch proxies: {e}")
    
    return None

def update_proxy_list():
    """Update proxy list from hide.mn (called daily)"""
    proxies = fetch_proxies_from_hidemn()
    if proxies:
        save_proxies(proxies)
        return proxies
    return None

# Load proxies on startup
IME_PROXIES = load_proxies()
if not IME_PROXIES:
    # Default proxies if none saved
    IME_PROXIES = [
        'socks5://206.123.156.232:7617',
        'socks5://206.123.156.223:4407',
        'socks5://206.123.156.229:4961',
        'socks5://206.123.156.227:4463',
        'socks5://206.123.156.224:5028',
    ]


def get_tehran_time():
    """Get current Tehran date and time"""
    now = datetime.now(TEHRAN_TZ)
    return now.strftime('%Y/%m/%d - %H:%M') + " (تهران)"


def fetch_with_proxy(url, timeout=12):
    """Try to fetch URL through SOCKS5 proxies"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    # Shuffle proxies to distribute load
    proxies = list(IME_PROXIES)
    random.shuffle(proxies)
    
    for proxy_url in proxies[:4]:  # Try max 4 proxies
        try:
            proxy_dict = {'http': proxy_url, 'https': proxy_url}
            r = requests.get(url, proxies=proxy_dict, headers=headers, 
                           timeout=timeout, verify=False)
            if r.status_code == 200:
                return r
        except:
            continue
    
    return None


def get_cached_or_fetch(key, fetch_function):
    """Cache mechanism"""
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


def fmt(price, currency='', decimals=2):
    """Format price"""
    try:
        num = float(price)
        if decimals == 0:
            return f"{num:,.0f} {currency}".strip()
        return f"{num:,.{decimals}f} {currency}".strip()
    except:
        return "N/A"


# ============================================
# LIVEDATA.IR - Primary source for ALL data
# ============================================
def fetch_livedata():
    """Fetch all prices from livedata.ir"""
    r = requests.get('https://livedata.ir/', headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return {}
    
    soup = BeautifulSoup(r.content, 'html.parser')
    text = soup.get_text()
    
    data = {}
    
    # Gold (USD/oz)
    match = re.search(r'انس طلا\s*([\d,]+)', text)
    if match:
        data['gold_usd'] = match.group(1).replace(',', '')
    
    # Silver (USD/oz)
    match = re.search(r'نقره\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['silver_usd'] = match.group(1).replace(',', '')
    
    # Copper (USD/lb)
    match = re.search(r'مس هایگرید\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['copper_usd'] = match.group(1).replace(',', '')
    
    # Aluminum (USD/ton)
    match = re.search(r'آلومینیوم\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['aluminum_usd'] = match.group(1).replace(',', '')
    
    # Nickel (USD/ton)
    match = re.search(r'نیکل\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['nickel_usd'] = match.group(1).replace(',', '')
    
    # Zinc (USD/ton)
    match = re.search(r'روی\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['zinc_usd'] = match.group(1).replace(',', '')
    
    # Lead (USD/ton)
    match = re.search(r'سرب\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['lead_usd'] = match.group(1).replace(',', '')
    
    # Tin (USD/ton)
    match = re.search(r'قلع\s*\n\s*([\d,]+\.?\d*)', text)
    if match:
        data['tin_usd'] = match.group(1).replace(',', '')
    
    # USD/Toman (exchange rate)
    match = re.search(r'دلار\s*-\s*صرافی\s*\n\s*([\d,]+)', text)
    if match:
        data['usd_toman'] = match.group(1).replace(',', '')
    
    # Gold 18K Iran (Toman/gram) - text: "هر گرم 1816,724,000104.1"
    # Price format: 16,724,000 (with commas every 3 digits)
    match = re.search(r'هر گرم 18(\d{1,3}(?:,\d{3})+)', text)
    if match:
        data['gold_18k_toman'] = match.group(1).replace(',', '')
    
    # Gold 24K Iran (Toman/gram)
    match = re.search(r'هر گرم 24\s*([\d,]+)', text)
    if match:
        data['gold_24k_toman'] = match.group(1).replace(',', '')
    
    return data


def get_livedata():
    return get_cached_or_fetch('livedata', fetch_livedata)


# ============================================
# 1. USD TO TOMAN
# ============================================
def fetch_usd_price():
    data = get_livedata()
    if data.get('usd_toman'):
        return f"💵 **دلار آمریکا:** {fmt(data['usd_toman'], 'تومان', 0)}"
    
    # Fallback: Try TradingEconomics
    try:
        r = requests.get('https://tradingeconomics.com/commodity/iron-ore', headers=HEADERS, timeout=10)
        # ... fallback logic
    except:
        pass
    
    return "💵 **دلار آمریکا:** در حال بروزرسانی..."


def get_usd_price():
    return get_cached_or_fetch('usd', fetch_usd_price)


# ============================================
# 2. GOLD
# ============================================
def fetch_gold_price():
    data = get_livedata()
    result = ""
    
    if data.get('gold_usd'):
        result += f"🥇 **طلا (جهانی):** ${fmt(data['gold_usd'], 'USD/اونس')}\n"
    
    if data.get('gold_18k_toman'):
        result += f"🥇 **طلای ۱۸ عیار (ایران):** {fmt(data['gold_18k_toman'], 'تومان/گرم', 0)}"
    
    if not result:
        # Fallback to gold-api.com
        try:
            r = requests.get('https://api.gold-api.com/price/XAU', timeout=10)
            if r.status_code == 200:
                price = r.json().get('price', 0)
                result = f"🥇 **طلا (جهانی):** ${fmt(price, 'USD/اونس')}"
        except:
            pass
    
    return result.strip() if result else "🥇 **طلا:** خطا در دریافت اطلاعات"


def get_gold_price():
    return get_cached_or_fetch('gold', fetch_gold_price)


# ============================================
# 3. SILVER
# ============================================
def fetch_silver_price():
    """Silver: International USD + calculated Iran Toman/gram"""
    data = get_livedata()
    result = ""
    
    silver_usd = data.get('silver_usd', '0')
    usd_toman = data.get('usd_toman', '0')
    
    if silver_usd:
        result += f"⚪ **نقره (جهانی):** ${fmt(silver_usd, 'USD/اونس')}\n"
        
        # Calculate Iran price: (USD/oz × Toman/USD) ÷ 31.1035 grams/oz
        try:
            silver_usd_float = float(silver_usd)
            usd_toman_float = float(usd_toman)
            toman_per_gram = (silver_usd_float * usd_toman_float) / 31.1035
            result += f"⚪ **نقره (ایران):** {fmt(toman_per_gram, 'تومان/گرم', 0)}"
        except:
            pass
    
    if not result:
        try:
            r = requests.get('https://api.gold-api.com/price/XAG', timeout=10)
            if r.status_code == 200:
                price = r.json().get('price', 0)
                result = f"⚪ **نقره (جهانی):** ${fmt(price, 'USD/اونس')}"
        except:
            pass
    
    return result if result else "⚪ **نقره:** خطا در دریافت اطلاعات"


def get_silver_price():
    return get_cached_or_fetch('silver', fetch_silver_price)


# ============================================
# 4. COPPER
# ============================================
def fetch_copper_price():
    data = get_livedata()
    if data.get('copper_usd'):
        price_per_ton = float(data['copper_usd']) * 2204.62  # lb -> ton
        return f"🔶 **مس:** ${fmt(price_per_ton, 'USD/ton')}"
    return "🔶 **مس:** در حال بروزرسانی..."


def get_copper_price():
    return get_cached_or_fetch('copper', fetch_copper_price)


# ============================================
# 5. NICKEL
# ============================================
def fetch_nickel_price():
    data = get_livedata()
    if data.get('nickel_usd'):
        return f"🔘 **نیکل:** ${fmt(data['nickel_usd'], 'USD/ton')}"
    return "🔘 **نیکل:** در حال بروزرسانی..."


def get_nickel_price():
    return get_cached_or_fetch('nickel', fetch_nickel_price)


# ============================================
# 6. ZINC
# ============================================
def fetch_zinc_price():
    data = get_livedata()
    if data.get('zinc_usd'):
        return f"⚫ **روی:** ${fmt(data['zinc_usd'], 'USD/ton')}"
    return "⚫ **روی:** در حال بروزرسانی..."


def get_zinc_price():
    return get_cached_or_fetch('zinc', fetch_zinc_price)


# ============================================
# 7. ALUMINUM
# ============================================
def fetch_aluminum_price():
    data = get_livedata()
    if data.get('aluminum_usd'):
        return f"⚪ **آلومینیوم:** ${fmt(data['aluminum_usd'], 'USD/ton')}"
    return "⚪ **آلومینیوم:** در حال بروزرسانی..."


def get_aluminum_price():
    return get_cached_or_fetch('aluminum', fetch_aluminum_price)


# ============================================
# 8. LEAD
# ============================================
def fetch_lead_price():
    data = get_livedata()
    if data.get('lead_usd'):
        return f"🔩 **سرب:** ${fmt(data['lead_usd'], 'USD/ton')}"
    return "🔩 **سرب:** در حال بروزرسانی..."


def get_lead_price():
    return get_cached_or_fetch('lead', fetch_lead_price)


# ============================================
# 9. TIN
# ============================================
def fetch_tin_price():
    data = get_livedata()
    if data.get('tin_usd'):
        return f"🪙 **قلع:** ${fmt(data['tin_usd'], 'USD/ton')}"
    return "🪙 **قلع:** در حال بروزرسانی..."


def get_tin_price():
    return get_cached_or_fetch('tin', fetch_tin_price)


# ============================================
# 10. IRON ORE - from TradingEconomics
# ============================================
def fetch_iron_ore_price():
    try:
        r = requests.get('https://tradingeconomics.com/commodity/iron-ore', headers=HEADERS, timeout=10)
        if r.status_code == 200:
            match = re.search(r'Iron Ore.*?(\d{2,3}\.\d{1,2})', r.text)
            if match:
                return f"🟤 **سنگ آهن (CFR چین):** ${match.group(1)} USD/ton"
    except:
        pass
    return "🟤 **سنگ آهن:** در حال بروزرسانی..."


def get_iron_ore_price():
    return get_cached_or_fetch('iron', fetch_iron_ore_price)


# ============================================
# IME PRICES - Daily Proxy Fetch at 1:00 PM Tehran
# ============================================

# IME cache (persists until next successful fetch)
ime_cache = {'prices': {}, 'last_update': None, 'last_attempt': None, 'last_success_date': None, 'proxy_update_date': None}

# Manual IME prices - persisted to file
IME_MANUAL_FILE = 'ime_manual_prices.json'

def load_manual_prices():
    """Load manual prices from file"""
    try:
        import json
        with open(IME_MANUAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_manual_prices(prices):
    """Save manual prices to file"""
    try:
        import json
        with open(IME_MANUAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save manual prices: {e}")

# Load manual prices on startup
ime_manual_prices = load_manual_prices()

# Price field name in IME JSON
PRICE_FIELD = 'قیمت پایانی میانگین   موزون'
SYMBOL_FIELD = 'نماد'
NAME_FIELD = 'نام کالا'
UNIT_FIELD = 'واحد'


def fetch_ime_via_proxy():
    """Try to fetch IME data via SOCKS5 proxies and export as JSON"""
    import time
    
    global IME_PROXIES
    
    # Check if we need to update proxy list (once per day)
    now = datetime.now(TEHRAN_TZ)
    if (not ime_cache.get('proxy_update_date') or 
        (now - ime_cache['proxy_update_date']).total_seconds() > 86400):  # 24 hours
        logger.info("Updating proxy list from hide.mn...")
        new_proxies = update_proxy_list()
        if new_proxies:
            IME_PROXIES = new_proxies
        ime_cache['proxy_update_date'] = now
    
    proxy_list = list(IME_PROXIES)
    random.shuffle(proxy_list)
    
    # Use today's date in Persian format (Shamsi)
    # For now, we'll let the form use its default date
    # The server will show latest data
    
    for proxy_url in proxy_list[:6]:
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            headers_proxy = {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            # Step 1: Get the page
            r = requests.get('https://www.ime.co.ir/arze.html', 
                           proxies=proxies, headers=headers_proxy, timeout=12, verify=False)
            
            if r.status_code != 200 or len(r.content) < 5000:
                continue
            
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Extract form fields
            viewstate = soup.find('input', {'id': '__VIEWSTATE'})
            if not viewstate:
                continue
            
            viewstate_gen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
            event_validation = soup.find('input', {'id': '__EVENTVALIDATION'})
            
            # Get the default dates from the form (server sets latest dates)
            from_date_input = soup.find('input', {'id': 'ctl05_ReportsHeaderControl_FromDate'})
            to_date_input = soup.find('input', {'id': 'ctl05_ReportsHeaderControl_ToDate'})
            
            from_date = from_date_input.get('value', '') if from_date_input else ''
            to_date = to_date_input.get('value', '') if to_date_input else ''
            
            # Step 2: Submit form to load data
            time.sleep(1)
            
            form_data = {
                '__VIEWSTATE': viewstate.get('value', ''),
                '__VIEWSTATEGENERATOR': viewstate_gen.get('value', '') if viewstate_gen else '',
                '__EVENTVALIDATION': event_validation.get('value', '') if event_validation else '',
                'ctl05$ReportsHeaderControl$FromDate': from_date,
                'ctl05$ReportsHeaderControl$ToDate': to_date,
                'ctl05$ReportsHeaderControl$FillGrid': 'نمایش',
                'mainCat': '',
                'Cats': '',
                'SubCat': '',
                'Producers': '',
                'PageSizeDD': '200',
            }
            
            r2 = requests.post('https://www.ime.co.ir/arze.html',
                             data=form_data, proxies=proxies, headers=headers_proxy,
                             timeout=15, verify=False)
            
            if r2.status_code == 200 and len(r2.content) > 10000:
                # Parse the HTML table and extract data
                return parse_ime_html_to_json(r2.text)
                
        except:
            continue
    
    return None


def parse_ime_html_to_json(html_text):
    """Parse IME HTML table and extract product data"""
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Find the main data table
    tables = soup.find_all('table')
    products = []
    
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 5:
            continue
        
        # Get headers from first row
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Check if this is the data table (has symbol column)
        if 'نماد' not in headers and 'نام کالا' not in headers:
            continue
        
        # Parse data rows
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 6:
                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_data[headers[i]] = cell.get_text(strip=True)
                
                if row_data.get(SYMBOL_FIELD):
                    products.append(row_data)
    
    return products if products else None


def parse_ime_data(items):
    """Parse IME items and extract prices for tracked symbols"""
    if not items:
        return {}
    
    prices = {}
    
    for item in items:
        symbol = item.get(SYMBOL_FIELD, '')
        
        if symbol in config.IME_PRODUCTS:
            price_str = item.get(PRICE_FIELD, '0')
            
            try:
                # Price is in Rial, convert to Toman
                price_rial = int(float(str(price_str).replace(',', '')))
                price_toman = price_rial // 10
                
                if price_toman > 0:
                    product = config.IME_PRODUCTS[symbol]
                    prices[symbol] = {
                        'price_toman': price_toman,
                        'price_rial': price_rial,
                        'name_fa': product['name_fa'],
                        'name_en': product['name_en'],
                        'supplier': product['supplier'],
                        'category': product['category'],
                        'unit': item.get(UNIT_FIELD, 'تن'),
                        'date': item.get('تاریخ معامله', ''),
                    }
            except:
                pass
    
    return prices


def update_ime_cache():
    """Update IME cache by fetching data via proxy"""
    logger.info("Attempting IME data fetch via proxy...")
    
    items = fetch_ime_via_proxy()
    if items:
        prices = parse_ime_data(items)
        if prices:
            ime_cache['prices'] = prices
            ime_cache['last_update'] = datetime.now(TEHRAN_TZ)
            logger.info(f"IME cache updated: {len(prices)} products found")
            return True
    
    logger.warning("IME fetch failed, using cached data")
    return False


def should_update_ime():
    """Check if we should attempt IME update (hourly)"""
    now = datetime.now(TEHRAN_TZ)
    
    # If we have no last attempt, try now
    if not ime_cache['last_attempt']:
        return True
    
    # Try every hour (3600 seconds)
    time_since_last = (now - ime_cache['last_attempt']).total_seconds()
    if time_since_last < 3600:  # Less than 1 hour
        return False
    
    # Only try during market hours (8 AM to 5 PM Tehran time)
    # This saves proxy resources when market is closed
    if 8 <= now.hour <= 17:
        return True
    
    # Outside market hours, try only once every 4 hours
    if time_since_last < 14400:  # Less than 4 hours
        return False
    
    return True


def fetch_ime_prices():
    """Fetch IME prices - try proxy if it's update time, otherwise use cache"""
    now = datetime.now(TEHRAN_TZ)
    
    # Check if we should try to update
    if should_update_ime():
        ime_cache['last_attempt'] = now
        success = update_ime_cache()
        if success:
            # Clear manual prices when fresh data arrives
            ime_manual_prices.clear()
            save_manual_prices({})
    
    # Use fresh cache if available
    prices = ime_cache.get('prices', {})
    
    # Fallback to manual prices if no fresh data
    if not prices and ime_manual_prices:
        prices = ime_manual_prices
    
    # Build result
    if prices:
        result = "📊 **بورس کالای ایران (IME):**\n\n"
        
        iron_products = []
        steel_products = []
        
        for symbol, data in prices.items():
            price_str = f"{data['price_toman']:,} تومان/تن"
            line = f"🔹 **{data['name_fa']}:** {price_str}"
            
            if data.get('category') == 'iron':
                iron_products.append(line)
            else:
                steel_products.append(line)
        
        if iron_products:
            result += "**محصولات آهنی:**\n"
            result += "\n".join(iron_products) + "\n\n"
        
        if steel_products:
            result += "**محصولات فولادی:**\n"
            result += "\n".join(steel_products) + "\n"
        
        # Show data date (from IME transaction date)
        data_date = None
        for d in prices.values():
            if d.get('date'):
                data_date = d['date']
                break
        
        if data_date:
            result += f"\n📅 تاریخ معامله: {data_date}"
        
        if ime_cache.get('last_update'):
            update_time = ime_cache['last_update'].strftime('%H:%M')
            result += f"\n🕐 بروزرسانی: {update_time} (تهران)"
        
        return result
    
    # No cached data
    return """📊 **بورس کالای ایران (IME):**

⏳ داده‌ای موجود نیست
🔄 در حال تلاش برای دریافت...

💡 ربات هر ساعت تلاش می‌کند
   قیمت‌ها پس از اولین موفقیت ذخیره می‌شوند"""


def set_manual_ime_price(symbol, price_toman):
    """Admin function: Manually set IME price (invisible to users)
    
    Args:
        symbol: Product symbol (e.g., 'GHZ-OAIOC-00')
        price_toman: Price in Toman per ton
    
    Returns:
        bool: True if successful
    """
    if symbol in config.IME_PRODUCTS:
        product = config.IME_PRODUCTS[symbol]
        ime_manual_prices[symbol] = {
            'price_toman': price_toman,
            'price_rial': price_toman * 10,
            'name_fa': product['name_fa'],
            'name_en': product['name_en'],
            'supplier': product['supplier'],
            'category': product['category'],
            'unit': 'تن',
            'date': datetime.now(TEHRAN_TZ).strftime('%Y/%m/%d'),
            'source': 'manual'
        }
        # Save to file for persistence
        save_manual_prices(ime_manual_prices)
        # Also update cache so it shows immediately
        ime_cache['prices'] = dict(ime_manual_prices)
        ime_cache['last_update'] = datetime.now(TEHRAN_TZ)
        return True
    return False


def set_multiple_manual_ime_prices(prices_dict):
    """Admin function: Set multiple IME prices at once
    
    Args:
        prices_dict: {symbol: price_toman, ...}
    
    Returns:
        int: Number of prices set successfully
    """
    success_count = 0
    for symbol, price_toman in prices_dict.items():
        if set_manual_ime_price(symbol, price_toman):
            success_count += 1
    return success_count


def clear_manual_prices():
    """Admin function: Clear all manual prices"""
    global ime_manual_prices
    ime_manual_prices = {}
    save_manual_prices({})
    logger.info("Manual IME prices cleared")


def get_ime_prices():
    return get_cached_or_fetch('ime', fetch_ime_prices)


# ============================================
# ALL PRICES
# ============================================
def get_all_prices():
    timestamp = get_tehran_time()
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
{get_lead_price()}
{get_tin_price()}
{get_iron_ore_price()}

━━━━━━━━━━━━━━━━━━━━
{get_ime_prices()}

━━━━━━━━━━━━━━━━━━━━
🔄 /all برای بروزرسانی
"""
