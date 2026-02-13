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
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioPiped, AudioVideoPiped

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

# Globals for Assistant Info
ASSISTANT_ID = None
ASSISTANT_NAME = None
ASSISTANT_USERNAME = None

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

QUEUES = {}

# ====================================================================
#  2. HELPER FUNCTIONS
# ====================================================================

async def get_assistant_details():
    """Fetch Assistant ID/Name on startup"""
    global ASSISTANT_ID, ASSISTANT_NAME, ASSISTANT_USERNAME
    if userbot:
        try:
            if not userbot.is_connected:
                await userbot.start()
            me = await userbot.get_me()
            ASSISTANT_ID = me.id
            ASSISTANT_NAME = me.first_name
            ASSISTANT_USERNAME = me.username
            LOGGER.info(f"Assistant Started: {ASSISTANT_NAME} (ID: {ASSISTANT_ID})")
        except Exception as e:
            LOGGER.error(f"Failed to fetch Assistant Details: {e}")

async def ensure_assistant_joined(chat_id):
    """
    Checks if assistant is in chat.
    If not, Bot invites Assistant OR generates link for Assistant to join.
    """
    if not userbot:
        return "Assistant client not initialized."
        
    try:
        # Check if already a member
        await userbot.get_chat_member(chat_id, "me")
        return True
    except UserNotParticipant:
        # Not a member, try to join
        pass
    except Exception:
        pass

    # Method 1: Bot invites Assistant (Needs Ban User Permission usually)
    if ASSISTANT_ID:
        try:
            await app.add_chat_members(chat_id, ASSISTANT_ID)
            return True
        except:
            pass
    
    # Method 2: Generate Invite Link and Join
    try:
        invite_link = await app.export_chat_invite_link(chat_id)
        if "+" in invite_link:
            await userbot.join_chat(invite_link)
            return True
    except ChatAdminRequired:
        return "I need **'Invite Users via Link'** permission to invite the assistant."
    except Exception as e:
        return f"Assistant failed to join: {e}"

    return "Could not add assistant. Manually add them."

def seconds_to_min(seconds):
    if seconds is not None:
        try:
            seconds = int(seconds)
            d, h, m, s = seconds // (3600 * 24), seconds // 3600 % 24, seconds % 3600 // 60, seconds % 3600 % 60
            if d > 0: return "{:02d}:{:02d}:{:02d}:{:02d}".format(d, h, m, s)
            elif h > 0: return "{:02d}:{:02d}:{:02d}".format(h, m, s)
            elif m > 0: return "{:02d}:{:02d}".format(m, s)
            elif s > 0: return "00:{:02d}".format(s)
        except:
            return "-"
    return "-"

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))

def clear_title(text):
    if not text:
        return "Unknown Title"
    try:
        list_words = text.split(" ")
        title = ""
        for i in list_words:
            if len(title) + len(i) < 60:
                title += " " + i
        return title.strip()
    except:
        return "Unknown Title"

async def gen_thumb(videoid, title, channel, views, duration):
    try:
        if os.path.isfile(f"cache/{videoid}.png"):
            return f"cache/{videoid}.png"
        
        thumbnail_url = f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status == 200:
                    if not os.path.exists("cache"): os.makedirs("cache")
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()
                else:
                    return thumbnail_url

        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(10))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.5)
        
        draw = ImageDraw.Draw(background)
        
        # Initialize fonts with fallback
        try:
            arial = ImageFont.truetype("AnshiRobot/resources/fonts/arial.ttf", 30)
            font = ImageFont.truetype("AnshiRobot/resources/fonts/arial.ttf", 40)
        except:
            arial = ImageFont.load_default()
            font = ImageFont.load_default()

        # Handle None values for text
        channel_text = str(channel) if channel else "Unknown Channel"
        views_text = str(views) if views else "N/A"
        duration_text = str(duration) if duration else "00:00"
        title_text = clear_title(title)

        draw.text((55, 560), f"{channel_text} | {views_text}", (255, 255, 255), font=arial)
        draw.text((57, 600), title_text, (255, 255, 255), font=font)
        draw.text((36, 685), "00:00", (255, 255, 255), font=arial)
        draw.text((1185, 685), duration_text, (255, 255, 255), font=arial)
        
        draw.line([(55, 660), (1220, 660)], fill="white", width=5, joint="curve")
        draw.ellipse([(918, 648), (942, 672)], outline="white", fill="white", width=15)

        background.save(f"cache/{videoid}.png")
        if os.path.exists(f"cache/thumb{videoid}.png"): os.remove(f"cache/thumb{videoid}.png")
        return f"cache/{videoid}.png"
    except Exception as e:
        LOGGER.error(f"Thumbnail Generation Error: {e}")
        return f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"

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
        except Exception:
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
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
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
        
        # Ensure Assistant is in Group
        joined = await ensure_assistant_joined(chat_id)
        if joined != True:
            await client.send_message(chat_id, f"⚠️ {joined}")
            clear_queue_db(chat_id)
            return

        # Try downloading file
        is_vid = (data["stream_type"] == "video")
        file_path = await download_track(data["vidid"], is_video=is_vid)
        
        stream = None
        if file_path:
            if is_vid:
                stream = AudioVideoPiped(file_path)
            else:
                stream = AudioPiped(file_path)
        else:
            # Fallback to direct URL
            stream_url = await get_direct_stream_url(data["vidid"])
            if stream_url:
                if is_vid:
                     stream = AudioVideoPiped(stream_url)
                else:
                     stream = AudioPiped(stream_url)

        if not stream:
             await client.send_message(chat_id, "🚫 **Error:** Failed to play track. YouTube blocked the IP. Please add `COOKIES` to Env.")
             queue.pop(0)
             return await play_next(chat_id, client, message)

        # PyTgCalls v1.x wrapper
        # play() does not exist in v1.x, we must check activity
        try:
            # call_py.active_calls is a list of Call objects in v1.x
            # We check if chat_id exists in any of them
            is_active = any(call.chat_id == chat_id for call in call_py.active_calls)
            
            if is_active:
                await call_py.change_stream(chat_id, stream)
            else:
                await call_py.join_group_call(chat_id, stream)
        except Exception as e:
            LOGGER.error(f"PyTgCalls 1.x Error: {e}")
            raise e
        
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
#  5. COMMAND HANDLERS
# ====================================================================

@app.on_message(filters.command(["play", "vplay"]))
async def play_handler(client, message: Message):
    if not call_py:
        return await message.reply_text("🚫 **Music Assistant is not active.** Check config `STRING_SESSION`.")

    if len(message.command) < 2:
        return await message.reply_text("💡 **Usage:** `/play <song>` or `/vplay <video>`")

    msg = await message.reply_text("🔎 **Searching...**")
    
    # 1. Join Assistant First
    join_status = await ensure_assistant_joined(message.chat.id)
    if join_status != True:
        return await msg.edit(f"⚠️ **Assistant Error:** {join_status}\nMake me Admin or use `/userbotjoin`.")

    try:
        query = message.text.split(None, 1)[1]
    except IndexError:
         return await msg.edit("⚠️ **Please provide a search query!**")

    is_video = message.command[0] == "vplay"
    user_mention = message.from_user.mention if message.from_user else "Admin"

    try:
        # Search
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: VideosSearch(query, limit=1).result())
        if not info["result"]:
            return await msg.edit("❌ **No results found.**")
        
        res = info["result"][0]
        # Robust extraction
        title = res.get("title", "Unknown Title")
        vidid = res.get("id")
        duration = res.get("duration", "00:00")
        link = res.get("link", f"https://www.youtube.com/watch?v={vidid}")
        
        # Safely extract channel and views, ensuring strings
        channel = "Unknown Channel"
        if "channel" in res and res["channel"] and "name" in res["channel"]:
            channel = str(res["channel"]["name"])
            
        views = "N/A"
        if "viewCount" in res and res["viewCount"] and "short" in res["viewCount"]:
            views = str(res["viewCount"]["short"])
        
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
        await msg.edit(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command(["userbotjoin", "joinassistant"]))
async def join_assistant_handler(client, message: Message):
    msg = await message.reply_text("⚙️ **Assistant Joining...**")
    res = await ensure_assistant_joined(message.chat.id)
    if res == True:
        await msg.edit(f"✅ **Assistant Joined Successfully**\nAccount: {ASSISTANT_NAME}")
    else:
        await msg.edit(f"❌ **Failed:** {res}")

@app.on_message(filters.command(["stop", "end"]))
async def stop_handler(client, message: Message):
    chat_id = message.chat.id
    if chat_id in QUEUES:
        clear_queue_db(chat_id)
        try:
            await start_call_if_not_active()
            await call_py.leave_group_call(chat_id)
            await message.reply_text("⏹️ **Playback Stopped & Queue Cleared.**")
        except:
            await message.reply_text("⚠️ **Nothing is playing.**")
    else:
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
        "• `/play <song>`\n• `/vplay <video>`\n• `/pause`\n• `/resume`\n• `/skip`\n• `/stop`\n• `/queue`\n• `/userbotjoin`"
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

# ====================================================================
#  7. INITIALIZATION (ASYNC)
# ====================================================================

if call_py:
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(get_assistant_details())
    except RuntimeError:
        pass