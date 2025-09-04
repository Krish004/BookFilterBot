import logging
import re
import base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN
from utils import get_settings, save_group_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


# ✅ Create index for fast search
async def ensure_indexes():
    try:
        await db[COLLECTION_NAME].create_index([("file_name", "text"), ("caption", "text")])
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")


async def save_file(media):
    """Save file in database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(f'{getattr(media, "file_name", "NO_FILE")} is already saved in database')
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return True, 1


# ✅ Optimized search
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset, total or None)"""
    if chat_id is not None:
        settings = await get_settings(int(chat_id))
        try:
            max_results = 10 if settings['max_btn'] else int(MAX_B_TN)
        except KeyError:
            await save_group_settings(int(chat_id), 'max_btn', False)
            settings = await get_settings(int(chat_id))
            max_results = 10 if settings['max_btn'] else int(MAX_B_TN)

    query = query.strip()
    if not query:
        return [], "", 0

    # Use text index filter
    search_filter = {"$text": {"$search": query}}

    if file_type:
        search_filter["file_type"] = file_type

    cursor = Media.find(search_filter).sort("_id", -1).skip(offset).limit(max_results + 1)
    files = await cursor.to_list(length=max_results + 1)

    if len(files) > max_results:
        next_offset = offset + max_results
        files = files[:max_results]
    else:
        next_offset = ""

    return files, next_offset, None


# ✅ Full fetch (only use for "Send All")
async def get_bad_files(query, file_type=None, filter=False):
    query = query.strip()
    if not query:
        return [], 0

    regex = re.compile(query, flags=re.IGNORECASE)

    if USE_CAPTION_FILTER:
        search_filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        search_filter = {'file_name': regex}

    if file_type:
        search_filter['file_type'] = file_type

    total_results = await Media.count_documents(search_filter)
    cursor = Media.find(search_filter).sort("_id", -1)
    files = await cursor.to_list(length=total_results)

    return files, total_results


async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


# --- Helper functions for file_id encoding/decoding ---

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
