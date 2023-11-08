import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, BaseMiddleware, Router
from aiogram.types import Message, \
    ContentType as CT, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from typing import Callable, Any, Awaitable, Union
from data.__all_models import *
from data import db_session
from db_func import *
import asyncio

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

db_session.global_init(f"{PROJECT_PATH}/data/main.db")

N_OF_DECISION = int(os.getenv("N_OF_DECISION"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_CHAT_IDS = list(map(lambda x: int(x), os.getenv("ADMIN_CHAT_IDS").split(",")))
API_TOKEN = os.getenv("SECRET_TG_API_TOKEN")
ADMIN_TAGS = os.getenv("ADMIN_TAGS").split()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router(name=__name__)
dp.include_router(router)

SENT_TEXT = "Пост отправлен. Ждите обработки админов. Если пост долгое время не выкладывается," \
            " значит его, скорее всего, не приняли админы"

# @dp.channel_post()
# def test(message: Message):
#     print(message.chat.id)


def get_image_id(message: Message) -> str:
    return message.photo[-1].file_id


def get_document_id(message: Message) -> str:
    return message.document.file_id


async def send_post_to_adm(bot: Bot, post_db: Post):
    post_id = post_db.id
    await send_post(bot, post_id, ADMIN_CHAT_IDS)

    inline_keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=
    [[InlineKeyboardButton(text="✅", callback_data=f"approve_post {post_id}"),
      InlineKeyboardButton(text="❌", callback_data=f"disapprove_post {post_id}")]])

    for chat_id in ADMIN_CHAT_IDS:
        await bot.send_message(chat_id=chat_id, text=f"Принять пост от @{post_db.username}?", reply_markup=inline_keyboard)


async def publish_post(bot: Bot, post_id):
    await send_post(bot, post_id, [CHANNEL_ID])


class AlbumMiddleware(BaseMiddleware):
    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 0.01):
        self.latency = latency

    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            message: Message,
            data: dict[str, Any]
    ) -> Any:
        if not message.media_group_id:
            await handler(message, data)
            return
        try:
            self.album_data[message.media_group_id].append(message)
        except KeyError:
            self.album_data[message.media_group_id] = [message]
            await asyncio.sleep(self.latency)

            data['_is_last'] = True
            data["album"] = self.album_data[message.media_group_id]
            await handler(message, data)

        if message.media_group_id and data.get("_is_last"):
            del self.album_data[message.media_group_id]
            del data['_is_last']


dp.message.middleware(AlbumMiddleware())


@dp.message(F.text == "/admin_tags")
async def admin_tags(message : Message):
    text = "Вот полный список админов:\n" + "\n".join(ADMIN_TAGS)
    await bot.send_message(chat_id=message.chat.id, text=text)


@dp.message(F.text == "/start")
async def adm_red(message: Message):
    # await bot.send_message(chat_id=CHANNEL_ID, text=".")
    await bot.send_message(chat_id=message.chat.id, text="Приветствуем в предложке Тяжести Трицепса! Просто отправьте пост который хотите предложить")


@dp.message(F.text.startswith("/ask_admin"))
async def ask_admin(message: Message):
    ask_text = message.text[10:]
    if not ask_text.strip():
        await message.reply(text="Вы пытаетесь отправить пустое сообщение. Пожалуйста, вводите команду в формате:\n"
                                 "/ask_admin [ваш вопрос]")
        return
    inline_keyboard_buttons = []
    db_sess = db_session.create_session()
    question = Question()
    question.username = message.from_user.username
    question.user_id = message.from_user.id
    question.text = ask_text
    db_sess.add(question)
    db_sess.commit()
    for adm in ADMIN_TAGS:
        inline_keyboard_buttons.append([InlineKeyboardButton(text=f"{adm}",
                                                             callback_data=f"ask_adm {adm} "
                                                                           f"{question.id}")])
    inline_keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard_buttons)
    await bot.send_message(chat_id=message.chat.id, text="Выберите админа, которому хотите задать вопрос",
                           reply_markup=inline_keyboard)


@dp.message(F.text == "/adm_req")
async def adm_red(message: Message):
    await bot.send_message(chat_id=ADMIN_CHAT_IDS[0], text=f"Новый запрос в админы: username - {message.from_user.username}"
                                                     f", user_id - {message.from_user.id}")


@dp.message(F.content_type.in_([CT.PHOTO, CT.VIDEO, CT.DOCUMENT]))
async def handle_albums(message: Message, album: list[Message]=None):
    if album:
        media_dict = {}
        text = None
        if album[0].caption:
            text = album[0].caption
        photo = []
        video = []
        document = []
        # media_group = []
        for msg in album:
            if msg.photo:
                file_id = msg.photo[-1].file_id
                photo.append(file_id)
            elif msg.video:
                file_id = msg.video.file_id
                video.append(file_id)
            elif msg.document:
                file_id = msg.document.file_id
                document.append(file_id)
        if photo:
            media_dict["photo"] = photo
        if video:
            media_dict["video"] = video
        if document:
            media_dict["document"] = document
        post_id = create_post(message, media=media_dict, text=text)
        await bot.send_message(chat_id=message.from_user.id, text=SENT_TEXT)
        # media_group[0].caption = "залил предложку"
        # await bot.send_media_group(chat_id=message.chat.id, media=media_group)
    elif message.photo:
        post_id = create_post(message, media={"photo": [message.photo[-1].file_id]}, text=message.caption)
        await bot.send_message(chat_id=message.from_user.id, text=SENT_TEXT)
    elif message.video:
        post_id = create_post(message, media={"video": [message.video.file_id]}, text=message.caption)
        await bot.send_message(chat_id=message.from_user.id, text=SENT_TEXT)
    elif message.document:
        post_id = create_post(message, media={"document": [message.document.file_id]}, text=message.caption)
        await bot.send_message(chat_id=message.from_user.id, text=SENT_TEXT)
    db_sess = db_session.create_session()
    post_db = db_sess.query(Post).filter(Post.id == post_id).first()
    await send_post_to_adm(bot, post_db)


@dp.message(F.text)
async def message_handler(message: Message) -> None:
    try:
        repl_msg_id = message.reply_to_message.message_id
        if not message.from_user.id in ADMIN_CHAT_IDS or not message.reply_to_message.text.startswith("Вам задали анонимное сообщение:"):
            return
        db_sess = db_session.create_session()
        question = db_sess.query(Question).where(Question.message_id == repl_msg_id).first()
        await bot.send_message(chat_id=question.user_id, text=f"Ответ на ваш вопрос для {question.adm_username}:\n"
                                                              f"{message.text}")
        return
    except AttributeError as e:
        pass
    post_id = create_post(message, media=None, text=message.text)
    db_sess = db_session.create_session()
    post_db = db_sess.query(Post).filter(Post.id == post_id).first()
    await send_post_to_adm(bot, post_db)
    await bot.send_message(chat_id=message.from_user.id, text=SENT_TEXT)


def delete_post(db_sess, post_db):
    "you must commit db_sess outside the function"
    db_sess.delete(post_db)
    os.remove(f"data/posts/{post_db.id}.json")


@router.callback_query()
async def callback_query_keyboard(callback_query: CallbackQuery):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    data = callback_query.data
    if data.startswith("approve") or data.startswith("disapprove"):
        post_id = data.split()[-1]
        db_sess = db_session.create_session()
        post_db = db_sess.query(Post).filter(Post.id == post_id).first()
        if not post_db:
            await bot.send_message(chat_id=callback_query.from_user.id, text="Похоже такого поста нет в предложке, "
                                                                             "значит"
                                                                             " он либо уже отвергнут админами, либо "
                                                                             "опубликован. Проверьте канал")
            return
        if data.startswith("approve"):
            if post_db.adm_approved + 1 >= N_OF_DECISION:
                await publish_post(bot, post_id)
                delete_post(db_sess, post_db)
            else:
                post_db.adm_approved += 1
        elif data.startswith("disapprove"):
            if post_db.adm_disapproved + 1 >= N_OF_DECISION:
                delete_post(db_sess, post_db)
            else:
                post_db.adm_disapproved += 1
                db_sess.merge(post_db)
        db_sess.commit()
    elif data.startswith("ask_adm"):
        asked_adm = data.split()[1]
        question_id = data.split()[2]
        db_sess = db_session.create_session()
        question = db_sess.query(Question).where(Question.id == question_id).first()
        text = question.text
        msg = await bot.send_message(chat_id=ADMIN_CHAT_IDS[ADMIN_TAGS.index(asked_adm)],
                                     text="Вам задали анонимное сообщение:\n" + text +
                                                                   "\n Ответьте на это сообщение чтобы отправить "
                                                                   "ответ пользователю (отвечайте текстом)")
        # question = Question()
        question.adm_username = asked_adm
        # question.username = username
        # question.user_id = user_id
        question.message_id = msg.message_id
        # db_sess = db_session.create_session()
        # db_sess.add(question)
        db_sess.merge(question)
        db_sess.commit()

dp.run_polling(bot)