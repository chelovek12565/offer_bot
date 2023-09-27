from data.__all_models import *
from data import db_session
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument
from aiogram import Bot
import json
import io
import os

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))


def create_post(message: Message, media=None, text=None):
    out_dict = {}
    # text = ""
    # media = {}
    # if not is_media:
    #     text = message.text
    # else:
    #     text = message.caption

    if text:
        out_dict["text"] = text
    if media:
        out_dict["media"] = media

    db_sess = db_session.create_session()
    post = Post()
    post.adm_disapproved = 0
    post.adm_approved = 0
    post.user_id = message.from_user.id
    post.username = message.from_user.username
    db_sess.add(post)
    db_sess.commit()
    post_id = post.id

    with io.open(f"{PROJECT_PATH}\\data\\posts\\{post_id}.json", "wt", encoding="utf-8") as f:
        f.write(json.dumps(out_dict, ensure_ascii=False))

    return post_id


async def send_post(bot: Bot, post_id: int, chat_ids: list[int | str]):
    print("asdasd")
    with open(f"{PROJECT_PATH}\\data\\posts\\{post_id}.json", "rt") as f:
        data = json.loads(f.read())

    if "media" in list(data.keys()):
        if len(list(data["media"].keys())) == 1:
            if len(data["media"][list(data["media"].keys())[0]]) == 1:
                text = None
                if "text" in list(data.keys()):
                    text = data["text"]
                if list(data["media"].keys())[0] == "photo":
                    for chat_id in chat_ids: await bot.send_photo(chat_id=chat_id, photo=data["media"]["photo"][0], caption=text)
                elif list(data["media"].keys())[0] == "video":
                    for chat_id in chat_ids: await bot.send_video(chat_id=chat_id, video=data["media"]["video"][0], caption=text)
                elif list(data["media"].keys())[0] == "document":
                    for chat_id in chat_ids: await bot.send_document(chat_id=chat_id, document=data["media"]["photo"][0], caption=text)
                return
        media_out = []
        first = True
        for key in list(data["media"].keys()):
            for item in data["media"][key]:
                caption = None
                if "text" in list(data.keys()) and first:
                    caption = data["text"]
                    first = False
                if key == "photo":
                    media_out.append(InputMediaPhoto(type="photo", media=item, caption=caption))
                elif key == "video":
                    media_out.append(InputMediaVideo(type="video", media=item, caption=caption))
                elif key == "document":
                    media_out.append(InputMediaDocument(type="document", media=item, caption=caption))
        for chat_id in chat_ids:
            await bot.send_media_group(chat_id=chat_id, media=media_out)
    else:
        for chat_id in chat_ids:
            await bot.send_message(chat_id=chat_id, text=data["text"])

