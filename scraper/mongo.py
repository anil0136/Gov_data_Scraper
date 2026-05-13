from dataclasses import dataclass

from django.conf import settings

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
    _PYMONGO_IMPORT_ERROR = None
except ImportError as exc:
    ASCENDING = 1
    DESCENDING = -1
    MongoClient = None
    _PYMONGO_IMPORT_ERROR = exc


COLLECTIONS = {
    "umang": "umang_schemes",
    "gov": "government_services",
    "myscheme": "myscheme",
    "india": "india_portal_schemes",
    "scholarships": "scholarships",
    "grants": "grants",
    "tenders": "tender_listings",
}


@dataclass
class MongoRecord:
    kind: str
    data: dict

    def __getattr__(self, name):
        if name == "id":
            return str(self.data.get("_id", ""))
        return self.data.get(name)


_client = None
_db = None
_indexes_ready = False


def get_client():
    global _client
    if MongoClient is None:
        raise RuntimeError(
            "pymongo is not installed. Add it to the deployment environment before using MongoDB."
        ) from _PYMONGO_IMPORT_ERROR
    if _client is None:
        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    global _db
    if _db is None:
        _db = get_client()[settings.MONGODB_DATABASE]
    return _db


def collection(kind):
    return get_db()[COLLECTIONS[kind]]


def ensure_indexes():
    global _indexes_ready
    if _indexes_ready:
        return

    collection("umang").create_index([("title", ASCENDING)], unique=True)
    collection("gov").create_index([("title", ASCENDING)], unique=True)
    collection("myscheme").create_index([("title", ASCENDING)], unique=True)
    collection("india").create_index([("title", ASCENDING)], unique=True)
    collection("scholarships").create_index([("title", ASCENDING)], unique=True)
    collection("grants").create_index([("title", ASCENDING)], unique=True)
    collection("tenders").create_index(
        [("source", ASCENDING), ("external_id", ASCENDING)],
        unique=True,
        sparse=True,
    )
    collection("tenders").create_index([("source", ASCENDING), ("title", ASCENDING), ("url", ASCENDING)], unique=True)
    _indexes_ready = True


def upsert_one(kind, lookup, item):
    ensure_indexes()
    return collection(kind).update_one(lookup, {"$set": item}, upsert=True)


def delete_many(kind, query):
    ensure_indexes()
    return collection(kind).delete_many(query)


def delete_by_id(kind, object_id):
    ensure_indexes()
    return collection(kind).delete_one({"_id": object_id})


def find_records(kind, query=None, sort=None, limit=None, skip=0, projection=None):
    cursor = collection(kind).find(query or {}, projection)
    if sort:
        cursor = cursor.sort(sort)
    if skip:
        cursor = cursor.skip(skip)
    if limit:
        cursor = cursor.limit(limit)
    return [MongoRecord(kind, document) for document in cursor]


def count_records(kind, query=None):
    try:
        return collection(kind).count_documents(query or {})
    except Exception:
        return 0


def latest_records(kind, limit=100, skip=0, projection=None):
    try:
        cursor = collection(kind).find({}, projection).sort([("_id", DESCENDING)])
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [MongoRecord(kind, document) for document in cursor]
    except Exception:
        return []
