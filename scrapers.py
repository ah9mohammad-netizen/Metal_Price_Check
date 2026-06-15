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

# SOCKS5 proxies for IME (from hide.mn - updated periodically)
IME_PROXIES = [
    'socks5://206.123.156.232:7617',
    'socks5://206.123.156.223:4407',
    'socks5://206.123.156.229:4961',
    'socks5://206.123.156.224:5028',
    'socks5://206.123.156.230:8168',
    'socks5://206.123.156.220:4384',
    'socks5://206.123.156.223:6114',
    'socks5://206.123.156.213:6111',
    'socks5://206.123.156.206:4139',
    'socks5://206.123.156.224:6182',
    'socks5://206.123.156.227:4463',
    'socks5://46.249.124.244:1390',  # HTTP proxy as fallback
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
    data = get_livedata()
    result = ""
    
    if data.get('silver_usd'):
        result += f"⚪ **نقره (جهانی):** ${fmt(data['silver_usd'], 'USD/اونس')}"
    
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
# IME PRICES - via SOCKS5 Proxy
# ============================================
def fetch_ime_prices():
    """Fetch IME prices from ime.co.ir via SOCKS5 proxy"""
    
    # Try to fetch auction report page
    try:
        r = fetch_with_proxy('https://www.ime.co.ir/auction-total-report.html', timeout=15)
        
        if r and r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            text = soup.get_text()
            
            result = "📊 **بورس کالای ایران (IME):**\n\n"
            
            # Extract products from text
            products = {
                'کنسانتره': ('🔹 کنسانتره آهن', 'iron'),
                'گندله': ('🔹 گندله آهن', 'iron'),
                'اسفنجی': ('🔹 آهن اسفنجی', 'iron'),
                'شمش فولاد': ('🔸 شمش فولاد', 'steel'),
                'شمش': ('🔸 شمش فولاد', 'steel'),
                'میلگرد': ('🔸 میلگرد', 'steel'),
                'ورق گرم': ('🔸 ورق گرم', 'steel'),
                'ورق سرد': ('🔸 ورق سرد', 'steel'),
            }
            
            found = []
            for keyword, (display, cat) in products.items():
                if keyword in text:
                    # Find price near keyword
                    idx = text.find(keyword)
                    context = text[idx:idx+200]
                    
                    # Look for price pattern (rial amounts)
                    price_match = re.search(r'(\d[\d,]{5,})', context)
                    if price_match:
                        price_rial = price_match.group(1).replace(',', '')
                        try:
                            price_toman = int(price_rial) // 10
                            found.append((display, f"{price_toman:,} تومان/تن", cat))
                        except:
                            pass
            
            if found:
                iron = [f for f in found if f[2] == 'iron']
                steel = [f for f in found if f[2] == 'steel']
                
                if iron:
                    result += "**محصولات آهنی:**\n"
                    for name, price, _ in iron:
                        result += f"{name}: {price}\n"
                    result += "\n"
                
                if steel:
                    result += "**محصولات فولادی:**\n"
                    for name, price, _ in steel:
                        result += f"{name}: {price}\n"
                
                result += f"\n⏰ {get_tehran_time()}"
                return result
            else:
                result += "📭 در حال بروزرسانی...\n"
                result += "(پروکسی فعال است ولی داده‌ها در دسترس نیستند)"
                return result
    except Exception as e:
        logger.error(f"IME proxy error: {e}")
    
    # Fallback message
    return """📊 **بورس کالای ایران (IME):**

⚠️ سرورهای ایران در دسترس نیستند
(پروکسی‌های رایگان موقتاً کار نمی‌کنند)

🔄 لطفاً چند دقیقه دیگر دوباره تلاش کنید

🔗 https://www.ime.co.ir"""


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
