import logging
import os
import sys
import time
import ast
import base64
import asyncio 
import socket
from SafoneAPI import SafoneAPI
import telegram.ext as tg
from aiohttp import ClientSession
from pyrogram import Client, errors
from telethon import TelegramClient

# --- AGGRESSIVE NETWORK FIX FOR DOCKER/HUGGINGFACE ---
# If DNS fails, force resolve api.telegram.org to its known IPs.
original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'api.telegram.org':
        # Try normal resolution first
        try:
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            # If it fails, use known Telegram API IPs
            logging.warning("DNS resolution failed for api.telegram.org. Using fallback IPs.")
            # 149.154.167.220 is a primary Telegram API IP
            return[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('149.154.167.220', port))]
    
    # For all other hosts, use the default behavior but force IPv4 to avoid IPv6 docker routing issues
    try:
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except socket.gaierror as e:
        # Fallback to default if AF_INET force fails
        return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo
# -----------------------------------------------------

StartTime = time.time()

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("telethon").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

api = SafoneAPI()
# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    LOGGER.error(
        "You MUST have a python version of at least 3.6! Multiple features depend on this. Bot quitting."
    )
    sys.exit(1)

ENV = bool(os.environ.get("ENV", False))

if ENV:

    API_ID = int(os.environ.get("API_ID", None))
    API_HASH = os.environ.get("API_HASH", None)
    
    ALLOW_CHATS = os.environ.get("ALLOW_CHATS", True)
    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)
    CASH_API_KEY = os.environ.get("CASH_API_KEY", None)
    DB_URI = os.environ.get("DATABASE_URL")
    DEL_CMDS = bool(os.environ.get("DEL_CMDS", False))
    EVENT_LOGS = os.environ.get("EVENT_LOGS", None)
    INFOPIC = bool(os.environ.get("INFOPIC", "True"))
    LOAD = os.environ.get("LOAD", "").split()
    MONGO_DB_URI = os.environ.get("MONGO_DB_URI", None)
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
    START_IMG = os.environ.get(
        "START_IMG", ""
    )
    STRICT_GBAN = bool(os.environ.get("STRICT_GBAN", True))
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "the_friendz")
    TEMP_DOWNLOAD_DIRECTORY = os.environ.get("TEMP_DOWNLOAD_DIRECTORY", "./")
    TOKEN = os.environ.get("TOKEN", None)
    TIME_API_KEY = os.environ.get("TIME_API_KEY", None)
    WORKERS = int(os.environ.get("WORKERS", 8))
    WALL_API = os.environ.get("WALL_API", None)
    LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", None)

    try:
        OWNER_ID = int(os.environ.get("OWNER_ID", None))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME", None)
        LOG_CHANNEL = os.environ.get("LOG_CHANNEL", None)
        HEROKU_API_KEY = os.environ.get("HEROKU_API_KEY", None)
    except ValueError:
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    try:
        BL_CHATS = set(int(x) for x in os.environ.get("BL_CHATS", "").split())
    except ValueError:
        raise Exception("Your blacklisted chats list does not contain valid integers.")

    try:
        DRAGONS = set(int(x) for x in os.environ.get("DRAGONS", "7753899951").split())
        DEV_USERS = set(int(x) for x in os.environ.get("DEV_USERS", "7753899951").split())
    except ValueError:
        raise Exception("Your sudo or dev users list does not contain valid integers.")

    try:
        DEMONS = set(int(x) for x in os.environ.get("DEMONS", "7753899951").split())
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        TIGERS = set(int(x) for x in os.environ.get("TIGERS", "7753899951").split())
    except ValueError:
        raise Exception("Your tiger users list does not contain valid integers.")

    try:
        WOLVES = set(int(x) for x in os.environ.get("WOLVES", "7753899951").split())
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")

else:
    from AnshiRobot.config import Development as Config

    API_ID = Config.API_ID
    API_HASH = Config.API_HASH
    ALLOW_CHATS = Config.ALLOW_CHATS
    ALLOW_EXCL = Config.ALLOW_EXCL
    CASH_API_KEY = Config.CASH_API_KEY
    DB_URI = Config.DATABASE_URL
    DEL_CMDS = Config.DEL_CMDS
    EVENT_LOGS = Config.EVENT_LOGS
    INFOPIC = Config.INFOPIC
    LOAD = Config.LOAD
    MONGO_DB_URI = Config.MONGO_DB_URI
    NO_LOAD = Config.NO_LOAD
    START_IMG = Config.START_IMG
    STRICT_GBAN = Config.STRICT_GBAN
    SUPPORT_CHAT = Config.SUPPORT_CHAT
    TEMP_DOWNLOAD_DIRECTORY = Config.TEMP_DOWNLOAD_DIRECTORY
    TOKEN = Config.TOKEN
    TIME_API_KEY = Config.TIME_API_KEY
    WALL_API = Config.WALL_API
    WORKERS = Config.WORKERS
    LOG_CHANNEL = Config.LOG_CHANNEL
    LASTFM_API_KEY = Config.LASTFM_API_KEY

    try:
        OWNER_ID = int(Config.OWNER_ID)
    except ValueError:
        raise Exception("Your OWNER_ID variable is not a valid integer.")

    try:
        BL_CHATS = set(int(x) for x in Config.BL_CHATS or[])
    except ValueError:
        raise Exception("Your blacklisted chats list does not contain valid integers.")

    try:
        DRAGONS = set(int(x) for x in Config.DRAGONS or[])
        DEV_USERS = set(int(x) for x in Config.DEV_USERS or[])
    except ValueError:
        raise Exception("Your sudo or dev users list does not contain valid integers.")

    try:
        DEMONS = set(int(x) for x in Config.DEMONS or[])
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        TIGERS = set(int(x) for x in Config.TIGERS or[])
    except ValueError:
        raise Exception("Your tiger users list does not contain valid integers.")

    try:
        WOLVES = set(int(x) for x in Config.WOLVES or[])
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")


DRAGONS.add(OWNER_ID)
DEV_USERS.add(OWNER_ID)

# Define custom request kwargs to prevent timeout crashes on startup
request_kwargs = {
    'read_timeout': 30.0,
    'connect_timeout': 30.0,
    'con_pool_size': 8
}

print("[INFO]: Getting Bot Info...")

# --- STARTUP RETRY MECHANISM ---
# We wrap the updater initialization in a retry block because it calls getMe() internally
max_retries = 10
updater = None
for attempt in range(max_retries):
    try:
        updater = tg.Updater(TOKEN, workers=WORKERS, use_context=True, request_kwargs=request_kwargs)
        dispatcher = updater.dispatcher
        BOT_ID = dispatcher.bot.id
        BOT_NAME = dispatcher.bot.first_name
        BOT_USERNAME = dispatcher.bot.username
        LOGGER.info(f"Successfully connected to Telegram as {BOT_NAME}!")
        break
    except Exception as e:
        LOGGER.warning(f"Network error on startup, retrying in 5 seconds... ({attempt+1}/{max_retries}) | Error: {e}")
        time.sleep(5)
else:
    LOGGER.error("Failed to connect to Telegram API after multiple attempts. Exiting.")
    sys.exit(1)
# -------------------------------

telethn = TelegramClient("Anshi", API_ID, API_HASH)

pbot = Client("AnshiRobot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN,in_memory=True)


# FIX: Initialize Event Loop and pass it to ClientSession safely
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Explicitly passing loop avoids the "no running event loop" error
aiohttpsession = ClientSession(loop=loop)

DRAGONS = list(DRAGONS) + list(DEV_USERS) 
DEV_USERS = list(DEV_USERS)
WOLVES = list(WOLVES)
DEMONS = list(DEMONS)
TIGERS = list(TIGERS)

# Load at end to ensure all prev variables have been set
from AnshiRobot.modules.helper_funcs.handlers import (
    CustomCommandHandler,
    CustomMessageHandler,
    CustomRegexHandler,
)

# make sure the regex handler can take extra kwargs
tg.RegexHandler = CustomRegexHandler
tg.CommandHandler = CustomCommandHandler
tg.MessageHandler = CustomMessageHandler
