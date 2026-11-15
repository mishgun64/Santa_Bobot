import telebot
import json
import random
import datetime
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

with open("data/secrets.json", "r") as file:
    token = json.loads(file.read())["Santa_Bobot"]
    file.close()

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "8443"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

bot = telebot.TeleBot(token)

with open("data/users.json", "r", encoding="UTF-8") as file:
    exceptions = json.loads(file.read())["exceptions"]
    file.close()
print(exceptions)

with open("data/users.json", "r", encoding="UTF-8") as file:
    invited_users = json.loads(file.read())["invited_users"]
    file.close()
print(invited_users)

with open("data/users.json", "r", encoding="UTF-8") as file:
    raw_bans = json.loads(file.read())["bans"]
    file.close()
# Обратная совместимость: старый формат хранил один бан строкой, новый — списком до двух банов
bans = {k: ([v] if isinstance(v, str) and v else ([] if isinstance(v, str) else list(v or [])))
        for k, v in raw_bans.items()}
# Дополняем участниками, которых ещё нет в bans, чтобы bans[giver] был всегда безопасен
for _name in invited_users.values():
    bans.setdefault(_name, [])
print(bans)

with open("data/users.json", "r", encoding="UTF-8") as file:
    is_registred = json.loads(file.read())["is_registred"]
    file.close()
print(is_registred)

ADMIN_USERNAME = "mishgun64"
last_mix_result = None
# RLock: webhook-обработчик держит лок на весь update, а callback_query берёт его же повторно
update_lock = threading.RLock()

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "8443"))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

commands = [
    telebot.types.BotCommand("start", "Запустить бота"),
]
bot.set_my_commands(commands)
def logger(text):
    try:
        with open("./data/log", mode="a", encoding="UTF-8") as log:
            log.write(str(datetime.datetime.now()) + " - " + text + "\n")
            log.close()
    except:
        print(str(datetime.datetime.now()) + " Логер сломался")

def get_registered_users():
    try:
        with open("./data/db.json", mode="r", encoding="UTF-8") as db:
            users = json.loads(db.read())
            db.close()
        return users
    except:
        logger("Не удалось выполнить чтение из БД.")

def write_registered_user(users):
    try:
        with open("./data/db.json", mode="w", encoding="UTF-8") as db:
            db.write(json.dumps(users, ensure_ascii=True))
            db.close()
    except:
        logger("Не удалось выполнить запись в БД.")

def save_users_config():
    config = {
        "invited_users": invited_users,
        "exceptions": exceptions,
        "bans": bans,
        "is_registred": is_registred,
    }
    try:
        with open("./data/users.json", mode="w", encoding="UTF-8") as f:
            f.write(json.dumps(config, ensure_ascii=False, indent=2))
    except:
        logger("Не удалось сохранить конфигурацию пользователей")

def clear_bans():
    for k in bans:
        bans[k] = []
    for k in is_registred:
        is_registred[k] = "❌"
    save_users_config()
    write_registered_user({})

def get_choice_range(user, exclude=()):
    choice_range = []
    name = invited_users.get(user)
    if name is None:
        return choice_range

    for n in invited_users.values():
        if n not in exceptions.get(name, []) and n not in exclude:
            choice_range.append(n)
    return choice_range

def build_ban_keyboard(giver_name, options, step, skip=None):
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    buttons = [telebot.types.InlineKeyboardButton(text=name, callback_data=f"b{step}:{giver_name}:{name}") for name in options]
    keyboard.add(*buttons)
    if skip:
        keyboard.add(telebot.types.InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"b{step}:{giver_name}:"))
    return keyboard

def complete_registration(call, username):
    global last_mix_result
    try:
        registered_users = get_registered_users()
        if registered_users is None:
            raise ValueError("не удалось прочитать БД")
        user_id = call.from_user.id
        registered_users[invited_users[username]] = user_id
        write_registered_user(registered_users)
        logger(f"Пользователь {username} зарегистрирован")
        bot.send_message(call.from_user.id, f"Вы зарегистирированы.")
        if len(registered_users) == len(invited_users):
            logger("Все пользователи зарегистрированы")
            last_mix_result = mixer()
            if last_mix_result is None:
                logger("Не удалось выполнить распределение после регистрации")
                admin_name = invited_users[ADMIN_USERNAME]
                bot.send_message(registered_users[admin_name], "Не удалось выполнить распределение после регистрации")
                return
            for name, user_id in registered_users.items():
                try:
                    message_text = f"{last_mix_result[name]} это тот кому вы дарите подарок"
                    bot.send_message(user_id, message_text)
                    logger(f"Пользователь {name} получил результат")
                except:
                    logger(f"Не удалось отправить сообщение с результатом пользователю {name}")
            admin_name = invited_users[ADMIN_USERNAME]
            send_admin_panel(registered_users[admin_name])
        else:
            bot.send_message(call.from_user.id, f"Всего зарегистрировалось {len(registered_users)}/{len(invited_users)} человек. Вы узнаете результат как только все пользователи пройдут регистрацию")
    except:
        logger(f"Не удалось зарегистрировать пользователя {username}")
        try:
            bot.send_message(call.from_user.id, "Не удалось завершить регистрацию. Нажмите 'Регистрация' ещё раз.")
        except:
            logger(f"Не удалось уведомить пользователя {username} об ошибке регистрации")

def get_history_exclusions():
    current_year = datetime.datetime.now().year
    exclusions = {}
    try:
        with open("./data/results.json", mode="r", encoding="UTF-8") as f:
            history = json.loads(f.read())
    except FileNotFoundError:
        return exclusions
    except:
        logger("Не удалось прочитать историю результатов")
        return exclusions
    for year_str, pairs in history.items():
        try:
            year = int(year_str)
        except:
            continue
        if current_year - 3 <= year <= current_year - 1:
            for giver, receiver in pairs.items():
                exclusions.setdefault(giver, set()).add(receiver)
    return exclusions

def mixer():
    try:
        users = list(get_registered_users().keys())
        if len(users) != len(invited_users):
            logger("Не удалось перемешать пользователей: зарегистрированы не все")
            return None
        receivers = list(invited_users.values())
        history = get_history_exclusions()

        adjacency = {}
        for user in users:
            excluded = set(exceptions.get(user, ()))
            for user_ban in bans.get(user, []):
                if user_ban:
                    excluded.add(user_ban)
            excluded |= history.get(user, set())
            allowed = [r for r in receivers if r not in excluded]
            random.shuffle(allowed)
            adjacency[user] = allowed

        random.shuffle(users)
        match_receiver = {}

        def try_kuhn(giver, seen):
            for receiver in adjacency[giver]:
                if receiver in seen:
                    continue
                seen.add(receiver)
                if receiver not in match_receiver or try_kuhn(match_receiver[receiver], seen):
                    match_receiver[receiver] = giver
                    return True
            return False

        for giver in users:
            if not try_kuhn(giver, set()):
                logger(f"Не удалось перемешать пользователей: нет решения для {giver}")
                return None

        dct = {giver: receiver for receiver, giver in match_receiver.items()}
        logger("Пользователи перемешаны")
        return dct
    except:
        logger("Не удалось перемешать пользователей")
        return None

def send_admin_panel(admin_id):
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn_remix = telebot.types.InlineKeyboardButton("🔄 Запустить распределение заново", callback_data="remix")
    btn_save = telebot.types.InlineKeyboardButton("💾 Запись результатов", callback_data="save_results")
    btn_clear = telebot.types.InlineKeyboardButton("🧹 Снять баны", callback_data="clear_bans")
    keyboard.add(btn_remix, btn_save, btn_clear)
    bot.send_message(admin_id, "Панель управления распределением:", reply_markup=keyboard)

def handle_remix(call):
    global last_mix_result
    if call.from_user.username != ADMIN_USERNAME:
        bot.answer_callback_query(call.id, "Нет доступа")
        return
    registered_users = get_registered_users()
    if len(registered_users) != len(invited_users):
        bot.answer_callback_query(call.id, "Не все пользователи зарегистрированы")
        return
    last_mix_result = mixer()
    if last_mix_result is None:
        bot.answer_callback_query(call.id, "Не удалось выполнить распределение")
        return
    for name, uid in registered_users.items():
        try:
            bot.send_message(uid, f"{last_mix_result[name]} это тот кому вы дарите подарок")
            logger(f"Пользователь {name} получил результат повторного распределения")
        except:
            logger(f"Не удалось отправить сообщение с результатом пользователю {name}")
    bot.answer_callback_query(call.id, "Распределение выполнено")
    send_admin_panel(call.from_user.id)

def handle_clear_bans(call):
    global last_mix_result
    if call.from_user.username != ADMIN_USERNAME:
        bot.answer_callback_query(call.id, "Нет доступа")
        return
    registered_users = get_registered_users()
    for name, uid in registered_users.items():
        try:
            bot.send_message(uid, "Баны сняты. Пройдите регистрацию заново и выберите до двух человек, которым не хотите дарить подарок.")
        except:
            logger(f"Не удалось уведомить пользователя {name}")
    clear_bans()
    last_mix_result = None
    bot.answer_callback_query(call.id, "Баны сняты")
    logger("Баны сняты администратором")
    send_admin_panel(call.from_user.id)

def handle_save_results(call):
    global last_mix_result
    if call.from_user.username != ADMIN_USERNAME:
        bot.answer_callback_query(call.id, "Нет доступа")
        return
    if last_mix_result is None:
        bot.answer_callback_query(call.id, "Сначала запустите распределение")
        return
    year = datetime.datetime.now().year
    path = "./data/results.json"
    try:
        try:
            with open(path, mode="r", encoding="UTF-8") as f:
                history = json.loads(f.read())
        except FileNotFoundError:
            history = {}
        history[str(year)] = last_mix_result
        with open(path, mode="w", encoding="UTF-8") as f:
            f.write(json.dumps(history, ensure_ascii=False, indent=2))
        bot.answer_callback_query(call.id, "Результаты записаны в файл")
        logger("Результаты распределения записаны в файл")
    except:
        bot.answer_callback_query(call.id, "Не удалось записать результаты")
        logger("Не удалось записать результаты в файл")


@bot.message_handler(commands=["start"])
def send_welcome(message):
    # создаём клавиатуру
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn1 = telebot.types.KeyboardButton("Регистрация")
    btn2 = telebot.types.KeyboardButton("Показать зарегистрированных пользователей")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        "Привет! Нажми кнопку 'Регистрация', чтобы начать.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "Регистрация")
def handle_reg_button(message):
    username = message.from_user.username
    try:
        registered_users = get_registered_users()
        if registered_users is None:
            raise ValueError("не удалось прочитать БД")
        if username in invited_users and invited_users[username] not in registered_users.keys():
            options = get_choice_range(username)
            if not options:
                logger(f"Нет доступных вариантов бана для пользователя {username}")
                bot.send_message(message.chat.id, "Нет доступных вариантов бана. Сообщите администратору.")
                return
            bot.send_message(message.chat.id, f"Приветствую {invited_users[username]}. Выберите первого человека, которому вы не хотите дарить подарок в этом году (всего можно до двух)", reply_markup=build_ban_keyboard(invited_users[username], options, 1))
        elif username in invited_users and invited_users[username] in registered_users:
            bot.send_message(message.from_user.id, f"Вы уже зарегистирированы.")
        else:
            bot.send_message(message.from_user.id, f"Вас сюда не звали {message.from_user.first_name}")
    except:
        logger(f"Не удалось вывести клавиатуру для пользователя {username}")
        try:
            bot.send_message(message.from_user.id, "Ошибка, попробуйте позже")
        except:
            logger(f"Не удалось уведомить пользователя {username} об ошибке")

@bot.message_handler(func=lambda m: m.text == "Показать зарегистрированных пользователей")
def handle_reg_users_button(message):
    registered_users = get_registered_users()
    for user, value in is_registred.items():
        if user in registered_users.keys():
            is_registred[user] = "✅"
    registred = ""
    for k, v in is_registred.items():
        registred += f"{v} {k}\n"
    bot.send_message(message.chat.id, registred)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    global last_mix_result
    data = call.data
    username = call.from_user.username
    if data == "remix":
        handle_remix(call)
        return
    if data == "save_results":
        handle_save_results(call)
        return
    if data == "clear_bans":
        handle_clear_bans(call)
        return
    parts = data.split(":", 2)
    step = parts[0]
    giver = parts[1] if len(parts) > 1 else ""
    banned = parts[2] if len(parts) > 2 else ""
    rejection = None       # текст ответа на нажатие при отказе, отправляется после лока
    log_line = None        # запись в лог, выполняется после лока
    step2_text = None
    step2_keyboard = None
    # Критическая секция: чтение db.json, проверки и запись банов атомарны, поэтому два
    # одновременных клика не могут записать бан дважды. Сетевые вызовы — после лока.
    with update_lock:
        # Защита от повторного клика по старой клавиатуре: уже зарегистрированный не перезапускает распределение
        registered_users = get_registered_users()
        giver_name = invited_users.get(username)
        if registered_users is None:
            rejection = "Ошибка, попробуйте позже"
            log_line = f"Не удалось проверить регистрацию пользователя {username}"
        elif giver_name in registered_users:
            rejection = "Вы уже зарегистирированы"
        elif step not in ("b1", "b2") or giver != giver_name:
            rejection = "Недоступно"
            log_line = f"Отклонён выбор бана от {username}: {data}"
        elif step == "b1":
            if banned not in get_choice_range(username):
                rejection = "Недоступно"
                log_line = f"Отклонён первый бан от {username}: {data}"
            else:
                bans[giver] = [banned]
                save_users_config()
                log_line = f"Добавлен первый бан для {username}"
                step2_text = "Выберите второго человека (необязательно) или нажмите \"Пропустить\""
                step2_keyboard = build_ban_keyboard(giver, get_choice_range(username, exclude=[banned]), 2, skip=True)
        elif len(bans.get(giver, [])) != 1:
            rejection = "Начните регистрацию заново"
            log_line = f"Отклонён второй бан без первого от {username}: {data}"
        elif banned and banned not in get_choice_range(username, exclude=bans[giver]):
            rejection = "Недоступно"
            log_line = f"Отклонён второй бан от {username}: {data}"
        elif banned:
            bans[giver].append(banned)
            save_users_config()
            log_line = f"Добавлен второй бан для {username}"
        else:
            log_line = f"Пользователь {username} пропустил второй бан"
    if log_line:
        logger(log_line)
    if rejection is not None:
        bot.answer_callback_query(call.id, rejection)
        return
    if step == "b1":
        try:
            bot.answer_callback_query(call.id)
        except:
            logger(f"Не удалось подтвердить нажатие для пользователя {username}")
        try:
            bot.edit_message_text(step2_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=step2_keyboard)
        except:
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            except:
                logger(f"Не удалось снять клавиатуру у старого сообщения для пользователя {username}")
            bot.send_message(call.from_user.id, step2_text, reply_markup=step2_keyboard)
        return
    try:
        bot.answer_callback_query(call.id)
    except:
        logger(f"Не удалось подтвердить нажатие для пользователя {username}")
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except:
        logger(f"Не удалось снять клавиатуру для пользователя {username}")
    # Регистрация, mixer() и рассылка — в одной критической секции: повторный клик из другого
    # потока увидит пользователя уже зарегистрированным и не запустит mixer() второй раз.
    already_registered = False
    with update_lock:
        registered_users = get_registered_users()
        if registered_users is not None and giver_name in registered_users:
            already_registered = True
            logger(f"Повторный клик от {username} после регистрации: {data}")
        else:
            complete_registration(call, username)
    if already_registered:
        bot.answer_callback_query(call.id, "Вы уже зарегистирированы")

logger("-------------------------------------------------------------------------")
logger("Бот запущен")

try:
    open("/data/db.json", mode="r", encoding="UTF-8")
except:
    write_registered_user({})


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != WEBHOOK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        if WEBHOOK_SECRET and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            self.send_response(403)
            self.end_headers()
            return
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            update = telebot.types.Update.de_json(json.loads(body))
            with update_lock:
                bot.process_new_updates([update])
        except Exception as e:
            logger(f"Не удалось обработать webhook: {e}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def do_GET(self):
        if self.path == WEBHOOK_PATH or self.path == "/":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def setup_webhook():
    try:
        bot.remove_webhook()
    except Exception as e:
        logger(f"Не удалось удалить предыдущий webhook: {e}")
    try:
        ok = bot.set_webhook(
            url=WEBHOOK_URL,
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        if ok:
            logger(f"Webhook установлен: {WEBHOOK_URL}")
        else:
            logger("Не удалось установить webhook")
    except Exception as e:
        logger(f"Ошибка установки webhook: {e}")


def start_webhook_server():
    server = ThreadingHTTPServer((WEBHOOK_HOST, WEBHOOK_PORT), WebhookHandler)
    logger(f"Webhook сервер слушает {WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}")
    server.serve_forever()


if WEBHOOK_URL:
    setup_webhook()
    start_webhook_server()
else:
    logger("WEBHOOK_URL не задан — запускаю polling")
    bot.infinity_polling()