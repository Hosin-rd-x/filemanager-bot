from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    is_admin, get_folder, add_file, get_files_in_folder,
    get_file, get_file_stats, delete_file, log_download
)
from utils.keyboards import (
    folder_files_menu, file_detail_menu, back_button,
    upload_settings_menu, folder_detail_menu
)
from utils.helpers import (
    generate_id, format_size, file_type_emoji,
    calc_expires_at, seconds_to_human, parse_expire_input
)

router = Router()

SUPPORTED_TYPES = ("document", "video", "audio", "photo", "voice", "animation")


class UploadStates(StatesGroup):
    waiting_file        = State()
    waiting_expire      = State()
    waiting_max_dl      = State()
    waiting_password    = State()
    confirming_settings = State()


def _get_file_info(msg: Message):
    """Extract file info from any message type."""
    if msg.document:
        return msg.document.file_id, msg.document.file_unique_id, \
               msg.document.file_name, "document", msg.document.file_size
    elif msg.video:
        return msg.video.file_id, msg.video.file_unique_id, \
               msg.video.file_name or "video.mp4", "video", msg.video.file_size
    elif msg.audio:
        return msg.audio.file_id, msg.audio.file_unique_id, \
               msg.audio.file_name or "audio.mp3", "audio", msg.audio.file_size
    elif msg.voice:
        return msg.voice.file_id, msg.voice.file_unique_id, \
               "voice.ogg", "voice", msg.voice.file_size
    elif msg.photo:
        p = msg.photo[-1]
        return p.file_id, p.file_unique_id, "photo.jpg", "photo", p.file_size
    elif msg.animation:
        return msg.animation.file_id, msg.animation.file_unique_id, \
               msg.animation.file_name or "anim.gif", "animation", msg.animation.file_size
    return None


# ─── Start upload for a specific folder ───────────────────────────────────

@router.callback_query(F.data.startswith("folder:upload:"))
async def cb_start_upload(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    folder = await get_folder(folder_id)
    if not folder:
        return await cb.answer("❌ پوشه یافت نشد")
    await state.set_state(UploadStates.waiting_file)
    await state.update_data(
        folder_id=folder_id,
        expire_seconds=0,
        max_downloads=0,
        password="",
        forward_protect=1
    )
    await cb.message.edit_text(
        f"📤 <b>آپلود به پوشه «{folder['name']}»</b>\n\n"
        "فایل، عکس، ویدیو یا صدا رو بفرست.\n"
        "می‌تونی چندتا فایل پشت سر هم بفرستی.\n\n"
        "⚙️ تنظیمات پیش‌فرض:\n"
        "• انقضا: ♾ بدون محدودیت\n"
        "• دانلود: ♾ بدون محدودیت\n"
        "• پسورد: ندارد\n"
        "• فوروارد: ❌ غیرفعال\n\n"
        "برای تغییر تنظیمات قبل از فرستادن فایل:",
        parse_mode="HTML",
        reply_markup=upload_settings_menu(folder_id)
    )


# ─── Upload settings: expire ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("upload:expire:"))
async def cb_set_expire(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_expire)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text(
        "⏳ <b>زمان انقضا</b>\n\n"
        "مثال‌ها:\n"
        "• <code>1d</code> = ۱ روز\n"
        "• <code>12h</code> = ۱۲ ساعت\n"
        "• <code>30m</code> = ۳۰ دقیقه\n"
        "• <code>0</code> = بدون انقضا\n\n"
        "مقدار رو بنویس:",
        reply_markup=back_button(f"folder:upload:{folder_id}"),
        parse_mode="HTML"
    )


@router.message(UploadStates.waiting_expire)
async def expire_received(msg: Message, state: FSMContext):
    secs = parse_expire_input(msg.text)
    if secs == -1:
        return await msg.answer("❌ فرمت اشتباهه. مثال: 1d یا 12h یا 0")
    data = await state.get_data()
    await state.update_data(expire_seconds=secs)
    await state.set_state(UploadStates.waiting_file)
    folder_id = data["folder_id"]
    await msg.answer(
        f"✅ انقضا تنظیم شد: <b>{seconds_to_human(secs)}</b>",
        parse_mode="HTML",
        reply_markup=upload_settings_menu(folder_id)
    )


# ─── Upload settings: max downloads ───────────────────────────────────────

@router.callback_query(F.data.startswith("upload:maxdl:"))
async def cb_set_maxdl(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_max_dl)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text(
        "⬇️ <b>حداکثر تعداد دانلود</b>\n\n"
        "عدد دلخواه رو بنویس (0 = بدون محدودیت):",
        reply_markup=back_button(f"folder:upload:{folder_id}"),
        parse_mode="HTML"
    )


@router.message(UploadStates.waiting_max_dl)
async def maxdl_received(msg: Message, state: FSMContext):
    try:
        n = int(msg.text.strip())
        if n < 0: raise ValueError
    except ValueError:
        return await msg.answer("❌ عدد صحیح غیر منفی وارد کن")
    data = await state.get_data()
    await state.update_data(max_downloads=n)
    await state.set_state(UploadStates.waiting_file)
    folder_id = data["folder_id"]
    label = f"{n} دانلود" if n > 0 else "بدون محدودیت"
    await msg.answer(
        f"✅ حداکثر دانلود: <b>{label}</b>",
        parse_mode="HTML",
        reply_markup=upload_settings_menu(folder_id)
    )


# ─── Upload settings: password ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("upload:pass:"))
async def cb_set_pass(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_password)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text(
        "🔑 <b>پسورد فایل</b>\n\n"
        "پسورد دلخواه رو بنویس (یا /skip برای بدون پسورد):",
        reply_markup=back_button(f"folder:upload:{folder_id}"),
        parse_mode="HTML"
    )


@router.message(UploadStates.waiting_password)
async def password_received(msg: Message, state: FSMContext):
    pwd = "" if msg.text == "/skip" else msg.text.strip()
    data = await state.get_data()
    await state.update_data(password=pwd)
    await state.set_state(UploadStates.waiting_file)
    folder_id = data["folder_id"]
    label = f"<code>{pwd}</code>" if pwd else "ندارد"
    await msg.answer(
        f"✅ پسورد: {label}",
        parse_mode="HTML",
        reply_markup=upload_settings_menu(folder_id)
    )


# ─── Toggle forward protection ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("upload:fwdprot:"))
async def cb_toggle_fwdprot(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current = data.get("forward_protect", 1)
    new_val = 0 if current else 1
    await state.update_data(forward_protect=new_val)
    folder_id = cb.data.split(":")[2]
    status = "روشن ✅" if new_val else "خاموش ❌"
    await cb.answer(f"فوروارد پروتکشن: {status}")
    await cb.message.edit_reply_markup(reply_markup=upload_settings_menu(folder_id))


# ─── Receive file ──────────────────────────────────────────────────────────

@router.message(UploadStates.waiting_file, F.content_type.in_(SUPPORTED_TYPES))
async def file_received(msg: Message, state: FSMContext):
    info = _get_file_info(msg)
    if not info:
        return await msg.answer("❌ این نوع فایل پشتیبانی نمیشه")

    tg_file_id, tg_unique_id, file_name, file_type, file_size = info
    caption = msg.caption or ""
    data = await state.get_data()
    folder_id      = data.get("folder_id", "")
    expire_seconds = data.get("expire_seconds", 0)
    max_downloads  = data.get("max_downloads", 0)
    password       = data.get("password", "")
    forward_protect= data.get("forward_protect", 1)

    file_pk = generate_id(10)
    expires_at = calc_expires_at(expire_seconds)

    await add_file(
        file_id_pk=file_pk,
        folder_id=folder_id,
        telegram_file_id=tg_file_id,
        file_unique_id=tg_unique_id,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size or 0,
        caption=caption,
        password=password,
        max_downloads=max_downloads,
        expire_seconds=expire_seconds,
        forward_protect=forward_protect,
        created_by=msg.from_user.id,
        expires_at=expires_at
    )

    bot_username = (await msg.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=file_{file_pk}"
    emoji = file_type_emoji(file_type)

    lines = [
        f"✅ <b>فایل ذخیره شد!</b>",
        f"{emoji} <b>{file_name}</b>",
        f"💾 حجم: {format_size(file_size or 0)}",
        f"⏳ انقضا: {seconds_to_human(expire_seconds)}",
        f"⬇️ محدودیت دانلود: {'بدون محدودیت' if not max_downloads else max_downloads}",
        f"🔑 پسورد: {'ندارد' if not password else f'<code>{password}</code>'}",
        f"🛡 فوروارد پروتکشن: {'✅' if forward_protect else '❌'}",
        f"\n🔗 <b>لینک دانلود:</b>",
        f"<code>{link}</code>"
    ]
    await msg.answer("\n".join(lines), parse_mode="HTML")


# ─── Files list in folder ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("folder:files:"))
async def cb_folder_files(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    files = await get_files_in_folder(folder_id)
    if not files:
        return await cb.message.edit_text(
            "📂 این پوشه هنوز فایلی ندارد.",
            reply_markup=back_button(f"folder:view:{folder_id}")
        )
    await cb.message.edit_text(
        f"📋 <b>فایل‌ها ({len(files)} عدد)</b>\nروی هر فایل کلیک کن:",
        reply_markup=folder_files_menu(files, folder_id),
        parse_mode="HTML"
    )


# ─── File detail ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("file:detail:"))
async def cb_file_detail(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    if not f:
        return await cb.answer("❌ فایل یافت نشد")
    stats = await get_file_stats(file_id)
    emoji = file_type_emoji(f["file_type"])
    from utils.helpers import is_expired
    status = "❌ منقضی" if is_expired(f["expires_at"]) else ("✅ فعال" if f["is_active"] else "🚫 غیرفعال")
    text = (
        f"{emoji} <b>{f['file_name']}</b>\n\n"
        f"📊 وضعیت: {status}\n"
        f"💾 حجم: {format_size(f['file_size'])}\n"
        f"⬇️ دانلود شده: <b>{f['download_count']}</b> بار\n"
        f"👥 کاربران یکتا: <b>{stats['unique_users']}</b>\n"
        f"📅 ساخته شده: {f['created_at']}\n"
        f"⏳ انقضا: {f['expires_at'] or 'ندارد'}\n"
        f"🔑 پسورد: {f['password'] or 'ندارد'}\n"
        f"🛡 فوروارد پروتکشن: {'✅' if f['forward_protect'] else '❌'}\n"
        f"🔢 محدودیت دانلود: {f['max_downloads'] or '∞'}"
    )
    await cb.message.edit_text(text, reply_markup=file_detail_menu(file_id, f["folder_id"]), parse_mode="HTML")


# ─── File link ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("file:link:"))
async def cb_file_link(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    bot_username = (await cb.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=file_{file_id}"
    await cb.message.answer(
        f"🔗 <b>لینک دانلود فایل:</b>\n<code>{link}</code>",
        parse_mode="HTML"
    )
    await cb.answer()


# ─── File stats ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("file:stats:"))
async def cb_file_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    stats = await get_file_stats(file_id)
    text = (
        f"📊 <b>آمار فایل</b>\n\n"
        f"📄 {f['file_name']}\n"
        f"⬇️ کل دانلود: <b>{stats['total']}</b>\n"
        f"👥 کاربران یکتا: <b>{stats['unique_users']}</b>\n"
        f"🔢 دانلود شده / حداکثر: {f['download_count']} / {f['max_downloads'] or '∞'}"
    )
    await cb.message.edit_text(text, reply_markup=back_button(f"file:detail:{file_id}"), parse_mode="HTML")


# ─── File folder stats ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("folder:stats:"))
async def cb_folder_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    folder = await get_folder(folder_id)
    stats = await get_folder_stats(folder_id)
    files = await get_files_in_folder(folder_id)
    text = (
        f"📊 <b>آمار پوشه «{folder['name']}»</b>\n\n"
        f"📄 فایل‌های فعال: <b>{len(files)}</b>\n"
        f"⬇️ کل دانلودها: <b>{stats['total']}</b>\n"
        f"👥 کاربران یکتا: <b>{stats['unique_users']}</b>"
    )
    await cb.message.edit_text(text, reply_markup=back_button(f"folder:view:{folder_id}"), parse_mode="HTML")


# ─── Delete file ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("file:delete:"))
async def cb_delete_file(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    from utils.keyboards import confirm_cancel
    await cb.message.edit_text(
        f"⚠️ حذف فایل «<b>{f['file_name']}</b>»؟",
        reply_markup=confirm_cancel(
            f"file:confirm_delete:{file_id}",
            f"file:detail:{file_id}"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("file:confirm_delete:"))
async def cb_confirm_delete_file(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    folder_id = f["folder_id"] if f else ""
    await delete_file(file_id)
    await cb.message.edit_text(
        "🗑 فایل حذف شد.",
        reply_markup=back_button(f"folder:files:{folder_id}")
    )
