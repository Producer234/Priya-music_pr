import threading
from AnshiRobot.modules.sql import BASE
from AnshiRobot.modules.helper_funcs.msg_types import Types

WELCOME = BASE["welcome_pref"]
WELCOME_MUTES = BASE["welcome_mutes"]
HUMAN_CHECKS = BASE["human_checks"]
LOCK = threading.RLock()

DEFAULT_WELCOME = "Hey {first}, how are you?"
DEFAULT_GOODBYE = "Nice knowing ya!"
DEFAULT_WELCOME_MESSAGES = ["✦ {first} ɪs ʜᴇʀᴇ !", "✦ ʀᴇᴀᴅʏ ᴘʟᴀʏᴇʀ {first}"]
DEFAULT_GOODBYE_MESSAGES = ["✦ {first} ʜᴀs ʟᴇғᴛ ᴛʜᴇ ɢʀᴏᴜᴘ."]

def get_welc_pref(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    if data:
        return (
            data.get("should_welcome", True),
            data.get("custom_welcome", DEFAULT_WELCOME),
            data.get("custom_content", None),
            data.get("welcome_type", Types.TEXT.value)
        )
    return True, DEFAULT_WELCOME, None, Types.TEXT.value

def get_gdbye_pref(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    if data:
        return (
            data.get("should_goodbye", True),
            data.get("custom_leave", DEFAULT_GOODBYE),
            data.get("leave_type", Types.TEXT.value)
        )
    return True, DEFAULT_GOODBYE, Types.TEXT.value

def set_welc_preference(chat_id, should_welcome):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"should_welcome": should_welcome}},
            upsert=True
        )

def set_gdbye_preference(chat_id, should_goodbye):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"should_goodbye": should_goodbye}},
            upsert=True
        )

def set_custom_welcome(chat_id, custom_content, custom_welcome, welcome_type, buttons=None):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {
                "custom_content": custom_content,
                "custom_welcome": custom_welcome,
                "welcome_type": welcome_type.value,
                "welcome_buttons": buttons
            }},
            upsert=True
        )

def set_custom_gdbye(chat_id, custom_goodbye, goodbye_type, buttons=None):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {
                "custom_leave": custom_goodbye,
                "leave_type": goodbye_type.value,
                "goodbye_buttons": buttons
            }},
            upsert=True
        )

def get_welc_buttons(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    return data.get("welcome_buttons", []) if data else []

def get_gdbye_buttons(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    return data.get("goodbye_buttons", []) if data else []

def welcome_mutes(chat_id):
    data = WELCOME_MUTES.find_one({"chat_id": str(chat_id)})
    return data["status"] if data else False

def set_welcome_mutes(chat_id, status):
    with LOCK:
        WELCOME_MUTES.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"status": status}},
            upsert=True
        )

def set_clean_welcome(chat_id, msg_id):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"clean_welcome": int(msg_id)}},
            upsert=True
        )

def get_clean_pref(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    return data.get("clean_welcome") if data else False

def set_human_checks(user_id, chat_id):
    with LOCK:
        HUMAN_CHECKS.update_one(
            {"user_id": int(user_id), "chat_id": str(chat_id)},
            {"$set": {"human_check": True}},
            upsert=True
        )

def get_human_checks(user_id, chat_id):
    data = HUMAN_CHECKS.find_one({"user_id": int(user_id), "chat_id": str(chat_id)})
    return data.get("human_check") if data else None

def clean_service(chat_id):
    data = WELCOME.find_one({"chat_id": str(chat_id)})
    return data.get("clean_service", True) if data else True

def set_clean_service(chat_id, setting):
    with LOCK:
        WELCOME.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"clean_service": setting}},
            upsert=True
        )