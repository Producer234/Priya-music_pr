import threading
from AnshiRobot.modules.sql import BASE
from AnshiRobot.modules.helper_funcs.msg_types import Types

FILTERS = BASE["cust_filters"]
LOCK = threading.RLock()
CHAT_FILTERS = {}

class FilterObj:
    def __init__(self, data):
        self.keyword = data["keyword"]
        self.reply = data["reply"]
        self.is_sticker = data.get("is_sticker", False)
        self.is_document = data.get("is_document", False)
        self.is_image = data.get("is_image", False)
        self.is_audio = data.get("is_audio", False)
        self.is_voice = data.get("is_voice", False)
        self.is_video = data.get("is_video", False)
        self.has_markdown = data.get("has_markdown", True)
        self.reply_text = data.get("reply_text")
        self.file_type = data.get("file_type", 1)
        self.file_id = data.get("file_id")

def add_filter(chat_id, keyword, reply, is_sticker=False, is_document=False, is_image=False, is_audio=False, is_voice=False, is_video=False, buttons=None):
    if not buttons: buttons = []
    with LOCK:
        FILTERS.update_one(
            {"chat_id": str(chat_id), "keyword": keyword},
            {"$set": {
                "reply": reply,
                "is_sticker": is_sticker,
                "is_document": is_document,
                "is_image": is_image,
                "is_audio": is_audio,
                "is_voice": is_voice,
                "is_video": is_video,
                "buttons": buttons
            }},
            upsert=True
        )
        if str(chat_id) not in CHAT_FILTERS: CHAT_FILTERS[str(chat_id)] = []
        if keyword not in CHAT_FILTERS[str(chat_id)]:
            CHAT_FILTERS[str(chat_id)].append(keyword)

def new_add_filter(chat_id, keyword, reply_text, file_type, file_id, buttons):
    if not buttons: buttons = []
    with LOCK:
        FILTERS.update_one(
            {"chat_id": str(chat_id), "keyword": keyword},
            {"$set": {
                "reply": "new_reply_placeholder",
                "reply_text": reply_text,
                "file_type": file_type.value,
                "file_id": file_id,
                "buttons": buttons,
                "has_markdown": True
            }},
            upsert=True
        )
        if str(chat_id) not in CHAT_FILTERS: CHAT_FILTERS[str(chat_id)] = []
        if keyword not in CHAT_FILTERS[str(chat_id)]:
            CHAT_FILTERS[str(chat_id)].append(keyword)

def remove_filter(chat_id, keyword):
    with LOCK:
        res = FILTERS.delete_one({"chat_id": str(chat_id), "keyword": keyword})
        if res.deleted_count > 0:
            if str(chat_id) in CHAT_FILTERS and keyword in CHAT_FILTERS[str(chat_id)]:
                CHAT_FILTERS[str(chat_id)].remove(keyword)
            return True
        return False

def get_chat_triggers(chat_id):
    return set(CHAT_FILTERS.get(str(chat_id), []))

def get_filter(chat_id, keyword):
    data = FILTERS.find_one({"chat_id": str(chat_id), "keyword": keyword})
    return FilterObj(data) if data else None

def get_buttons(chat_id, keyword):
    data = FILTERS.find_one({"chat_id": str(chat_id), "keyword": keyword})
    return data.get("buttons", []) if data else []

def num_filters():
    return FILTERS.count_documents({})

def num_chats():
    return len(FILTERS.distinct("chat_id"))

def __load_chat_filters():
    global CHAT_FILTERS
    try:
        for x in FILTERS.find():
            if x["chat_id"] not in CHAT_FILTERS:
                CHAT_FILTERS[x["chat_id"]] = []
            CHAT_FILTERS[x["chat_id"]].append(x["keyword"])
    except:
        pass

__load_chat_filters()