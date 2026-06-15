"""
Configuration management - Railway compatible
⚠️  SECURITY: Never hardcode API keys! Use environment variables only.
"""
import os
import sys

# ============================================
# Bot Configuration
# Railway provides these as environment variables
# Set them in Railway dashboard → Variables tab
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

# API Endpoints (free, no auth required)
GOLD_API_BASE = "https://api.gold-api.com"
TGJU_BASE = "https://www.tgju.org"

# Logging configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

print("=" * 50)
print("🔧 CONFIGURATION LOADED")
print("=" * 50)
print(f"BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
print(f"IME_API_KEY: {'✅ Set' if IME_API_KEY else '⚠️  Not set (IME prices disabled)'}")
print(f"Cache duration: {CACHE_DURATION}s")
print("=" * 50)
