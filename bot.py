import os
import json
import asyncio
import glob
import re
import random
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, ChatPrivileges
from pyrogram.enums import ParseMode, ChatType
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, FloodWait, RPCError

# --- SAFE DATABASE CLEANUP ---
def clean_journals():
    for journal in glob.glob("*.session-journal"):
        try: os.remove(journal)
        except: pass
clean_journals()

# ==========================================
# 🛑 CONFIGURATION & PREMIUM EMOJIS 🛑
# ==========================================
API_ID = 34203777
API_HASH = "28879e1da5422e2d7a2f2beb187d465e"
BOT_TOKEN = "8380584487:AAE1a61nGHCC3YbBkBB3VqQ_ib6wyJ92ExI"
ADMIN_ID = 8157285805  

# 💎 PREMIUM EMOJIS (HTML Format for Text Messages)
P_ADMIN = '<emoji id="5242625192475244017">🛠</emoji>'
P_HELP = '<emoji id="5364125638275910182">📖</emoji>'
P_CRYSTAL = '<emoji id="6314316435879370390">🔮</emoji>'
P_SPARKLES = '<emoji id="4956436416142771580">✨</emoji>'
P_CHECK = '<emoji id="5249245047043428865">✅</emoji>'
P_EPIC = '<emoji id="5222079954421818267">🆒</emoji>'
P_DIAMOND = '<emoji id="5201914481671682382">💎</emoji>'
P_STAR = '<emoji id="5469744063815102906">🌟</emoji>'
P_HEART = '💜'

LIGHTNING_IDS = ["5220128956937678240", "5219680686906029436", "5222104830872400346", "5222244748022001872"]
def get_p_lightning(): return f'<emoji id="{random.choice(LIGHTNING_IDS)}">⚡</emoji>'

bot = Client("master_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
userbot = None

admin_states = {}
config_data = {
    "users": [], "admins": [ADMIN_ID],
    "fsub_channels": [], "fsub_image": None
}
db_lock = asyncio.Lock()

async def load_config():
    global config_data
    if os.path.exists("config.json"):
        async with db_lock:
            with open("config.json", "r") as f:
                saved = json.load(f)
                config_data.update(saved)
                if ADMIN_ID not in config_data.get("admins", []):
                    config_data.setdefault("admins", []).append(ADMIN_ID)

async def save_config():
    async with db_lock:
        with open("config.json", "w") as f:
            json.dump(config_data, f)

async def start_userbot_if_configured():
    global userbot
    await load_config()
    if "api_id" in config_data and "api_hash" in config_data:
        try:
            print("Starting saved Userbot session...")
            userbot = Client("userbot", api_id=config_data["api_id"], api_hash=config_data["api_hash"])
            await userbot.start()
            return True
        except Exception as e: print(f"Failed to start userbot: {e}")
    return False

def parse_time(time_str):
    time_str = time_str.lower().strip()
    if time_str in ["0", "off"]: return 0
    match = re.match(r"(\d+)([smhd]?)", time_str)
    if not match: return None
    val, unit = int(match.group(1)), match.group(2)
    if unit in ['s', '']: return val
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    return None

async def is_user_admin_safe(client: Client, message: Message):
    if message.chat.type == ChatType.CHANNEL: return True
    if message.sender_chat and message.sender_chat.id == message.chat.id: return True
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status.name in ["OWNER", "ADMINISTRATOR"]
    except: return False

def is_bot_admin(user_id):
    return user_id in config_data.get("admins", [])

async def delayed_delete(chat_id, message_id, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        if userbot and userbot.is_connected: await userbot.delete_messages(chat_id, message_id)
        else: await bot.delete_messages(chat_id, message_id)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        try: await bot.delete_messages(chat_id, message_id)
        except: pass
    except: pass

# --- UI GENERATORS ---
def get_start_menu(bot_username, is_userbot_connected, is_admin):
    text = (
        f"{P_EPIC} <b>Aᴜᴛᴏ Pᴏsᴛ Dᴇʟᴇᴛᴇʀ Bᴏᴛ</b> {P_STAR}\n\n"
        f"<i>{P_SPARKLES} ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛs ᴀғᴛᴇʀ ᴀ sᴘᴇᴄɪғɪᴇᴅ ᴅᴇʟᴀʏ</i>\n\n"
        f"<b>Hᴏᴡ Tᴏ Usᴇ:</b>\n"
        f"1. ᴍᴀᴋᴇ ᴍᴇ <b>ᴀᴅᴍɪɴ</b> ɪɴ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ\n"
        f"2. Rᴇᴘʟʏ ᴛᴏ ᴀ ᴘᴏsᴛ ᴏʀ ᴀᴅᴅ /setdelay ɪɴ ᴘᴏsᴛ ᴛᴇxᴛ!\n\n"
    )
    
    if is_admin:
        status_emoji = P_CHECK if is_userbot_connected else "❌"
        text += f"<b>Aᴅᴍɪɴ Sᴛᴀᴛᴜs:</b>\nUsᴇʀʙᴏᴛ Cᴏɴɴᴇᴄᴛᴇᴅ: {status_emoji}\n"

    add_url = f"https://t.me/{bot_username}?startchannel&admin=delete_messages+invite_users+promote_members+manage_chat"
    
    btn_help = InlineKeyboardButton("Hᴇʟᴘ & Gᴜɪᴅᴇ", callback_data="help_menu")
    btn_help.custom_emoji = "5364125638275910182"
    
    btn_admin = InlineKeyboardButton("Aᴅᴍɪɴ Pᴀɴᴇʟ", callback_data="admin_panel")
    btn_admin.custom_emoji = "5242625192475244017"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Aᴅᴅ Tᴏ Cʜᴀɴɴᴇʟ", url=add_url)],
        [btn_help, btn_admin]
    ])
    return text, keyboard

def get_fsub_ui():
    channels = [ch for ch in config_data.get("fsub_channels", []) if ch.get("fsub", True)]
    buttons, row = [], []
    for ch in channels:
        row.append(InlineKeyboardButton("📢 Jᴏɪɴ", url=ch["link"]))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    verify_btn = InlineKeyboardButton("Jᴏɪɴᴇᴅ", callback_data="verify_fsub")
    verify_btn.custom_emoji = "5249245047043428865"
    buttons.append([verify_btn])
    
    text = f"{P_HEART} <b>Jᴏɪɴ Rᴇǫᴜɪʀᴇᴅ</b>\n\nPʟᴇᴀsᴇ ᴊᴏɪɴ ᴀʟʟ ᴛʜᴇ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ."
    return text, InlineKeyboardMarkup(buttons)

async def check_user_fsub(client, user_id):
    channels = [ch for ch in config_data.get("fsub_channels", []) if ch.get("fsub", True)]
    if not channels: return True
    if is_bot_admin(user_id): return True 
    for ch in channels:
        try:
            member = await client.get_chat_member(ch["id"], user_id)
            if member.status.name in ["LEFT", "KICKED", "RESTRICTED", "BANNED"]: return False
        except: return False
    return True

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    admin_states[message.from_user.id] = {"step": "IDLE"}
    user_id = message.from_user.id
    
    if user_id not in config_data.get("users", []):
        config_data.setdefault("users", []).append(user_id)
        await save_config()
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"{P_STAR} <b>Nᴇᴡ Usᴇʀ Nᴏᴛɪғɪᴄᴀᴛɪᴏɴ</b> {P_STAR}\n\n"
                    f"👤 <b>Usᴇʀ:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                    f"🆔 <b>Usᴇʀ Iᴅ:</b> <code>{user_id}</code>\n\n"
                    f"🌝 <b>Tᴏᴛᴀʟ Usᴇʀs Cᴏᴜɴᴛ:</b> {len(config_data['users'])}"
                ), parse_mode=ParseMode.HTML, disable_web_page_preview=True
            )
        except: pass

    is_joined = await check_user_fsub(client, user_id)
    if not is_joined:
        text, kb = get_fsub_ui()
        img = config_data.get("fsub_image")
        if img: await message.reply_photo(photo=img, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
        else: await message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        return

    bot_info = await bot.get_me()
    is_admin = is_bot_admin(user_id)
    text, keyboard = get_start_menu(bot_info.username, bool(userbot and userbot.is_connected), is_admin)
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("verify_fsub"))
async def verify_fsub_callback(client, callback_query):
    is_joined = await check_user_fsub(client, callback_query.from_user.id)
    if not is_joined:
        return await callback_query.answer("❌ Pʟᴇᴀsᴇ Jᴏɪɴ ᴀʟʟ Cʜᴀɴɴᴇʟs ғɪʀsᴛ!", show_alert=True)
    
    await callback_query.answer("✅ Vᴇʀɪғɪᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!")
    bot_info = await bot.get_me()
    is_admin = is_bot_admin(callback_query.from_user.id)
    text, keyboard = get_start_menu(bot_info.username, bool(userbot and userbot.is_connected), is_admin)
    
    if callback_query.message.photo:
        await callback_query.message.delete()
        await client.send_message(callback_query.message.chat.id, text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("help_menu"))
async def help_menu_callback(client, callback_query):
    text = (
        f"{P_HELP} <b>Gᴜɪᴅᴇ & Cᴏᴍᴍᴀɴᴅs</b> {P_DIAMOND}\n\n"
        f"<b>1. Sɪɴɢʟᴇ Pᴏsᴛ Tɪᴍᴇʀ (Iɴ Tᴇxᴛ):</b>\n"
        f"➜ Iɴᴄʟᴜᴅᴇ <code>/setdelay 10s</code> ᴀɴʏᴡʜᴇʀᴇ ɪɴ ʏᴏᴜʀ ᴘᴏsᴛ ᴛᴏ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ *ᴛʜᴀᴛ sᴘᴇᴄɪғɪᴄ ᴘᴏsᴛ*.\n\n"
        f"<b>2. Sɪɴɢʟᴇ Pᴏsᴛ Tɪᴍᴇʀ (Rᴇᴘʟʏ):</b>\n"
        f"➜ <b>Rᴇᴘʟʏ</b> ᴛᴏ ᴀɴʏ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ <code>/setdelay 1m</code> ᴛᴏ ᴅᴇʟᴇᴛᴇ ɪᴛ.\n\n"
        f"<blockquote expandable><b>{get_p_lightning()} Dᴇʟᴀʏ Fᴏʀᴍᴀᴛ Exᴀᴍᴘʟᴇs:</b>\n\n"
        f"10s - 10 Sᴇᴄᴏɴᴅs | 1m - 1 Mɪɴᴜᴛᴇ\n"
        f"15m - 15 Mɪɴᴜᴛᴇs | 2h - 2 Hᴏᴜʀs\n"
        f"1d - 1 Dᴀʏ\n</blockquote>\n"
        f"<b>Bᴜʟᴋ Dᴇʟᴇᴛᴇʀ (Oʟᴅ Mᴇssᴀɢᴇs):</b>\n"
        f"➜ <code>/delall</code> - Wɪᴘᴇs ᴇᴠᴇʀʏᴛʜɪɴɢ ɪɴ ᴄʜᴀᴛ\n"
        f"➜ <code>/delfrom</code> - (Rᴇᴘʟʏ) Wɪᴘᴇs ғʀᴏᴍ ᴛʜᴀᴛ ᴍᴇssᴀɢᴇ ᴀɴᴅ ᴀʟʟ ɴᴇᴡᴇʀ ᴏɴᴇs."
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="main_menu")]])
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("main_menu"))
async def main_menu_callback(client, callback_query):
    admin_states[callback_query.from_user.id] = {"step": "IDLE"}
    bot_info = await bot.get_me()
    is_admin = is_bot_admin(callback_query.from_user.id)
    text, keyboard = get_start_menu(bot_info.username, bool(userbot and userbot.is_connected), is_admin)
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("admin_panel"))
async def admin_panel_callback(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return await callback_query.answer("⛔️ Aᴅᴍɪɴ ᴏɴʟʏ!", show_alert=True)
    admin_states[callback_query.from_user.id] = {"step": "IDLE"}
    
    text = f"{P_ADMIN} <b>Aᴅᴍɪɴ Pᴀɴᴇʟ</b> {P_DIAMOND}\n\nMᴀɴᴀɢᴇ Usᴇʀʙᴏᴛ, Fᴏʀᴄᴇ Sᴜʙsᴄʀɪʙᴇ, ᴀɴᴅ Cᴏ-Aᴅᴍɪɴs."
    buttons = [
        [InlineKeyboardButton("🔑 Usᴇʀʙᴏᴛ Mᴀɴᴀɢᴇᴍᴇɴᴛ", callback_data="ub_menu")],
        [InlineKeyboardButton("📢 Cʜᴀɴɴᴇʟs (F-Sᴜʙ)", callback_data="ch_menu")],
        [InlineKeyboardButton("🖼 Sᴇᴛ Fsᴜʙ Iᴍᴀɢᴇ", callback_data="fsub_image_set")]
    ]
    if callback_query.from_user.id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("👮 Mᴀɴᴀɢᴇ Aᴅᴍɪɴs", callback_data="manage_admins")])
    buttons.append([InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="main_menu")])
    
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("ub_menu"))
async def ub_menu_callback(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    status = f"{P_CHECK} Lᴏɢɢᴇᴅ Iɴ" if bool(userbot and userbot.is_connected) else "❌ Nᴏᴛ Lᴏɢɢᴇᴅ Iɴ"
    text = f"🔑 <b>Usᴇʀʙᴏᴛ Mᴀɴᴀɢᴇᴍᴇɴᴛ</b>\n\nSᴛᴀᴛᴜs: <b>{status}</b>\nLᴏɢɪɴ ᴛᴏ ᴇɴᴀʙʟᴇ ʙᴜʟᴋ-ᴅᴇʟᴇᴛɪᴏɴ."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Lᴏɢɪɴ Nᴇᴡ Aᴄᴄᴏᴜɴᴛ", callback_data="setup_userbot")],
        [InlineKeyboardButton("🗑 Cʟᴇᴀʀ Sᴇssɪᴏɴ", callback_data="ub_clear_conf")],
        [InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="admin_panel")]
    ])
    await callback_query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("ub_clear_conf"))
async def ub_clear_conf_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yᴇs, Cʟᴇᴀʀ Sᴇssɪᴏɴ", callback_data="ub_clear_yes")],
        [InlineKeyboardButton("❌ Nᴏ, Cᴀɴᴄᴇʟ", callback_data="ub_menu")]
    ])
    await callback_query.message.edit_text("⚠️ <b>Aʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ Cʟᴇᴀʀ Usᴇʀʙᴏᴛ Dᴀᴛᴀ ᴀɴᴅ Lᴏɢᴏᴜᴛ?</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("ub_clear_yes"))
async def ub_clear_yes_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    global userbot
    if userbot: 
        try: await userbot.disconnect()
        except: pass
        userbot = None
    try: os.remove("userbot.session")
    except: pass
    
    config_data.pop("api_id", None)
    config_data.pop("api_hash", None)
    await save_config()
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="ub_menu")]])
    await callback_query.message.edit_text(f"{P_CHECK} <b>Usᴇʀʙᴏᴛ Sᴇssɪᴏɴ Cʟᴇᴀʀᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ!</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("setup_userbot"))
async def setup_userbot_callback(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    admin_states[callback_query.from_user.id] = {"step": "ASK_API_ID"}
    await callback_query.message.edit_text("📝 **Sᴛᴇᴘ 1:** Sᴇɴᴅ ʏᴏᴜʀ **API ID** (Nᴜᴍʙᴇʀs ᴏɴʟʏ).\n\n*(Sᴇɴᴅ /start ᴛᴏ ᴄᴀɴᴄᴇʟ)*", parse_mode=ParseMode.HTML)

def get_channels_ui():
    channels = config_data.get("fsub_channels", [])
    text = f"📢 <b>Mᴀɴᴀɢᴇ Cʜᴀɴɴᴇʟs</b>\n\nCʟɪᴄᴋ ᴏɴ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ Eᴅɪᴛ, Rᴇᴍᴏᴠᴇ, ᴏʀ Tᴏɢɢʟᴇ ɪᴛs F-Sᴜʙ sᴛᴀᴛᴜs."
    btns = []
    for ch in channels:
        status_dot = "🟢" if ch.get("fsub", True) else "🔴"
        btns.append([InlineKeyboardButton(f"{status_dot} {ch['name']}", callback_data=f"chedit_{ch['id']}")])
    btns.append([InlineKeyboardButton("➕ Aᴅᴅ Nᴇᴡ Cʜᴀɴɴᴇʟ", callback_data="ch_add")])
    btns.append([InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Aᴅᴍɪɴ", callback_data="admin_panel")])
    return text, InlineKeyboardMarkup(btns)

@bot.on_callback_query(filters.regex("ch_menu"))
async def ch_menu_callback(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    text, kb = get_channels_ui()
    await callback_query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex(r"^chedit_(.*)"))
async def ch_edit_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    channels = config_data.get("fsub_channels", [])
    ch = next((c for c in channels if c['id'] == ch_id), None)
    if not ch: return await callback_query.answer("Cʜᴀɴɴᴇʟ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
    
    fsub_text = "ON" if ch.get("fsub", True) else "OFF"
    
    text = f"📢 <b>Eᴅɪᴛ Cʜᴀɴɴᴇʟ:</b> {ch['name']}\n\nFᴏʀᴄᴇ Sᴜʙsᴄʀɪʙᴇ ɪs <b>{fsub_text}</b> ғᴏʀ ᴛʜɪs ᴄʜᴀɴɴᴇʟ."
    btns = [
        [InlineKeyboardButton(f"🔄 Tᴏɢɢʟᴇ F-Sᴜʙ: {fsub_text}", callback_data=f"chtog_{ch_id}")],
        [InlineKeyboardButton("⬆️ Mᴏᴠᴇ Uᴘ", callback_data=f"chup_{ch_id}"), InlineKeyboardButton("⬇️ Mᴏᴠᴇ Dᴏᴡɴ", callback_data=f"chdown_{ch_id}")],
        [InlineKeyboardButton("🗑 Rᴇᴍᴏᴠᴇ Cʜᴀɴɴᴇʟ", callback_data=f"chdelconf_{ch_id}")],
        [InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Cʜᴀɴɴᴇʟs", callback_data="ch_menu")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex(r"^chtog_(.*)"))
async def ch_tog_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    for ch in config_data.get("fsub_channels", []):
        if ch['id'] == ch_id:
            ch['fsub'] = not ch.get('fsub', True)
            break
    await save_config()
    await ch_edit_cb(client, callback_query)

@bot.on_callback_query(filters.regex(r"^chup_(.*)"))
async def ch_up_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    channels = config_data.get("fsub_channels", [])
    idx = next((i for i, c in enumerate(channels) if c['id'] == ch_id), -1)
    if idx > 0:
        channels[idx], channels[idx-1] = channels[idx-1], channels[idx]
        await save_config()
    await ch_edit_cb(client, callback_query)

@bot.on_callback_query(filters.regex(r"^chdown_(.*)"))
async def ch_down_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    channels = config_data.get("fsub_channels", [])
    idx = next((i for i, c in enumerate(channels) if c['id'] == ch_id), -1)
    if idx != -1 and idx < len(channels) - 1:
        channels[idx], channels[idx+1] = channels[idx+1], channels[idx]
        await save_config()
    await ch_edit_cb(client, callback_query)

@bot.on_callback_query(filters.regex(r"^chdelconf_(.*)"))
async def ch_delconf_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yᴇs, Rᴇᴍᴏᴠᴇ", callback_data=f"chdel_{ch_id}")],
        [InlineKeyboardButton("❌ Nᴏ, Cᴀɴᴄᴇʟ", callback_data=f"chedit_{ch_id}")]
    ])
    await callback_query.message.edit_text("⚠️ <b>Aʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴛʜɪs ᴄʜᴀɴɴᴇʟ?</b>", reply_markup=kb, parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex(r"^chdel_(.*)"))
async def ch_del_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    ch_id = int(callback_query.matches[0].group(1))
    config_data["fsub_channels"] = [c for c in config_data.get("fsub_channels", []) if c["id"] != ch_id]
    await save_config()
    await callback_query.answer("Cʜᴀɴɴᴇʟ Rᴇᴍᴏᴠᴇᴅ!", show_alert=True)
    await ch_menu_callback(client, callback_query)

@bot.on_callback_query(filters.regex("ch_add"))
async def ch_add_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    admin_states[callback_query.from_user.id] = {"step": "ASK_CH_ADD"}
    await callback_query.message.edit_text("📢 **Sᴇɴᴅ ᴛʜᴇ Cʜᴀɴɴᴇʟ Usᴇʀɴᴀᴍᴇ (e.g. @channel) ᴏʀ ID (e.g. -100...).**\n\n⚠️ *Mᴀᴋᴇ ᴍᴇ ᴀᴅᴍɪɴ ɪɴ ɪᴛ ғɪʀsᴛ!*\n*(Sᴇɴᴅ /start ᴛᴏ ᴄᴀɴᴄᴇʟ)*", parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("fsub_image_set"))
async def fsub_img_cb(client, callback_query):
    if not is_bot_admin(callback_query.from_user.id): return
    admin_states[callback_query.from_user.id] = {"step": "ASK_FSUB_IMG"}
    await callback_query.message.edit_text("🖼 **Sᴇɴᴅ ᴀ ᴘʜᴏᴛᴏ** ᴛᴏ sᴇᴛ ᴀs Fᴏʀᴄᴇ Sᴜʙ ʙᴀᴄᴋɢʀᴏᴜɴᴅ. (Sᴇɴᴅ 'off' ᴛᴏ ʀᴇᴍᴏᴠᴇ).\n*(Sᴇɴᴅ /start ᴛᴏ ᴄᴀɴᴄᴇʟ)*", parse_mode=ParseMode.HTML)

@bot.on_callback_query(filters.regex("manage_admins"))
async def manage_admins_cb(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID: return
    admin_list = "\n".join([f"<code>{aid}</code>" for aid in config_data.get("admins", [])])
    admin_states[callback_query.from_user.id] = {"step": "ASK_ADMIN_ID"}
    await callback_query.message.edit_text(f"👮 **Cᴜʀʀᴇɴᴛ Aᴅᴍɪɴs:**\n{admin_list}\n\n👉 **Sᴇɴᴅ ᴀ Tᴇʟᴇɢʀᴀᴍ ID ᴛᴏ Aᴅᴅ/Rᴇᴍᴏᴠᴇ ᴛʜᴇᴍ.**\n*(Sᴇɴᴅ /start ᴛᴏ ᴄᴀɴᴄᴇʟ)*", parse_mode=ParseMode.HTML)

@bot.on_message(filters.private & ~filters.command(["start", "delall", "delfrom", "setdelay", "set_delay"]))
async def admin_steps_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_bot_admin(user_id): return
    
    state = admin_states.get(user_id, {}).get("step", "IDLE")
    if state == "IDLE": return

    if state == "ASK_CH_ADD":
        try:
            target = message.text.strip()
            if target.startswith("-100"): target = int(target)
            chat = await client.get_chat(target)
            invite_link = chat.invite_link
            if not invite_link: invite_link = await client.export_chat_invite_link(chat.id)
            
            config_data.setdefault("fsub_channels", []).append({
                "id": chat.id, "name": chat.title, "link": invite_link, "fsub": True
            })
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            
            text, kb = get_channels_ui()
            await message.reply_text(f"{P_CHECK} <b>{chat.title}</b> ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\nIᴛ ʜᴀs ʙᴇᴇɴ sᴇᴛ ᴛᴏ F-Sᴜʙ <b>ON</b>.", reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply_text(f"❌ Cᴏᴜʟᴅ ɴᴏᴛ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ. Pʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ɪғ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ID/Usᴇʀɴᴀᴍᴇ ᴀɴᴅ ɪғ I'ᴍ ᴀɴ ᴀᴅᴍɪɴ ᴡɪᴛʜ 'Iɴᴠɪᴛᴇ Usᴇʀs' ᴘᴇʀᴍɪssɪᴏɴ.\n\nSᴇɴᴅ ᴀɢᴀɪɴ ᴏʀ ᴛʏᴘᴇ /start ᴛᴏ ᴄᴀɴᴄᴇʟ.", parse_mode=ParseMode.HTML)

    elif state == "ASK_FSUB_IMG":
        if message.text and message.text.lower() == "off":
            config_data["fsub_image"] = None
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"{P_CHECK} Fsᴜʙ Iᴍᴀɢᴇ ʀᴇᴍᴏᴠᴇᴅ.", parse_mode=ParseMode.HTML)
        elif message.photo:
            config_data["fsub_image"] = message.photo.file_id
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"{P_CHECK} Fsᴜʙ Iᴍᴀɢᴇ Sᴀᴠᴇᴅ!", parse_mode=ParseMode.HTML)
        else:
            await message.reply_text("❌ Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴘʜᴏᴛᴏ.", parse_mode=ParseMode.HTML)

    elif state == "ASK_ADMIN_ID":
        if user_id != ADMIN_ID: return
        try:
            target_id = int(message.text.strip())
            admins = config_data.setdefault("admins", [ADMIN_ID])
            if target_id in admins:
                if target_id == ADMIN_ID: return await message.reply_text("❌ Yᴏᴜ ᴄᴀɴ'ᴛ ʀᴇᴍᴏᴠᴇ ᴛʜᴇ Oᴡɴᴇʀ.")
                admins.remove(target_id)
                msg = f"➖ Rᴇᴍᴏᴠᴇᴅ Aᴅᴍɪɴ: `{target_id}`"
            else:
                admins.append(target_id)
                msg = f"➕ Aᴅᴅᴇᴅ Nᴇᴡ Aᴅᴍɪɴ: `{target_id}`"
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"{P_CHECK} {msg}", parse_mode=ParseMode.HTML)
        except: await message.reply_text("❌ Iɴᴠᴀʟɪᴅ ID.")

    elif state == "ASK_API_ID":
        try:
            config_data["api_id"] = int(message.text.strip())
            admin_states[user_id]["step"] = "ASK_API_HASH"
            await message.reply_text("📝 **Sᴛᴇᴘ 2:** Sᴇɴᴅ ʏᴏᴜʀ **API HASH**.", parse_mode=ParseMode.HTML)
        except: await message.reply_text("❌ Nᴜᴍʙᴇʀs ᴏɴʟʏ ғᴏʀ API ID.")
    elif state == "ASK_API_HASH":
        config_data["api_hash"] = message.text.strip()
        admin_states[user_id]["step"] = "ASK_PHONE"
        await message.reply_text("📝 **Sᴛᴇᴘ 3:** Sᴇɴᴅ **Pʜᴏɴᴇ Nᴜᴍʙᴇʀ**.", parse_mode=ParseMode.HTML)
    elif state == "ASK_PHONE":
        config_data["phone"] = message.text.strip()
        await message.reply_text(f"{get_p_lightning()} `Cᴏɴɴᴇᴄᴛɪɴɢ...`", parse_mode=ParseMode.HTML)
        try:
            global userbot
            if userbot: await userbot.disconnect()
            userbot = Client("userbot", api_id=config_data["api_id"], api_hash=config_data["api_hash"], in_memory=False)
            await userbot.connect()
            sent_code = await userbot.send_code(config_data["phone"])
            config_data["phone_code_hash"] = sent_code.phone_code_hash
            admin_states[user_id]["step"] = "ASK_OTP"
            await message.reply_text("📩 **Sᴛᴇᴘ 4:** Sᴇɴᴅ OTP **ᴡɪᴛʜ sᴘᴀᴄᴇs**.")
        except Exception as e:
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"❌ Eʀʀᴏʀ: {e}")
    elif state == "ASK_OTP":
        otp = message.text.replace(" ", "")
        await message.reply_text(f"{get_p_lightning()} `Vᴇʀɪғʏɪɴɢ OTP...`", parse_mode=ParseMode.HTML)
        try:
            await userbot.sign_in(config_data["phone"], config_data["phone_code_hash"], otp)
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"{P_CHECK} **Lᴏɢɪɴ Sᴜᴄᴄᴇssғᴜʟ!**", parse_mode=ParseMode.HTML)
        except SessionPasswordNeeded:
            admin_states[user_id]["step"] = "ASK_PASSWORD"
            await message.reply_text("🔐 **Sᴛᴇᴘ 5:** Sᴇɴᴅ ʏᴏᴜʀ **2FA Pᴀssᴡᴏʀᴅ**.")
        except Exception as e:
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"❌ Eʀʀᴏʀ: {e}")
    elif state == "ASK_PASSWORD":
        await message.reply_text(f"{get_p_lightning()} `Vᴇʀɪғʏɪɴɢ Pᴀssᴡᴏʀᴅ...`", parse_mode=ParseMode.HTML)
        try:
            await userbot.check_password(message.text)
            await save_config()
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"{P_CHECK} **Lᴏɢɪɴ Sᴜᴄᴄᴇssғᴜʟ!**", parse_mode=ParseMode.HTML)
        except Exception as e:
            admin_states[user_id]["step"] = "IDLE"
            await message.reply_text(f"❌ Eʀʀᴏʀ: {e}")

@bot.on_message((filters.group | filters.channel) & filters.regex(r"/(?:setdelay|set_delay)\s+(\d+[smhd]?)", flags=re.IGNORECASE))
async def specific_post_delay_handler(client: Client, message: Message):
    if not await is_user_admin_safe(client, message): return
    text = message.text or message.caption or ""
    match = re.search(r"/(?:setdelay|set_delay)\s+(\d+[smhd]?)", text, re.IGNORECASE)
    if not match: return
    time_str = match.group(1)
    delay_sec = parse_time(time_str)
    
    if delay_sec is None or delay_sec == 0:
        msg = await message.reply_text("❌ <b>Iɴᴠᴀʟɪᴅ Tɪᴍᴇ Fᴏʀᴍᴀᴛ.</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass
        return

    text_clean = text.strip()
    is_pure_command = text_clean.startswith("/") and len(text_clean.split()) <= 2
    
    if message.reply_to_message and is_pure_command:
        target_msg_id = message.reply_to_message.id
        asyncio.create_task(delayed_delete(message.chat.id, target_msg_id, delay_sec))
        msg_to_delete = await message.reply_text(f"{P_CHECK} Rᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b>{time_str}</b>.", parse_mode=ParseMode.HTML)
        await asyncio.sleep(5)
        try:
            await msg_to_delete.delete()
            await message.delete() 
        except: pass
    else:
        target_msg_id = message.id
        asyncio.create_task(delayed_delete(message.chat.id, target_msg_id, delay_sec))
        msg_to_delete = await message.reply_text(f"{P_CHECK} Tʜɪs ᴘᴏsᴛ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b>{time_str}</b>.", parse_mode=ParseMode.HTML)
        await asyncio.sleep(5)
        try: await msg_to_delete.delete()
        except: pass

async def ensure_userbot_admin(client: Client, message: Message, chat_id: int):
    try:
        ub_info = await userbot.get_me()
        ub_name = f"@{ub_info.username}" if ub_info.username else ub_info.first_name
        try:
            ub_member = await userbot.get_chat_member(chat_id, "me")
            if ub_member.privileges and ub_member.privileges.can_delete_messages: return True 
        except: pass 
        bot_member = await client.get_chat_member(chat_id, "me")
        if bot_member.privileges and bot_member.privileges.can_promote_members:
            try:
                target = ub_info.username if ub_info.username else ub_info.id
                await client.promote_chat_member(chat_id, target, privileges=ChatPrivileges(can_delete_messages=True))
                await asyncio.sleep(1) 
                return True
            except: pass
        await message.reply_text(
            f"⚠️ <b>Aᴄᴛɪᴏɴ Rᴇǫᴜɪʀᴇᴅ</b>\n\n{ub_name} ɴᴇᴇᴅs ᴀᴅᴍɪɴ ʀɪɢʜᴛs ᴛᴏ ʙᴜʟᴋ-ᴅᴇʟᴇᴛᴇ.\n👉 <b>Mᴀɴᴜᴀʟʟʏ ᴘʀᴏᴍᴏᴛᴇ ɪᴛ.</b>",
            parse_mode=ParseMode.HTML
        )
        return False
    except: return False

@bot.on_message(filters.command("delall") & (filters.group | filters.channel))
async def del_all_command(client: Client, message: Message):
    if not await is_user_admin_safe(client, message): return
    global userbot
    if not userbot or not userbot.is_connected: return await message.reply_text("❌ Usᴇʀʙᴏᴛ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ.", parse_mode=ParseMode.HTML)
    if not await ensure_userbot_admin(client, message, message.chat.id): return

    status_msg = await message.reply_text(f"{get_p_lightning()} `Wɪᴘɪɴɢ Aʟʟ Mᴇssᴀɢᴇs...`", parse_mode=ParseMode.HTML)
    count, chunk = 0, []
    
    try:
        async for msg in userbot.get_chat_history(message.chat.id):
            chunk.append(msg.id)
            count += 1
            if len(chunk) == 100:
                try:
                    await userbot.delete_messages(message.chat.id, chunk)
                    await asyncio.sleep(1.5)
                except FloodWait as e: await asyncio.sleep(e.value + 1)
                except: pass
                chunk = []
        if chunk:
            try: await userbot.delete_messages(message.chat.id, chunk)
            except: pass
            
        await status_msg.edit_text(f"{P_CHECK} <b>Dᴏɴᴇ!</b> Dᴇʟᴇᴛᴇᴅ {count} ᴍᴇssᴀɢᴇs.", parse_mode=ParseMode.HTML)
        await asyncio.sleep(5)
        try:
            await status_msg.delete()
            await message.delete()
        except: pass
    except Exception as e:
        await status_msg.edit_text(f"⚠️ Sᴛᴏᴘᴘᴇᴅ: {e}", parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("delfrom") & (filters.group | filters.channel))
async def del_from_command(client: Client, message: Message):
    if not await is_user_admin_safe(client, message): return
    global userbot
    if not userbot or not userbot.is_connected: return await message.reply_text("❌ Usᴇʀʙᴏᴛ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ.", parse_mode=ParseMode.HTML)
    
    if not message.reply_to_message:
        msg = await message.reply_text("❌ Rᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴡɪᴛʜ `/delfrom`.")
        await asyncio.sleep(5)
        try: await msg.delete(); await message.delete()
        except: pass
        return
        
    if not await ensure_userbot_admin(client, message, message.chat.id): return
    status_msg = await message.reply_text(f"{get_p_lightning()} `Dᴇʟᴇᴛɪɴɢ sᴇʟᴇᴄᴛᴇᴅ ᴍᴇssᴀɢᴇs...`", parse_mode=ParseMode.HTML)
    
    ids_to_delete = list(range(message.reply_to_message.id, message.id + 1))
    count, chunk = 0, []
    
    for msg_id in reversed(ids_to_delete):
        chunk.append(msg_id)
        count += 1
        if len(chunk) == 100:
            try:
                await userbot.delete_messages(message.chat.id, chunk)
                await asyncio.sleep(1.5)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await userbot.delete_messages(message.chat.id, chunk)
            except: pass
            chunk = []
            
    if chunk:
        try: await userbot.delete_messages(message.chat.id, chunk)
        except: pass
        
    await status_msg.edit_text(f"{P_CHECK} <b>Dᴏɴᴇ!</b> Dᴇʟᴇᴛᴇᴅ {count} ᴍᴇssᴀɢᴇs.", parse_mode=ParseMode.HTML)
    await asyncio.sleep(5)
    try: await status_msg.delete()
    except: pass

# --- DUMMY WEB SERVER FOR RENDER.COM ---
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running smoothly!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Dummy Web Server started on port {port}")

async def main():
    await web_server()  # Render needs this!
    await start_userbot_if_configured()
    await bot.start()
    print("✅ Bot is Online & Render-Ready!")
    import pyrogram
    await pyrogram.idle()

if __name__ == "__main__":
    bot.run(main())
EOF
