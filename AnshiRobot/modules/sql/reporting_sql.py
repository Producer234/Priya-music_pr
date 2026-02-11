import threading
from AnshiRobot.modules.sql import BASE

REPORT = BASE["reporting"]
LOCK = threading.RLock()

def chat_should_report(chat_id):
    res = REPORT.find_one({"chat_id": str(chat_id)})
    return res.get("should_report", True) if res else True

def user_should_report(user_id):
    res = REPORT.find_one({"user_id": int(user_id)})
    return res.get("should_report", True) if res else True

def set_chat_setting(chat_id, setting):
    with LOCK:
        REPORT.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"should_report": setting}},
            upsert=True
        )

def set_user_setting(user_id, setting):
    with LOCK:
        REPORT.update_one(
            {"user_id": int(user_id)},
            {"$set": {"should_report": setting}},
            upsert=True
        )