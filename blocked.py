from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import is_admin, get_all_admins, block_user, unblock_user, is_blocked
from utils.keyboards import back_button

router = Router()


class BlockStates(StatesGroup):
    waiting_block_id   = State()
    waiting_unblock_id = State()


@router.callback_query(F.data == "admin:blocked")
async def cb_blocked(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    import aiosqlite
    async with aiosqlite.connect("filemanager.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM blocked_users ORDER BY blocked_at DESC") as cur:
            blocked = await cur.fetchall()

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for u in blocked:
        kb.row(InlineKeyboardButton(
            text=f"🚫 {u['user_id']} — رفع بلاک",
            callback_data=f"block:remove:{u['user_id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ بلاک کاربر", callback_data="block:add"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",     callback_data="admin:back"))

    text = f"🚫 <b>کاربران بلاک‌شده ({len(blocked)} نفر)</b>"
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "block:add")
async def cb_block_add(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    await state.set_state(BlockStates.waiting_block_id)
    await cb.message.edit_text(
        "🚫 آیدی عددی کاربر مورد نظر برای بلاک را وارد کنید:",
        reply_markup=back_button("admin:blocked")
    )


@router.message(BlockStates.waiting_block_id)
async def block_id_received(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        return await msg.answer("❌ آیدی باید عدد باشد!")
    await block_user(uid, reason="توسط ادمین")
    await state.clear()
    await msg.answer(f"✅ کاربر {uid} بلاک شد.", reply_markup=back_button("admin:blocked"))


@router.callback_query(F.data.startswith("block:remove:"))
async def cb_block_remove(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id): return await cb.answer("⛔ دسترسی ندارید")
    uid = int(cb.data.split(":")[2])
    await unblock_user(uid)
    await cb.answer(f"✅ کاربر {uid} رفع بلاک شد")
    # Refresh list
    import aiosqlite
    async with aiosqlite.connect("filemanager.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM blocked_users ORDER BY blocked_at DESC") as cur:
            blocked = await cur.fetchall()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for u in blocked:
        kb.row(InlineKeyboardButton(
            text=f"🚫 {u['user_id']} — رفع بلاک",
            callback_data=f"block:remove:{u['user_id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ بلاک کاربر", callback_data="block:add"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",     callback_data="admin:back"))
    await cb.message.edit_text(
        f"🚫 <b>کاربران بلاک‌شده ({len(blocked)} نفر)</b>",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )
