from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import (
    is_admin, get_folder, add_file, get_files_in_folder,
    get_file, get_file_stats, delete_file
)
from keyboards import (
    folder_files_menu, file_detail_menu, back_button,
    upload_settings_menu, confirm_cancel
)
from helpers import (
    generate_id, format_size, file_type_emoji,
    calc_expires_at, seconds_to_human, parse_expire_input
)

router = Router()
SUPPORTED_TYPES = ("document", "video", "audio", "photo", "voice", "animation")

class UploadStates(StatesGroup):
    waiting_file     = State()
    waiting_expire   = State()
    waiting_max_dl   = State()
    waiting_password = State()

def _get_file_info(msg: Message):
    if msg.document:
        return msg.document.file_id, msg.document.file_unique_id, msg.document.file_name, "document", msg.document.file_size
    elif msg.video:
        return msg.video.file_id, msg.video.file_unique_id, msg.video.file_name or "video.mp4", "video", msg.video.file_size
    elif msg.audio:
        return msg.audio.file_id, msg.audio.file_unique_id, msg.audio.file_name or "audio.mp3", "audio", msg.audio.file_size
    elif msg.voice:
        return msg.voice.file_id, msg.voice.file_unique_id, "voice.ogg", "voice", msg.voice.file_size
    elif msg.photo:
        p = msg.photo[-1]
        return p.file_id, p.file_unique_id, "photo.jpg", "photo", p.file_size
    elif msg.animation:
        return msg.animation.file_id, msg.animation.file_unique_id, msg.animation.file_name or "anim.gif", "animation", msg.animation.file_size
    return None

@router.callback_query(F.data.startswith("folder:upload:"))
async def cb_start_upload(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    folder = await get_folder(folder_id)
    if not folder: return await cb.answer("❌ پوشه یافت نشد")
    await state.set_state(UploadStates.waiting_file)
    await state.update_data(folder_id=folder_id, expire_seconds=0, max_downloads=0, password="", forward_protect=1)
    await cb.message.edit_text(
        f"📤 <b>آپلود به پوشه «{folder['name']}»</b>\n\nفایل رو بفرست یا تنظیمات رو تغییر بده:",
        parse_mode="HTML", reply_markup=upload_settings_menu(folder_id))

@router.callback_query(F.data.startswith("upload:expire:"))
async def cb_set_expire(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_expire)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text(
        "⏳ زمان انقضا:\n• <code>1d</code> = ۱ روز\n• <code>12h</code> = ۱۲ ساعت\n• <code>30m</code> = ۳۰ دقیقه\n• <code>0</code> = بدون انقضا",
        reply_markup=back_button(f"folder:upload:{folder_id}"), parse_mode="HTML")

@router.message(UploadStates.waiting_expire)
async def expire_received(msg: Message, state: FSMContext):
    secs = parse_expire_input(msg.text)
    if secs == -1: return await msg.answer("❌ فرمت اشتباهه. مثال: 1d یا 12h یا 0")
    data = await state.get_data()
    await state.update_data(expire_seconds=secs)
    await state.set_state(UploadStates.waiting_file)
    await msg.answer(f"✅ انقضا: <b>{seconds_to_human(secs)}</b>", parse_mode="HTML",
                     reply_markup=upload_settings_menu(data["folder_id"]))

@router.callback_query(F.data.startswith("upload:maxdl:"))
async def cb_set_maxdl(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_max_dl)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text("⬇️ حداکثر دانلود (0 = بدون محدودیت):",
                                reply_markup=back_button(f"folder:upload:{folder_id}"))

@router.message(UploadStates.waiting_max_dl)
async def maxdl_received(msg: Message, state: FSMContext):
    try:
        n = int(msg.text.strip())
        if n < 0: raise ValueError
    except ValueError:
        return await msg.answer("❌ عدد صحیح وارد کن")
    data = await state.get_data()
    await state.update_data(max_downloads=n)
    await state.set_state(UploadStates.waiting_file)
    await msg.answer(f"✅ حداکثر دانلود: <b>{n or 'بدون محدودیت'}</b>", parse_mode="HTML",
                     reply_markup=upload_settings_menu(data["folder_id"]))

@router.callback_query(F.data.startswith("upload:pass:"))
async def cb_set_pass(cb: CallbackQuery, state: FSMContext):
    folder_id = cb.data.split(":")[2]
    await state.set_state(UploadStates.waiting_password)
    await state.update_data(folder_id=folder_id)
    await cb.message.edit_text("🔑 پسورد فایل (یا /skip):",
                                reply_markup=back_button(f"folder:upload:{folder_id}"))

@router.message(UploadStates.waiting_password)
async def password_received(msg: Message, state: FSMContext):
    pwd = "" if msg.text == "/skip" else msg.text.strip()
    data = await state.get_data()
    await state.update_data(password=pwd)
    await state.set_state(UploadStates.waiting_file)
    await msg.answer(f"✅ پسورد: {pwd or 'ندارد'}", reply_markup=upload_settings_menu(data["folder_id"]))

@router.callback_query(F.data.startswith("upload:fwdprot:"))
async def cb_toggle_fwdprot(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = 0 if data.get("forward_protect", 1) else 1
    await state.update_data(forward_protect=new_val)
    folder_id = cb.data.split(":")[2]
    await cb.answer(f"فوروارد پروتکشن: {'روشن ✅' if new_val else 'خاموش ❌'}")
    await cb.message.edit_reply_markup(reply_markup=upload_settings_menu(folder_id))

@router.message(UploadStates.waiting_file, F.content_type.in_(SUPPORTED_TYPES))
async def file_received(msg: Message, state: FSMContext):
    info = _get_file_info(msg)
    if not info: return await msg.answer("❌ این نوع فایل پشتیبانی نمیشه")
    tg_file_id, tg_unique_id, file_name, file_type, file_size = info
    data = await state.get_data()
    file_pk = generate_id(10)
    expires_at = calc_expires_at(data.get("expire_seconds", 0))
    await add_file(file_id_pk=file_pk, folder_id=data.get("folder_id",""),
                   telegram_file_id=tg_file_id, file_unique_id=tg_unique_id,
                   file_name=file_name, file_type=file_type, file_size=file_size or 0,
                   caption=msg.caption or "", password=data.get("password",""),
                   max_downloads=data.get("max_downloads",0), expire_seconds=data.get("expire_seconds",0),
                   forward_protect=data.get("forward_protect",1), created_by=msg.from_user.id,
                   expires_at=expires_at)
    bot_username = (await msg.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=file_{file_pk}"
    await msg.answer(
        f"✅ <b>ذخیره شد!</b>\n{file_type_emoji(file_type)} {file_name}\n"
        f"💾 {format_size(file_size or 0)}\n⏳ {seconds_to_human(data.get('expire_seconds',0))}\n"
        f"⬇️ {data.get('max_downloads',0) or '∞'} | 🔑 {data.get('password','') or 'ندارد'}\n\n"
        f"🔗 <code>{link}</code>", parse_mode="HTML")

@router.callback_query(F.data.startswith("folder:files:"))
async def cb_folder_files(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    files = await get_files_in_folder(folder_id)
    if not files:
        return await cb.message.edit_text("📂 این پوشه فایلی ندارد.", reply_markup=back_button(f"folder:view:{folder_id}"))
    await cb.message.edit_text(f"📋 <b>فایل‌ها ({len(files)})</b>",
                                reply_markup=folder_files_menu(files, folder_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("file:detail:"))
async def cb_file_detail(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    if not f: return await cb.answer("❌ فایل یافت نشد")
    stats = await get_file_stats(file_id)
    from helpers import is_expired
    status = "❌ منقضی" if is_expired(f["expires_at"]) else ("✅ فعال" if f["is_active"] else "🚫 غیرفعال")
    await cb.message.edit_text(
        f"{file_type_emoji(f['file_type'])} <b>{f['file_name']}</b>\n\n"
        f"📊 {status} | ⬇️ {f['download_count']} بار\n"
        f"👥 {stats['unique_users']} کاربر یکتا\n"
        f"🔑 {f['password'] or 'ندارد'} | 🛡 {'✅' if f['forward_protect'] else '❌'}",
        reply_markup=file_detail_menu(file_id, f["folder_id"]), parse_mode="HTML")

@router.callback_query(F.data.startswith("file:link:"))
async def cb_file_link(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    bot_username = (await cb.bot.get_me()).username
    await cb.message.answer(f"🔗 <code>https://t.me/{bot_username}?start=file_{file_id}</code>", parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("file:stats:"))
async def cb_file_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    stats = await get_file_stats(file_id)
    await cb.message.edit_text(
        f"📊 <b>آمار</b>\n⬇️ کل: {stats['total']} | 👥 یکتا: {stats['unique_users']}\n"
        f"شده/حداکثر: {f['download_count']}/{f['max_downloads'] or '∞'}",
        reply_markup=back_button(f"file:detail:{file_id}"), parse_mode="HTML")

@router.callback_query(F.data.startswith("folder:stats:"))
async def cb_folder_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    from db import get_folder_stats
    folder = await get_folder(folder_id)
    stats = await get_folder_stats(folder_id)
    files = await get_files_in_folder(folder_id)
    await cb.message.edit_text(
        f"📊 <b>«{folder['name']}»</b>\n📄 {len(files)} فایل | ⬇️ {stats['total']} دانلود | 👥 {stats['unique_users']} کاربر",
        reply_markup=back_button(f"folder:view:{folder_id}"), parse_mode="HTML")

@router.callback_query(F.data.startswith("file:delete:"))
async def cb_delete_file(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    await cb.message.edit_text(f"⚠️ حذف «<b>{f['file_name']}</b>»؟",
                                reply_markup=confirm_cancel(f"file:confirm_delete:{file_id}", f"file:detail:{file_id}"),
                                parse_mode="HTML")

@router.callback_query(F.data.startswith("file:confirm_delete:"))
async def cb_confirm_delete_file(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    file_id = cb.data.split(":")[2]
    f = await get_file(file_id)
    folder_id = f["folder_id"] if f else ""
    await delete_file(file_id)
    await cb.message.edit_text("🗑 حذف شد.", reply_markup=back_button(f"folder:files:{folder_id}"))
