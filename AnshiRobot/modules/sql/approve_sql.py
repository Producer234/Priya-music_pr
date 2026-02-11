import threading
from AnshiRobot.modules.sql import BASE

APPROVALS = BASE["approvals"]
LOCK = threading.RLock()

# Helper class for object access
class ApproveObj:
    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = chat_id

def approve(chat_id, user_id):
    with LOCK:
        APPROVALS.update_one(
            {"chat_id": str(chat_id), "user_id": int(user_id)},
            {"$set": {"approved": True}},
            upsert=True
        )

def is_approved(chat_id, user_id):
    return APPROVALS.find_one({"chat_id": str(chat_id), "user_id": int(user_id)}) is not None

def disapprove(chat_id, user_id):
    with LOCK:
        res = APPROVALS.delete_one({"chat_id": str(chat_id), "user_id": int(user_id)})
        return res.deleted_count > 0

def list_approved(chat_id):
    results = APPROVALS.find({"chat_id": str(chat_id)})
    return [ApproveObj(res["user_id"], res["chat_id"]) for res in results]