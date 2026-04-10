#!/usr/bin/env python3
"""
PSCall SMS মনিটর বট - ফাইনাল ওয়ার্কিং
"""

import asyncio
import aiohttp
import json
import logging
import re
from datetime import datetime
from typing import Optional, List
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest

# ============= কনফিগারেশন =============
TELEGRAM_BOT_TOKEN = "5929619535:AAGsgoN5pYczsKWOGqVWTrslk0qJr2jJVYA"
GROUP_CHAT_ID = "-1001153782407"

# ✅ সঠিক কুকি (আপনার দেওয়া)
PHPSESSID = "r4isp11idcuir0cu3ab12bg88e"

PSCALL_CONFIG = {
    "data_url": "http://pscall.net/agent/res/data_smscdr.php",
    "cookie": f"PHPSESSID={PHPSESSID}",
    "referer": "http://pscall.net/agent/SMSCDRReports",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "interval": 3
}

MAIN_CHANNEL_LINK = "https://t.me/updaterange"
NUMBER_BOT_LINK = "https://t.me/Updateotpnew_bot"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class PSCallBot:
    def __init__(self):
        # ✅ সঠিকভাবে request সেটআপ
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
        with open("pscall_processed.json", 'w') as f:
            json.dump(list(self.processed), f)
    
    def create_keyboard(self):
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_LINK),
            InlineKeyboardButton("🤖 Number Bot", url=NUMBER_BOT_LINK)
        ]])
    
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
    
    def extract_otp_from_message(self, text: str) -> Optional[str]:
        """মেসেজ থেকে OTP বের করুন"""
        if not text:
            return None
        
        # প্যাটার্ন 1: "Telegram code 73141"
        match = re.search(r'code\s+(\d{5,6})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # প্যাটার্ন 2: "login73141"
        match = re.search(r'login(\d{5,6})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # প্যাটার্ন 3: শুধু 5-6 ডিজিট
        match = re.search(r'\b(\d{5,6})\b', text)
        if match:
            code = match.group(1)
            if code not in ['2024', '2025', '2026']:
                return code
        
        return None
    
    def extract_platform(self, text: str) -> str:
        if 'telegram' in text.lower():
            return 'TELEGRAM'
        elif 'whatsapp' in text.lower():
            return 'WHATSAPP'
        elif 'instagram' in text.lower():
            return 'INSTAGRAM'
        return 'SERVICE'
    
    def format_phone(self, phone: str) -> str:
        phone = str(phone)
        if len(phone) >= 10:
            return phone[:5] + "***" + phone[-3:]
        return phone
    
    async def fetch_sms(self) -> List:
        """API থেকে SMS ডাটা fetch"""
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
                            # আপনার রেসপন্স স্ট্রাকচার অনুযায়ী:
                            # sms[0] = time, sms[1] = range, sms[2] = number, 
                            # sms[3] = client, sms[4] = null, sms[5] = message
                            
                            timestamp = sms[0]
                            phone = sms[2]
                            client = sms[3]
                            message = sms[5] if len(sms) > 5 else ""
                            
                            if not message:
                                continue
                            
                            logger.info(f"📱 Phone: {phone}, Message: {message[:80]}")
                            
                            otp = self.extract_otp_from_message(message)
                            
                            if otp:
                                otp_id = f"{phone}_{otp}"
                                
                                if otp_id not in self.processed:
                                    self.save_processed(otp_id)
                                    
                                    platform = self.extract_platform(message)
                                    hidden_phone = self.format_phone(phone)
                                    
                                    msg_text = f"""
{platform} - {hidden_phone}

🔐 Your code: {otp}

[ Main Channel ]    [ Number Bot ]
"""
                                    await self.send_message(msg_text)
                                    logger.info(f"✅ OTP Sent: {otp} to {phone}")
                                    await asyncio.sleep(1)
                            else:
                                logger.debug(f"No OTP in: {message[:50]}")
                
                await asyncio.sleep(PSCALL_CONFIG["interval"])
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        print("=" * 50)
        print("🚀 PSCall SMS Monitor Bot")
        print(f"🍪 Cookie: {PHPSESSID[:15]}...")
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