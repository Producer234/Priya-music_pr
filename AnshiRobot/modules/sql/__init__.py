from pymongo import MongoClient
from AnshiRobot import MONGO_DB_URI, LOGGER

try:
    client = MongoClient(MONGO_DB_URI)
    BASE = client["AnshiRobot_DB"]
    LOGGER.info("[MongoDB] Connection successful, SQL Session replaced.")
except Exception as e:
    LOGGER.exception(f"[MongoDB] Failed to connect: {e}")
    exit()

# We keep SESSION variable to prevent import errors in other modules
SESSION = client