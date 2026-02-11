import threading
from AnshiRobot.modules.sql import BASE

WARNS = BASE["warns"]
WARN_FILTERS = BASE["warn_filters"]
WARN_SETTINGS = BASE["warn_settings"]
LOCK = threading.RLock()
FILTER_CACHE = {}

class WarnFilterObj:
    def __init__(self, data):
        self.keyword = data["keyword"]
        self.reply = data["reply"]

def warn_user(user_id, chat_id, reason=None):
    with LOCK:
        warn = WARNS.find_one({"user_id": int(user_id), "chat_id": str(chat_id)})
        reasons = warn["reasons"] if warn else []
        if reason:
            reasons.append(reason)
        num_warns = (warn["num_warns"] if warn else 0) + 1
        
        WARNS.update_one(
            {"user_id": int(user_id), "chat_id": str(chat_id)},
            {"$set": {"num_warns": num_warns, "reasons": reasons}},
            upsert=True
        )
        return num_warns, reasons

def remove_warn(user_id, chat_id):
    with LOCK:
        warn = WARNS.find_one({"user_id": int(user_id), "chat_id": str(chat_id)})
        if warn and warn["num_warns"] > 0:
            num = warn["num_warns"] - 1
            reasons = warn["reasons"][:-1]
            WARNS.update_one(
                {"user_id": int(user_id), "chat_id": str(chat_id)},
                {"$set": {"num_warns": num, "reasons": reasons}}
            )
            return True
        return False

def reset_warns(user_id, chat_id):
    with LOCK:
        WARNS.delete_one({"user_id": int(user_id), "chat_id": str(chat_id)})

def get_warns(user_id, chat_id):
    warn = WARNS.find_one({"user_id": int(user_id), "chat_id": str(chat_id)})
    if warn:
        return warn["num_warns"], warn["reasons"]
    return None

def add_warn_filter(chat_id, keyword, reply):
    with LOCK:
        WARN_FILTERS.update_one(
            {"chat_id": str(chat_id), "keyword": keyword},
            {"$set": {"reply": reply}},
            upsert=True
        )
        if str(chat_id) not in FILTER_CACHE: FILTER_CACHE[str(chat_id)] = set()
        FILTER_CACHE[str(chat_id)].add(keyword)

def remove_warn_filter(chat_id, keyword):
    with LOCK:
        res = WARN_FILTERS.delete_one({"chat_id": str(chat_id), "keyword": keyword})
        if res.deleted_count > 0:
            if str(chat_id) in FILTER_CACHE:
                FILTER_CACHE[str(chat_id)].discard(keyword)
            return True
        return False

def get_chat_warn_triggers(chat_id):
    return FILTER_CACHE.get(str(chat_id), set())

def get_warn_filter(chat_id, keyword):
    data = WARN_FILTERS.find_one({"chat_id": str(chat_id), "keyword": keyword})
    return WarnFilterObj(data) if data else None

def set_warn_limit(chat_id, warn_limit):
    with LOCK:
        WARN_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"warn_limit": warn_limit}},
            upsert=True
        )

def set_warn_strength(chat_id, soft_warn):
    with LOCK:
        WARN_SETTINGS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"soft_warn": soft_warn}},
            upsert=True
        )

def get_warn_setting(chat_id):
    setting = WARN_SETTINGS.find_one({"chat_id": str(chat_id)})
    if setting:
        return setting.get("warn_limit", 3), setting.get("soft_warn", False)
    return 3, False

def num_warns():
    return WARNS.count_documents({})

def num_warn_chats():
    return len(WARNS.distinct("chat_id"))

def num_warn_filters():
    return WARN_FILTERS.count_documents({})

def num_warn_chat_filters(chat_id):
    return WARN_FILTERS.count_documents({"chat_id": str(chat_id)})

def num_warn_filter_chats():
    return len(WARN_FILTERS.distinct("chat_id"))

def __load_chat_warn_filters():
    global FILTER_CACHE
    try:
        for x in WARN_FILTERS.find():
            if x["chat_id"] not in FILTER_CACHE:
                FILTER_CACHE[x["chat_id"]] = set()
            FILTER_CACHE[x["chat_id"]].add(x["keyword"])
    except:
        pass

__load_chat_warn_filters()