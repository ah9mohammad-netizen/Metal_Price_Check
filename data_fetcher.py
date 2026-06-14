import httpx
import time
from datetime import datetime

class DataFetcher:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.CACHE_DURATION = 1800  # 30 minutes

    def _is_cache_valid(self, key):
        if key not in self.cache_time:
            return False
        return time.time() - self.cache_time[key] < self.CACHE_DURATION

    async def get_dollar_toman(self):
        """Get USD to Toman from tgju.org"""
        if self._is_cache_valid("dollar"):
            return self.cache["dollar"]
        
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get("https://www.tgju.org/profile/price_dollar_rl")
                # Simple parsing - tgju uses JSON in script tags. This is a stable endpoint.
                data = await client.get("https://www.tgju.org/json?type=dollar")
                price = data.json().get("price", "N/A")
                self.cache["dollar"] = f"{int(price):,}" if price != "N/A" else "N/A"
                self.cache_time["dollar"] = time.time()
                return self.cache["dollar"]
        except:
            return "خطا در دریافت"

    async def get_alpha_price(self, symbol: str, name: str):
        """Get price from Alpha Vantage"""
        key = f"alpha_{symbol}"
        if self._is_cache_valid(key):
            return self.cache[key]
        
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=BGZVC2NKH7YM5X2N"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
                price = data.get("Global Quote", {}).get("05. price", "N/A")
                if price != "N/A":
                    price = f"${float(price):,.2f}"
                self.cache[key] = price
                self.cache_time[key] = time.time()
                return price
        except:
            return "N/A"

    async def get_ime_data(self):
        """IME Products from BrsApi.ir - in Tomans"""
        if self._is_cache_valid("ime"):
            return self.cache["ime"]
        
        headers = {"X-API-KEY": "BfPww5C8aF9gyjqsTuTzLL4kXLyuTGFz"}
        try:
            async with httpx.AsyncClient() as client:
                # You may need to change the endpoint below. Test these:
                # Common endpoints: /v1/steel, /market/products, /v2/ime/steel etc.
                resp = await client.get("https://brsapi.ir/api/v1/steel", headers=headers, timeout=15)
                data = resp.json()
                
                # ←←← UPDATE THIS SECTION AFTER YOU TEST THE REAL API RESPONSE ←←←
                self.cache["ime"] = {
                    "کنسانتره": data.get("concentrate", "API تست شود"),
                    "گندله": data.get("pellet", "API تست شود"),
                    "آهن اسفنجی": data.get("sponge_iron", "API تست شود"),
                    "شمش فولاد": data.get("billet", "API تست شود"),
                    "میلگرد": data.get("rebar", "API تست شود"),
                    "ورق گرم": data.get("hot_sheet", "API تست شود"),
                    "ورق سرد": data.get("cold_sheet", "API تست شود"),
                }
                self.cache_time["ime"] = time.time()
                return self.cache["ime"]
        except Exception as e:
            return {"error": "خطا در API بورس کالا - endpoint را چک کنید"}

    async def get_all_prices(self):
        prices = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "dollar": await self.get_dollar_toman(),
            "gold": await self.get_alpha_price("XAUUSD", "Gold"),
            "silver": await self.get_alpha_price("XAGUSD", "Silver"),
            "copper": await self.get_alpha_price("HG=F", "Copper"),
            "nickel": await self.get_alpha_price("NICKEL", "Nickel"),   # May need better symbol
            "zinc": await self.get_alpha_price("ZINC", "Zinc"),
            "aluminum": await self.get_alpha_price("ALUMINUM", "Aluminum"),
            "iron_ore": "API بعداً اضافه میشود (CFD China)",   # Hard to get free real-time
            "ime": await self.get_ime_data()
        }
        return prices
