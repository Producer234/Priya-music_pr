import threading
from AnshiRobot.modules.sql import BASE

LOG_CHANNELS = BASE["log_channels"]
LOCK = threading.RLock()
CHANNELS = {}

def set_chat_log_channel(chat_id, log_channel):
    with LOCK:
        LOG_CHANNELS.update_one(
            {"chat_id": str(chat_id)},
            {"$set": {"log_channel": str(log_channel)}},
            upsert=True
        )
        CHANNELS[str(chat_id)] = str(log_channel)

def get_chat_log_channel(chat_id):
    return CHANNELS.get(str(chat_id))

def stop_chat_logging(chat_id):
    with LOCK:
        if str(chat_id) in CHANNELS:
            del CHANNELS[str(chat_id)]
        LOG_CHANNELS.delete_one({"chat_id": str(chat_id)})

def num_logchannels():
    return LOG_CHANNELS.count_documents({})

def __load_log_channels():
    global CHANNELS
    try:
        for x in LOG_CHANNELS.find():
            CHANNELS[x["chat_id"]] = x["log_channel"]
    except:
        pass

__load_log_channels()