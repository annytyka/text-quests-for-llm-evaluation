from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def start_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Играть",
                    callback_data="start_game"
                )
            ]
        ]
    )


def choices_keyboard(branches):

    buttons = []

    for i, b in enumerate(branches):

        buttons.append(
            [
                InlineKeyboardButton(
                    text=b["branch_text"],
                    callback_data=str(i)
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )