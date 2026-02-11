import threading
from AnshiRobot.modules.sql import BASE

STICKERS = BASE["blacklist_stickers"]
STICKER_SETTINGS = BASE["blsticker_settings"]
LOCK = threading.RLock()
CHAT_STICKERS = {}

def add_to_stickers(chat_id, trigger):
    with LOCK:
        STICKERS.update_one(
            {"chat_id": str(chat_id), "trigger": trigger},
            {"$set": {"trigger": trigger}},
            upsert=True
        )
        if str(chat_id) not in CHAT_STICKERS:
            CHAT_STICKERS[str(chat_id)] = set()
        CHAT_STICKERS[str(chat_id)].add(trigger)

def rm_from_stickers(chat_id, trigger):
    with LOCK:
        res = STICKERS.delete_one({"chat_id": str(chat_id), "trigger": trigger})
        if res.deleted_count > 0:
            if str(chat_id) in CHAT_STICKERS and trigger in CHAT_STICKERS[str(chat_id)]:
                CHAT_STICKERS[str(chat_id)].remove(trigger)
            return True
        return False

def get_chat_stickers(chat_id):
    return CHAT_STICKERS.get(str(chat_id), set())

def num_stickers_filters():
    return STICKERS.count_documents({})

def num_stickers_filter_chats():
    return len(STICKERS.distinct("chat_id"))

def set_blacklist_strength(chat_id, blacklist_type, value):
    with LOCK:
        STICKER_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"type": int(blacklist_type), "value": str(value)}},
            upsert=True
        )

def get_blacklist_setting(chat_id):
    setting = STICKER_SETTINGS.find_one({"chat_id": str(chat_id)})
    if setting:
        return setting["type"], setting["value"]
    return 1, "0"

def __load_stickers():
    global CHAT_STICKERS
    try:
        for x in STICKERS.find():
            if x["chat_id"] not in CHAT_STICKERS:
                CHAT_STICKERS[x["chat_id"]] = set()
            CHAT_STICKERS[x["chat_id"]].add(x["trigger"])
    except:
        pass

__load_stickers()