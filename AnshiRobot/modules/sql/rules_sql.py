import threading
from AnshiRobot.modules.sql import BASE

RULES = BASE["rules"]
INSERTION_LOCK = threading.RLock()

def set_rules(chat_id, rules_text):
    with INSERTION_LOCK:
        RULES.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"rules": rules_text}},
            upsert=True
        )

def get_rules(chat_id):
    res = RULES.find_one({"chat_id": str(chat_id)})
    return res["rules"] if res else ""

def num_chats():
    return RULES.count_documents({})

def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        RULES.update_one(
            {"chat_id": str(old_chat_id)},
            {"$set": {"chat_id": str(new_chat_id)}}
        )