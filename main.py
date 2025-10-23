import telebot
import json
import random
import datetime

with open('secrets.json', 'r') as file:
    token = json.loads(file.read())['Santa_Bobot']
    file.close()

bot = telebot.TeleBot(token)

exceptions = {
    'Михаил': ('Михаил', 'Регина'),
    'Регина': ('Регина', 'Михаил'),
    'Дмитрий': ('Дмитрий', 'Евгения'),
    'Евгения': ('Евгения', 'Дмитрий'),
    'Сергей': ('Сергей', 'Татьяна'),
    'Татьяна': ('Татьяна', 'Сергей'),
    'Пётр': ('Пётр', 'Ксения'),
    'Ксения': ('Ксения', 'Пётр'),
    'Борис': ('Борис', 'Анастасия'),
    'Анастасия': ('Анастасия', 'Борис')
}

invited_users = {
    'mishgun64': 'Михаил',
    'regialf': 'Регина',
    'Qenter': 'Дмитрий',
    'in_genue': 'Евгения',
    'oOSRGOo': 'Сергей',
    'Rrikki_tikki_tavi': 'Татьяна',
    'creatoff': 'Пётр',
    'sad_sad_morning': 'Ксения',
    'arhitectbg': 'Борис',
    'nanmoore': 'Анастасия'
}

bans = {
    'Михаил': '',
    'Регина': '',
    'Дмитрий': '',
    'Евгения': '',
    'Сергей': '',
    'Татьяна': '',
    'Пётр': '',
    'Ксения': '',
    'Борис': '',
    'Анастасия': ''
}

def logger(text):
    try:
        with open('./data/log', mode='a', encoding='UTF-8') as log:
            log.write(str(datetime.datetime.now()) + ' - ' + text + '\n')
            log.close()
    except:
        print(str(datetime.datetime.now()) + ' Логер сломался')

def get_registered_users():
    try:
        with open('./data/db.json', mode='r', encoding='UTF-8') as db:
            users = json.loads(db.read())
            db.close()
        return users
    except:
        logger('Не удалось выполнить чтение из БД.')

def write_registered_user(users):
    try:
        with open('./data/db.json', mode='w', encoding='UTF-8') as db:
            db.write(json.dumps(users, ensure_ascii=True))
            db.close()
    except:
        logger('Не удалось выполнить запись в БД.')

def get_choice_range(user):
    choice_range = []
    name = invited_users[user]

    for n in invited_users.values():
        if n not in exceptions[name]:
            choice_range.append(n)
    return choice_range

def mixer():
    while len(invited_users) > 0:
        try:
            dct = {}
            users = get_registered_users().keys()
            for user in users:
                user_exception = exceptions[user]
                user_ban = bans[user]
                choice_range = list(filter(lambda x: x != user_exception[0] and x != user_exception[1] and x != user_ban, list(invited_users.values())))
                dct[user] = random.choice(choice_range)
                for k, v in invited_users.items():
                    if v == dct[user]:
                        invited_users.pop(k)
                        break
            logger('Пользователи перемешаны')
            return dct
        except:
            logger('Не удалось перемешать пользователей')


@bot.message_handler(commands=['start'])
def start_message(message):
    registered_users = get_registered_users()
    username = message.from_user.username
    ban_range = get_choice_range(username)
    try:
        if username in invited_users and invited_users[username] not in registered_users.keys():
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
            button_1 = telebot.types.InlineKeyboardButton(text=ban_range[0], callback_data=invited_users[username] + ":" + ban_range[0])
            button_2 = telebot.types.InlineKeyboardButton(text=ban_range[1], callback_data=invited_users[username] + ":" + ban_range[1])
            button_3 = telebot.types.InlineKeyboardButton(text=ban_range[2], callback_data=invited_users[username] + ":" + ban_range[2])
            button_4 = telebot.types.InlineKeyboardButton(text=ban_range[3], callback_data=invited_users[username] + ":" + ban_range[3])
            button_5 = telebot.types.InlineKeyboardButton(text=ban_range[4], callback_data=invited_users[username] + ":" + ban_range[4])
            button_6 = telebot.types.InlineKeyboardButton(text=ban_range[5], callback_data=invited_users[username] + ":" + ban_range[5])
            button_7 = telebot.types.InlineKeyboardButton(text=ban_range[6], callback_data=invited_users[username] + ":" + ban_range[6])
            button_8 = telebot.types.InlineKeyboardButton(text=ban_range[7], callback_data=invited_users[username] + ":" + ban_range[7])
            keyboard.add(button_1, button_2, button_3, button_4, button_5, button_6, button_7, button_8)
            bot.send_message(message.chat.id, f'Приветствую {invited_users[username]}. Выбери одного человека, которому ты не хочешь дарить подарок в этом году', reply_markup=keyboard)
        elif username in invited_users and invited_users[username] in registered_users:
            bot.send_message(message.from_user.id, f'Снова здравствуйте {invited_users[username]}. Вы уже зарегестирированы.')
        else:
            bot.send_message(message.from_user.id, f'Вас сюда не звали {message.from_user.first_name}')
    except:
        logger(f'Не удалось вывести клавиатуру для пользователя {username}')



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    data = call.data
    username = call.from_user.username
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    try:
        bans[data.split(':')[0]] = data.split(':')[1]
        logger(f'Добавлен бан для {username}')
    except:
        logger(f'Не удалось добавить бан для {username}')
    try:
        registered_users = get_registered_users()
        id = call.from_user.id
        registered_users[invited_users[username]] = id
        write_registered_user(registered_users)
        logger(f'Пользователь {username} зарегистрирован')
        bot.send_message(call.from_user.id, f'Вы зарегистирированы.')
        if len(registered_users) == len(invited_users):
            logger('Все пользователи зарегистрированы')
            mix_result = mixer()
            for name, id in registered_users.items():
                try:
                    message_text = f'{mix_result[name]} это тот кому вы дарите подарок'
                    bot.send_message(id, message_text)
                    logger(f'Пользователь {name} получил результат')
                except:
                    logger(f'Не удалось отправить сообщение с результатом пользователю {name}')
        else:
            bot.send_message(call.from_user.id, f'Всего зарегистрировалось {len(registered_users)}/{len(invited_users)} человек. Вы узнаете результат как только все пользователи пройдут регистрацию')
    except:
        logger(f'Не удалось зарегистрировать пользователя {username}')

logger('-------------------------------------------------------------------------')
logger('Бот запущен')

try:
    open('/data/db.json', mode='r', encoding='UTF-8')
except:
    write_registered_user({})

bot.infinity_polling()