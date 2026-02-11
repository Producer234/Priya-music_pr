import threading
from AnshiRobot.modules.sql import BASE
NSFW = BASE["nsfw_chats"]
LOCK = threading.RLock()

def is_nsfw(chat_id):
    return NSFW.find_one({"chat_id": str(chat_id)}) is not None

def set_nsfw(chat_id):
    with LOCK:
        NSFW.insert_one({"chat_id": str(chat_id)})

def rem_nsfw(chat_id):
    with LOCK:
        NSFW.delete_one({"chat_id": str(chat_id)})

def get_all_nsfw_chats():
    return [x["chat_id"] for x in NSFW.find()]