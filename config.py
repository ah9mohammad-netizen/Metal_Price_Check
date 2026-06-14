"""
Configuration management - Railway compatible
"""
import os

# Bot Configuration - Railway provides these as environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7702491065:AAEVHCOBeJR7jBUSrvajHnTWvWcJgvk7gis')

# API Keys
IME_API_KEY = os.environ.get('IME_API_KEY', 'BfPww5C8aF9gyjqsTuTzLL4kXLyuTGFz')
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', 'BGZVC2NKH7YM5X2N')

# API Endpoints
BRSAPI_BASE_URL = "https://brsapi.ir/api/v1"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Cache settings (5 minutes)
CACHE_DURATION = int(os.environ.get('CACHE_DURATION', '300'))

# Logging
print("=" * 50)
print("🔧 CONFIGURATION")
print("=" * 50)
print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
print(f"BOT_TOKEN length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
print(f"IME_API_KEY: {IME_API_KEY[:10]}..." if IME_API_KEY else "Missing")
print(f"ALPHA_VANTAGE: {ALPHA_VANTAGE_API_KEY[:10]}..." if ALPHA_VANTAGE_API_KEY else "Missing")
print(f"Cache duration: {CACHE_DURATION}s")
print("=" * 50)

# Validate
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable is missing!")
    print("Please set it in Railway dashboard under Variables tab")
    raise ValueError("BOT_TOKEN is required!")

print("✅ Configuration loaded successfully")
