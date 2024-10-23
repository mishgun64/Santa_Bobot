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

def logger(text):
    try:
        with open('/data/log', mode='a', encoding='UTF-8') as log:
            log.write(str(datetime.datetime.now()) + ' - ' + text + '\n')
            log.close()
    except:
        print(str(datetime.datetime.now()) + ' Логер сломался')

def get_registered_users():
    try:
        with open('/data/db.json', mode='r', encoding='UTF-8') as db:
            users = json.loads(db.read())
            db.close()
        return users
    except:
        logger('Не удалось выполнить чтение из БД.')


def write_registered_user(users):
    try:
        with open('/data/db.json', mode='w', encoding='UTF-8') as db:
            db.write(json.dumps(users, ensure_ascii=True))
            db.close()
    except:
        logger('Не удалось выполнить запись в БД.')

def mixer():
    while len(invited_users) > 0:
        try:
            dct = {}
            users = get_registered_users().keys()
            for user in users:
                user_exception = exceptions[user]
                choice_range = list(filter(lambda x: x != user_exception[0] and x != user_exception[1], list(invited_users.values())))
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
    try:
        registered_users = get_registered_users()
        username = message.from_user.username
        id = message.from_user.id
        if username in invited_users and invited_users[username] not in registered_users.keys():
            registered_users[invited_users[username]] = id
            write_registered_user(registered_users)
            logger(str(datetime.datetime.now()) + f' - Пользователь {username} зарегистрирован')
            bot.send_message(message.from_user.id, f'Приветствую {invited_users[username]}. Вы зарегистирировались.')
            if len(registered_users) == len(invited_users):
                logger(str(datetime.datetime.now()) + ' - Все пользователи зарегистрированы')
                mix_result = mixer()

                for name, id in registered_users.items():
                    try:
                        message_text = f'{mix_result[name]} это тот кому вы дарите подарок'
                        bot.send_message(id, message_text)
                        logger(f'Пользователь {name} получил результат')
                    except:
                        logger(f'Не удалось отправить сообщение с результатом пользователю {name}')
            else:
                bot.send_message(message.from_user.id, f'Всего зарегистрировалось {len(registered_users)}/{len(invited_users)} человек. Вы узнаете результат как только все пользователи пройдут регистрацию')

        elif username in invited_users and invited_users[username] in registered_users:
            bot.send_message(message.from_user.id, f'Снова здравствуйте {invited_users[username]}. Вы уже зарегестирированы.')
        else:
            bot.send_message(message.from_user.id, f'Вас сюда не звали {message.from_user.first_name}')
    except:
        logger(f'Не удалось зарегистрировать пользователя {username}')


logger('-------------------------------------------------------------------------')
logger('Бот запущен')

try:
    open('/data/db.json', mode='r', encoding='UTF-8')
except:
    write_registered_user({})

bot.infinity_polling()