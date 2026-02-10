import asyncio
import os
import aiohttp
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioVideoPiped
from AnshiRobot import pbot as app, LOGGER
from AnshiRobot.config import Development as Config

# ====================================================================
#  CONFIGURATION & INITIALIZATION
# ====================================================================

SESSION = Config.STRING_SESSION
API_ID = Config.API_ID
API_HASH = Config.API_HASH

# --- FALLBACK API SETTINGS (From Priya-music01) ---
YOUR_API_URL = None
FALLBACK_API_URL = "https://shrutibots.site"
PASTEBIN_URL = "https://pastebin.com/raw/rLsBhAQa"

if not SESSION:
    LOGGER.error("STRING_SESSION not found! Music module commands will fail.")
    userbot = None
    call_py = None
else:
    try:
        userbot = Client("MusicAssistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)
        call_py = PyTgCalls(userbot)
    except Exception as e:
        LOGGER.error(f"Failed to initialize Music Assistant: {e}")
        userbot = None
        call_py = None

QUEUES = {}

# ====================================================================
#  FALLBACK API LOGIC (From Priya-music01/Youtube.py)
# ====================================================================

async def load_api_url():
    global YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PASTEBIN_URL, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    content = await response.text()
                    YOUR_API_URL = content.strip()
                    LOGGER.info(f"Loaded Music API: {YOUR_API_URL}")
                else:
                    YOUR_API_URL = FALLBACK_API_URL
                    LOGGER.info("Using Fallback API URL")
    except Exception:
        YOUR_API_URL = FALLBACK_API_URL
        LOGGER.info("Connection failed, Using Fallback API URL")

async def download_via_api(video_id):
    """Attempts to download song via external API (The Fallback Logic)"""
    global YOUR_API_URL
    if not YOUR_API_URL:
        await load_api_url()

    # Create downloads folder
    if not os.path.isdir("downloads"):
        os.makedirs("downloads")
    
    file_path = os.path.join("downloads", f"{video_id}.mp3")
    
    # If file exists, return it
    if os.path.exists(file_path):
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Request Download
            params = {"url": video_id, "type": "audio"}
            async with session.get(f"{YOUR_API_URL}/download", params=params, timeout=60) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                token = data.get("download_token")
                if not token: return None

            # 2. Stream File to Disk
            stream_url = f"{YOUR_API_URL}/stream/{video_id}?type=audio"
            async with session.get(stream_url, headers={"X-Download-Token": token}, timeout=300) as stream_resp:
                if stream_resp.status != 200: return None
                with open(file_path, "wb") as f:
                    async for chunk in stream_resp.content.iter_chunked(16384):
                        f.write(chunk)
            return file_path
    except Exception as e:
        LOGGER.error(f"API Download Failed: {e}")
        return None

# ====================================================================
#  QUEUE & PLAYBACK LOGIC
# ====================================================================

def get_queue(chat_id):
    return QUEUES.get(chat_id, [])

def clear_queue(chat_id):
    if chat_id in QUEUES:
        QUEUES.pop(chat_id)

def add_to_queue(chat_id, title, link, vidid, user):
    if chat_id not in QUEUES:
        QUEUES[chat_id] = []
    QUEUES[chat_id].append({"title": title, "link": link, "vidid": vidid, "user": user})
    return len(QUEUES[chat_id])

async def play_stream(chat_id, link, vidid, title, message):
    try:
        if not userbot.is_connected:
            await userbot.start()
        
        # 1. Try API Download (Fallback System)
        audio_file = await download_via_api(vidid)

        # 2. If API fails, use Local yt-dlp (Standard System)
        if not audio_file:
            LOGGER.info("API failed, switching to local yt-dlp...")
            opts = {'format': 'bestaudio', 'quiet': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                audio_file = info['url'] # Direct URL stream
                stream = MediaStream(audio_file)
        else:
             # If API worked, play the downloaded file
             stream = MediaStream(audio_file)

        # Join and Play
        await call_py.play(chat_id, stream)

        await message.reply_photo(
            photo=Config.START_IMG,
            caption=f"🎵 **Started Playing**\n\n🏷 **Title:** [{title}]({link})\n👤 **Requested by:** {message.from_user.mention}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏹️ Stop Music", callback_data="music_stop")]])
        )
    except Exception as e:
        await message.reply_text(f"🚫 **Playback Error:** `{e}`")
        clear_queue(chat_id)

# ====================================================================
#  COMMANDS
# ====================================================================

@app.on_message(filters.command(["play", "vplay"]))
async def play_handler(_, message: Message):
    if not call_py:
        return await message.reply_text("🚫 **Assistant not initialized.** Check STRING_SESSION.")
    
    if len(message.command) < 2:
        return await message.reply_text("💡 **Usage:** `/play <song name>`")

    m = await message.reply_text("🔎 **Searching...**")
    query = message.text.split(None, 1)[1]

    try:
        # Extract Info
        opts = {'format': 'bestaudio', 'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            if "http" in query:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        
        title = info['title']
        link = info['webpage_url']
        vidid = info['id']
        chat_id = message.chat.id

        pos = add_to_queue(chat_id, title, link, vidid, message.from_user.first_name)

        if pos == 1:
            await m.edit(f"⏱️ **Processing:** `{title}`...")
            await play_stream(chat_id, link, vidid, title, message)
        else:
            await m.edit(f"✅ **Queued at #{pos}:** `{title}`")

    except Exception as e:
        await m.edit(f"❌ **Error:** {e}")

@app.on_message(filters.command(["stop", "end"]))
async def stop_handler(_, message: Message):
    if not call_py: return
    chat_id = message.chat.id
    try:
        clear_queue(chat_id)
        await call_py.leave_call(chat_id)
        await message.reply_text("⏹️ **Playback Ended.**")
    except:
        await message.reply_text("⚠️ **Not playing.**")

@app.on_message(filters.command("pause"))
async def pause_handler(_, message: Message):
    if not call_py: return
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply_text("II **Paused.**")
    except:
        await message.reply_text("⚠️ Not playing.")

@app.on_message(filters.command("resume"))
async def resume_handler(_, message: Message):
    if not call_py: return
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply_text("▶️ **Resumed.**")
    except:
        await message.reply_text("⚠️ Not paused.")

@app.on_message(filters.command("skip"))
async def skip_handler(_, message: Message):
    if not call_py: return
    chat_id = message.chat.id
    queue = get_queue(chat_id)

    if len(queue) > 0:
        queue.pop(0) # Remove current
    
    if len(queue) > 0:
        nxt = queue[0]
        await message.reply_text(f"⏭️ **Skipped.** Now: `{nxt['title']}`")
        await play_stream(chat_id, nxt['link'], nxt['vidid'], nxt['title'], message)
    else:
        await stop_handler(_, message)

@app.on_message(filters.command("mstart"))
async def mstart_handler(_, message: Message):
    await message.reply_text("🎵 **Music Module is Active.**\n\nFallback API loaded.")

@app.on_message(filters.command("mhelp"))
async def mhelp_handler(_, message: Message):
    await message.reply_text(
        "🎧 **Music Commands**\n\n"
        "/play <song> - Play Music\n"
        "/stop - Stop\n"
        "/pause - Pause\n"
        "/resume - Resume\n"
        "/skip - Skip\n"
        "/queue - Check Queue"
    )

@app.on_callback_query(filters.regex("music_stop"))
async def cb_stop(_, query):
    chat_id = query.message.chat.id
    try:
        clear_queue(chat_id)
        await call_py.leave_call(chat_id)
        await query.message.edit_text("⏹️ **Stopped by User.**")
    except:
        await query.answer("Nothing playing.")

# Start API Loader
try:
    loop = asyncio.get_event_loop()
    loop.create_task(load_api_url())
    if call_py and not call_py.active:
        loop.create_task(call_py.start())
except:
    pass

__mod_name__ = "˹ ᴍᴜsɪᴄ ˼"
__help__ = """
🎵 **Music & Video Player**

• `/play <song>` : Play song via YouTube.
• `/vplay <song>` : Play video (Audio only for now).
• `/pause`, `/resume`, `/skip`, `/stop` : Controls.
• `/mstart` : Check system status.
"""