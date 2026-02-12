from os import getenv

class Config(object):
    LOGGER = True

    ANILIST_CLIENT = getenv("ANILIST_CLIENT", "8679")
    ANILIST_SECRET = getenv("ANILIST_SECRET", "NeCEq9A1hVnjsjZlTZyNvqK11krQ4HtSliaM7rTN")
    API_ID = getenv("API_ID", None)
    API_HASH = getenv("API_HASH", None)
    TOKEN = getenv("TOKEN", None)
    STRING_SESSION = getenv("STRING_SESSION", None)
    OWNER_ID = getenv("OWNER_ID", "7291963092") 
    OWNER_USERNAME = getenv("OWNER_USERNAME", "GAYATRIxANAND")
    SUPPORT_CHAT = getenv("SUPPORT_CHAT", "Unique_society")
    START_IMG = getenv("START_IMG", "https://graph.org/file/eaa3a2602e43844a488a5.jpg")
    JOIN_LOGGER = getenv("JOIN_LOGGER", "-1002362839740")
    EVENT_LOGS = getenv("EVENT_LOGS",  "-1002362839740")
    ERROR_LOGS = getenv("ERROR_LOGS", "-1002362839740")
    MONGO_DB_URI = getenv("MONGO_DB_URI", None)
    LOG_CHANNEL = getenv("LOG_CHANNEL", "-1002362839740")
    BOT_USERNAME = getenv("BOT_USERNAME" , "AnshiRobot")
    DATABASE_URL = getenv("DATABASE_URL", None)
    CASH_API_KEY = getenv("CASH_API_KEY", "V48U2FLLKRHSVD4X")
    TIME_API_KEY = getenv("TIME_API_KEY", "1CUBX1HXGNHW")
    SPAMWATCH_API = getenv("SPAMWATCH_API", "3624487efd8e4ca9c949f1ab99654ad1e4de854f41a14afd00f3ca82d808dc8c")
    SPAMWATCH_SUPPORT_CHAT = getenv("SPAMWATCH_SUPPORT_CHAT", "h_cc_help")
    WALL_API = getenv("WALL_API", "2455acab48f3a935a8e703e54e26d121")
    REM_BG_API_KEY = getenv("REM_BG_API_KEY", "xYCR1ZyK3ZsofjH7Y6hPcyzC")
    OPENWEATHERMAP_ID = getenv("OPENWEATHERMAP_ID", "887da2c60d9f13fe78b0f9d0c5cbaade")
    BAN_STICKER = getenv("BAN_STICKER", "CAACAgEAAxkBAAIrTWYljyX_lqcubkAzg0jy45CRvxAFAAKvAgACrLHoRU50VVvh3xWwNAQ")
    HEROKU_APP_NAME = getenv("HEROKU_APP_NAME", None)
    HEROKU_API_KEY = getenv("HEROKU_API_KEY", None)
    LASTFM_API_KEY = getenv("LASTFM_API_KEY", "8f3315b5806c21004b2822f07825187d")

    # Optional fields
    BL_CHATS = []
    DRAGONS = []
    DEV_USERS = []
    DEMONS = []
    TIGERS = []
    WOLVES = []

    ALLOW_CHATS = True
    ALLOW_EXCL = True
    DEL_CMDS = True
    INFOPIC = True
    LOAD = []
    NO_LOAD = []
    STRICT_GBAN = True
    TEMP_DOWNLOAD_DIRECTORY = "./"
    WORKERS = 8

class Production(Config):
    LOGGER = True

class Development(Config):
    LOGGER = True
