import threading
from AnshiRobot.modules.sql import BASE

BL_USERS = BASE["blacklist_users"]
LOCK = threading.RLock()
BLACKLIST_USERS = set()

def blacklist_user(user_id, reason=None):
    with LOCK:
        BL_USERS.update_one(
            {"user_id": int(user_id)},
            {"$set": {"reason": reason}},
            upsert=True
        )
        BLACKLIST_USERS.add(int(user_id))

def unblacklist_user(user_id):
    with LOCK:
        BL_USERS.delete_one({"user_id": int(user_id)})
        if int(user_id) in BLACKLIST_USERS:
            BLACKLIST_USERS.remove(int(user_id))

def is_user_blacklisted(user_id):
    return int(user_id) in BLACKLIST_USERS

def get_reason(user_id):
    user = BL_USERS.find_one({"user_id": int(user_id)})
    return user["reason"] if user else None

def __load_bl_users():
    global BLACKLIST_USERS
    try:
        BLACKLIST_USERS = {x["user_id"] for x in BL_USERS.find()}
    except:
        pass

__load_bl_users()