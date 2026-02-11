import threading
from AnshiRobot.modules.sql import BASE

USERINFO = BASE["user_info"]
LOCK = threading.RLock()

def get_user_me_info(user_id):
    res = USERINFO.find_one({"user_id": int(user_id)})
    return res["info"] if res else None

def set_user_me_info(user_id, info):
    with LOCK:
        USERINFO.update_one(
            {"user_id": int(user_id)},
            {"$set": {"info": info}},
            upsert=True
        )

def get_user_bio(user_id):
    res = USERINFO.find_one({"user_id": int(user_id)})
    return res.get("bio") if res else None

def set_user_bio(user_id, bio):
    with LOCK:
        USERINFO.update_one(
            {"user_id": int(user_id)},
            {"$set": {"bio": bio}},
            upsert=True
        )