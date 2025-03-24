# Импорты всякие
import os
import yaml
import logging
import random
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from sqlhelper import Base, User, Post, Settings




# Инициализация логгера
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN)

# Инициализация базы данных
print('[Predlozhka]Инициализация базы данных...')
engine = create_engine('sqlite:///database.db') # Подключение к бд
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))

# Инициализация Telegram API
print('[Predlozhka]Инициализация Telegram API...')
with open('token.yaml') as f:
    token = yaml.safe_load(f)['token']
updater = Updater(token, use_context=True)

# Создание папки для изображений
print('[Predlozhka]Creating temp folder...')
if not os.path.exists('temp'):
    os.makedirs('temp')

# Проверка настроек
print('[Predlozhka]Проверка настроек...')
session = Session()
settings = session.query(Settings).first()
if not settings: # Если их нет
    settings = Settings(False, None, None)
    session.add(settings)
# Инициализация настроек, в случае их отсутствия
initialized = settings.initialized
target_channel = settings.target_channel
if initialized:
    if target_channel:
        print('[Predlozhka]Настройки...[OK], целевой канал: {}'.format(target_channel))
    elif settings.initializer_id:
        print('[Predlozhka][WARN]Кажется, что бот инициализирован, но цель не выбрана. Раздражающий инициализатор...')
        updater.bot.send_message(settings.initializer_id, 'Предупреждение! Целевой канал не указан.')
    else:
        print('[Predlozhka][WARN]Кажется, что бот инициализирован, но ни цель, ни инициализатор не указаны. '
              'Требуется техническое обслуживание базы данных!')
else:
    print('[Predlozhka][CRITICAL]Бот не инициализирован! Ждем инициализатора...')
session.commit()
session.close()

# Функции самого бота
print('[Predlozhka]Объявление функций и обработчиков...')

# Действия при команде /start
def start(update: Update, context: CallbackContext): # Действия при команде /start
    user_name = f'{update.effective_user.first_name} {update.effective_user.last_name}'
    print(f'[Predlozhka][start]Сработало сообщение команды запуска от пользователя {user_name}({update.effective_user.id})')
    db = Session()
    if not db.query(User).filter_by(user_id=update.effective_user.id).first():
        db.add(User(update.effective_user.id))
    update.message.reply_text('Добро пожаловать! Для того чтобы предложить пост, просто отправьте изображение '
                              '(можно с текстом).')
    db.commit()

# Действия при команде инициализации (первого запуска) бота
def initialize(update: Update, context: CallbackContext):
    global initialized, target_channel
    if not initialized:
        db = Session()
        print('[Predlozhka][INFO]Запущена команда инициализации!')
        initialized = True
        initializer = update.effective_user.id
        parameters = update.message.text.replace('/init ', '').split(';')
        print('[Predlozhka][INFO]Инициализирующие параметры: {}'.format(parameters))
        target_channel = parameters[0]
        settings = db.query(Settings).first()
        settings.initialized = True
        settings.initializer_id = initializer
        settings.target_channel = target_channel
        update.message.reply_text('Бот успешно инициализирован:\n{}'.format(repr(settings)))
        print('[Predlozhka]Пользователь {} выбран в качестве администратора'.format(parameters[1]))
        target_user = db.query(User).filter_by(user_id=int(parameters[1])).first()
        if target_user:
            target_user.is_admin = True
            update.message.reply_text('Пользователь {} теперь администратор!'.format(parameters[1]))
        else:
            print('[Predlozhka][WARN]User {} does not exists, creating...'.format(parameters[1]))
            update.message.reply_text("Warning! User {} does not exists. "
                                      "I'll create it anyway, but you need to know.".format(parameters[1]))
            db.add(User(user_id=int(parameters[1]), is_admin=True))
        db.commit()
        db.close()

# Получение поста
def photo_handler(update: Update, context: CallbackContext):
    print('[Predlozhka][photo_handler]Изображение получено, скачиваем...')
    db = Session()
    photo = update.message.photo[-1].get_file()
    path = 'temp/{}_{}'.format(random.randint(1, 100000000000), photo.file_path.split('/')[-1])
    photo.download(path)
    print(f'[Predlozhka][photo_handler]Изображение от {update.effective_user.first_name} ({update.effective_user.id}) скачивается, генерируется пост...')
    post = Post(update.effective_user.id, path, update.message.caption, update.effective_user.first_name, 'img')
    db.add(post)
    db.commit()
    print('[Predlozhka][photo_handler]Отправка сообщения администратору...')
    buttons = [
        [InlineKeyboardButton('✅', callback_data=json.dumps({'post': post.post_id, 'action': 'accept'})),
         InlineKeyboardButton('❌', callback_data=json.dumps({'post': post.post_id, 'action': 'decline'}))]
    ]
    updater.bot.send_photo(db.query(User).filter_by(is_admin=True).first().user_id, open(post.attachment_path, 'rb'),
                           f"{post.text}\n\nПост от {update.effective_user.first_name} ({update.effective_user.id})", reply_markup=InlineKeyboardMarkup(buttons))
    db.close()

    print('[Predlozhka][photo_handler]Sending confirmation to source...')
    update.message.reply_text('Ваш пост отправлен администратору.\nЕсли он будет опубликован - вы получите сообщение.')

def data_handler(update: Update, context: CallbackContext):
    print('[Predlozhka][photo_handler]Файл получен, скачиваем...')
    db = Session()
    file = update.message.document
    # photo = update.message.photo[-1].get_file()
    # path = 'temp/{}_{}'.format(random.randint(1, 100000000000), photo.file_path.split('/')[-1])
    # photo.download(path)
    path = context.bot.get_file(file.file_id).download('temp/' + file.file_name)
    print(f'[Predlozhka][photo_handler]Изображение от {update.effective_user.first_name} ({update.effective_user.id}) скачивается, генерируется пост...')
    post = Post(update.effective_user.id, path, update.message.caption, update.effective_user.first_name, 'file')
    db.add(post)
    db.commit()
    print('[Predlozhka][photo_handler]Отправка сообщения администратору...')
    buttons = [
        [InlineKeyboardButton('✅', callback_data=json.dumps({'post': post.post_id, 'action': 'accept'})),
         InlineKeyboardButton('❌', callback_data=json.dumps({'post': post.post_id, 'action': 'decline'}))]
    ]
    updater.bot.send_document(db.query(User).filter_by(is_admin=True).first().user_id, open(post.attachment_path, 'rb'),
                           f"{post.text}\n\nПост от {update.effective_user.first_name} ({update.effective_user.id})", reply_markup=InlineKeyboardMarkup(buttons))
    db.close()

    print('[Predlozhka][photo_handler]Sending confirmation to source...')
    update.message.reply_text('Ваш пост отправлен администратору.\nЕсли он будет опубликован - вы получите сообщение.')

def video_handler(update: Update, context: CallbackContext):
    print('[Predlozhka][photo_handler]Файл получен, скачиваем...')
    db = Session()
    file = update.message.video
    # photo = update.message.photo[-1].get_file()
    # path = 'temp/{}_{}'.format(random.randint(1, 100000000000), photo.file_path.split('/')[-1])
    # photo.download(path)
    path = context.bot.get_file(file.file_id).download('temp/' + file.file_name)
    print(f'[Predlozhka][photo_handler]Изображение от {update.effective_user.first_name} ({update.effective_user.id}) скачивается, генерируется пост...')
    post = Post(update.effective_user.id, path, update.message.caption, update.effective_user.first_name, 'video')
    db.add(post)
    db.commit()
    print('[Predlozhka][photo_handler]Отправка сообщения администратору...')
    buttons = [
        [InlineKeyboardButton('✅', callback_data=json.dumps({'post': post.post_id, 'action': 'accept'})),
         InlineKeyboardButton('❌', callback_data=json.dumps({'post': post.post_id, 'action': 'decline'}))]
    ]
    updater.bot.send_video(db.query(User).filter_by(is_admin=True).first().user_id, open(post.attachment_path, 'rb'),
                           f"{post.text}\n\nПост от {update.effective_user.first_name} ({update.effective_user.id})", reply_markup=InlineKeyboardMarkup(buttons))
    db.close()

    print('[Predlozhka][photo_handler]Sending confirmation to source...')
    update.message.reply_text('Ваш пост отправлен администратору.\nЕсли он будет опубликован - вы получите сообщение.')

def audio_handler(update: Update, context: CallbackContext):
    print('[Predlozhka][photo_handler]Файл получен, скачиваем...')
    db = Session()
    file = update.message.audio
    # photo = update.message.photo[-1].get_file()
    # path = 'temp/{}_{}'.format(random.randint(1, 100000000000), photo.file_path.split('/')[-1])
    # photo.download(path)
    path = context.bot.get_file(file.file_id).download('temp/' + file.file_name)
    print(f'[Predlozhka][photo_handler]Изображение от {update.effective_user.first_name} ({update.effective_user.id}) скачивается, генерируется пост...')
    post = Post(update.effective_user.id, path, update.message.caption, update.effective_user.first_name, 'audio')
    db.add(post)
    db.commit()
    print('[Predlozhka][photo_handler]Отправка сообщения администратору...')
    buttons = [
        [InlineKeyboardButton('✅', callback_data=json.dumps({'post': post.post_id, 'action': 'accept'})),
         InlineKeyboardButton('❌', callback_data=json.dumps({'post': post.post_id, 'action': 'decline'}))]
    ]
    updater.bot.send_audio(db.query(User).filter_by(is_admin=True).first().user_id, open(post.attachment_path, 'rb'),
                           f"{post.text}\n\nПост от {update.effective_user.first_name} ({update.effective_user.id})", reply_markup=InlineKeyboardMarkup(buttons))
    db.close()

    print('[Predlozhka][photo_handler]Sending confirmation to source...')
    update.message.reply_text('Ваш пост отправлен администратору.\nЕсли он будет опубликован - вы получите сообщение.')


def callback_handler(update: Update, context: CallbackContext):
    print('[Predlozhka][callback_handler]Processing admin interaction')
    db = Session()
    if db.query(User).filter_by(user_id=update.effective_user.id).first().is_admin:
        print('[Predlozhka][callback_handler][auth_ring]Authentication successful')
        data = json.loads(update.callback_query.data)
        print('[Predlozhka][callback_handler]Data: {}'.format(data))
        post = db.query(Post).filter_by(post_id=data['post']).first()
        if post:
            print('[Predlozhka][callback_handler]Найдено сообщение')
            if data['action'] == 'accept':
                print('[Predlozhka][callback_handler]Действие: принять')
                if post.file_type == "img":
                    if post.text is None:
                        updater.bot.send_photo(target_channel, open(post.attachment_path, 'rb'), caption=f"Пост от {post.owner_name}")
                    else:
                        updater.bot.send_photo(target_channel, open(post.attachment_path, 'rb'), caption=f"{post.text} \n \n Пост от {post.owner_name}")
                if post.file_type == "file":
                    if post.text is None:
                        updater.bot.send_document(target_channel, open(post.attachment_path, 'rb'), caption=f"Пост от {post.owner_name}")
                    else:
                        updater.bot.send_document(target_channel, open(post.attachment_path, 'rb'), caption=f"{post.text} \n \n Пост от {post.owner_name}")
                if post.file_type == "video":
                    if post.text is None:
                        updater.bot.send_video(target_channel, open(post.attachment_path, 'rb'), caption=f"Пост от {post.owner_name}")
                    else:
                        updater.bot.send_video(target_channel, open(post.attachment_path, 'rb'), caption=f"{post.text} \n \n Пост от {post.owner_name}")
                if post.file_type == "audio":
                    if post.text is None:
                        updater.bot.send_audio(target_channel, open(post.attachment_path, 'rb'), caption=f"Пост от {post.owner_name}")
                    else:
                        updater.bot.send_audio(target_channel, open(post.attachment_path, 'rb'), caption=f"{post.text} \n \n Пост от {post.owner_name}")
                update.callback_query.answer('✅ Пост успешно отправлен')
                updater.bot.send_message(post.owner_id, 'Предложеный вами пост был опубликован')
            elif data['action'] == 'decline':
                print('[Predlozhka][callback_handler]Действие: отклонить')
                update.callback_query.answer('Пост отклонен')
            print('[Predlozhka][callback_handler]Уборка...')
            try:
                os.remove(post.attachment_path)
            except:
                pass
            db.delete(post)
            updater.bot.delete_message(update.callback_query.message.chat_id, update.callback_query.message.message_id)
        else:
            update.callback_query.answer('Ошибка: пост не найден')
    else:
        print('[Predlozhka][callback_handler][auth_ring]ОШИБКА аутентификации!')
        update.callback_query.answer('Обнаружен несанкционированный доступ!')
    db.commit()
    db.close()

print('[Predlozhka]Все, что связано с кодом, сделано. Ждем, когда что-нибудь произойдет...')

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('init', initialize))
updater.dispatcher.add_handler(MessageHandler(Filters.photo & Filters.private, photo_handler))
updater.dispatcher.add_handler(MessageHandler(Filters.document & Filters.private, data_handler))
updater.dispatcher.add_handler(MessageHandler(Filters.video & Filters.private, video_handler))
updater.dispatcher.add_handler(MessageHandler(Filters.audio & Filters.private, audio_handler))
updater.dispatcher.add_handler(CallbackQueryHandler(callback_handler))

updater.start_polling()