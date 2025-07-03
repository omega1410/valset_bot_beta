from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters

tests = {
    1: [
        {
            "question": "Что входит в стоимость проживания?",
            "options": [
                "Только завтрак",
                "Завтрак и ужин",
                "Проживание, завтрак и услуги",
            ],
            "correct_index": 1,
        },
        {
            "question": "Сколько человек может жить в номере стандарт?",
            "options": ["1", "2", "4"],
            "correct_index": 1,
        },
    ],
    2: [
        {
            "question": "Когда начинается заезд?",
            "options": ["После 12:00", "После 14:00", "После 16:00"],
            "correct_index": 1,
        }
    ],
}

test_state = {}


def register_test_handlers(app: Client):
    @app.on_callback_query(filters.regex(r"^start_test_(\d+)$"))
    async def start_test(client: Client, callback_query: CallbackQuery):
        section_id = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id

        if section_id not in tests:
            await callback_query.message.reply("Тест к этому разделу пока не добавлен.")
            return

        test_state[user_id] = (section_id, 0, 0)
        await send_question(client, callback_query.message.chat.id, user_id)

    @app.on_callback_query(filters.regex(r"^answer_(\d+)_(\d+)$"))
    async def handle_answer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        section_id, current_q, correct = test_state.get(user_id, (None, None, None))

        if section_id is None:
            await callback_query.answer("Что-то пошло не так.")
            return

        selected = int(callback_query.data.split("_")[2])
        question_data = tests[section_id][current_q]
        if selected == question_data["correct_index"]:
            correct += 1

        current_q += 1
        if current_q >= len(tests[section_id]):
            await callback_query.message.edit_text(
                f"Тест завершён ✅\n\nПравильных ответов: {correct} из {len(tests[section_id])}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙 Назад", callback_data="open_section_menu"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔁 Пройти тест заново",
                                callback_data=f"start_test_{section_id}",
                            )
                        ],
                    ]
                ),
            )
            del test_state[user_id]
        else:
            test_state[user_id] = (section_id, current_q, correct)
            await send_question(client, callback_query.message.chat.id, user_id)

        await callback_query.answer()


def generate_test_button(section_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📝 Пройти тест", callback_data=f"start_test_{section_id}"
                )
            ]
        ]
    )


async def send_question(client: Client, chat_id: int, user_id: int):
    section_id, q_index, _ = test_state[user_id]
    question_data = tests[section_id][q_index]
    question = question_data["question"]
    options = question_data["options"]

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"answer_{section_id}_{i}")]
        for i, opt in enumerate(options)
    ]

    await client.send_message(
        chat_id, f"❓ {question}", reply_markup=InlineKeyboardMarkup(keyboard)
    )
