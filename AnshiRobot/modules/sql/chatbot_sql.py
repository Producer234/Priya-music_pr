import threading
from AnshiRobot.modules.sql import BASE

CHATBOT = BASE["chatbot"]
LOCK = threading.RLock()

def is_Anshi(chat_id):
    return CHATBOT.find_one({"chat_id": str(chat_id)}) is not None

def set_Anshi(chat_id):
    with LOCK:
        CHATBOT.insert_one({"chat_id": str(chat_id)})

def rem_Anshi(chat_id):
    with LOCK:
        CHATBOT.delete_one({"chat_id": str(chat_id)})