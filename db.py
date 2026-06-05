import aiosqlite
import asyncio
from datetime import datetime
import os

DB_PATH = "filemanager.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                added_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS folders (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                password    TEXT,
                created_by  INTEGER,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS files (
                id              TEXT PRIMARY KEY,
                folder_id       TEXT,
                file_id         TEXT NOT NULL,
                file_unique_id  TEXT,
                file_name       TEXT,
                file_type       TEXT,
                file_size       INTEGER DEFAULT 0,
                caption         TEXT,
                password        TEXT,
                max_downloads   INTEGER DEFAULT 0,
                download_count  INTEGER DEFAULT 0,
                expire_seconds  INTEGER DEFAULT 0,
                forward_protect INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,
                created_by      INTEGER,
                created_at      TEXT DEFAULT (datetime('now')),
                expires_at      TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders(id)
            );

            CREATE TABLE IF NOT EXISTS download_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id     TEXT,
                folder_id   TEXT,
                user_id     INTEGER,
                username    TEXT,
                downloaded_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id     INTEGER PRIMARY KEY,
                reason      TEXT,
                blocked_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );
        """)
        await db.commit()

# ─── Admin ─────────────────────────────────────────────────────────────────

async def add_admin(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def get_all_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins") as cur:
            return await cur.fetchall()

# ─── Folders ───────────────────────────────────────────────────────────────

async def create_folder(folder_id: str, name: str, description: str = "",
                        password: str = "", created_by: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO folders (id, name, description, password, created_by) VALUES (?, ?, ?, ?, ?)",
            (folder_id, name, description, password, created_by)
        )
        await db.commit()

async def get_folder(folder_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)) as cur:
            return await cur.fetchone()

async def get_all_folders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM folders ORDER BY created_at DESC") as cur:
            return await cur.fetchall()

async def delete_folder(folder_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM files WHERE folder_id = ?", (folder_id,))
        await db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        await db.commit()

async def update_folder(folder_id: str, name: str, description: str, password: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE folders SET name=?, description=?, password=? WHERE id=?",
            (name, description, password, folder_id)
        )
        await db.commit()

# ─── Files ─────────────────────────────────────────────────────────────────

async def add_file(file_id_pk: str, folder_id: str, telegram_file_id: str,
                   file_unique_id: str, file_name: str, file_type: str,
                   file_size: int, caption: str, password: str,
                   max_downloads: int, expire_seconds: int,
                   forward_protect: int, created_by: int,
                   expires_at: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO files
            (id, folder_id, file_id, file_unique_id, file_name, file_type,
             file_size, caption, password, max_downloads, expire_seconds,
             forward_protect, created_by, expires_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (file_id_pk, folder_id, telegram_file_id, file_unique_id,
              file_name, file_type, file_size, caption, password,
              max_downloads, expire_seconds, forward_protect, created_by,
              expires_at))
        await db.commit()

async def get_file(file_id_pk: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM files WHERE id = ?", (file_id_pk,)) as cur:
            return await cur.fetchone()

async def get_files_in_folder(folder_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM files WHERE folder_id = ? AND is_active = 1 ORDER BY created_at DESC",
            (folder_id,)
        ) as cur:
            return await cur.fetchall()

async def increment_download(file_id_pk: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE files SET download_count = download_count + 1 WHERE id = ?",
            (file_id_pk,)
        )
        await db.commit()

async def deactivate_file(file_id_pk: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE files SET is_active = 0 WHERE id = ?", (file_id_pk,))
        await db.commit()

async def delete_file(file_id_pk: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM files WHERE id = ?", (file_id_pk,))
        await db.commit()

async def get_all_active_files():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM files WHERE is_active = 1 AND (expire_seconds > 0 OR max_downloads > 0)"
        ) as cur:
            return await cur.fetchall()

# ─── Download Logs ─────────────────────────────────────────────────────────

async def log_download(file_id: str, folder_id: str, user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO download_logs (file_id, folder_id, user_id, username) VALUES (?,?,?,?)",
            (file_id, folder_id, user_id, username)
        )
        await db.commit()

async def get_file_stats(file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as unique_users FROM download_logs WHERE file_id = ?",
            (file_id,)
        ) as cur:
            return await cur.fetchone()

async def get_folder_stats(folder_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as unique_users FROM download_logs WHERE folder_id = ?",
            (folder_id,)
        ) as cur:
            return await cur.fetchone()

async def get_global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        stats = {}
        async with db.execute("SELECT COUNT(*) as c FROM files WHERE is_active=1") as cur:
            row = await cur.fetchone(); stats["active_files"] = row["c"]
        async with db.execute("SELECT COUNT(*) as c FROM folders") as cur:
            row = await cur.fetchone(); stats["folders"] = row["c"]
        async with db.execute("SELECT COUNT(*) as c FROM download_logs") as cur:
            row = await cur.fetchone(); stats["total_downloads"] = row["c"]
        async with db.execute("SELECT COUNT(DISTINCT user_id) as c FROM download_logs") as cur:
            row = await cur.fetchone(); stats["unique_users"] = row["c"]
        async with db.execute("SELECT SUM(file_size) as s FROM files WHERE is_active=1") as cur:
            row = await cur.fetchone(); stats["total_size"] = row["s"] or 0
        return stats

# ─── Blocked Users ─────────────────────────────────────────────────────────

async def block_user(user_id: int, reason: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO blocked_users (user_id, reason) VALUES (?, ?)",
            (user_id, reason)
        )
        await db.commit()

async def unblock_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_blocked(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None

# ─── Settings ──────────────────────────────────────────────────────────────

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()
