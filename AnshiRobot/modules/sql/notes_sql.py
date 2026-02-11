import threading
from AnshiRobot.modules.sql import BASE
from AnshiRobot.modules.helper_funcs.msg_types import Types

NOTES = BASE["notes"]
INSERTION_LOCK = threading.RLock()

# Helper class to mimic SQL object behavior for existing code
class NoteObject:
    def __init__(self, data):
        self.name = data["name"]
        self.value = data["value"]
        self.file = data.get("file")
        self.is_reply = data.get("is_reply", False)
        self.has_buttons = data.get("has_buttons", False)
        self.msgtype = data.get("msgtype", Types.BUTTON_TEXT.value)

def add_note_to_db(chat_id, note_name, note_data, msgtype, buttons=None, file=None):
    if not buttons:
        buttons = []
    with INSERTION_LOCK:
        NOTES.update_one(
            {"chat_id": str(chat_id), "name": note_name},
            {"$set": {
                "value": note_data,
                "msgtype": msgtype,
                "file": file,
                "buttons": buttons,
                "has_buttons": bool(buttons)
            }},
            upsert=True
        )

def get_note(chat_id, note_name):
    data = NOTES.find_one({"chat_id": str(chat_id), "name": note_name})
    if data:
        return NoteObject(data)
    return None

def rm_note(chat_id, note_name):
    with INSERTION_LOCK:
        res = NOTES.delete_one({"chat_id": str(chat_id), "name": note_name})
        return res.deleted_count > 0

def get_all_chat_notes(chat_id):
    results = NOTES.find({"chat_id": str(chat_id)}).sort("name", 1)
    return [NoteObject(res) for res in results]

def get_buttons(chat_id, note_name):
    data = NOTES.find_one({"chat_id": str(chat_id), "name": note_name})
    if data:
        return data.get("buttons", [])
    return []

def num_notes():
    return NOTES.count_documents({})

def num_chats():
    return len(NOTES.distinct("chat_id"))

def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        NOTES.update_many(
            {"chat_id": str(old_chat_id)},
            {"$set": {"chat_id": str(new_chat_id)}}
        )