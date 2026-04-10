#!/usr/bin/env python3
"""
PSCall SMS মনিটর বট - শুধু বাটাম (টেক্সট লাইন ছাড়া)
"""

import asyncio
import aiohttp
import json
import logging
import re
from datetime import datetime
from typing import Optional, List
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# ============= কনফিগারেশন =============
TELEGRAM_BOT_TOKEN = "5929619535:AAGsgoN5pYczsKWOGqVWTrslk0qJr2jJVYA"
GROUP_CHAT_ID = "-1001153782407"

# ✅ আপনার কুকি
PHPSESSID = "r4isp11idcuir0cu3ab12bg88e"

PSCALL_CONFIG = {
    "data_url": "http://pscall.net/agent/res/data_smscdr.php",
    "cookie": f"PHPSESSID={PHPSESSID}",
    "referer": "http://pscall.net/agent/SMSCDRReports",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "interval": 3
}

# ============= কান্ট্রি ফ্লাগ ম্যাপিং =============
COUNTRY_FLAGS = {
    "niger": "🇳🇪",
    "bangladesh": "🇧🇩",
    "india": "🇮🇳",
    "usa": "🇺🇸",
    "uk": "🇬🇧",
    "madagascar": "🇲🇬",
    "nigeria": "🇳🇬",
    "egypt": "🇪🇬",
    "turkey": "🇹🇷",
    "pakistan": "🇵🇰",
    "saudi": "🇸🇦",
    "uae": "🇦🇪",
    "indonesia": "🇮🇩",
    "malaysia": "🇲🇾",
    "thailand": "🇹🇭",
    "vietnam": "🇻🇳",
    "philippines": "🇵🇭",
    "russia": "🇷🇺",
    "germany": "🇩🇪",
    "france": "🇫🇷",
    "italy": "🇮🇹",
    "spain": "🇪🇸",
    "brazil": "🇧🇷",
    "mexico": "🇲🇽",
    "australia": "🇦🇺",
    "canada": "🇨🇦",
    "poland": "🇵🇱",
}

MAIN_CHANNEL_LINK = "https://t.me/updaterange"
NUMBER_BOT_LINK = "https://t.me/Updateotpnew_bot"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class PSCallBot:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = GROUP_CHAT_ID
        self.processed = set()
        self.load_processed()
    
    def load_processed(self):
        try:
            with open("pscall_processed.json", 'r') as f:
                self.processed = set(json.load(f))
                logger.info(f"📂 {len(self.processed)} OTPs loaded")
        except:
            self.processed = set()
    
    def save_processed(self, otp_id: str):
        self.processed.add(otp_id)
        if len(self.processed) > 1000:
            self.processed = set(list(self.processed)[-500:])
        with open("pscall_processed.json", 'w') as f:
            json.dump(list(self.processed), f)
    
    def create_keyboard(self):
        """শুধু বাটাম - কোন টেক্সট লাইন থাকবে না"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_LINK),
            InlineKeyboardButton("🤖 Number Bot", url=NUMBER_BOT_LINK)
        ]])
        return keyboard
    
    async def send_message(self, text: str):
        try:
            await self.bot.send_message(
                self.chat_id, 
                text, 
                reply_markup=self.create_keyboard()
            )
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def send_start_message(self):
        msg = f"""
🚀 PSCall Bot Started
━━━━━━━━━━━━━━━━━━━
✅ Active
📡 Monitoring
⏰ {datetime.now().strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━
"""
        await self.send_message(msg)
    
    def extract_country_from_range(self, range_text: str) -> str:
        """Range টেক্সট থেকে শুধু কান্ট্রির নাম বের করে"""
        if not range_text:
            return "Unknown"
        
        first_word = range_text.split()[0] if range_text.split() else ""
        lower_word = first_word.lower()
        
        for country, flag in COUNTRY_FLAGS.items():
            if country in lower_word:
                return f"{flag} {country.title()}"
        
        return first_word.capitalize() if first_word else "Unknown"
    
    def extract_otp_from_message(self, text: str) -> Optional[str]:
        """মেসেজ থেকে OTP বের করুন"""
        if not text:
            return None
        
        match = re.search(r'code\s+(\d{3}-\d{3}|\d{5,6})', text, re.IGNORECASE)
        if match:
            code = match.group(1)
            return code.replace('-', '')
        
        match = re.search(r'login(\d{5,6})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r'\b(\d{5,6})\b', text)
        if match:
            code = match.group(1)
            if code not in ['2024', '2025', '2026']:
                return code
        
        return None
    
    def extract_platform(self, text: str, client: str = "") -> str:
        if client and client.upper() != "UNKNOWN":
            return client.upper()
        
        if 'telegram' in text.lower():
            return 'TELEGRAM'
        elif 'whatsapp' in text.lower():
            return 'WHATSAPP'
        elif 'instagram' in text.lower():
            return 'INSTAGRAM'
        elif 'spova' in text.lower():
            return 'SPOVA'
        elif 'fintana' in text.lower():
            return 'FINTANA'
        
        return 'SERVICE'
    
    def format_phone(self, phone: str) -> str:
        phone = str(phone)
        if len(phone) >= 10:
            return phone[:5] + "***" + phone[-3:]
        return phone
    
    async def fetch_sms(self) -> List:
        headers = {
            "User-Agent": PSCALL_CONFIG["user_agent"],
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": PSCALL_CONFIG["referer"],
            "Cookie": PSCALL_CONFIG["cookie"],
        }
        
        today = datetime.now().strftime("%Y-%m-%d")
        params = {
            "fdate1": f"{today} 00:00:00",
            "fdate2": f"{today} 23:59:59",
            "iDisplayStart": "0",
            "iDisplayLength": "50",
            "sSortDir_0": "desc",
            "_": str(int(datetime.now().timestamp() * 1000))
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    PSCALL_CONFIG["data_url"], 
                    headers=headers, 
                    params=params, 
                    timeout=15
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        
                        if "Direct Script Access" in text:
                            logger.error("❌ Cookie expired!")
                            return []
                        
                        data = json.loads(text)
                        return data.get("aaData", [])
                    else:
                        logger.warning(f"HTTP {resp.status}")
                        return []
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return []
    
    async def monitor(self):
        await self.send_start_message()
        logger.info("✅ Bot monitoring started")
        
        while True:
            try:
                sms_list = await self.fetch_sms()
                
                if sms_list:
                    logger.info(f"📨 Found {len(sms_list)} records")
                    
                    for sms in sms_list:
                        if len(sms) >= 6:
                            range_text = sms[1] if len(sms) > 1 else ""
                            phone = sms[2]
                            client = sms[3] if len(sms) > 3 else ""
                            message = sms[5] if len(sms) > 5 else ""
                            
                            if not message:
                                continue
                            
                            otp = self.extract_otp_from_message(message)
                            
                            if otp:
                                otp_id = f"{phone}_{otp}"
                                
                                if otp_id not in self.processed:
                                    self.save_processed(otp_id)
                                    
                                    country = self.extract_country_from_range(range_text)
                                    platform = self.extract_platform(message, client)
                                    hidden_phone = self.format_phone(phone)
                                    
                                    # 6 ডিজিট হলে ড্যাশ যোগ করুন
                                    if len(otp) == 6:
                                        formatted_otp = f"{otp[:3]}-{otp[3:]}"
                                        msg_text = f"""
{country} - #{platform} - {hidden_phone}

💌Language - #English - Your {platform} code {formatted_otp}
Don't share this code with others

🔐{otp}
"""
                                    else:
                                        msg_text = f"""
{country} - #{platform} - {hidden_phone}

💌Language - #English - Your {platform} code {otp}
Don't share this code with others

🔐{otp}
"""
                                    await self.send_message(msg_text)
                                    logger.info(f"✅ OTP Sent: {otp} | Country: {country}")
                                    await asyncio.sleep(1)
                
                await asyncio.sleep(PSCALL_CONFIG["interval"])
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        print("=" * 50)
        print("🚀 PSCall SMS Monitor Bot")
        print("=" * 50)
        await self.monitor()


async def main():
    bot = PSCallBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped!")