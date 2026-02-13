import asyncio
import os
import time
import math
import random
import re
import wget
import aiohttp
import aiofiles
from io import BytesIO
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

import yt_dlp
from youtubesearchpython import VideosSearch
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# Import from AnshiRobot
from AnshiRobot import pbot as app, LOGGER
from AnshiRobot.config import Development as Config

# ====================================================================
#  1. CONFIGURATION & CLIENT SETUP
# ====================================================================

API_ID = Config.API_ID
API_HASH = Config.API_HASH
STRING_SESSION = Config.STRING_SESSION
SUPPORT_CHAT = Config.SUPPORT_CHAT or "PR_ALL_BOT_SUPPORT"

# Fallback API settings
FALLBACK_API_URL = "https://shrutibots.site"
PASTEBIN_URL = "https://batbin.me/snored"
YOUR_API_URL = None

# Create cookies.txt from ENV if available
if "COOKIES" in os.environ:
    with open("cookies.txt", "w") as f:
        f.write(os.environ["COOKIES"])

if not STRING_SESSION:
    LOGGER.error("STRING_SESSION not found! Music module disabled.")
    userbot = None
    call_py = None
else:
    try:
        userbot = Client(
            "MusicAssistant",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=STRING_SESSION,
            in_memory=True
        )
        call_py = PyTgCalls(userbot)
    except Exception as e:
        LOGGER.error(f"Music Assistant Init Failed: {e}")
        userbot = None
        call_py = None

# In-Memory Database
QUEUES = {}

# ====================================================================
#  2. HELPER FUNCTIONS
# ====================================================================

def seconds_to_min(seconds):
    if seconds is not None:
        seconds = int(seconds)
        d, h, m, s = seconds // (3600 * 24), seconds // 3600 % 24, seconds % 3600 // 60, seconds % 3600 % 60
        if d > 0: return "{:02d}:{:02d}:{:02d}:{:02d}".format(d, h, m, s)
        elif h > 0: return "{:02d}:{:02d}:{:02d}".format(h, m, s)
        elif m > 0: return "{:02d}:{:02d}".format(m, s)
        elif s > 0: return "00:{:02d}".format(s)
    return "-"

def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))

def clear_title(text):
    list_words = text.split(" ")
    title = ""
    for i in list_words:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()

async def gen_thumb(videoid, title, channel, views, duration):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"
    
    thumbnail_url = f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status == 200:
                    if not os.path.exists("cache"): os.makedirs("cache")
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(10))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.5)
        
        draw = ImageDraw.Draw(background)
        try:
            arial = ImageFont.load_default()
            font = ImageFont.load_default()
        except:
            pass

        draw.text((55, 560), f"{channel} | {views}", (255, 255, 255), font=arial)
        draw.text((57, 600), clear_title(title), (255, 255, 255), font=font)
        draw.text((36, 685), "00:00", (255, 255, 255), font=arial)
        draw.text((1185, 685), f"{duration}", (255, 255, 255), font=arial)
        
        draw.line([(55, 660), (1220, 660)], fill="white", width=5, joint="curve")
        draw.ellipse([(918, 648), (942, 672)], outline="white", fill="white", width=15)

        background.save(f"cache/{videoid}.png")
        if os.path.exists(f"cache/thumb{videoid}.png"): os.remove(f"cache/thumb{videoid}.png")
        return f"cache/{videoid}.png"
    except Exception as e:
        return thumbnail_url

# ====================================================================
#  3. DOWNLOAD LOGIC
# ====================================================================

async def load_api_url():
    global YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PASTEBIN_URL) as response:
                if response.status == 200:
                    text = await response.text()
                    if "http" in text and "<" not in text:
                        YOUR_API_URL = text.strip()
                    else:
                        YOUR_API_URL = FALLBACK_API_URL
                else:
                    YOUR_API_URL = FALLBACK_API_URL
    except:
        YOUR_API_URL = FALLBACK_API_URL

async def download_track(videoid, is_video=False):
    global YOUR_API_URL
    if not YOUR_API_URL: await load_api_url()

    if not os.path.isdir("downloads"): os.makedirs("downloads")
    ext = "mp4" if is_video else "mp3"
    file_path = os.path.join("downloads", f"{videoid}.{ext}")

    if os.path.exists(file_path): return file_path

    # --- Method 1: API ---
    # We skip API logic if it returned HTML junk previously
    if YOUR_API_URL and "shrutibots" in YOUR_API_URL: 
        try:
            async with aiohttp.ClientSession() as session:
                params = {"url": videoid, "type": "video" if is_video else "audio"}
                async with session.get(f"{YOUR_API_URL}/download", params=params, timeout=20) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        token = data.get("download_token")
                        if token:
                            stream_url = f"{YOUR_API_URL}/stream/{videoid}?type={params['type']}"
                            async with session.get(stream_url, headers={"X-Download-Token": token}) as f_resp:
                                if f_resp.status == 200:
                                    with open(file_path, "wb") as f:
                                        async for chunk in f_resp.content.iter_chunked(1024):
                                            f.write(chunk)
                                    return file_path
        except Exception as e:
            pass

    # --- Method 2: Local yt-dlp with COOKIES ---
    try:
        cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
        
        opts = {
            'format': 'best' if is_video else 'bestaudio',
            'outtmpl': file_path,
            'quiet': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'cookiefile': cookie_file,
            # Trying Android client which is sometimes less strict
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
        }
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(opts).download([f"https://www.youtube.com/watch?v={videoid}"]))
        
        if os.path.exists(file_path):
            return file_path
    except Exception as e:
        LOGGER.error(f"Local Download Failed: {e}")
    
    return None

async def get_direct_stream_url(videoid):
    try:
        cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
        opts = {
            'format': 'bestaudio', 
            'quiet': True, 
            'cookiefile': cookie_file,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(opts).extract_info(f"https://www.youtube.com/watch?v={videoid}", download=False))
        return info.get('url')
    except:
        return None

# ====================================================================
#  4. QUEUE & PLAYBACK
# ====================================================================

def add_to_queue(chat_id, track_dict):
    if chat_id not in QUEUES: QUEUES[chat_id] = []
    QUEUES[chat_id].append(track_dict)
    return len(QUEUES[chat_id])

def get_queue(chat_id):
    return QUEUES.get(chat_id, [])

def clear_queue_db(chat_id):
    if chat_id in QUEUES: QUEUES.pop(chat_id)

async def start_call_if_not_active():
    if call_py:
        try: await call_py.start()
        except: pass

async def play_next(chat_id, client, message):
    queue = get_queue(chat_id)
    if not queue:
        try: return await call_py.leave_group_call(chat_id)
        except: return
    
    data = queue[0]
    
    try:
        await start_call_if_not_active()
        
        # Try downloading file
        file_path = await download_track(data["vidid"], is_video=(data["stream_type"] == "video"))
        
        stream = None
        if file_path:
            stream = MediaStream(file_path, video_flags=MediaStream.Flags.IGNORE if data["stream_type"] == "audio" else None)
        else:
            # Fallback to direct URL
            stream_url = await get_direct_stream_url(data["vidid"])
            if stream_url:
                stream = MediaStream(stream_url, video_flags=MediaStream.Flags.IGNORE if data["stream_type"] == "audio" else None)

        if not stream:
             await client.send_message(chat_id, "🚫 **Error:** Failed to play track. YouTube blocked the IP. Please add `COOKIES` to Env.")
             queue.pop(0)
             return await play_next(chat_id, client, message)

        await call_py.play(chat_id, stream)
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Pause", callback_data="music_pause"),
             InlineKeyboardButton("⏹ Stop", callback_data="music_stop"),
             InlineKeyboardButton("⏭ Skip", callback_data="music_skip")]
        ])
        
        await client.send_photo(
            chat_id,
            photo=data["thumb"],
            caption=f"🎵 **Now Playing:** [{data['title']}]({data['link']})\n"
                    f"👤 **Requested by:** {data['user']}\n"
                    f"⏱ **Duration:** {data['dur']}",
            reply_markup=buttons
        )
    except Exception as e:
        LOGGER.error(f"Playback error: {e}")
        if len(queue) > 0: queue.pop(0)
        await play_next(chat_id, client, message)

# ====================================================================
#  5. COMMANDS
# ====================================================================

@app.on_message(filters.command(["play", "vplay"]))
async def play_handler(client, message: Message):
    if not call_py:
        return await message.reply_text("🚫 **Music Module Disabled.** check logs.")

    if len(message.command) < 2:
        return await message.reply_text("💡 **Usage:** `/play <song>` or `/vplay <video>`")

    msg = await message.reply_text("🔎 **Searching...**")
    query = message.text.split(None, 1)[1]
    is_video = message.command[0] == "vplay"
    user_mention = message.from_user.mention if message.from_user else "Admin"

    try:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: VideosSearch(query, limit=1).result())
        if not info["result"]:
            return await msg.edit("❌ **No results found.**")
        
        res = info["result"][0]
        title = res["title"]
        vidid = res["id"]
        duration = res["duration"]
        link = res["link"]
        channel = res["channel"]["name"]
        views = res["viewCount"]["short"]
        
        thumb_path = await gen_thumb(vidid, title, channel, views, duration)

        track_data = {
            "title": title, "link": link, "vidid": vidid,
            "user": user_mention, "dur": duration, "thumb": thumb_path,
            "stream_type": "video" if is_video else "audio"
        }

        pos = add_to_queue(message.chat.id, track_data)
        
        if pos == 1:
            await msg.edit(f"📥 **Processing:** `{title}`...")
            await play_next(message.chat.id, client, message)
            await msg.delete()
        else:
            await msg.delete()
            await message.reply_photo(
                photo=thumb_path,
                caption=f"✅ **Added to Queue at #{pos}**\n🏷 **Title:** {title}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="music_close")]])
            )

    except Exception as e:
        LOGGER.error(f"Play Error: {e}")
        await msg.edit(f"❌ **Error:** {e}")

@app.on_message(filters.command(["stop", "end"]))
async def stop_handler(client, message: Message):
    chat_id = message.chat.id
    clear_queue_db(chat_id)
    try:
        await start_call_if_not_active()
        await call_py.leave_group_call(chat_id)
        await message.reply_text("⏹️ **Playback Stopped.**")
    except:
        await message.reply_text("⚠️ **Nothing is playing.**")

@app.on_message(filters.command(["skip", "next"]))
async def skip_handler(client, message: Message):
    chat_id = message.chat.id
    queue = get_queue(chat_id)
    if len(queue) > 0:
        queue.pop(0)
        if len(queue) > 0:
            await message.reply_text("⏭️ **Skipped.**")
            await play_next(chat_id, client, message)
        else:
            await stop_handler(client, message)
    else:
        await message.reply_text("⚠️ **Queue is empty.**")

@app.on_message(filters.command("pause"))
async def pause_handler(client, message: Message):
    try:
        await start_call_if_not_active()
        await call_py.pause_stream(message.chat.id)
        await message.reply_text("II **Paused.**")
    except:
        await message.reply_text("⚠️ **Nothing playing.**")

@app.on_message(filters.command("resume"))
async def resume_handler(client, message: Message):
    try:
        await start_call_if_not_active()
        await call_py.resume_stream(message.chat.id)
        await message.reply_text("▶️ **Resumed.**")
    except:
        await message.reply_text("⚠️ **Nothing paused.**")

@app.on_message(filters.command("queue"))
async def queue_handler(client, message: Message):
    queue = get_queue(message.chat.id)
    if not queue:
        return await message.reply_text("📭 **Queue is empty.**")
    text = "**📂 Music Queue:**\n\n"
    for i, track in enumerate(queue):
        text += f"**{i+1}.** [{track['title']}]({track['link']})\n"
    await message.reply_text(text, disable_web_page_preview=True)

@app.on_message(filters.command("mstart"))
async def music_start(client, message: Message):
    await message.reply_text("🎵 **Anshi Music System Online!**")

@app.on_message(filters.command("mhelp"))
async def music_help(client, message: Message):
    await message.reply_text(
        "🎧 **Music Commands:**\n\n"
        "• `/play <song>`\n• `/vplay <video>`\n• `/pause`\n• `/resume`\n• `/skip`\n• `/stop`\n• `/queue`"
    )

# ====================================================================
#  6. CALLBACKS
# ====================================================================

@app.on_callback_query(filters.regex("music_"))
async def music_callbacks(client, query: CallbackQuery):
    data = query.data
    chat_id = query.message.chat.id
    
    if data == "music_close":
        return await query.message.delete()

    try:
        user = await client.get_chat_member(chat_id, query.from_user.id)
        if user.status not in ["creator", "administrator"]:
            return await query.answer("❌ Admins only.", show_alert=True)
    except:
        return

    if data == "music_stop":
        clear_queue_db(chat_id)
        try: await call_py.leave_group_call(chat_id)
        except: pass
        await query.message.edit_text("⏹️ **Stopped.**")
    elif data == "music_pause":
        try: await call_py.pause_stream(chat_id)
        except: pass
        await query.answer("Paused")
    elif data == "music_skip":
        queue = get_queue(chat_id)
        if len(queue) > 0: queue.pop(0)
        if len(queue) > 0:
            await query.message.delete()
            await play_next(chat_id, client, query.message)
        else:
            clear_queue_db(chat_id)
            try: await call_py.leave_group_call(chat_id)
            except: pass
            await query.message.edit_text("⏹️ **Queue Ended.**")