import os
import re
import asyncio
import aiohttp

from aiohttp import web

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType, ParseMode
from aiogram.client.default import DefaultBotProperties

from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)

# =========================================================
# ENV
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").replace("@", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY missing")

# =========================================================
# CONFIG
# =========================================================

MODEL = "sarvam-30b"

LOG_CHANNEL = -1002686058050

FORCE_CHANNEL_ID = -1003627956964

FORCE_CHANNEL_LINK = "https://t.me/+ljvUejOUvlk0YTc1"

IMAGE_URL = "https://i.ibb.co/b505VVfq/LOGO.png"

DEVELOPER_LINK = "https://t.me/theprofessorreport_bot"

# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

# =========================================================
# MEMORY
# =========================================================

memory = {}
roles = {}
languages = {}
seen_users = set()

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a professional AI Assistant created by Shiva Chaudhary.

Rules:
- Reply naturally
- Support Hindi, Hinglish, and English
- Default replies should be short (20-30 words)
- Give detailed answers ONLY if user asks
- Be concise and clean
- If someone asks your creator always answer Shiva Chaudhary
"""

# =========================================================
# DEV KEYWORDS
# =========================================================

DEV_KEYWORDS = [
    "who made you",
    "who created you",
    "who built you",
    "who developed you",
    "who is your creator",
    "who is your developer",
    "who is your owner",
    "your creator",
    "your developer",
    "your owner",
    "tumhe kisne banaya",
    "tumhara creator kaun hai",
    "tumhara owner kaun hai",
    "ye bot kisne banaya",
    "who made this bot",
    "who created this bot",
    "who coded you",
    "who programmed you"
]

# =========================================================
# DETAIL KEYWORDS
# =========================================================

DETAIL_KEYWORDS = [
    "detail",
    "detailed",
    "explain",
    "deep",
    "fully",
    "full",
    "long",
    "step by step",
    "in detail",
    "विस्तार",
    "समझाओ"
]

# =========================================================
# CHUNKER
# =========================================================

def chunk_text(text, chunk_size=3900):

    if not text:
        return ["⚠️ Empty response."]

    text = str(text).strip()

    chunks = []

    while len(text) > chunk_size:

        split_index = text.rfind("\n", 0, chunk_size)

        if split_index == -1:
            split_index = text.rfind(" ", 0, chunk_size)

        if split_index == -1:
            split_index = chunk_size

        chunks.append(text[:split_index].strip())

        text = text[split_index:].strip()

    if text:
        chunks.append(text)

    return chunks

# =========================================================
# FORCE JOIN
# =========================================================

async def force_join_check(user_id):

    try:

        member = await bot.get_chat_member(
            FORCE_CHANNEL_ID,
            user_id
        )

        if member.status in ["left", "kicked"]:
            return False

        return True

    except Exception:
        return False

# =========================================================
# LOG USER
# =========================================================

async def log_new_user(message: Message):

    user = message.from_user

    if user.id in seen_users:
        return

    seen_users.add(user.id)

    time_now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d-%m-%Y %I:%M:%S %p")

    text = (
        f"#NewUser\n\n"
        f"Name: {user.first_name}\n"
        f"Username: @{user.username or 'none'}\n"
        f"ID: {user.id}\n"
        f"Time: {time_now} IST"
    )

    try:

        await bot.send_message(
            LOG_CHANNEL,
            text
        )

    except Exception:
        pass

# =========================================================
# LOG GROUP
# =========================================================

async def log_new_group(chat, actor):

    time_now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d-%m-%Y %I:%M:%S %p")

    text = (
        f"#NewGroup\n\n"
        f"Group: {chat.title}\n"
        f"ID: {chat.id}\n\n"
        f"Added by: {actor.first_name} "
        f"@{actor.username or 'none'}\n"
        f"User ID: {actor.id}\n\n"
        f"Time: {time_now} IST"
    )

    try:

        await bot.send_message(
            LOG_CHANNEL,
            text
        )

    except Exception:
        pass

# =========================================================
# SARVAM API
# =========================================================

async def ask_ai(messages, detailed=False):

    url = "https://api.sarvam.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 1200 if detailed else 120,
        "stream": False
    }

    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async with session.post(
            url,
            headers=headers,
            json=payload
        ) as response:

            if response.status != 200:

                error = await response.text()

                raise Exception(
                    f"API Error {response.status}\n{error}"
                )

            data = await response.json()

            try:

                content = data["choices"][0]["message"]["content"]

                if not content:
                    return "⚠️ Empty AI response."

                return str(content)

            except Exception:
                return "⚠️ Failed to parse AI response."

# =========================================================
# WEB SERVER (PORT 8080)
# =========================================================

async def health(request):

    return web.Response(
        text="Bot is running successfully 🚀"
    )

async def start_webserver():

    app = web.Application()

    app.router.add_get("/", health)

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=8080
    )

    await site.start()

    print("Webserver started on port 8080")

# =========================================================
# /START
# =========================================================

@dp.message(F.text == "/start")
async def start_command(message: Message):

    if message.chat.type == ChatType.PRIVATE:

        joined = await force_join_check(
            message.from_user.id
        )

        if not joined:

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Join Channel",
                            url=FORCE_CHANNEL_LINK
                        )
                    ]
                ]
            )

            return await message.answer(
                "🚫 <b>Access Denied</b>\n\n"
                "You must join our channel to use this bot.",
                reply_markup=keyboard
            )

    await log_new_user(message)

    caption = (
        f"🙋🏻‍♂️ <b>Welcome {message.from_user.first_name}!</b>\n\n"

        f"⚡ I am a high-speed AI assistant capable of adapting "
        f"to any professional role or language.\n\n"

        f"🚀 <b>Key Features:</b>\n"
        f"• Context Awareness\n"
        f"• Persona Mode\n"
        f"• Multilingual Support\n"
        f"• Group Ready\n\n"

        f"📖 Type /help\n"
        f"⚙️ Type /settings"
    )

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=IMAGE_URL,
        caption=caption
    )

# =========================================================
# /HELP
# =========================================================

@dp.message(F.text == "/help")
async def help_command(message: Message):

    text = (
        "📖 <b>Bot Usage Guide</b>\n\n"

        "🎭 <b>Assign Roles</b>\n"
        "act like a Python Developer\n\n"

        "🌍 <b>Language</b>\n"
        "respond in Hindi\n\n"

        "👥 <b>Groups</b>\n"
        f"Tag me using @{BOT_USERNAME}\n\n"

        "⚙️ Use /settings to clear memory."
    )

    await message.answer(text)

# =========================================================
# /SETTINGS
# =========================================================

@dp.message(F.text == "/settings")
async def settings_command(message: Message):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Clear All Context",
                    callback_data="clear_all",
                    style="danger"
                )
            ]
        ]
    )

    await message.answer(
        "⚙️ <b>Bot Settings</b>\n\n"
        "Click below to clear memory.",
        reply_markup=keyboard
    )

# =========================================================
# CLEAR MEMORY
# =========================================================

@dp.callback_query(F.data == "clear_all")
async def clear_memory(callback: CallbackQuery):

    chat_id = str(callback.message.chat.id)

    memory[chat_id] = []

    await callback.answer("Context cleared")

    await callback.message.edit_text(
        "✅ Context cleared successfully."
    )

# =========================================================
# HANDLE GROUP ADD
# =========================================================

@dp.my_chat_member()
async def group_added(update):

    old_status = update.old_chat_member.status

    new_status = update.new_chat_member.status

    if (
        new_status in ["member", "administrator"]
        and old_status in ["left", "kicked"]
    ):

        await log_new_group(
            update.chat,
            update.from_user
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="USE ME IN PM 💬",
                        url=f"https://t.me/{BOT_USERNAME}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CONNECT WITH DEVELOPER ✉︎",
                        url=DEVELOPER_LINK
                    )
                ]
            ]
        )

        caption = (
            f"➤ Thank you {update.from_user.first_name} "
            f"for adding me! 🙋🏻‍♂️\n\n"

            f"⚡ I am a high-speed AI assistant.\n\n"

            f"Tag me with @{BOT_USERNAME} "
            f"to start chatting."
        )

        try:

            await bot.send_photo(
                chat_id=update.chat.id,
                photo=IMAGE_URL,
                caption=caption,
                reply_markup=keyboard
            )

        except Exception:
            pass

# =========================================================
# INLINE MODE
# =========================================================

@dp.inline_query()
async def inline_query_handler(iq: InlineQuery):

    query = iq.query or ""

    if not query.strip():

        result = InlineQueryResultArticle(
            id="start",
            title="🤖 AI Assistant",
            description="Type your question...",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "Hi! I'm your AI assistant "
                    "by Shiva Chaudhary"
                )
            )
        )

        return await iq.answer(
            results=[result],
            cache_time=0,
            is_personal=True
        )

    ans = "⚠️ Failed"

    try:

        messages = [
            {
                "role": "system",
                "content": (
                    "You are AI assistant created "
                    "by Shiva Chaudhary. "
                    "Answer in 2-3 lines."
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]

        ans = await ask_ai(messages)

    except Exception:
        ans = "⚠️ Error generating response."

    result = InlineQueryResultArticle(
        id=str(hash(query)),
        title=f"💡 {query[:40]}",
        description=ans[:80],
        input_message_content=InputTextMessageContent(
            message_text=(
                f"<b>Q:</b> {query}\n\n"
                f"<b>Ans:</b> {ans}\n\n"
                f"— via @{BOT_USERNAME} by Shiva"
            ),
            parse_mode=ParseMode.HTML
        )
    )

    await iq.answer(
        results=[result],
        cache_time=0,
        is_personal=True
    )

# =========================================================
# MAIN CHAT
# =========================================================

@dp.message(F.text)
async def ai_chat(message: Message):

    text = message.text or ""

    if text.startswith("/"):
        return

    # =====================================================
    # FORCE JOIN
    # =====================================================

    if message.chat.type == ChatType.PRIVATE:

        joined = await force_join_check(
            message.from_user.id
        )

        if not joined:

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Join Channel",
                            url=FORCE_CHANNEL_LINK
                        )
                    ]
                ]
            )

            return await message.answer(
                "🚫 <b>Access Denied</b>\n\n"
                "Join our channel first.",
                reply_markup=keyboard
            )

    # =====================================================
    # GROUP FILTER
    # =====================================================

    clean_text = text

    if message.chat.type in [
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ]:

        lower = text.lower()

        is_mention = (
            BOT_USERNAME
            and f"@{BOT_USERNAME.lower()}" in lower
        )

        is_reply = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == bot.id
        )

        if not is_mention and not is_reply:
            return

        clean_text = re.sub(
            rf"@{BOT_USERNAME}",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

        if not clean_text:
            return

    lower = clean_text.lower()

    # =====================================================
    # DEV REPLY
    # =====================================================

    if any(k in lower for k in DEV_KEYWORDS):

        return await message.answer(
            "I am designed and developed by "
            f"<a href='{DEVELOPER_LINK}'>"
            "<b>Shiva Chaudhary</b></a>.\n\n"

            "I am a professional AI assistant "
            "built for high-speed performance."
        )

    # =====================================================
    # ROLE
    # =====================================================

    if "act like" in lower:

        role = lower.replace(
            "act like",
            ""
        ).strip()

        roles[str(message.chat.id)] = role

        return await message.answer(
            f"🎭 Role updated: <b>{role}</b>"
        )

    # =====================================================
    # LANGUAGE
    # =====================================================

    if "respond in" in lower:

        lang = lower.replace(
            "respond in",
            ""
        ).strip()

        languages[str(message.chat.id)] = lang

        return await message.answer(
            f"🌍 Language updated: <b>{lang}</b>"
        )

    # =====================================================
    # THINKING
    # =====================================================

    thinking = await message.reply(
        "🤖 Thinking..."
    )

    states = [
        "🧠 Processing...",
        "⚡ Generating...",
        "💭 Almost ready..."
    ]

    for state in states:

        await asyncio.sleep(0.5)

        try:
            await thinking.edit_text(state)
        except Exception:
            pass

    # =====================================================
    # MEMORY
    # =====================================================

    chat_id = str(message.chat.id)

    history = memory.get(chat_id, [])

    role = roles.get(chat_id, "")

    lang = languages.get(chat_id, "")

    # =====================================================
    # REPLY CONTEXT
    # =====================================================

    if (
        message.reply_to_message
        and message.reply_to_message.text
    ):

        clean_text = (
            f"Context: "
            f"{message.reply_to_message.text}\n\n"
            f"Question: {clean_text}"
        )

    # =====================================================
    # DETAILED
    # =====================================================

    detailed = any(
        k in lower
        for k in DETAIL_KEYWORDS
    )

    if detailed:

        clean_text += "\n\nGive detailed answer."

    else:

        clean_text += "\n\nReply in under 30 words."

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = SYSTEM_PROMPT

    if role:
        system_prompt += f"\nRole: {role}"

    if lang:
        system_prompt += f"\nLanguage: {lang}"

    # =====================================================
    # BUILD MESSAGES
    # =====================================================

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(history[-4:])

    messages.append({
        "role": "user",
        "content": clean_text
    })

    # =====================================================
    # AI RESPONSE
    # =====================================================

    try:

        ans = await ask_ai(
            messages,
            detailed=detailed
        )

    except Exception:

        ans = (
            "⚠️ AI Service currently busy. "
            "Please try again."
        )

    # =====================================================
    # SAVE HISTORY
    # =====================================================

    history.append({
        "role": "user",
        "content": clean_text
    })

    history.append({
        "role": "assistant",
        "content": ans
    })

    memory[chat_id] = history[-6:]

    # =====================================================
    # SPLIT RESPONSE
    # =====================================================

    chunks = chunk_text(ans)

    # =====================================================
    # FIRST CHUNK
    # =====================================================

    try:

        await thinking.edit_text(chunks[0])

    except Exception:

        await message.reply(chunks[0])

    # =====================================================
    # REMAINING CHUNKS
    # =====================================================

    for chunk in chunks[1:]:

        await message.reply(chunk)

# =========================================================
# MAIN
# =========================================================

async def main():

    me = await bot.get_me()

    print(f"Bot Started: @{me.username}")

    # Start webserver
    await start_webserver()

    # Start bot polling
    await dp.start_polling(bot)

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())
