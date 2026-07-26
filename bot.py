import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder, InlineQueryHandler
import sqlite3
from datetime import datetime
import asyncio

TOKEN = "8765639328:AAFk1v5PnqcnqOqk3N7Xbugquy8MT3BBr_U"
CREATOR_ID = 8269156736
TELEGRAM_API_PROXY = None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== ВСТРОЕННЫЕ ДЕЙСТВИЯ =====
DEFAULT_ACTIONS = {
    "обнять": {"male": "Обнял", "female": "Обняла", "emoji": "🫂"},
    "ударить": {"male": "Ударил", "female": "Ударила", "emoji": "👊"},
    "погладить": {"male": "Погладил", "female": "Погладила", "emoji": "🤲"},
    "поцеловать": {"male": "Поцеловал", "female": "Поцеловала", "emoji": "💋"},
    "сесть": {"male": "Сел рядом с", "female": "Села рядом с", "emoji": "🪑"},
    "успокоить": {"male": "Успокоил", "female": "Успокоила", "emoji": "🫂"},
    "поговорить": {"male": "Поговорил с", "female": "Поговорила с", "emoji": "💬"},
    "пожениться": {"male": "Поженился на", "female": "Поженилась на", "emoji": "💍❤️"},
    "завести отношения": {"male": "Завел отношения с", "female": "Завела отношения с", "emoji": "💕"},
    "укусить": {"male": "Укусил", "female": "Укусила", "emoji": "🦷"},
    "щекотать": {"male": "Пощекотал", "female": "Пощекотала", "emoji": "😂"},
    "подарить цветы": {"male": "Подарил цветы", "female": "Подарила цветы", "emoji": "💐"},
    "обнять крепко": {"male": "Крепко обнял", "female": "Крепко обняла", "emoji": "🤗"},
    "потанцевать": {"male": "Потанцевал с", "female": "Потанцевала с", "emoji": "💃🕺"},
    "спеть": {"male": "Спел для", "female": "Спела для", "emoji": "🎤"},
    "приготовить еду": {"male": "Приготовил еду для", "female": "Приготовила еду для", "emoji": "🍳"},
    "сделать массаж": {"male": "Сделал массаж", "female": "Сделала массаж", "emoji": "💆"},
    "поздравить": {"male": "Поздравил", "female": "Поздравила", "emoji": "🎉"},
    "извиниться": {"male": "Извинился перед", "female": "Извинилась перед", "emoji": "🙏"},
    "попросить прощения": {"male": "Попросил прощения у", "female": "Попросила прощения у", "emoji": "🥺"}
}

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('dotbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            gender TEXT DEFAULT 'male',
            custom_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            is_premium BOOLEAN DEFAULT FALSE,
            premium_until TIMESTAMP NULL,
            registered_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            trigger TEXT,
            response_male TEXT,
            response_female TEXT,
            emoji TEXT DEFAULT '',
            uses INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_name TEXT,
            target_name TEXT,
            used_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, first_name, role, registered_at)
        VALUES (?, ?, ?, ?)
    ''', (CREATOR_ID, "𝓜𝓪𝓭𝓪𝓶", "creator", datetime.now()))
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_user(user_id):
    conn = sqlite3.connect('dotbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id, first_name, gender='male'):
    conn = sqlite3.connect('dotbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, first_name, gender, registered_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, first_name, gender, datetime.now()))
    conn.commit()
    conn.close()

def update_user_gender(user_id, gender):
    conn = sqlite3.connect('dotbot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET gender = ? WHERE user_id = ?', (gender, user_id))
    conn.commit()
    conn.close()

def get_custom_actions():
    conn = sqlite3.connect('dotbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT trigger, response_male, response_female, emoji FROM custom_actions')
    actions = cursor.fetchall()
    conn.close()
    return actions

# ===== ИНЛАЙН-РЕЖИМ =====
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower().strip()
    user_id = update.effective_user.id
    
    # Если пустой запрос
    if not query:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="📖 Помощь",
                description="Введите: trig. <действие> @username",
                input_message_content=InputTextMessageContent(
                    "📖 DotBotRPG\nВведите trig. <действие> @username"
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=60)
        return
    
    # Если запрос начинается с "trig."
    if not query.startswith("trig."):
        results = [
            InlineQueryResultArticle(
                id="hint",
                title="💡 Начните с trig.",
                description='Пример: trig. Обнять @username',
                input_message_content=InputTextMessageContent(
                    '💡 Напишите: trig. <действие> @username'
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=60)
        return
    
    # Парсим: trig. Обнять @username
    parts = query.split(" ", 2)
    if len(parts) < 3:
        # Показать популярные действия
        results = []
        for action in ["обнять", "поцеловать", "ударить", "погладить"]:
            results.append(
                InlineQueryResultArticle(
                    id=action,
                    title=action.capitalize(),
                    description=f"trig. {action} @username",
                    input_message_content=InputTextMessageContent(
                        f"@{update.effective_user.username} {DEFAULT_ACTIONS[action]['male']} @username {DEFAULT_ACTIONS[action]['emoji']}"
                    )
                )
            )
        await update.inline_query.answer(results[:5], cache_time=60)
        return
    
    action = parts[1].lower()
    target = parts[2].strip()
    
    # Убираем @ если есть
    if target.startswith("@"):
        target = target[1:]
    
    # Проверяем на себя
    if target == update.effective_user.username:
        results = [
            InlineQueryResultArticle(
                id="self",
                title="😅 Нельзя на себя!",
                input_message_content=InputTextMessageContent(
                    "😅 Нельзя сделать это на самого себя!"
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return
    
    # Проверяем на бота
    if target == "DotBotRPG_bot":
        results = [
            InlineQueryResultArticle(
                id="bot",
                title="🤖 Я всего лишь бот!",
                input_message_content=InputTextMessageContent(
                    "🤖 Я всего лишь бот, но спасибо!"
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return
    
    user = get_user(user_id)
    if not user:
        results = [
            InlineQueryResultArticle(
                id="nouser",
                title="❌ Зарегистрируйтесь!",
                description="Напишите /start в личные сообщения",
                input_message_content=InputTextMessageContent(
                    "❌ Вы не зарегистрированы! Напишите /start"
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=60)
        return
    
    gender = user[2] if user else 'male'
    name = user[3] if user and user[3] else user[1] if user else update.effective_user.first_name
    
    # Проверяем встроенные действия
    if action in DEFAULT_ACTIONS:
        action_data = DEFAULT_ACTIONS[action]
        response_template = action_data['male'] if gender == 'male' else action_data['female']
        emoji = action_data['emoji']
        
        # Формируем ответ
        response = f"{name} {response_template} @{target} {emoji}"
        
        results = [
            InlineQueryResultArticle(
                id=action,
                title=f"{action.capitalize()} @{target}",
                description=response,
                input_message_content=InputTextMessageContent(response)
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return
    
    # Проверяем кастомные действия
    custom_actions = get_custom_actions()
    for custom in custom_actions:
        if custom[0].lower() == action:
            response_template = custom[1] if gender == 'male' else custom[2]
            emoji = custom[3] if custom[3] else ""
            response = f"{name} {response_template} @{target} {emoji}".strip()
            
            results = [
                InlineQueryResultArticle(
                    id=f"custom_{action}",
                    title=f"{action.capitalize()} @{target}",
                    description=response,
                    input_message_content=InputTextMessageContent(response)
                )
            ]
            await update.inline_query.answer(results, cache_time=0)
            return
    
    # Действие не найдено
    results = [
        InlineQueryResultArticle(
            id="notfound",
            title="🤖 Такого действия нет!",
            input_message_content=InputTextMessageContent(
                "🤖 Такого действия нет!"
            )
        )
    ]
    await update.inline_query.answer(results, cache_time=60)

# ===== ОБЫЧНЫЕ КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    user = get_user(user_id)
    
    if user is None:
        keyboard = [
            [
                InlineKeyboardButton("👦 Мужской", callback_data="gender_male"),
                InlineKeyboardButton("👧 Женский", callback_data="gender_female")
            ]
        ]
        await update.message.reply_text(
            "👋 Добро пожаловать в DotBotRPG!\n\nДля начала выберите свой пол:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return
    
    role = user[5] if user else 'user'
    name = user[3] if user and user[3] else update.effective_user.first_name
    
    keyboard = []
    if role == 'creator':
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("📋 Все действия", callback_data="all_actions")],
            [InlineKeyboardButton("⭐ Премиум", callback_data="premium")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("📋 Все действия", callback_data="all_actions")],
            [InlineKeyboardButton("⭐ Премиум", callback_data="premium")]
        ]
    
    await update.message.reply_text(
        f"📱 DotBotRPG\n\n👋 Привет, {name}!\n\nИспользуй инлайн-режим:\n@DotBotRPG_bot trig. Обнять @username",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_main_menu_from_query(query):
    user = get_user(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ Ошибка")
        return
    
    role = user[5] if user else 'user'
    name = user[3] if user and user[3] else query.from_user.first_name
    
    keyboard = []
    if role == 'creator':
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("📋 Все действия", callback_data="all_actions")],
            [InlineKeyboardButton("⭐ Премиум", callback_data="premium")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("📋 Все действия", callback_data="all_actions")],
            [InlineKeyboardButton("⭐ Премиум", callback_data="premium")]
        ]
    
    await query.edit_message_text(
        f"📱 DotBotRPG\n\n👋 Привет, {name}!\n\nИспользуй инлайн-режим:\n@DotBotRPG_bot trig. Обнять @username",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("gender_"):
        gender = "male" if data == "gender_male" else "female"
        register_user(query.from_user.id, query.from_user.first_name, gender)
        await query.edit_message_text(f"✅ Пол установлен: {'Мужской' if gender == 'male' else 'Женский'}!")
        await show_main_menu_from_query(query)
    
    elif data == "settings":
        await show_settings(query)
    
    elif data == "back_to_menu":
        await show_main_menu_from_query(query)
    
    elif data == "change_gender":
        await change_gender(update, context)
    
    elif data.startswith("set_gender_"):
        await set_gender(update, context)
    
    elif data == "all_actions":
        await show_all_actions(query)

async def show_settings(query):
    user = get_user(query.from_user.id)
    if not user:
        return
    
    gender_text = "Мужской" if user[2] == 'male' else "Женский"
    role_text = "Создатель" if user[5] == 'creator' else "Премиум" if user[6] else "Бесплатный"
    name = user[3] if user[3] else user[1]
    
    keyboard = [
        [InlineKeyboardButton("🔄 Сменить пол", callback_data="change_gender")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        f"⚙️ Настройки\n\n👤 Имя: {name}\n⚧ Пол: {gender_text}\n📊 Статус: {role_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("👦 Мужской", callback_data="set_gender_male"), InlineKeyboardButton("👧 Женский", callback_data="set_gender_female")]]
    await query.edit_message_text("Выберите ваш пол:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gender = "male" if query.data == "set_gender_male" else "female"
    update_user_gender(query.from_user.id, gender)
    gender_text = "Мужской" if gender == "male" else "Женский"
    await query.edit_message_text(f"✅ Пол изменён на {gender_text}!")
    await show_settings(query)

async def show_all_actions(query):
    actions_text = "📋 Все действия:\n\n"
    actions_text += "🔹 Встроенные (20):\n"
    for action in list(DEFAULT_ACTIONS.keys())[:5]:
        actions_text += f"• {action.capitalize()}\n"
    actions_text += f"... и ещё {len(DEFAULT_ACTIONS) - 5}\n\n"
    actions_text += "Используй:\n@DotBotRPG_bot trig. Обнять @username"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
    await query.edit_message_text(actions_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 DotBotRPG\n\n"
        "📌 Инлайн-режим:\n"
        "@DotBotRPG_bot trig. Обнять @username\n\n"
        "📌 Команды:\n"
        "/start - Главное меню\n"
        "/help - Помощь"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено")

# ===== ЗАПУСК =====
async def main():
    print("🚀 Инициализация базы данных...")
    init_db()
    
    print("🔧 Создание приложения...")
    builder = ApplicationBuilder().token(TOKEN)
    if TELEGRAM_API_PROXY:
        builder = builder.base_url(TELEGRAM_API_PROXY)
    else:
        print("🌐 Прямое подключение к Telegram API")
    
    builder = builder.connect_timeout(60).read_timeout(60).write_timeout(60)
    application = builder.build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ИНЛАЙН-РЕЖИМ
    application.add_handler(InlineQueryHandler(inline_query))
    
    print("=" * 50)
    print("🤖 DotBotRPG запущен с инлайн-режимом!")
    print("=" * 50)
    print(f"👑 Создатель: {CREATOR_ID}")
    print(f"📋 Встроенных действий: {len(DEFAULT_ACTIONS)}")
    print("=" * 50)
    print("✅ Бот готов к работе!")
    print("=" * 50)
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
