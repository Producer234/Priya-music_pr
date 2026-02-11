import threading
from AnshiRobot.modules.sql import BASE

GBAN_USER = BASE["gbans"]
GBAN_SETTINGS = BASE["gban_settings"]
LOCK = threading.RLock()

GBANNED_LIST = set()
GBANSTAT_LIST = set()

def gban_user(user_id, name, reason=None):
    with LOCK:
        GBAN_USER.update_one(
            {"user_id": int(user_id)},
            {"$set": {"name": name, "reason": reason}},
            upsert=True
        )
        GBANNED_LIST.add(int(user_id))

def ungban_user(user_id):
    with LOCK:
        GBAN_USER.delete_one({"user_id": int(user_id)})
        if int(user_id) in GBANNED_LIST:
            GBANNED_LIST.remove(int(user_id))

def is_user_gbanned(user_id):
    return int(user_id) in GBANNED_LIST

def get_gbanned_user(user_id):
    res = GBAN_USER.find_one({"user_id": int(user_id)})
    # Return object with reason attribute
    if res:
        class Obj: pass
        o = Obj()
        o.reason = res.get("reason")
        return o
    return None

def get_gban_list():
    return list(GBAN_USER.find())

def enable_gbans(chat_id):
    with LOCK:
        GBAN_SETTINGS.update_one({"chat_id": str(chat_id)}, {"$set": {"setting": True}}, upsert=True)
        if str(chat_id) in GBANSTAT_LIST:
            GBANSTAT_LIST.remove(str(chat_id))

def disable_gbans(chat_id):
    with LOCK:
        GBAN_SETTINGS.update_one({"chat_id": str(chat_id)}, {"$set": {"setting": False}}, upsert=True)
        GBANSTAT_LIST.add(str(chat_id))

def does_chat_gban(chat_id):
    return str(chat_id) not in GBANSTAT_LIST

def num_gbanned_users():
    return len(GBANNED_LIST)

def __load_gbanned_userid_list():
    global GBANNED_LIST
    GBANNED_LIST = {user["user_id"] for user in GBAN_USER.find()}

def __load_gban_stat_list():
    global GBANSTAT_LIST
    GBANSTAT_LIST = {x["chat_id"] for x in GBAN_SETTINGS.find({"setting": False})}

__load_gbanned_userid_list()
__load_gban_stat_list()