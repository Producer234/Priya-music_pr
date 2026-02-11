import threading
from AnshiRobot.modules.sql import BASE

BLACKLIST = BASE["blacklist"]
BLACKLIST_SETTINGS = BASE["blacklist_settings"]
LOCK = threading.RLock()
CHAT_BLACKLISTS = {}

def add_to_blacklist(chat_id, trigger):
    with LOCK:
        BLACKLIST.update_one(
            {"chat_id": str(chat_id), "trigger": trigger},
            {"$set": {"trigger": trigger}},
            upsert=True
        )
        if str(chat_id) not in CHAT_BLACKLISTS:
            CHAT_BLACKLISTS[str(chat_id)] = set()
        CHAT_BLACKLISTS[str(chat_id)].add(trigger)

def rm_from_blacklist(chat_id, trigger):
    with LOCK:
        res = BLACKLIST.delete_one({"chat_id": str(chat_id), "trigger": trigger})
        if res.deleted_count > 0:
            if str(chat_id) in CHAT_BLACKLISTS and trigger in CHAT_BLACKLISTS[str(chat_id)]:
                CHAT_BLACKLISTS[str(chat_id)].remove(trigger)
            return True
        return False

def get_chat_blacklist(chat_id):
    return CHAT_BLACKLISTS.get(str(chat_id), set())

def num_blacklist_filters():
    return BLACKLIST.count_documents({})

def num_blacklist_filter_chats():
    return len(BLACKLIST.distinct("chat_id"))

def set_blacklist_strength(chat_id, blacklist_type, value):
    with LOCK:
        BLACKLIST_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"type": int(blacklist_type), "value": str(value)}},
            upsert=True
        )

def get_blacklist_setting(chat_id):
    setting = BLACKLIST_SETTINGS.find_one({"chat_id": str(chat_id)})
    if setting:
        return setting["type"], setting["value"]
    return 1, "0"

def __load_chat_blacklists():
    global CHAT_BLACKLISTS
    try:
        for x in BLACKLIST.find():
            if x["chat_id"] not in CHAT_BLACKLISTS:
                CHAT_BLACKLISTS[x["chat_id"]] = set()
            CHAT_BLACKLISTS[x["chat_id"]].add(x["trigger"])
    except:
        pass

__load_chat_blacklists()