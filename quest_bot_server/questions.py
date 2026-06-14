from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import FIRST_SCENE_ID, START_MESSAGE
from engine import safe_delete
from aiogram import Router
storage = None

router = Router()

class Survey(StatesGroup):
    gender = State()
    age = State()
    played = State()
    education_level = State()
    study = State()
    work = State()

def is_survey_completed(user):
    return all([
        user.get("survey", {}).get("gender"),
        user.get("survey", {}).get("age"),
        user.get("survey", {}).get("played"),
        user.get("survey", {}).get("education"),
        user.get("survey", {}).get("study"),
        user.get("survey", {}).get("work"),
    ])


async def start_survey(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мужской", callback_data="gender_male")],
            [InlineKeyboardButton(text="Женский", callback_data="gender_female")]
        ]
    )

    await message.answer("<i>Анкета 1/6.</i>\n\nУкажите Ваш пол.", parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(Survey.gender)

@router.callback_query(Survey.gender)
async def process_gender(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)

    username = str(callback.from_user.id)
    user_gender = callback.data.replace("gender_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "gender": user_gender
    }))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="до 12", callback_data="age_child")],
            [InlineKeyboardButton(text="13–17", callback_data="age_teen")],
            [InlineKeyboardButton(text="18–24", callback_data="age_young")],
            [InlineKeyboardButton(text="25–35", callback_data="age_adult")],
            [InlineKeyboardButton(text="36–50", callback_data="age_mid")],
            [InlineKeyboardButton(text="50+", callback_data="age_senior")]
        ]
    )

    await callback.message.answer("<i>Анкета 2/6.</i>\n\nУкажите Ваш возраст.", parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(Survey.age)
    await callback.answer()

@router.callback_query(Survey.age)
async def process_age(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)
    
    username = str(callback.from_user.id)

    user_age = callback.data.replace("age_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "age": user_age
    }))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="4 класса", callback_data="edu_4")],
            [InlineKeyboardButton(text="9 классов", callback_data="edu_9")],
            [InlineKeyboardButton(text="11 классов", callback_data="edu_11")],
            [InlineKeyboardButton(text="Колледж", callback_data="edu_college")],
            [InlineKeyboardButton(text="Бакалавриат", callback_data="edu_bachelor")],
            [InlineKeyboardButton(text="Магистратура или специалитет", callback_data="edu_master")],
            [InlineKeyboardButton(text="Аспирантура", callback_data="edu_phd")]
        ]
    )

    await callback.message.answer("<i>Анкета 3/6.</i>\n\nУкажите Ваш уровень образования.", parse_mode="HTML", reply_markup=keyboard)

    await state.set_state(Survey.education_level)

    await callback.answer()

@router.callback_query(Survey.education_level)
async def process_edu(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)
    
    username = str(callback.from_user.id)

    user_education = callback.data.replace("edu_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "education": user_education
    }))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="study_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="study_no")]
        ]
    )

    await callback.message.answer("<i>Анкета 4/6.</i>\n\nВы сейчас учитесь?", parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(Survey.study)

    await callback.answer()
    


@router.callback_query(Survey.study)
async def process_study(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)
    
    username = str(callback.from_user.id)

    user_study = callback.data.replace("study_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "study": user_study
    }))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="work_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="work_no")]
        ]
    )

    await callback.message.answer("<i>Анкета 5/6.</i>\n\nВы сейчас работаете?", parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(Survey.work)

    await callback.answer()


@router.callback_query(Survey.work)
async def process_work(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)
    
    username = str(callback.from_user.id)

    user_work = callback.data.replace("work_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "work": user_work
    }))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="played_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="played_no")]
        ]
    )

    await callback.message.answer("<i>Анкета 6/6.</i>\n\nВы играли в текстовые квесты раньше?", parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(Survey.played)
    await callback.answer()



@router.callback_query(Survey.played)
async def process_played(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.message)
    
    username = str(callback.from_user.id)

    user_played = callback.data.replace("played_", "")
    await storage.update_user(username, lambda u: u["survey"].update({
        "played": user_played
    }))

    await state.clear()

    user = await storage.get_user(username)

    if user and user["run_counter"] > 0:
        current_scene_id = user.get("current_scene")

        if not current_scene_id:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Начать квест заново", callback_data=f"checkpoint_{FIRST_SCENE_ID}")]
                ]
            )

            if len(user["checkpoints"]) > 1:
                keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text="Начать с чекпойнта", callback_data="choose_checkpoint")
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

        await callback.message.answer(
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
            ]
        ]
    )

    await callback.message.answer(
        START_MESSAGE,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await callback.answer()
