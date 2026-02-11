import threading
from AnshiRobot.modules.sql import BASE

FLOOD_SETTINGS = BASE["antiflood_settings"]
INSERTION_LOCK = threading.RLock()

# In-memory cache for flood counting (same as SQL version logic)
CHAT_FLOOD = {}
DEF_COUNT = 1
DEF_LIMIT = 0
DEF_OBJ = (None, DEF_COUNT, DEF_LIMIT)

def set_flood(chat_id, amount):
    with INSERTION_LOCK:
        # In Mongo, we only persist the setting if necessary, 
        # but standard logic keeps count in memory and limit in DB if needed.
        # For compatibility, we update the limit in memory.
        CHAT_FLOOD[str(chat_id)] = (None, DEF_COUNT, amount)
        # We save the limit to DB so it persists restarts
        FLOOD_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"limit": amount}},
            upsert=True
        )

def update_flood(chat_id: str, user_id) -> bool:
    if str(chat_id) in CHAT_FLOOD:
        curr_user_id, count, limit = CHAT_FLOOD.get(str(chat_id), DEF_OBJ)

        if limit == 0:
            return False

        if user_id != curr_user_id or user_id is None:
            CHAT_FLOOD[str(chat_id)] = (user_id, DEF_COUNT, limit)
            return False

        count += 1
        if count > limit:
            CHAT_FLOOD[str(chat_id)] = (None, DEF_COUNT, limit)
            return True

        CHAT_FLOOD[str(chat_id)] = (user_id, count, limit)
        return False

def get_flood_limit(chat_id):
    return CHAT_FLOOD.get(str(chat_id), DEF_OBJ)[2]

def set_flood_strength(chat_id, flood_type, value):
    with INSERTION_LOCK:
        FLOOD_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"flood_type": int(flood_type), "value": str(value)}},
            upsert=True
        )

def get_flood_setting(chat_id):
    setting = FLOOD_SETTINGS.find_one({"chat_id": str(chat_id)})
    if setting:
        return setting.get("flood_type", 1), setting.get("value", "0")
    return 1, "0"

def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        FLOOD_SETTINGS.update_one(
            {"chat_id": str(old_chat_id)},
            {"$set": {"chat_id": str(new_chat_id)}}
        )
        if str(old_chat_id) in CHAT_FLOOD:
            CHAT_FLOOD[str(new_chat_id)] = CHAT_FLOOD[str(old_chat_id)]
            del CHAT_FLOOD[str(old_chat_id)]

def __load_flood_settings():
    global CHAT_FLOOD
    try:
        all_chats = FLOOD_SETTINGS.find()
        for chat in all_chats:
            if "limit" in chat:
                CHAT_FLOOD[chat["chat_id"]] = (None, DEF_COUNT, chat["limit"])
    except:
        pass

__load_flood_settings()