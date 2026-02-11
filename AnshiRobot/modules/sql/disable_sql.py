import threading
from AnshiRobot.modules.sql import BASE

DISABLED = BASE["disabled_commands"]
LOCK = threading.RLock()
DISABLED_CACHE = {}

def disable_command(chat_id, command):
    with LOCK:
        DISABLED.update_one(
            {"chat_id": str(chat_id)},
            {"$addToSet": {"commands": command}},
            upsert=True
        )
        if str(chat_id) not in DISABLED_CACHE:
            DISABLED_CACHE[str(chat_id)] = set()
        DISABLED_CACHE[str(chat_id)].add(command)
        return True

def enable_command(chat_id, command):
    with LOCK:
        DISABLED.update_one(
            {"chat_id": str(chat_id)},
            {"$pull": {"commands": command}}
        )
        if str(chat_id) in DISABLED_CACHE and command in DISABLED_CACHE[str(chat_id)]:
            DISABLED_CACHE[str(chat_id)].remove(command)
            return True
        return False

def is_command_disabled(chat_id, cmd):
    return cmd.lower() in DISABLED_CACHE.get(str(chat_id), set())

def get_all_disabled(chat_id):
    return DISABLED_CACHE.get(str(chat_id), set())

def num_chats():
    return len(DISABLED_CACHE)

def num_disabled():
    return sum(len(cmds) for cmds in DISABLED_CACHE.values())

def __load_disabled():
    global DISABLED_CACHE
    try:
        for chat in DISABLED.find():
            DISABLED_CACHE[chat["chat_id"]] = set(chat.get("commands", []))
    except:
        pass

__load_disabled()