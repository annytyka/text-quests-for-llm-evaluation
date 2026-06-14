import json
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from config import TOKEN, QUEST_PATH, ENDINGS_PATH, USERS_DIR, USERS_INDEX_FILE, START_MESSAGE, FULL_INFO
from config import FIRST_SCENE_ID
from engine import safe_delete

import questions
from questions import router, is_survey_completed, start_survey

from storage import UserStorage, UserIndex

storage = UserStorage(USERS_DIR)
questions.storage = storage

users_index = UserIndex(USERS_INDEX_FILE)

os.makedirs(os.path.dirname(USERS_DIR), exist_ok=True)

if not os.path.exists(USERS_INDEX_FILE):
    with open(USERS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

with open(QUEST_PATH, "r", encoding="utf-8") as f:
    QUEST_DATA = json.load(f)

with open(ENDINGS_PATH, "r", encoding="utf-8") as f:
    ENDINGS_DATA = json.load(f)

COUNT_ENDINGS = len(ENDINGS_DATA)

def get_ending_description(number: str):
        for e in ENDINGS_DATA:
            if e["id"] == number:
                return e["text"]
        return "???"

async def build_endings_text(username):
    user = await storage.get_user(username)
    opened = user.get("endings_opened", [])

    count = len([id for id, counter in opened.items() if counter > 0])

    endings_suffix = ""

    if 11 <= count % 100 <= 19:
        endings_suffix = "ок"        
    elif 2 <= count % 10 <= 4:
        endings_suffix = "ки"
    elif count % 10 == 1:
        endings_suffix = "ку"
    else:
        endings_suffix = "ок"

    count_text = f"Вы открыли {count} концов{endings_suffix} из 30 возможных!\n\n"

    text = "<b>ОТКРЫТЫЕ КОНЦОВКИ</b>\n\n"

    lines = []

    for i in range(1, 31):
        num = str(i)

        if opened[num] > 0:
            desc = get_ending_description(num)
            lines.append(f"{i} — {desc}")
        else:
            lines.append(f"{i} — ✕")

    full_text = count_text + text + "\n".join(lines)

    if count == COUNT_ENDINGS:
        full_text = "🎉Поздравляем с успешным прохождением квеста!🎉\n\n" + full_text

    return full_text
    
def get_scene_by_id(scene_id):
    for item in QUEST_DATA:
        if item["id"] == scene_id:
            return item
    return None


async def record_choice(username, node_id, choice_id, next_scene_id):

    def updater(user):
        run = user.get("current_run")

        if not run:
            return

        run["choices"].append(choice_id)
        run["scenes"].append(next_scene_id)
        run["choices_history"].append(choice_id)
        run["scenes_history"].append(next_scene_id)

        user["current_scene"] = next_scene_id

        user.setdefault("choices_visited", {})
        user["choices_visited"].setdefault(node_id, {})
        user["choices_visited"][node_id].setdefault(choice_id, 0)
        user["choices_visited"][node_id][choice_id] += 1

        if next_scene_id in user["scenes_visited"]:
            user.setdefault("scenes_visited", {})
            user["scenes_visited"].setdefault(next_scene_id, 0)
            user["scenes_visited"][next_scene_id] += 1

    await storage.update_user(username, updater)


async def record_back(username):

    def updater(user):
        run = user.get("current_run")

        if not run:
            return

        choice_id = run["choices"].pop()
        scene_id = run["scenes"].pop()
        prev_scene_id = run["scenes"][-1]
        run["choices_history"].append("0")
        run["scenes_history"].append(prev_scene_id)

        user["current_scene"] = prev_scene_id
        
        node_id = get_scene_by_id(prev_scene_id)["target"]
        user["choices_visited"][node_id][choice_id] -= 1
        user["scenes_visited"][scene_id] -= 1

    await storage.update_user(username, updater)


async def record_ending(username, end_number):

    def updater(user):
        run = user.get("current_run")
        if run:
            run.setdefault("ending", None)
            run["ending"] = end_number

        user.setdefault("endings_history", [])
        user["endings_history"].append(end_number)

        user.setdefault("endings_opened", {})
        user["endings_opened"].setdefault(end_number, 0)
        user["endings_opened"][end_number] += 1

        if run:
            user.setdefault("runs", [])
            run_with_id = run.copy()
            run_with_id["run_id"] = user["run_counter"]
            user["runs"].append(run_with_id)

        user["current_run"] = {
                "choices": [],
                "scenes": [],
                "ending": [],
                "choices_history": [],
                "scenes_history": []
            }
        user["current_scene"] = None

    await storage.update_user(username, updater)


async def unlock_checkpoint(username, scene):

    def updater(user):
        if not scene.get("checkpoint_num"):
            return

        checkpoint = {
            "num": scene["checkpoint_num"],
            "text": scene["checkpoint_text"],
            "scene_id": scene["id"]
        }

        user.setdefault("checkpoints", [])

        if not any(c["num"] == checkpoint["num"] for c in user["checkpoints"]):
            user["checkpoints"].append(checkpoint)

    await storage.update_user(username, updater)


async def send_scene(bot, chat_id: int, scene: dict, username: str):

    if not scene:
        await bot.send_message(chat_id, "Ошибка: сцена не найдена.")
        return

    await unlock_checkpoint(username, scene)
    
    user = await storage.get_user(username)

    if scene["type"] == "end":
        end_number = scene.get("number", "?")
        text = scene["text"]

        final_text = f"<b>КОНЦОВКА {end_number}</b>\n\n{text}"

        await record_ending(username, end_number)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Показать открытые концовки", callback_data="show_endings"),
                ],
                [
                    InlineKeyboardButton(text="Начать квест заново", callback_data=f"checkpoint_{FIRST_SCENE_ID}")
                ]
            ]
        )

        if len(user["checkpoints"]) > 1:
            keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text="Начать с чекпойнта", callback_data="choose_checkpoint")
                ])

        keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="Подробности и дополнительная информация", callback_data="show_info")
            ])

        await bot.send_message(chat_id, final_text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    if scene["type"] == "scene":
        target = scene.get("target")

        if target:
            next_item = get_scene_by_id(target)

            if next_item and next_item["type"] == "choice":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])

                for branch in next_item["branches"]:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=branch["branch_text"],
                            callback_data=branch["branch_id"]
                        )
                    ])

                if len(user["current_run"]["scenes"]) > 1:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text="↩ Вернуться назад", callback_data="back")
                    ])

                if len(user["checkpoints"]) > 1 and len(user["current_run"]["scenes_history"]) <= 1:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text="Сменить чекпойнт", callback_data="rechoose_checkpoint")
                    ])

                scene_and_choices = scene["text"] + "\n"
                
                for branch in next_item["branches"]:
                    id = branch["branch_id"]
                    text = branch["branch_text"]
                    scene_and_choices += f"\n{id}. {text}"

                cp_num = scene.get("checkpoint_num")
                if cp_num and cp_num > 0:
                    cp_text = scene.get("checkpoint_text")
                    cp_notif = f"<b>ЧЕКПОЙНТ {cp_num}. {cp_text}</b>\n\n" 
                    scene_and_choices = cp_notif + scene_and_choices

                await bot.send_message(chat_id, scene_and_choices, parse_mode="HTML", reply_markup=keyboard)
                return

        await bot.send_message(chat_id, scene["text"])

session = AiohttpSession()
bot = Bot(TOKEN, session=session)
dp = Dispatcher()
dp.include_router(router)

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    username = str(message.from_user.id)
    user = await storage.get_user(username)

    if not user:
        scene = get_scene_by_id(FIRST_SCENE_ID)
        users_counter = len(os.listdir(USERS_DIR))

        user_data = {
            "users_counter": users_counter,
            "user_alias": message.from_user.username,
            "survey": {
                "gender": None,
                "age": None,
                "education": None,
                "study": None,
                "work": None,
                "played": None,
            },
            "run_counter": 0,
            "current_scene": None,
            "current_run": {
                "choices": [],
                "scenes": [],
                "ending": None,
                "choices_history": [],
                "scenes_history": []
            },
            "runs": [],
            "endings_opened": {
                ending["id"]: 0 for ending in ENDINGS_DATA
            },
            "endings_history": [],
            "checkpoints": [{
                "num": scene["checkpoint_num"],
                "text": scene["checkpoint_text"],
                "scene_id": scene["id"]
            }],

            "scenes_visited": {
                node["id"]: 0
                for node in QUEST_DATA
                if node["type"] == "scene"
            },
            "choices_visited": {
                node["id"]: {
                    branch["branch_id"]: 0
                    for branch in node["branches"]
                }
                for node in QUEST_DATA
                if node["type"] == "choice"
            }
        }

        await storage.create_user(username, user_data)

        users_index.add_user(
            username=str(message.from_user.id),
            user_alias=message.from_user.username,
            users_counter=users_counter
        )

    user = await storage.get_user(username)
    if not is_survey_completed(user):
        await start_survey(message, state)
        return

    user = await storage.get_user(username)

    if user and user["run_counter"] > 0:
        current_scene_id = user.get("current_scene")

        if not current_scene_id:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Показать открытые концовки", callback_data="show_endings")],
                    [InlineKeyboardButton(text="Начать квест заново", callback_data=f"checkpoint_{FIRST_SCENE_ID}")]
                ]
            )

            if len(user["checkpoints"]) > 1:
                keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text="Начать с чекпойнта", callback_data="choose_checkpoint")
                    ])

            keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text="Подробности и дополнительная информация", callback_data="show_info")
                ])
    
        else:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Продолжить квест",
                            callback_data="repeat"
                        )
                    ]
                ]
            )

        await message.answer(
            START_MESSAGE,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Начать квест",
                    callback_data=f"checkpoint_{FIRST_SCENE_ID}"
                )
            ],
            [InlineKeyboardButton(text="Подробности и дополнительная информация", callback_data="show_info")]
        ]
    )

    await message.answer(
        START_MESSAGE,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("checkpoint_"))
async def start_from_checkpoint(callback: CallbackQuery):
    username = str(callback.from_user.id)
    scene_id = callback.data.replace("checkpoint_", "")

    user = await storage.get_user(username)

    if user and user.get("current_run").get("scenes"):
        await callback.answer("Сначала завершите текущее прохождение")
        return

    def updater(user):
        user["current_run"] = {
            "choices": [],
            "scenes": [scene_id],
            "ending": None,
            "choices_history": [],
            "scenes_history": [scene_id]
        }

        user["current_scene"] = scene_id
        user["run_counter"] += 1

        user["scenes_visited"][scene_id] += 1

    await storage.update_user(username, updater)

    user = await storage.get_user(username)

    current_scene = get_scene_by_id(user["current_scene"])

    if not current_scene:
        await callback.answer("Ошибка: сцена не найдена")
        return

    if user.get("run_counter") > 1:
        await safe_delete(callback.message)

    await send_scene(bot, callback.message.chat.id, current_scene, username)

    await callback.answer()


@dp.callback_query(lambda c: c.data == "show_info")
async def show_info_handler(callback: CallbackQuery):
    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    if user and user.get("current_run").get("scenes"):
        await callback.answer("Сначала завершите текущее прохождение")
        return
    
    chat_id = callback.message.chat.id

    await safe_delete(callback.message)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать квест заново", callback_data=f"checkpoint_{FIRST_SCENE_ID}")]
        ]
    )

    if len(user["checkpoints"]) > 1:
        keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="Начать с чекпойнта", callback_data="choose_checkpoint")
            ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="Показать открытые концовки", callback_data="show_endings"),
    ])

    await bot.send_message(chat_id, FULL_INFO, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


@dp.callback_query(lambda c: c.data == "show_endings")
async def show_endings_handler(callback: CallbackQuery):
    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    if user and user.get("current_run").get("scenes"):
        await callback.answer("Сначала завершите текущее прохождение")
        return
    
    chat_id = callback.message.chat.id

    await safe_delete(callback.message)

    text = await build_endings_text(username)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать квест заново", callback_data=f"checkpoint_{FIRST_SCENE_ID}")]
        ]
    )

    if len(user["checkpoints"]) > 1:
        keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="Начать с чекпойнта", callback_data="choose_checkpoint")
            ])

    keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="Подробности и дополнительная информация", callback_data="show_info")
        ])

    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


@dp.callback_query(lambda c: c.data in ["1", "2", "3"])
async def handle_choice(callback: CallbackQuery):

    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    if not user or not user.get("current_scene"):
        await callback.answer("Начните игру заново")
        return
    
    current_scene_id = user.get("current_scene")
    current_scene = get_scene_by_id(current_scene_id)

    choice = None
    choice_list = []
    if current_scene["type"] == "scene":
        target = current_scene.get("target")
        if target:
            next_item = get_scene_by_id(target)
            if next_item["type"] == "choice":
                choice_list = next_item["branches"]
    for branch in choice_list:
        if branch["branch_id"] == callback.data:
            choice = branch
            break

    if not choice:
        await callback.answer("Ошибка выбора.")
        return

    await record_choice(username, target, choice["branch_id"], choice["target"])
    next_scene = get_scene_by_id(choice["target"])

    await safe_delete(callback.message)

    await send_scene(bot, callback.message.chat.id, next_scene, username)

    await callback.answer()


@dp.callback_query(lambda c: c.data == "back")
async def handle_back(callback: CallbackQuery):
    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    if not user or not user.get("current_run"):
        await callback.answer("Нет истории")
        return

    run = user["current_run"]

    if len(run["scenes"]) <= 1:
        await callback.answer("Нельзя вернуться назад")
        return

    await record_back(username)

    user = await storage.get_user(username)
    run = user["current_run"]

    prev_scene_id = run["scenes"][-1]

    await safe_delete(callback.message)

    prev_scene = get_scene_by_id(prev_scene_id)
    await send_scene(bot, callback.message.chat.id, prev_scene, username)

    await callback.answer()


@dp.callback_query(lambda c: c.data == "choose_checkpoint")
async def choose_checkpoint(callback: CallbackQuery):
    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    checkpoints = user.get("checkpoints", [])

    if not checkpoints:
        await callback.answer("Нет доступных чекпойнтов")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for cp in checkpoints:
        cp_text = str(cp["num"]) + ". " + cp["text"]
        cp_scene_id = cp["scene_id"]
        cp_callback_data = f"checkpoint_{cp_scene_id}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=cp_text,
                callback_data=cp_callback_data
            )
        ])

    await safe_delete(callback.message)
    await callback.message.answer("Выберите чекпойнт", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "rechoose_checkpoint")
async def rechoose_checkpoint(callback: CallbackQuery):
    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    if not (len(user["checkpoints"]) > 1 and len(user["current_run"]["scenes_history"]) <= 1):
        await callback.answer("Сначала завершите прохождение")
        return

    def updater(user):
        scene_id = user["current_scene"]
        user["scenes_visited"][scene_id] -= 1

        user["current_run"] = {
            "choices": [],
            "scenes": [],
            "ending": None,
            "choices_history": [],
            "scenes_history": []
        }

        user["current_scene"] = None
        user["run_counter"] -= 1

    await storage.update_user(username, updater)

    user = await storage.get_user(username)

    checkpoints = user.get("checkpoints", [])

    if not checkpoints:
        await callback.answer("Нет доступных чекпойнтов")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for cp in checkpoints:
        cp_text = str(cp["num"]) + ". " + cp["text"]
        cp_scene_id = cp["scene_id"]
        cp_callback_data = f"checkpoint_{cp_scene_id}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=cp_text,
                callback_data=cp_callback_data
            )
        ])

    await safe_delete(callback.message)
    await callback.message.answer("Выберите чекпойнт", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "repeat")
async def repeat_sending(callback: CallbackQuery):

    username = str(callback.from_user.id)
    user = await storage.get_user(username)

    current_scene_id = user.get("current_scene")
    current_scene = get_scene_by_id(current_scene_id)

    await send_scene(bot, callback.message.chat.id, current_scene, username)

    await callback.answer()


async def main():
    import logging
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
