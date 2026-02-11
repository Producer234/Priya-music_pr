from AnshiRobot.modules.sql import BASE

FSUB = BASE["force_subscribe"]

# Helper object
class FSubObj:
    def __init__(self, channel):
        self.channel = channel

def fs_settings(chat_id):
    data = FSUB.find_one({"chat_id": str(chat_id)})
    if data:
        return FSubObj(data["channel"])
    return None

def add_channel(chat_id, channel):
    FSUB.update_one(
        {"chat_id": str(chat_id)},
        {"$set": {"channel": channel}},
        upsert=True
    )

def disapprove(chat_id):
    FSUB.delete_one({"chat_id": str(chat_id)})