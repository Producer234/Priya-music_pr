from AnshiRobot.modules.sql import BASE

NIGHTMODE = BASE["nightmode"]

def add_nightmode(chat_id):
    NIGHTMODE.insert_one({"chat_id": str(chat_id)})

def rmnightmode(chat_id):
    NIGHTMODE.delete_one({"chat_id": str(chat_id)})

def get_all_chat_id():
    # Return list of objects with chat_id attribute
    res = list(NIGHTMODE.find())
    class ChatObj:
        def __init__(self, id): self.chat_id = id
    return [ChatObj(x["chat_id"]) for x in res]

def is_nightmode_indb(chat_id):
    return NIGHTMODE.find_one({"chat_id": str(chat_id)}) is not None