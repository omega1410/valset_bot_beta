from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

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
        {
            "question": "Сколько человек может жить в номере стандарт?",
            "options": ["1", "2", "4"],
            "correct_index": 1,
        },
    ]
}

test_state = {}


def register_test_handlers(app: Client):
    @app.on_callback_query(filters.regex(r"^start_test_(\d+)$"), group=2)
    async def start_test(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        section_id = int(str(callback_query.data).split("_")[2])
        print(f"[test] пользователь {user_id} начал тест по разделу {section_id}")

        if section_id not in tests:
            await callback_query.message.reply("Тест не найден.")
            return

        test_state[user_id] = (section_id, 0, 0)
        await send_question(client, callback_query.message.chat.id, user_id)

    @app.on_callback_query(filters.regex(r"^answer_(\d+)_(\d+)$"), group=2)
    async def handle_answer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        section_id, current_q, correct = test_state.get(user_id, (None, None, None))

        if section_id is None:
            await callback_query.answer("Ошибка состояния.")
            return

        selected = int(str(callback_query.data).split("_")[2])
        if selected == tests[section_id][current_q]["correct_index"]:
            correct += 1
        current_q += 1

        if current_q >= len(tests[section_id]):
            await callback_query.message.edit_text(
                f"✅ Тест завершён!\nПравильных ответов: {correct} из {len(tests[section_id])}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Пройти заново", callback_data=f"start_test_{section_id}")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="open_section_menu")]
                ])
            )
            test_state.pop(user_id, None)
        else:
            test_state[user_id] = (section_id, current_q, correct)
            await send_question(client, callback_query.message.chat.id, user_id)

        await callback_query.answer()


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
