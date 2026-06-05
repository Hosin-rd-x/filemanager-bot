from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    is_admin, get_all_folders, create_folder, get_folder,
    delete_folder, update_folder, get_all_admins, add_admin,
    remove_admin, get_global_stats, get_folder_stats,
    get_files_in_folder, get_setting, set_setting
)
from utils.keyboards import (
    admin_main_menu, folders_menu, folder_detail_menu,
    confirm_cancel, back_button, admins_menu
)
from utils.helpers import generate_id, format_size, seconds_to_human

router = Router()


class AdminStates(StatesGroup):
    waiting_folder_name    = State()
    waiting_folder_desc    = State()
    waiting_folder_pass    = State()
    waiting_edit_folder    = State()
    waiting_add_admin      = State()
    waiting_broadcast      = State()
    confirm_delete_folder  = State()


# ─── /start for admin ──────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    if not await is_admin(msg.from_user.id):
        return  # handled by user handler

    await msg.answer(
        "👋 خوش اومدی به پنل مدیریت فایل منیجر!\n\n"
        "از منوی زیر یه گزینه انتخاب کن:",
        reply_markup=admin_main_menu()
    )


@router.message(Command("panel"))
async def cmd_panel(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.clear()
    await msg.answer("🎛 پنل مدیریت:", reply_markup=admin_main_menu())


# ─── Back / main menu ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:back")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("🎛 پنل مدیریت:", reply_markup=admin_main_menu())


# ─── Folders list ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:folders")
async def cb_folders(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folders = await get_all_folders()
    if folders:
        text = f"📁 <b>پوشه‌ها ({len(folders)} عدد)</b>"
    else:
        text = "📂 هیچ پوشه‌ای وجود ندارد.\n\nاولین پوشه‌ات رو بساز!"
    await cb.message.edit_text(text, reply_markup=folders_menu(folders), parse_mode="HTML")


# ─── Create folder ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "folder:create")
async def cb_create_folder(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    await state.set_state(AdminStates.waiting_folder_name)
    await cb.message.edit_text(
        "📁 <b>ایجاد پوشه جدید</b>\n\nاسم پوشه رو بنویس:",
        reply_markup=back_button("admin:folders"),
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_folder_name)
async def folder_name_received(msg: Message, state: FSMContext):
    await state.update_data(folder_name=msg.text.strip())
    await state.set_state(AdminStates.waiting_folder_desc)
    await msg.answer("📝 توضیحات پوشه رو بنویس (یا /skip برای رد کردن):")


@router.message(AdminStates.waiting_folder_desc)
async def folder_desc_received(msg: Message, state: FSMContext):
    desc = "" if msg.text == "/skip" else msg.text.strip()
    await state.update_data(folder_desc=desc)
    await state.set_state(AdminStates.waiting_folder_pass)
    await msg.answer("🔑 پسورد پوشه رو بنویس (یا /skip برای بدون پسورد):")


@router.message(AdminStates.waiting_folder_pass)
async def folder_pass_received(msg: Message, state: FSMContext):
    pwd = "" if msg.text == "/skip" else msg.text.strip()
    data = await state.get_data()
    folder_id = generate_id(8)
    await create_folder(
        folder_id=folder_id,
        name=data["folder_name"],
        description=data.get("folder_desc", ""),
        password=pwd,
        created_by=msg.from_user.id
    )
    await state.clear()
    bot_username = (await msg.bot.get_me()).username
    lock_text = f"🔒 پسورد: <code>{pwd}</code>\n" if pwd else ""
    await msg.answer(
        f"✅ <b>پوشه ساخته شد!</b>\n\n"
        f"📁 نام: <b>{data['folder_name']}</b>\n"
        f"🆔 آیدی: <code>{folder_id}</code>\n"
        f"{lock_text}"
        f"\n🔗 لینک پوشه:\n"
        f"<code>https://t.me/{bot_username}?start=folder_{folder_id}</code>",
        parse_mode="HTML",
        reply_markup=folder_detail_menu(folder_id)
    )


# ─── View folder ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("folder:view:"))
async def cb_view_folder(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    folder = await get_folder(folder_id)
    if not folder:
        return await cb.answer("❌ پوشه یافت نشد")
    files = await get_files_in_folder(folder_id)
    stats = await get_folder_stats(folder_id)
    lock = "🔒 " if folder["password"] else "🔓 "
    text = (
        f"📁 <b>{lock}{folder['name']}</b>\n\n"
        f"📝 {folder['description'] or 'بدون توضیحات'}\n"
        f"📄 فایل‌ها: <b>{len(files)}</b>\n"
        f"⬇️ کل دانلودها: <b>{stats['total']}</b>\n"
        f"👥 کاربران یکتا: <b>{stats['unique_users']}</b>\n"
        f"🆔 <code>{folder_id}</code>"
    )
    await cb.message.edit_text(text, reply_markup=folder_detail_menu(folder_id), parse_mode="HTML")


# ─── Folder link ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("folder:link:"))
async def cb_folder_link(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    bot_username = (await cb.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=folder_{folder_id}"
    await cb.message.answer(
        f"🔗 <b>لینک پوشه:</b>\n<code>{link}</code>",
        parse_mode="HTML"
    )
    await cb.answer()


# ─── Delete folder ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("folder:delete:"))
async def cb_delete_folder_confirm(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    folder = await get_folder(folder_id)
    await cb.message.edit_text(
        f"⚠️ آیا مطمئنی؟\n\nپوشه «<b>{folder['name']}</b>» و تمام فایل‌هاش حذف میشه!",
        reply_markup=confirm_cancel(
            f"folder:confirm_delete:{folder_id}",
            f"folder:view:{folder_id}"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("folder:confirm_delete:"))
async def cb_delete_folder_do(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    folder_id = cb.data.split(":")[2]
    await delete_folder(folder_id)
    await cb.message.edit_text("🗑 پوشه حذف شد.", reply_markup=back_button("admin:folders"))


# ─── Global stats ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def cb_stats(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    s = await get_global_stats()
    text = (
        "📊 <b>آمار کلی ربات</b>\n\n"
        f"📄 فایل‌های فعال:       <b>{s['active_files']}</b>\n"
        f"📁 تعداد پوشه‌ها:        <b>{s['folders']}</b>\n"
        f"⬇️ کل دانلودها:         <b>{s['total_downloads']}</b>\n"
        f"👥 کاربران یکتا:         <b>{s['unique_users']}</b>\n"
        f"💾 حجم کل فایل‌ها:       <b>{format_size(s['total_size'])}</b>"
    )
    await cb.message.edit_text(text, reply_markup=back_button("admin:back"), parse_mode="HTML")


# ─── Admin management ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:admins")
async def cb_admins(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    admins = await get_all_admins()
    await cb.message.edit_text(
        f"👥 <b>لیست ادمین‌ها ({len(admins)} نفر)</b>",
        reply_markup=admins_menu(admins),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_mgmt:add")
async def cb_add_admin(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    await state.set_state(AdminStates.waiting_add_admin)
    await cb.message.edit_text(
        "👤 آیدی عددی کاربر جدید رو بنویس:",
        reply_markup=back_button("admin:admins")
    )


@router.message(AdminStates.waiting_add_admin)
async def add_admin_received(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ آیدی باید عدد باشه!")
    await add_admin(uid)
    await state.clear()
    await msg.answer(f"✅ کاربر {uid} به ادمین‌ها اضافه شد.", reply_markup=back_button("admin:admins"))


@router.callback_query(F.data.startswith("admin_mgmt:remove:"))
async def cb_remove_admin(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    uid = int(cb.data.split(":")[2])
    if uid == cb.from_user.id:
        return await cb.answer("❌ نمیتونی خودت رو حذف کنی!")
    await remove_admin(uid)
    await cb.answer("✅ ادمین حذف شد")
    admins = await get_all_admins()
    await cb.message.edit_text(
        f"👥 <b>لیست ادمین‌ها ({len(admins)} نفر)</b>",
        reply_markup=admins_menu(admins),
        parse_mode="HTML"
    )


# ─── Settings ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:settings")
async def cb_settings(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    force_join = await get_setting("force_join_channel", "")
    welcome = await get_setting("welcome_message", "سلام! فایل مورد نظرت رو انتخاب کن.")
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 تنظیم کانال اجباری", callback_data="settings:force_join"))
    kb.row(InlineKeyboardButton(text="💬 پیام خوش‌آمد",       callback_data="settings:welcome"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",             callback_data="admin:back"))
    text = (
        "⚙️ <b>تنظیمات</b>\n\n"
        f"📢 کانال اجباری: <code>{force_join or 'ندارد'}</code>\n"
        f"💬 پیام خوش‌آمد: {welcome[:60]}..."
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
