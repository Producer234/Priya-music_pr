import threading
import time
from AnshiRobot.modules.sql import BASE

ACCESS = BASE["access_connection"]
CONNECTION = BASE["connection"]
HISTORY = BASE["connection_history"]
LOCK = threading.RLock()

# Helper for object compatibility
class ConnObj:
    def __init__(self, data):
        self.chat_id = data["chat_id"]
        self.chat_name = data.get("chat_name")

def allow_connect_to_chat(chat_id):
    res = ACCESS.find_one({"chat_id": str(chat_id)})
    if res:
        return res.get("allow", True)
    return False

def set_allow_connect_to_chat(chat_id, setting):
    with LOCK:
        ACCESS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"allow": setting}},
            upsert=True
        )

def connect(user_id, chat_id):
    with LOCK:
        CONNECTION.update_one(
            {"user_id": int(user_id)},
            {"$set": {"chat_id": str(chat_id)}},
            upsert=True
        )
    return True

def get_connected_chat(user_id):
    res = CONNECTION.find_one({"user_id": int(user_id)})
    if res:
        return ConnObj(res)
    return None

def disconnect(user_id):
    with LOCK:
        res = CONNECTION.delete_one({"user_id": int(user_id)})
        return res.deleted_count > 0

def add_history_conn(user_id, chat_id, chat_name):
    with LOCK:
        conn_time = int(time.time())
        HISTORY.insert_one({
            "user_id": int(user_id),
            "chat_id": str(chat_id),
            "chat_name": str(chat_name),
            "conn_time": conn_time
        })

def get_history_conn(user_id):
    results = HISTORY.find({"user_id": int(user_id)}).sort("conn_time", -1)
    history = {}
    for r in results:
        history[r["conn_time"]] = {
            "chat_name": r["chat_name"],
            "chat_id": r["chat_id"]
        }
    return history

def clear_history_conn(user_id):
    with LOCK:
        HISTORY.delete_many({"user_id": int(user_id)})
        return True