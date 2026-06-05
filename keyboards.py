from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ─── Admin Main Menu ────────────────────────────────────────────────────────

def admin_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📁 پوشه‌ها",        callback_data="admin:folders"),
        InlineKeyboardButton(text="📤 آپلود فایل",     callback_data="admin:upload"),
    )
    kb.row(
        InlineKeyboardButton(text="📊 آمار کلی",       callback_data="admin:stats"),
        InlineKeyboardButton(text="⚙️ تنظیمات",        callback_data="admin:settings"),
    )
    kb.row(
        InlineKeyboardButton(text="👥 مدیریت ادمین‌ها", callback_data="admin:admins"),
        InlineKeyboardButton(text="🚫 کاربران بلاک",   callback_data="admin:blocked"),
    )
    kb.row(
        InlineKeyboardButton(text="📋 همه فایل‌ها",    callback_data="admin:all_files"),
    )
    return kb.as_markup()


# ─── Folders ────────────────────────────────────────────────────────────────

def folders_menu(folders: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in folders:
        lock = "🔒 " if f["password"] else ""
        kb.row(InlineKeyboardButton(
            text=f"📁 {lock}{f['name']}",
            callback_data=f"folder:view:{f['id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ پوشه جدید", callback_data="folder:create"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",    callback_data="admin:back"))
    return kb.as_markup()


def folder_detail_menu(folder_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📤 افزودن فایل",   callback_data=f"folder:upload:{folder_id}"),
        InlineKeyboardButton(text="📋 فایل‌ها",        callback_data=f"folder:files:{folder_id}"),
    )
    kb.row(
        InlineKeyboardButton(text="🔗 کپی لینک پوشه", callback_data=f"folder:link:{folder_id}"),
        InlineKeyboardButton(text="📊 آمار",           callback_data=f"folder:stats:{folder_id}"),
    )
    kb.row(
        InlineKeyboardButton(text="✏️ ویرایش",         callback_data=f"folder:edit:{folder_id}"),
        InlineKeyboardButton(text="🗑 حذف پوشه",       callback_data=f"folder:delete:{folder_id}"),
    )
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:folders"))
    return kb.as_markup()


def folder_files_menu(files: list, folder_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in files:
        from utils.helpers import file_type_emoji
        emoji = file_type_emoji(f["file_type"])
        name = (f["file_name"] or "بی‌نام")[:25]
        kb.row(InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"file:detail:{f['id']}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"folder:view:{folder_id}"))
    return kb.as_markup()


def file_detail_menu(file_id: str, folder_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔗 کپی لینک",  callback_data=f"file:link:{file_id}"),
        InlineKeyboardButton(text="📊 آمار",       callback_data=f"file:stats:{file_id}"),
    )
    kb.row(
        InlineKeyboardButton(text="✏️ ویرایش",     callback_data=f"file:edit:{file_id}"),
        InlineKeyboardButton(text="🗑 حذف فایل",   callback_data=f"file:delete:{file_id}"),
    )
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"folder:files:{folder_id}"))
    return kb.as_markup()


# ─── Confirm / Cancel ───────────────────────────────────────────────────────

def confirm_cancel(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ تایید", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ انصراف", callback_data=cancel_data),
    )
    return kb.as_markup()


def back_button(callback_data: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=callback_data))
    return kb.as_markup()


# ─── Upload settings wizard ─────────────────────────────────────────────────

def upload_settings_menu(folder_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ انقضا (پیش‌فرض: بدون)",    callback_data=f"upload:expire:{folder_id}"))
    kb.row(InlineKeyboardButton(text="⬇️ حداکثر دانلود (پیش‌فرض: ∞)", callback_data=f"upload:maxdl:{folder_id}"))
    kb.row(InlineKeyboardButton(text="🔑 پسورد (پیش‌فرض: بدون)",     callback_data=f"upload:pass:{folder_id}"))
    kb.row(InlineKeyboardButton(text="🛡 فوروارد پروتکشن: روشن",     callback_data=f"upload:fwdprot:{folder_id}"))
    kb.row(InlineKeyboardButton(text="✅ ذخیره فایل",               callback_data=f"upload:save:{folder_id}"))
    kb.row(InlineKeyboardButton(text="❌ لغو",                       callback_data=f"folder:view:{folder_id}"))
    return kb.as_markup()


# ─── Admin management ───────────────────────────────────────────────────────

def admins_menu(admins: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in admins:
        uname = f"@{a['username']}" if a["username"] else str(a["user_id"])
        kb.row(InlineKeyboardButton(
            text=f"👤 {uname}",
            callback_data=f"admin_mgmt:remove:{a['user_id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ افزودن ادمین", callback_data="admin_mgmt:add"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",       callback_data="admin:back"))
    return kb.as_markup()
