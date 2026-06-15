"""
Configuration management - Railway compatible
⚠️  SECURITY: Never hardcode API keys! Use environment variables only.
"""
import os
import sys

# ============================================
# Bot Configuration
# ============================================

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable is missing!")
    print("Set it in Railway dashboard → Variables tab")
    sys.exit(1)

# BrsApi for Iran Mercantile Exchange (IME) prices
IME_API_KEY = os.environ.get('IME_API_KEY', '')

# Cache settings (5 minutes = 300 seconds)
CACHE_DURATION = int(os.environ.get('CACHE_DURATION', '300'))

# ============================================
# IME Product Symbols to Track
# ============================================
IME_PRODUCTS = {
    'GHZ-OAIOC-00': {
        'name_fa': 'کنسانتره سنگ آهن',
        'name_en': 'Iron Ore Concentrate',
        'supplier': 'معدنی و صنعتی گهر زمین',
        'category': 'iron'
    },
    'GHZ-PELL-00': {
        'name_fa': 'گندله سنگ آهن',
        'name_en': 'Iron Ore Pellet',
        'supplier': 'معدنی و صنعتی گهر زمین',
        'category': 'iron'
    },
    'KSC-BSG194X-00': {
        'name_fa': 'شمش بلوم',
        'name_en': 'Steel Bloom/Billet',
        'supplier': 'فولاد خوزستان',
        'category': 'steel'
    },
    'MSC-HS40009-00': {
        'name_fa': 'ورق گرم',
        'name_en': 'Hot Rolled Sheet',
        'supplier': 'فولاد مبارکه اصفهان',
        'category': 'steel'
    },
    'ESC-MRNNENA3B-00': {
        'name_fa': 'میلگرد 18',
        'name_en': 'Rebar 18',
        'supplier': 'ذوب آهن اصفهان',
        'category': 'steel'
    },
}

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

print("=" * 50)
print("🔧 CONFIGURATION LOADED")
print("=" * 50)
print(f"BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
print(f"IME_API_KEY: {'✅ Set' if IME_API_KEY else '⚠️  Not set'}")
print(f"IME Products: {len(IME_PRODUCTS)} symbols configured")
print(f"Cache duration: {CACHE_DURATION}s")
print("=" * 50)
