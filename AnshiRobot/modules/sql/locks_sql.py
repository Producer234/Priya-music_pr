import threading
from AnshiRobot.modules.sql import BASE

PERMISSIONS = BASE["permissions"]
RESTRICTIONS = BASE["restrictions"]
PERM_LOCK = threading.RLock()
RESTR_LOCK = threading.RLock()

# Helper to mimic object access (perms.audio instead of perms['audio'])
class DictObj:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)

def init_permissions(chat_id):
    default = {
        "audio": False, "voice": False, "contact": False, "video": False,
        "document": False, "photo": False, "sticker": False, "gif": False,
        "url": False, "bots": False, "forward": False, "game": False,
        "location": False, "rtl": False, "button": False, "egame": False, "inline": False
    }
    PERMISSIONS.update_one({"chat_id": str(chat_id)}, {"$setOnInsert": default}, upsert=True)
    return default

def update_lock(chat_id, lock_type, locked):
    with PERM_LOCK:
        PERMISSIONS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {lock_type: locked}},
            upsert=True
        )

def is_locked(chat_id, lock_type):
    perm = PERMISSIONS.find_one({"chat_id": str(chat_id)})
    if not perm: return False
    return perm.get(lock_type, False)

def get_locks(chat_id):
    perm = PERMISSIONS.find_one({"chat_id": str(chat_id)})
    if not perm:
        return DictObj(init_permissions(chat_id))
    return DictObj(perm)

def update_restriction(chat_id, restr_type, locked):
    with RESTR_LOCK:
        if restr_type == "all":
            update = {"messages": locked, "media": locked, "other": locked, "preview": locked}
        else:
            update = {restr_type: locked}
        RESTRICTIONS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": update},
            upsert=True
        )

def is_restr_locked(chat_id, lock_type):
    restr = RESTRICTIONS.find_one({"chat_id": str(chat_id)})
    if not restr: return False
    if lock_type == "all":
        return restr.get("messages") and restr.get("media") and restr.get("other") and restr.get("preview")
    return restr.get(lock_type, False)

def get_restr(chat_id):
    return RESTRICTIONS.find_one({"chat_id": str(chat_id)})