"""
Diagnostic Script - Run on Railway to check what data sources work
Usage: python diagnose.py
"""

import requests
import json
from bs4 import BeautifulSoup
import os
from datetime import datetime

print("=" * 70)
print("🔍 METAL PRICE BOT - DIAGNOSTIC TOOL")
print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# Get API key from environment
IME_API_KEY = os.environ.get('IME_API_KEY', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

print(f"\n📋 ENVIRONMENT VARIABLES:")
print(f"   BOT_TOKEN: {'✅ Set (' + BOT_TOKEN[:10] + '...)' if BOT_TOKEN else '❌ NOT SET'}")
print(f"   IME_API_KEY: {'✅ Set (' + IME_API_KEY[:10] + '...)' if IME_API_KEY else '❌ NOT SET'}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/html, */*',
}

results = {}

# ============================================
# Test 1: gold-api.com (Gold, Silver, Copper)
# ============================================
print("\n" + "=" * 70)
print("📌 TEST 1: gold-api.com (Gold, Silver, Copper)")
print("=" * 70)

for symbol, name in [('XAU', 'Gold'), ('XAG', 'Silver'), ('HG', 'Copper')]:
    try:
        url = f'https://api.gold-api.com/price/{symbol}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('price', 0)
            print(f"  ✅ {name}: ${price}")
            results[f'goldapi_{symbol}'] = {'status': 'OK', 'price': price}
        else:
            print(f"  ❌ {name}: HTTP {response.status_code}")
            results[f'goldapi_{symbol}'] = {'status': f'HTTP {response.status_code}'}
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:80]}")
        results[f'goldapi_{symbol}'] = {'status': 'ERROR', 'error': str(e)[:50]}

# ============================================
# Test 2: TGJU.org (USD/Toman, Iran Gold, Silver)
# ============================================
print("\n" + "=" * 70)
print("📌 TEST 2: TGJU.org (Iran Prices)")
print("=" * 70)

tgju_tests = [
    ('https://www.tgju.org/profile/price_dollar_rl', 'USD/Toman'),
    ('https://www.tgju.org/profile/geram18', 'Gold 18K Iran'),
    ('https://www.tgju.org/profile/silver', 'Silver Iran'),
]

for url, name in tgju_tests:
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            price_elem = soup.find('span', {'data-col': 'info.last_trade.PDrCotVal'})
            if price_elem:
                text = price_elem.text.strip()
                print(f"  ✅ {name}: {text}")
                results[f'tgju_{name}'] = {'status': 'OK', 'price': text}
            else:
                print(f"  ⚠️  {name}: Page loaded but price element not found")
                results[f'tgju_{name}'] = {'status': 'NO_ELEMENT'}
        else:
            print(f"  ❌ {name}: HTTP {response.status_code}")
            results[f'tgju_{name}'] = {'status': f'HTTP {response.status_code}'}
    except requests.exceptions.Timeout:
        print(f"  ⏰ {name}: TIMEOUT (15s) - May be geo-blocked")
        results[f'tgju_{name}'] = {'status': 'TIMEOUT'}
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:80]}")
        results[f'tgju_{name}'] = {'status': 'ERROR', 'error': str(e)[:50]}

# ============================================
# Test 3: BrsApi.ir (IME Prices)
# ============================================
print("\n" + "=" * 70)
print("📌 TEST 3: BrsApi.ir (IME Prices)")
print("=" * 70)

if IME_API_KEY:
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Test the correct endpoint format
    url = f"https://Api.BrsApi.ir/IME/Physical.php?key={IME_API_KEY}&date_start={today}&date_end={today}"
    print(f"  URL: {url[:80]}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  ✅ JSON Response received!")
                print(f"  Type: {type(data).__name__}")
                
                # Analyze structure
                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())[:10]}")
                    # Check for data array
                    for key in data.keys():
                        val = data[key]
                        if isinstance(val, list) and len(val) > 0:
                            print(f"  Found list '{key}' with {len(val)} items")
                            if isinstance(val[0], dict):
                                print(f"    First item keys: {list(val[0].keys())[:10]}")
                                # Show first item
                                print(f"    First item: {json.dumps(val[0], ensure_ascii=False)[:300]}")
                elif isinstance(data, list):
                    print(f"  List with {len(data)} items")
                    if data and isinstance(data[0], dict):
                        print(f"  First item keys: {list(data[0].keys())[:10]}")
                
                results['brsapi'] = {'status': 'OK', 'items': len(data) if isinstance(data, list) else 'dict'}
            except json.JSONDecodeError:
                print(f"  ⚠️  Response is not valid JSON")
                print(f"  Text: {response.text[:300]}")
                results['brsapi'] = {'status': 'NOT_JSON'}
        else:
            print(f"  ❌ Error: {response.text[:200]}")
            results['brsapi'] = {'status': f'HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ TIMEOUT (30s)")
        print(f"  The API may be unreachable from this location.")
        results['brsapi'] = {'status': 'TIMEOUT'}
    except requests.exceptions.SSLError as e:
        print(f"  ❌ SSL Error: {str(e)[:100]}")
        results['brsapi'] = {'status': 'SSL_ERROR'}
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")
        results['brsapi'] = {'status': 'ERROR', 'error': str(e)[:50]}
else:
    print("  ⚠️  IME_API_KEY not set - skipping test")
    results['brsapi'] = {'status': 'NO_KEY'}

# ============================================
# Summary
# ============================================
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

working = [k for k, v in results.items() if v.get('status') == 'OK']
not_working = [k for k, v in results.items() if v.get('status') != 'OK']

print(f"\n✅ Working ({len(working)}):")
for k in working:
    print(f"   - {k}")

print(f"\n❌ Not Working ({len(not_working)}):")
for k in not_working:
    status = results[k].get('status', 'Unknown')
    print(f"   - {k}: {status}")

print("\n" + "=" * 70)
print("💡 RECOMMENDATIONS:")
print("=" * 70)

if 'brsapi' in not_working:
    print("""
⚠️  BrsApi.ir is not reachable!
    
    Possible solutions:
    1. Check if your API key is valid
    2. The API may require Iran IP (use VPN if testing locally)
    3. Railway servers may be in a location that can access the API
    4. Contact BrsApi support if issue persists
    """)

if any('tgju' in k for k in not_working):
    print("""
⚠️  TGJU.org is not reachable!
    
    This is likely due to geo-blocking.
    Railway servers may have better access.
    """)

print("\n✨ Gold, Silver, Copper from gold-api.com should always work!")
print("=" * 70)
