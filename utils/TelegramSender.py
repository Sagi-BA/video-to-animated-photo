import os
from dotenv import load_dotenv
import asyncio
import aiohttp
from typing import Optional
import base64
from io import BytesIO

load_dotenv()

class TelegramSender:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def _make_request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}/{endpoint}"
        async with getattr(self.session, method)(url, **kwargs) as response:
            if response.status != 200:
                print(f"Failed to {endpoint}. Status: {response.status}")
                print(f"Response: {await response.text()}")
                return None
            return await response.json()

    async def verify_bot_token(self):
        result = await self._make_request('get', 'getMe')
        return bool(result)

    async def send_animation(self, base64_gif: str, caption: Optional[str] = None) -> None:
        print('Sending animated GIF to Telegram')
        gif_data = base64.b64decode(base64_gif)
        gif_byte_arr = BytesIO(gif_data)
        
        data = aiohttp.FormData()
        data.add_field("chat_id", self.chat_id)
        data.add_field("animation", gif_byte_arr, filename="animation.gif", content_type="image/gif")
        if caption:
            data.add_field("caption", caption)

        result = await self._make_request('post', 'sendAnimation', data=data)
        if result:
            print("Animated GIF sent successfully to Telegram")
        else:
            print("Failed to send animated GIF to Telegram")

async def send_telegram_gif(base64_gif: str, caption: Optional[str] = None):
    async with TelegramSender() as sender:
        if await sender.verify_bot_token():
            await sender.send_animation(base64_gif, caption)
        else:
            print("Bot token verification failed")

# This function will be called from the main Streamlit script
def send_telegram_gif_sync(base64_gif: str, caption: Optional[str] = None):
    asyncio.run(send_telegram_gif(base64_gif, caption))