import threading
from AnshiRobot.modules.sql import BASE

USERS = BASE["users"]
CHATS = BASE["chats"]
CHAT_MEMBERS = BASE["chat_members"]

INSERTION_LOCK = threading.RLock()

def ensure_bot_in_db():
    pass

def update_user(user_id, username, chat_id=None, chat_name=None):
    with INSERTION_LOCK:
        USERS.update_one(
            {"_id": int(user_id)},
            {"$set": {"username": username}},
            upsert=True
        )
        if chat_id and chat_name:
            CHATS.update_one(
                {"_id": str(chat_id)},
                {"$set": {"chat_name": chat_name}},
                upsert=True
            )
            CHAT_MEMBERS.update_one(
                {"chat_id": str(chat_id), "user_id": int(user_id)},
                {"$set": {"chat_id": str(chat_id), "user_id": int(user_id)}},
                upsert=True
            )

def get_userid_by_name(username):
    return list(USERS.find({"username": {"$regex": f"^{username}$", "$options": "i"}}))

def get_name_by_userid(user_id):
    return USERS.find_one({"_id": int(user_id)})

def get_chat_members(chat_id):
    return list(CHAT_MEMBERS.find({"chat_id": str(chat_id)}))

def get_all_chats():
    # Adapting to return objects compatible with existing code
    chats = list(CHATS.find())
    return [{"chat_id": x["_id"], "chat_name": x["chat_name"]} for x in chats]

def get_all_users():
    return list(USERS.find())

def get_user_num_chats(user_id):
    return CHAT_MEMBERS.count_documents({"user_id": int(user_id)})

def num_chats():
    return CHATS.count_documents({})

def num_users():
    return USERS.count_documents({})

def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        chat = CHATS.find_one({"_id": str(old_chat_id)})
        if chat:
            CHATS.delete_one({"_id": str(old_chat_id)})
            chat["_id"] = str(new_chat_id)
            CHATS.insert_one(chat)
        CHAT_MEMBERS.update_many(
            {"chat_id": str(old_chat_id)},
            {"$set": {"chat_id": str(new_chat_id)}}
        )

def del_user(user_id):
    with INSERTION_LOCK:
        USERS.delete_one({"_id": int(user_id)})
        CHAT_MEMBERS.delete_many({"user_id": int(user_id)})
        return True