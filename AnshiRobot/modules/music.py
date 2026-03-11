import asyncio
import os
import time
import math
import random
import re
import aiohttp
import aiofiles
from typing import Union
from bs4 import BeautifulSoup

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Voice
from pyrogram.enums import ChatMemberStatus, MessageEntityType
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait

from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo

import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from youtubesearchpython.__future__ import VideosSearch, CustomSearch
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from motor.motor_asyncio import AsyncIOMotorClient

# ====================================================================
#  1. CONFIGURATION & CLIENT SETUP
# ====================================================================
from AnshiRobot import pbot as app, LOGGER
from AnshiRobot.config import Development as Config

API_ID = Config.API_ID
API_HASH = Config.API_HASH
STRING_SESSION = Config.STRING_SESSION
SUPPORT_CHAT = Config.SUPPORT_CHAT or "PR_ALL_BOT_SUPPORT"

# YouTube Cache & Database Setup
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://demo38174_db_user:myhTrNGcYm5zpQus@cluster0.dboqmtf.mongodb.net/?appName=Cluster0")
PLAYLIST_ID = -1003729108569 # Your Cache Channel ID
YT_API_KEY = "xbit_B4TNnBAoe6uoSM7NLFz-dk6X7GibJ6Bh"
YTPROXY = "https://tgapi.xbitcode.com"
FALLBACK_API_URL = "https://shrutibots.site"

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "1c21247d714244ddbb09925dac565aed")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "709e1a2969664491b58200860623ef19")

# Init DB
_mongo_async_ = AsyncIOMotorClient(MONGO_DB_URI)
mongodb = _mongo_async_.PritiMusic
trackdb = mongodb.track_cache

# Globals
ASSISTANT_ID = None
ASSISTANT_NAME = None
ASSISTANT_USERNAME = None
QUEUES = {}
LOOP = {}
SPEED = {}
PLAYING_STATE = {}

# Write cookies
if "COOKIES" in os.environ:
    with open("cookies.txt", "w") as f:
        f.write(os.environ["COOKIES"])

# Assistant Setup
if not STRING_SESSION:
    LOGGER.error("STRING_SESSION not found! Music module disabled.")
    userbot = None
    call_py = None
else:
    try:
        userbot = Client("MusicAssistant", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION, in_memory=True)
        call_py = PyTgCalls(userbot)
    except Exception as e:
        LOGGER.error(f"Music Assistant Init Failed: {e}")
        userbot, call_py = None, None


# ====================================================================
#  2. FORMATTERS & UTILS
# ====================================================================

def time_to_seconds(time_str):
    try:
        return sum(int(x) * 60**i for i, x in enumerate(reversed(str(time_str).split(":"))))
    except:
        return 0

def seconds_to_min(seconds):
    try:
        seconds = int(seconds)
        d, h, m, s = seconds // 86400, seconds // 3600 % 24, seconds % 3600 // 60, seconds % 3600 % 60
        if d > 0: return f"{d:02d}:{h:02d}:{m:02d}:{s:02d}"
        elif h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
        else: return f"{m:02d}:{s:02d}"
    except: return "00:00"

def convert_bytes(size: float) -> str:
    if not size: return ""
    power, t_n = 1024, 0
    power_dict = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    while size > power:
        size /= power
        t_n += 1
    return "{:.2f} {}".format(size, power_dict[t_n])

def get_readable_time(seconds: int) -> str:
    count, ping_time, time_list = 0, "", []
    time_suffix_list =["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0: break
        time_list.append(int(result))
        seconds = int(remainder)
    for i in range(len(time_list)): time_list[i] = str(time_list[i]) + time_suffix_list[i]
    if len(time_list) == 4: ping_time += time_list.pop() + ", "
    time_list.reverse()
    return ping_time + ":".join(time_list)

async def ensure_assistant_joined(chat_id):
    if not userbot: return "Assistant not initialized."
    try:
        await userbot.get_chat_member(chat_id, "me")
        return True
    except UserNotParticipant: pass
    except Exception: pass

    try:
        invite_link = await app.export_chat_invite_link(chat_id)
        if "+" in invite_link:
            await userbot.join_chat(invite_link)
            return True
    except ChatAdminRequired:
        return "❌ **I need 'Invite Users via Link' permission to add the assistant.**"
    except Exception as e:
        return f"Assistant failed to join: {e}"
    return "❌ **Could not add assistant.**"

def AdminRightsCheck(func):
    async def wrapper(client, message: Message):
        if not message.from_user: return
        if message.from_user.id == Config.OWNER_ID: return await func(client, message)
        try:
            member = await app.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text("❌ **You must be an admin to use this command.**")
            if not member.privileges.can_manage_video_chats and member.status != ChatMemberStatus.OWNER:
                return await message.reply_text("❌ **You need 'Manage Video Chats' permission.**")
        except:
            return await message.reply_text("❌ **Could not verify your admin status.**")
        return await func(client, message)
    return wrapper

# ====================================================================
#  3. PLATFORMS (Spotify, Apple, Resso, Soundcloud, Telegram)
# ====================================================================

class SpotifyAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/open.spotify.com\/)(.*)$"
        if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
            self.client_credentials_manager = SpotifyClientCredentials(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
            self.spotify = spotipy.Spotify(client_credentials_manager=self.client_credentials_manager)
        else:
            self.spotify = None

    async def track(self, link: str):
        track = self.spotify.track(link)
        info = track["name"] + " " + " ".join([artist["name"] for artist in track["artists"] if "Various Artists" not in artist["name"]])
        results = await VideosSearch(info, limit=1).next()
        res = results["result"][0]
        return {"title": res["title"], "link": res["link"], "vidid": res["id"], "duration_min": res["duration"], "thumb": res["thumbnails"][0]["url"].split("?")[0]}, res["id"]

    async def playlist(self, url):
        playlist = self.spotify.playlist(url)
        results = [item["track"]["name"] + " " + " ".join([artist["name"] for artist in item["track"]["artists"]]) for item in playlist["tracks"]["items"]]
        return results, playlist["id"]

class AppleAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/music.apple.com\/)(.*)$"
    async def track(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        search = next((tag.get("content") for tag in soup.find_all("meta") if tag.get("property") == "og:title"), None)
        if not search: return False
        results = await VideosSearch(search, limit=1).next()
        res = results["result"][0]
        return {"title": res["title"], "link": res["link"], "vidid": res["id"], "duration_min": res["duration"], "thumb": res["thumbnails"][0]["url"].split("?")[0]}, res["id"]

class SoundAPI:
    def __init__(self):
        self.opts = {"outtmpl": "downloads/%(id)s.%(ext)s", "format": "best", "quiet": True}
    async def download(self, url):
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(self.opts).extract_info(url))
        xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
        return {"title": info["title"], "duration_sec": info["duration"], "duration_min": seconds_to_min(info["duration"]), "filepath": xyz}, xyz

class TeleAPI:
    async def get_filename(self, file, audio=False):
        return file.file_name if getattr(file, "file_name", None) else ("Telegram Audio" if audio else "Telegram Video")

    async def get_duration(self, file):
        return seconds_to_min(file.duration) if getattr(file, "duration", None) else "Unknown"

    async def get_filepath(self, audio=None, video=None):
        file = audio or video
        ext = "ogg" if isinstance(file, Voice) else (file.file_name.split(".")[-1] if getattr(file, "file_name", None) else "mp4")
        return os.path.join(os.path.realpath("downloads"), f"{file.file_unique_id}.{ext}")

    async def download(self, message, mystic, fname):
        if os.path.exists(fname): return True
        try:
            await app.download_media(message.reply_to_message, file_name=fname)
            return True
        except: return False

Spotify = SpotifyAPI()
Apple = AppleAPI()
SoundCloud = SoundAPI()
Telegram = TeleAPI()

# ====================================================================
#  4. YOUTUBE API (WITH CACHE TO PLAYLIST_ID)
# ====================================================================

class YouTubeAPI:
    def _find_file(self, vid_id):
        if not os.path.exists("downloads"): return None
        for ext in["m4a", "mp4", "mp3", "webm"]:
            filepath = f"downloads/{vid_id}.{ext}"
            if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
                return os.path.abspath(filepath)
        return None

    async def _upload_to_cache(self, vid_id, file_path, title, is_video):
        try:
            if not os.path.exists(file_path): return
            db_id = f"{vid_id}_video" if is_video else vid_id
            exists = await trackdb.find_one({"vid_id": db_id})
            if exists: return
            
            cap = f"**Song:** {title}\n**ID:** `{vid_id}`"
            msg = await app.send_video(PLAYLIST_ID, file_path, caption=cap) if is_video else await app.send_audio(PLAYLIST_ID, file_path, caption=cap, title=title)
            if msg:
                await trackdb.update_one({"vid_id": db_id}, {"$set": {"message_id": msg.id, "title": title, "type": "video" if is_video else "audio"}}, upsert=True)
        except Exception as e: LOGGER.error(f"Upload Error: {e}")

    async def get_cached_file(self, vid_id: str, is_video: bool = False):
        db_id = f"{vid_id}_video" if is_video else vid_id
        local_path = self._find_file(vid_id)
        if local_path: return local_path

        doc = await trackdb.find_one({"vid_id": db_id})
        if doc and "message_id" in doc:
            temp_path = os.path.join("downloads", f"{vid_id}.mp4")
            try:
                cached_msg = await app.get_messages(PLAYLIST_ID, doc['message_id'])
                if not cached_msg or cached_msg.empty:
                    await trackdb.delete_one({"vid_id": db_id})
                    return None
                media_file = cached_msg.video.file_id if cached_msg.video else (cached_msg.audio.file_id if cached_msg.audio else cached_msg.document.file_id)
                if media_file:
                    file = await app.download_media(media_file, file_name=temp_path)
                    if file and os.path.exists(file): return file
            except Exception as e: LOGGER.error(f"Cache Retrieval Failed: {e}")
        return None

    async def download(self, link: str, video: bool = False, title: str = None) -> tuple:
        vid_id = link.split('v=')[-1].split('&')[0] if "v=" in link else link.split('/')[-1]
        
        # 1. Check Cache
        cached_path = await self.get_cached_file(vid_id, is_video=video)
        if cached_path: return cached_path, True

        # 2. XBIT API Download
        ext = "mp4" if video else "mp3"
        file_path = os.path.join("downloads", f"{vid_id}.{ext}")
        if not os.path.exists("downloads"): os.makedirs("downloads")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{YTPROXY}/info/{vid_id}", headers={"x-api-key": YT_API_KEY}, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        api_url = data.get("video_url") if video else data.get("audio_url")
                        if api_url:
                            async with session.get(api_url) as f_resp:
                                async with aiofiles.open(file_path, mode='wb') as f:
                                    async for chunk in f_resp.content.iter_chunked(1048576):
                                        await f.write(chunk)
                            if os.path.exists(file_path):
                                asyncio.create_task(self._upload_to_cache(vid_id, file_path, title or vid_id, video))
                                return file_path, True
        except: pass

        # 3. Yt-dlp Fallback
        try:
            cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
            opts = {'format': 'best' if video else 'bestaudio', 'outtmpl': file_path, 'quiet': True, 'cookiefile': cookie_file}
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(opts).download([f"https://www.youtube.com/watch?v={vid_id}"]))
            if os.path.exists(file_path):
                asyncio.create_task(self._upload_to_cache(vid_id, file_path, title or vid_id, video))
                return file_path, True
        except: pass

        return None, False

    async def track(self, link: str):
        vid_id = link.split('v=')[-1].split('&')[0] if "v=" in link else link.split('/')[-1]
        results = await VideosSearch(f"https://www.youtube.com/watch?v={vid_id}", limit=1).next()
        res = results["result"][0]
        return {"title": res["title"], "link": res["link"], "vidid": res["id"], "duration_min": res["duration"], "thumb": res["thumbnails"][0]["url"].split("?")[0]}, res["id"]
        
    async def url(self, message: Message):
        for msg in[message, message.reply_to_message]:
            if msg and msg.entities:
                for ent in msg.entities:
                    if ent.type == MessageEntityType.URL:
                        return (msg.text or msg.caption)[ent.offset: ent.offset + ent.length]
        return None

YouTube = YouTubeAPI()

# ====================================================================
#  5. THUMBNAILS & QUEUE
# ====================================================================

async def gen_thumb(videoid, title, duration):
    try:
        if os.path.isfile(f"cache/{videoid}.png"): return f"cache/{videoid}.png"
        thumbnail_url = f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"
        
        if not os.path.exists("cache"): os.makedirs("cache")
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = youtube.resize((1280, 720))
        background = image1.convert("RGBA").filter(ImageFilter.BoxBlur(10))
        background = ImageEnhance.Brightness(background).enhance(0.5)
        draw = ImageDraw.Draw(background)

        try:
            font = ImageFont.truetype("AnshiRobot/resources/fonts/arial.ttf", 40)
            arial = ImageFont.truetype("AnshiRobot/resources/fonts/arial.ttf", 30)
        except:
            font = ImageFont.load_default()
            arial = ImageFont.load_default()

        title_text = title[:60] + "..." if len(title) > 60 else title
        draw.text((55, 560), f"PritiMusic | Now Playing", (255, 255, 255), font=arial)
        draw.text((57, 600), title_text, (255, 255, 255), font=font)
        draw.text((36, 685), "00:00", (255, 255, 255), font=arial)
        draw.text((1185, 685), str(duration), (255, 255, 255), font=arial)
        draw.line([(55, 660), (1220, 660)], fill="white", width=5, joint="curve")
        draw.ellipse([(918, 648), (942, 672)], outline="white", fill="white", width=15)

        background.save(f"cache/{videoid}.png")
        return f"cache/{videoid}.png"
    except Exception:
        return f"https://img.youtube.com/vi/{videoid}/hqdefault.jpg"

def get_markup(chat_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏸ Pause", callback_data=f"mpause_{chat_id}"),
         InlineKeyboardButton("▶️ Resume", callback_data=f"mresume_{chat_id}"),
         InlineKeyboardButton("⏹ Stop", callback_data=f"mstop_{chat_id}"),
         InlineKeyboardButton("⏭ Skip", callback_data=f"mskip_{chat_id}")],[InlineKeyboardButton("⚙️ Advanced", callback_data=f"madv_{chat_id}"),
         InlineKeyboardButton("🗑 Close", callback_data="mclose")]
    ])

def add_to_queue(chat_id, track_dict, force=False):
    if chat_id not in QUEUES: QUEUES[chat_id] = []
    if force: QUEUES[chat_id].insert(0, track_dict)
    else: QUEUES[chat_id].append(track_dict)
    return len(QUEUES[chat_id])

def clear_queue(chat_id):
    if chat_id in QUEUES: QUEUES.pop(chat_id)
    if chat_id in LOOP: LOOP.pop(chat_id)
    if chat_id in SPEED: SPEED.pop(chat_id)

async def play_next(chat_id, client):
    queue = QUEUES.get(chat_id,[])
    if not queue:
        try: await call_py.leave_group_call(chat_id)
        except: pass
        return

    data = queue[0]
    
    if LOOP.get(chat_id, 0) > 0:
        LOOP[chat_id] -= 1
    else:
        if PLAYING_STATE.get(chat_id): 
            queue.pop(0)
            if not queue:
                try: await call_py.leave_group_call(chat_id)
                except: pass
                return
            data = queue[0]

    try:
        is_video = (data["stream_type"] == "video")
        
        # Telegram File Playback
        if data["vidid"] == "telegram":
            file_path = data["link"]
        # Index/Live M3U8 URLs
        elif data["vidid"] in ["live", "index"]:
            file_path = data["link"]
        # YouTube / Standard
        else:
            file_path, _ = await YouTube.download(data["vidid"], video=is_video, title=data["title"])

        if not file_path:
            await client.send_message(chat_id, "🚫 **Failed to process track. Skipping...**")
            queue.pop(0)
            return await play_next(chat_id, client)

        spd = SPEED.get(chat_id, 1.0)
        ff_args = f"-filter:a atempo={spd}" if spd != 1.0 else ""
        
        stream = AudioVideoPiped(file_path, audio_parameters=HighQualityAudio(), video_parameters=MediumQualityVideo(), additional_ffmpeg_parameters=ff_args or None) if is_video else AudioPiped(file_path, audio_parameters=HighQualityAudio(), additional_ffmpeg_parameters=ff_args or None)

        try:
            if any(c.chat_id == chat_id for c in call_py.active_calls):
                await call_py.change_stream(chat_id, stream)
            else:
                await call_py.join_group_call(chat_id, stream, stream_type=StreamType().pulse_stream)
        except Exception as e:
            if "not in a call" in str(e).lower():
                await call_py.join_group_call(chat_id, stream)
            else: raise e

        PLAYING_STATE[chat_id] = True
        await client.send_photo(
            chat_id,
            photo=data["thumb"],
            caption=f"🎵 **Started Streaming**\n\n📌 **Title:** [{data['title']}]({data['link']})\n⏱ **Duration:** {data['dur']}\n👤 **Requested by:** {data['user']}",
            reply_markup=get_markup(chat_id)
        )
    except Exception as e:
        LOGGER.error(f"Playback Error: {e}")
        queue.pop(0)
        await play_next(chat_id, client)

if call_py:
    @call_py.on_stream_end()
    async def on_stream_end_handler(client: PyTgCalls, update: Update):
        if isinstance(update, StreamAudioEnded):
            await play_next(update.chat_id, app)

    @call_py.on_kicked()
    @call_py.on_closed_voice_chat()
    @call_py.on_left()
    async def on_kick_handler(client: PyTgCalls, chat_id: int):
        clear_queue(chat_id)

# ====================================================================
#  6. PLAY COMMANDS (SINGLE TRACK)
# ====================================================================

@app.on_message(filters.command(["play", "vplay", "playforce", "vplayforce"]))
async def play_handler(client, message: Message):
    if not call_py: return await message.reply_text("🚫 **Music Assistant is not active.**")
    
    msg = await message.reply_text("🔎 **Processing...**")
    join_status = await ensure_assistant_joined(message.chat.id)
    if join_status != True: return await msg.edit(join_status)

    is_video = "vplay" in message.command[0]
    force_play = "force" in message.command[0]
    user_mention = message.from_user.mention if message.from_user else "Admin"

    # 1. Telegram File Reply
    audio_tg = (message.reply_to_message.audio or message.reply_to_message.voice) if message.reply_to_message else None
    video_tg = (message.reply_to_message.video or message.reply_to_message.document) if message.reply_to_message else None
    
    if audio_tg or video_tg:
        file_obj = audio_tg or video_tg
        file_path = await Telegram.get_filepath(audio=audio_tg, video=video_tg)
        if await Telegram.download(message, msg, file_path):
            title = await Telegram.get_filename(file_obj, audio=bool(audio_tg))
            dur = await Telegram.get_duration(file_obj)
            thumb = "https://files.catbox.moe/4oez30.jpg"
            track_data = {"title": title, "link": file_path, "vidid": "telegram", "user": user_mention, "dur": dur, "thumb": thumb, "stream_type": "video" if video_tg else "audio"}
            
            pos = add_to_queue(message.chat.id, track_data, force=force_play)
            if pos == 1 or force_play:
                await msg.delete()
                if force_play: PLAYING_STATE[message.chat.id] = False
                await play_next(message.chat.id, client)
            else:
                await msg.edit(f"✅ **Added to Queue at #{pos}**\n🏷 **Title:** {title}")
        return

    # 2. URL or Query
    url = await YouTube.url(message)
    query = message.text.split(None, 1)[1] if len(message.command) > 1 else url

    if not query:
        return await msg.edit("💡 **Usage:** `/play <song name/link/reply to audio>`")

    try:
        if "open.spotify.com" in query:
            details, track_id = await Spotify.track(query)
        elif "music.apple.com" in query:
            details, track_id = await Apple.track(query)
        elif "soundcloud.com" in query:
            details, track_path = await SoundCloud.download(query)
            track_data = {"title": details["title"], "link": track_path, "vidid": "telegram", "user": user_mention, "dur": details["duration_min"], "thumb": "https://files.catbox.moe/4oez30.jpg", "stream_type": "audio"}
            pos = add_to_queue(message.chat.id, track_data, force=force_play)
            if pos == 1 or force_play:
                await msg.delete()
                if force_play: PLAYING_STATE[message.chat.id] = False
                return await play_next(message.chat.id, client)
            return await msg.edit(f"✅ **Added to Queue at #{pos}**")
        elif "m3u8" in query or "index" in query.lower():
            track_data = {"title": "Live Stream / M3U8", "link": query, "vidid": "live", "user": user_mention, "dur": "Live", "thumb": "https://files.catbox.moe/4oez30.jpg", "stream_type": "video" if is_video else "audio"}
            pos = add_to_queue(message.chat.id, track_data, force=force_play)
            if pos == 1 or force_play:
                await msg.delete()
                if force_play: PLAYING_STATE[message.chat.id] = False
                return await play_next(message.chat.id, client)
            return await msg.edit(f"✅ **Added to Queue at #{pos}**")
        else:
            details, track_id = await YouTube.track(query)

        title = details["title"]
        vidid = details["vidid"]
        duration = details["duration_min"]
        link = details["link"]
        
        thumb_path = await gen_thumb(vidid, title, duration)

        track_data = {
            "title": title, "link": link, "vidid": vidid,
            "user": user_mention, "dur": duration, "thumb": thumb_path,
            "stream_type": "video" if is_video else "audio"
        }

        pos = add_to_queue(message.chat.id, track_data, force=force_play)
        
        if pos == 1 or force_play:
            await msg.delete()
            if force_play: PLAYING_STATE[message.chat.id] = False
            await play_next(message.chat.id, client)
        else:
            await msg.delete()
            await message.reply_photo(
                photo=thumb_path,
                caption=f"✅ **Added to Queue at #{pos}**\n\n🏷 **Title:** {title[:40]}\n⏱ **Duration:** {duration}\n👤 **Requested by:** {user_mention}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="mclose")]])
            )

    except Exception as e:
        LOGGER.error(f"Play Error: {e}")
        await msg.edit(f"❌ **Error:** {str(e)}")


# ====================================================================
#  7. PLAYLIST & MIX COMMAND (/mplay)
# ====================================================================

@app.on_message(filters.command(["mplay", "vplaymix", "mplayforce", "vplaymixforce"]))
async def mplay_handler(client, message: Message):
    if not call_py: return await message.reply_text("🚫 **Music Assistant is not active.**")
    
    msg = await message.reply_text("🔍 **Analyzing Mix/Playlist...**")
    join_status = await ensure_assistant_joined(message.chat.id)
    if join_status != True: return await msg.edit(join_status)

    is_video = "vplay" in message.command[0]
    force_play = "force" in message.command[0]
    user_mention = message.from_user.mention if message.from_user else "Admin"

    query = message.text.split(None, 1)[1] if len(message.command) > 1 else None
    if not query:
        return await msg.edit("💡 **Usage:** `/mplay <song name or youtube link>`\n_Fetches an Auto-Mix of 30 songs and adds them to queue._")

    try:
        vidid = None
        mix_url = query
        
        if not ("youtube.com" in query or "youtu.be" in query):
            search = await asyncio.get_event_loop().run_in_executor(None, lambda: VideosSearch(query, limit=1).result())
            if not search["result"]:
                return await msg.edit("❌ **No results found.**")
            vidid = search["result"][0]["id"]
            mix_url = f"https://www.youtube.com/watch?v={vidid}&list=RD{vidid}"
        else:
            if "list=" not in query:
                match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", query)
                if match:
                    vidid = match.group(1)
                    mix_url = f"https://www.youtube.com/watch?v={vidid}&list=RD{vidid}"
                else:
                    mix_url = query

        # Extract Playlist using yt-dlp (Limited to 30 songs to avoid spam)
        opts = {'quiet': True, 'skip_download': True, 'extract_flat': True, 'playlistend': 30}
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(opts).extract_info(mix_url, download=False))
        
        if not info or 'entries' not in info:
            return await msg.edit("❌ **Failed to fetch mix/playlist.**")

        entries = [e for e in info['entries'] if e]
        if not entries:
            return await msg.edit("❌ **Playlist is empty.**")

        added_count = 0
        if force_play:
            clear_queue(message.chat.id)
            PLAYING_STATE[message.chat.id] = False

        for i, entry in enumerate(entries):
            track_vidid = entry.get('id')
            if not track_vidid: continue
            
            track_title = entry.get('title', 'Unknown Title')
            track_duration = seconds_to_min(entry.get('duration', 0))
            track_link = entry.get('url') or f"https://www.youtube.com/watch?v={track_vidid}"
            
            # Fast thumbnail mapping: only generate real thumb for the very first item
            if i == 0:
                track_thumb = await gen_thumb(track_vidid, track_title, track_duration)
            else:
                track_thumb = f"https://img.youtube.com/vi/{track_vidid}/hqdefault.jpg"

            track_data = {
                "title": track_title, "link": track_link, "vidid": track_vidid,
                "user": user_mention, "dur": track_duration, "thumb": track_thumb,
                "stream_type": "video" if is_video else "audio"
            }

            add_to_queue(message.chat.id, track_data, force=(force_play and i == 0))
            added_count += 1

        if added_count > 0:
            await msg.delete()
            await message.reply_text(f"🔀 **Added {added_count} tracks from Mix/Playlist to Queue!**\n👤 **Requested by:** {user_mention}")
            
            if force_play or not PLAYING_STATE.get(message.chat.id):
                await play_next(message.chat.id, client)
        else:
            await msg.edit("❌ **Could not extract tracks from this mix.**")

    except Exception as e:
        LOGGER.error(f"Mix Play Error: {e}")
        await msg.edit(f"❌ **Error:** {str(e)}")


# ====================================================================
#  8. ADMIN CONTROLS & COMMANDS
# ====================================================================

@app.on_message(filters.command(["stop", "end"]))
@AdminRightsCheck
async def stop_handler(client, message: Message):
    chat_id = message.chat.id
    clear_queue(chat_id)
    try:
        await call_py.leave_group_call(chat_id)
        await message.reply_text("⏹️ **Stream Ended & Queue Cleared.**")
    except: await message.reply_text("⚠️ **Nothing is playing.**")

@app.on_message(filters.command(["skip", "next"]))
@AdminRightsCheck
async def skip_handler(client, message: Message):
    chat_id = message.chat.id
    if QUEUES.get(chat_id):
        PLAYING_STATE[chat_id] = False
        await message.reply_text("⏭️ **Track Skipped.**")
        await play_next(chat_id, client)
    else: await message.reply_text("⚠️ **Queue is empty.**")

@app.on_message(filters.command("pause"))
@AdminRightsCheck
async def pause_handler(client, message: Message):
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply_text("⏸ **Stream Paused.**")
    except: await message.reply_text("⚠️ **Nothing is currently playing.**")

@app.on_message(filters.command("resume"))
@AdminRightsCheck
async def resume_handler(client, message: Message):
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply_text("▶️ **Stream Resumed.**")
    except: await message.reply_text("⚠️ **Stream is not paused.**")

@app.on_message(filters.command("queue"))
async def queue_handler(client, message: Message):
    queue = QUEUES.get(message.chat.id,[])
    if not queue: return await message.reply_text("📭 **Queue is empty.**")
    text = "**📂 Current Queue:**\n\n"
    for i, track in enumerate(queue[:20]): # Show up to 20 to avoid message length limits
        text += f"**{i+1}.** [{track['title'][:40]}]({track['link']}) | `{track['dur']}`\n"
    if len(queue) > 20: text += f"\n*...and {len(queue) - 20} more tracks.*"
    await message.reply_text(text, disable_web_page_preview=True)

@app.on_message(filters.command("loop"))
@AdminRightsCheck
async def loop_handler(client, message: Message):
    if len(message.command) < 2: return await message.reply_text("💡 **Usage:** `/loop <1-10>` or `/loop disable`")
    val = message.command[1].lower()
    if val in["disable", "0"]:
        if message.chat.id in LOOP: LOOP.pop(message.chat.id)
        return await message.reply_text("🔁 **Loop disabled.**")
    if val.isdigit() and 1 <= int(val) <= 10:
        LOOP[message.chat.id] = int(val)
        await message.reply_text(f"🔁 **Loop enabled for {val} times.**")
    else: await message.reply_text("❌ **Please provide a number between 1 and 10.**")

@app.on_message(filters.command("shuffle"))
@AdminRightsCheck
async def shuffle_handler(client, message: Message):
    queue = QUEUES.get(message.chat.id,[])
    if len(queue) > 2:
        current, rest = queue[0], queue[1:]
        random.shuffle(rest)
        QUEUES[message.chat.id] = [current] + rest
        await message.reply_text("🔀 **Queue Shuffled Successfully.**")
    else: await message.reply_text("⚠️ **Not enough tracks in queue to shuffle.**")

@app.on_message(filters.command("speed"))
@AdminRightsCheck
async def speed_handler(client, message: Message):
    chat_id = message.chat.id
    if not QUEUES.get(chat_id): return await message.reply_text("⚠️ **Nothing is playing.**")
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("0.5x", callback_data=f"mspd_0.5_{chat_id}"), InlineKeyboardButton("0.75x", callback_data=f"mspd_0.75_{chat_id}")],[InlineKeyboardButton("1.0x (Normal)", callback_data=f"mspd_1.0_{chat_id}")],[InlineKeyboardButton("1.5x", callback_data=f"mspd_1.5_{chat_id}"), InlineKeyboardButton("2.0x", callback_data=f"mspd_2.0_{chat_id}")]])
    await message.reply_text("⏩ **Select Playback Speed:**", reply_markup=buttons)

@app.on_message(filters.command("seek"))
@AdminRightsCheck
async def seek_handler(client, message: Message):
    chat_id = message.chat.id
    queue = QUEUES.get(chat_id,[])
    if not queue: return await message.reply_text("⚠️ **Nothing is playing.**")
    if len(message.command) < 2: return await message.reply_text("💡 **Usage:** `/seek 30` (Seeks to 30 seconds)")
    try:
        seek_sec = int(message.command[1])
        file_path, _ = await YouTube.download(queue[0]["vidid"])
        if file_path:
             stream = AudioPiped(file_path, audio_parameters=HighQualityAudio(), additional_ffmpeg_parameters=f"-ss {seek_sec}")
             await call_py.change_stream(chat_id, stream)
             await message.reply_text(f"⏩ **Seeked to {seek_sec} seconds.**")
    except Exception as e: await message.reply_text(f"❌ **Failed to seek:** {e}")

@app.on_message(filters.command("mstart"))
async def music_start(client, message: Message):
    await message.reply_photo(
        photo="https://files.catbox.moe/d95om6.jpg",
        caption=f"🎵 **{app.me.first_name} Music System Online!**\n\nI can play music in Voice Chats from YouTube, Spotify, Apple Music, Telegram, and more!\n\nUse /mhelp to see all commands."
    )

@app.on_message(filters.command("mhelp"))
async def music_help(client, message: Message):
    await message.reply_text(
        "🎧 **Music Commands:**\n\n"
        "• `/play <song/url>` - Play audio.\n"
        "• `/vplay <video/url>` - Play video.\n"
        "• `/mplay <song/url>` - 🔀 **Auto-Mix! Play 30 songs related to your search.**\n"
        "• `/playforce` / `/vplayforce` - Force play instantly.\n"
        "• `/pause` - Pause stream.\n"
        "• `/resume` - Resume stream.\n"
        "• `/skip` - Skip to next track.\n"
        "• `/stop` - Clear queue and end stream.\n"
        "• `/queue` - Check queued tracks.\n"
        "• `/loop <1-10>` - Loop current track.\n"
        "• `/shuffle` - Shuffle queue.\n"
        "• `/speed` - Adjust playback speed.\n"
        "• `/seek <seconds>` - Seek track."
    )

# ====================================================================
#  9. INLINE CALLBACKS
# ====================================================================

@app.on_callback_query(filters.regex(r"^m"))
async def music_callbacks(client, query: CallbackQuery):
    data = query.data
    if data == "mclose": return await query.message.delete()

    chat_id = query.message.chat.id
    try:
        user = await client.get_chat_member(chat_id, query.from_user.id)
        if user.status not in[ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and query.from_user.id != Config.OWNER_ID:
            return await query.answer("❌ Admins only.", show_alert=True)
    except: return

    if data.startswith("mstop_"):
        clear_queue(chat_id)
        try: await call_py.leave_group_call(chat_id)
        except: pass
        await query.message.edit_text("⏹️ **Stream Stopped.**")
        
    elif data.startswith("mpause_"):
        try: await call_py.pause_stream(chat_id)
        except: pass
        await query.answer("Paused", show_alert=True)
        
    elif data.startswith("mresume_"):
        try: await call_py.resume_stream(chat_id)
        except: pass
        await query.answer("Resumed", show_alert=True)
        
    elif data.startswith("mskip_"):
        queue = QUEUES.get(chat_id,[])
        if len(queue) > 0:
            PLAYING_STATE[chat_id] = False
            await query.message.delete()
            await play_next(chat_id, client)
        else:
            clear_queue(chat_id)
            try: await call_py.leave_group_call(chat_id)
            except: pass
            await query.message.edit_text("⏹️ **Queue Ended.**")
            
    elif data.startswith("madv_"):
        adv_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔀 Shuffle", callback_data=f"mshuf_{chat_id}"), InlineKeyboardButton("🔁 Loop", callback_data=f"mloop_{chat_id}")],[InlineKeyboardButton("⏩ Speed", callback_data=f"mspeedmenu_{chat_id}")],[InlineKeyboardButton("🔙 Back", callback_data=f"mback_{chat_id}")]])
        await query.message.edit_reply_markup(reply_markup=adv_markup)
        
    elif data.startswith("mback_"):
        await query.message.edit_reply_markup(reply_markup=get_markup(chat_id))
        
    elif data.startswith("mshuf_"):
        queue = QUEUES.get(chat_id,[])
        if len(queue) > 2:
            current, rest = queue[0], queue[1:]
            random.shuffle(rest)
            QUEUES[chat_id] =[current] + rest
            await query.answer("Queue Shuffled!", show_alert=True)
        else: await query.answer("Not enough tracks.", show_alert=True)
            
    elif data.startswith("mloop_"):
        LOOP[chat_id] = 3 
        await query.answer("Loop enabled (3x)!", show_alert=True)
        
    elif data.startswith("mspeedmenu_"):
        speed_markup = InlineKeyboardMarkup([[InlineKeyboardButton("0.5x", callback_data=f"mspd_0.5_{chat_id}"), InlineKeyboardButton("0.75x", callback_data=f"mspd_0.75_{chat_id}")],[InlineKeyboardButton("1.0x", callback_data=f"mspd_1.0_{chat_id}"), InlineKeyboardButton("1.5x", callback_data=f"mspd_1.5_{chat_id}")],[InlineKeyboardButton("🔙 Back", callback_data=f"madv_{chat_id}")]])
        await query.message.edit_reply_markup(reply_markup=speed_markup)
        
    elif data.startswith("mspd_"):
        spd = float(data.split("_")[1])
        SPEED[chat_id] = spd
        queue = QUEUES.get(chat_id,[])
        if queue:
            try:
                file_path, _ = await YouTube.download(queue[0]["vidid"])
                if file_path:
                    ff_args = f"-filter:a atempo={spd}" if spd != 1.0 else ""
                    stream = AudioPiped(file_path, audio_parameters=HighQualityAudio(), additional_ffmpeg_parameters=ff_args or None)
                    await call_py.change_stream(chat_id, stream)
                    await query.answer(f"Speed set to {spd}x", show_alert=True)
            except Exception: await query.answer("Failed to change speed.", show_alert=True)

if call_py:
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(get_assistant_details())
        if not call_py.is_running:
            loop.create_task(call_py.start())
    except RuntimeError: pass

