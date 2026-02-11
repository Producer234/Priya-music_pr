import threading
import ast
from AnshiRobot.modules.sql import BASE

FEDS = BASE["feds"]
FED_SUBS = BASE["fed_subs"]
LOCK = threading.RLock()

# Caches
FEDERATION_BYOWNER = {}
FEDERATION_BYFEDID = {}
FEDERATION_BYNAME = {}
FEDERATION_CHATS = {}

def new_fed(owner_id, fed_name, fed_id):
    with LOCK:
        data = {
            "owner_id": str(owner_id),
            "fed_name": fed_name,
            "fed_id": str(fed_id),
            "fed_rules": "Rules is not set in this federation.",
            "fed_log": None,
            "fed_users": str({"owner": str(owner_id), "members": "[]"}),
            "chats": []
        }
        FEDS.insert_one(data)
        __load_all_feds()
        return True

def get_fed_info(fed_id):
    return FEDERATION_BYFEDID.get(str(fed_id))

def chat_join_fed(fed_id, chat_name, chat_id):
    with LOCK:
        FEDS.update_one(
            {"fed_id": str(fed_id)},
            {"$addToSet": {"chats": {"chat_id": str(chat_id), "chat_name": chat_name}}}
        )
        __load_all_feds()

def chat_leave_fed(chat_id):
    with LOCK:
        # Find which fed this chat is in and pull it
        FEDS.update_one(
            {"chats.chat_id": str(chat_id)},
            {"$pull": {"chats": {"chat_id": str(chat_id)}}}
        )
        __load_all_feds()
        return True

def user_join_fed(fed_id, user_id):
    with LOCK:
        fed = FEDS.find_one({"fed_id": str(fed_id)})
        if not fed: return False
        
        users = ast.literal_eval(fed["fed_users"])
        members = ast.literal_eval(users["members"])
        if user_id not in members:
            members.append(user_id)
            users["members"] = str(members)
            FEDS.update_one(
                {"fed_id": str(fed_id)},
                {"$set": {"fed_users": str(users)}}
            )
            __load_all_feds()
            return True
        return False

def user_demote_fed(fed_id, user_id):
    with LOCK:
        fed = FEDS.find_one({"fed_id": str(fed_id)})
        if not fed: return False
        
        users = ast.literal_eval(fed["fed_users"])
        members = ast.literal_eval(users["members"])
        if user_id in members:
            members.remove(user_id)
            users["members"] = str(members)
            FEDS.update_one(
                {"fed_id": str(fed_id)},
                {"$set": {"fed_users": str(users)}}
            )
            __load_all_feds()
            return True
        return False

def del_fed(fed_id):
    with LOCK:
        FEDS.delete_one({"fed_id": str(fed_id)})
        __load_all_feds()

def __load_all_feds():
    global FEDERATION_BYOWNER, FEDERATION_BYFEDID, FEDERATION_BYNAME, FEDERATION_CHATS
    FEDERATION_BYOWNER = {}
    FEDERATION_BYFEDID = {}
    FEDERATION_BYNAME = {}
    FEDERATION_CHATS = {}
    
    try:
        for x in FEDS.find():
            # Populate Caches
            fed_data = {
                "fid": x["fed_id"],
                "fname": x["fed_name"],
                "frules": x["fed_rules"],
                "flog": x["fed_log"],
                "fusers": x["fed_users"],
                "owner": x["owner_id"]
            }
            FEDERATION_BYOWNER[x["owner_id"]] = fed_data
            FEDERATION_BYFEDID[x["fed_id"]] = fed_data
            FEDERATION_BYNAME[x["fed_name"]] = fed_data
            
            for chat in x.get("chats", []):
                FEDERATION_CHATS[chat["chat_id"]] = {"fid": x["fed_id"], "chat_name": chat["chat_name"]}
    except:
        pass

__load_all_feds()