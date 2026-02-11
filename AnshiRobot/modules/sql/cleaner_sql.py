import threading
from AnshiRobot.modules.sql import BASE

CLEANER = BASE["cleaner"]
LOCK = threading.RLock()
CLEANER_CHATS = {}

def set_cleanbt(chat_id, is_enable):
    with LOCK:
        CLEANER.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"is_enable": is_enable}},
            upsert=True
        )
        if str(chat_id) not in CLEANER_CHATS: CLEANER_CHATS[str(chat_id)] = {}
        CLEANER_CHATS[str(chat_id)]["setting"] = is_enable

def is_enabled(chat_id):
    return CLEANER_CHATS.get(str(chat_id), {}).get("setting", False)

# Minimal implementation of cleaning to prevent errors
def __load():
    try:
        for x in CLEANER.find():
            CLEANER_CHATS[x["chat_id"]] = {"setting": x.get("is_enable", False)}
    except: pass
__load()