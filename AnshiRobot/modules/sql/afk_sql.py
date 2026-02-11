import threading
from AnshiRobot.modules.sql import BASE

AFK_COLLECTION = BASE["afk_users"]
INSERTION_LOCK = threading.RLock()
AFK_USERS = {}

def is_afk(user_id):
    return user_id in AFK_USERS

def check_afk_status(user_id):
    return AFK_COLLECTION.find_one({"_id": int(user_id)})

def set_afk(user_id, reason=""):
    with INSERTION_LOCK:
        AFK_COLLECTION.update_one(
            {"_id": int(user_id)},
            {"$set": {"reason": reason, "is_afk": True}},
            upsert=True
        )
        AFK_USERS[user_id] = reason

def rm_afk(user_id):
    with INSERTION_LOCK:
        if user_id in AFK_USERS:
            del AFK_USERS[user_id]
        res = AFK_COLLECTION.delete_one({"_id": int(user_id)})
        return res.deleted_count > 0

def toggle_afk(user_id, reason=""):
    with INSERTION_LOCK:
        curr = AFK_COLLECTION.find_one({"_id": int(user_id)})
        if not curr:
            set_afk(user_id, reason)
        else:
            rm_afk(user_id)

def __load_afk_users():
    global AFK_USERS
    try:
        all_afk = AFK_COLLECTION.find({"is_afk": True})
        AFK_USERS = {user["_id"]: user["reason"] for user in all_afk}
    except Exception:
        pass

__load_afk_users()