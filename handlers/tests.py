from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

tests = {
    1: [
        {
            "question": "Как вызвать Dashboard?",
            "options": [
                "Alt + F4",
                "Shift + F4",
                "Ctrl + F4",
            ],
            "correct_index": 2,
        },
        {
            "question": "Как называется основной тариф?",
            "options": ["BARNB", "PROADVNB", "BTAWEBNB"],
            "correct_index": 0,
        },
        {
            "question": "Куда нажать, чтобы посмотреть полную стоимость бронирования?",
            "options": ["Rate Query", "Dashboard", "Rate Info"],
            "correct_index": 2,
        },
    ],
    2: [
        {
            "question": "Какой документ обязателен для заселения гражданина РФ?",
            "options": [
                "Заграничный паспорт",
                "Внутренний паспорт",
                "Водительское удостоверение",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какие документы нужны для заселения иностранного гостя?",
            "options": [
                "Только паспорт",
                "Паспорт и виза (если есть)",
                "Паспорт, миграционная карта и виза (если есть)",
            ],
            "correct_index": 2,
        },
        {
            "question": "Что делать, если у гостя паспорт на замене?",
            "options": [
                "Принять временное удостоверение личности или скан старого паспорта",
                "Позвонить в МВД для подтверждения личности",
                "Отказать в заселении до получения нового паспорта",
            ],
            "correct_index": 0,
        },
    ],
    3: [
        {
            "question": "Когда ранний заезд может быть предоставлен бесплатно?",
            "options": [
                "До 06:00 утра",
                "В 11-12 утра и номер уже готов",
                "Гость заплатил половину стоимости ночи",
            ],
            "correct_index": 1,
        },
        {
            "question": "Сколько стоит ранний заезд, если гость приехал в 07:00 утра?",
            "options": [
                "Полная стоимость ночи (BARNB)",
                "Половина стоимости ночи (BARNB)",
                "Бесплатно",
            ],
            "correct_index": 1,
        },
        {
            "question": "Гость приехал в 23:00 предыдущего дня. Как рассчитать стоимость раннего заезда?",
            "options": [
                "Полная стоимость ночи (BARNB)",
                "Половина стоимости ночи (BARNB)",
                "Бесплатно",
            ],
            "correct_index": 0,
        },
    ],
    4: [
        {
            "question": "Когда поздний выезд может быть комплиментарным?",
            "options": [
                "Если выезд до 12:00",
                "Если выезд до 15:00",
                "Если выезд до 18:00",
            ],
            "correct_index": 1,
        },
        {
            "question": "Сколько стоит поздний выезд до 18:00?",
            "options": [
                "Полная стоимость ночи (BARNB)",
                "Половина стоимости ночи (BARNB)",
                "Бесплатно",
            ],
            "correct_index": 1,
        },
        {
            "question": "Что нужно сделать, если гость оплатил поздний выезд?",
            "options": [
                "Просто сообщить гостю время выезда",
                "Продлить ключи и проставить C/O Time в Opera",
                "Ничего не делать - система автоматически все обновит",
            ],
            "correct_index": 1,
        },
    ],
    8: [
        {
            "question": "Какое первое действие при отказе гостя от номера?",
            "options": [
                "Сразу предлагать возврат средств",
                "Предложить другой свободный готовый номер",
                "Настаивать на проживании в забронированном номере",
            ],
            "correct_index": 1,
        },
        {
            "question": "Когда возможен возврат средств на стойке?",
            "options": [
                "Если гость бронировал через агентство",
                "Если гость сам оплачивал на стойке",
                "В любом случае по желанию гостя",
            ],
            "correct_index": 1,
        },
        {
            "question": "Что делать, если невозможно предложить повышение категории?",
            "options": [
                "Предложить размещение в другом корпусе",
                "Настаивать на проживании в текущем номере",
                "Выписать гостя без возврата средств",
            ],
            "correct_index": 0,
        },
    ],
    12: [
        {
            "question": "Что нужно сделать в первую очередь при запросе гостя на переезд?",
            "options": [
                "Сразу оформить Room Move в Опере",
                "Предупредить в рабочем чате",
                "Выписать новые ключи",
            ],
            "correct_index": 1,
            "explanation": "Первым делом необходимо сообщить в рабочий чат: имя гостя, текущий номер и причину переезда.",
        },
        {
            "question": "Какие действия выполняются при одобренном переезде?",
            "options": [
                "Только перевыпуск ключей",
                "Room Move в Опере и перевыпуск ключей",
                "Только внесение Fixed Charges",
            ],
            "correct_index": 1,
            "explanation": "При одобренном переезде необходимо выполнить Room Move в Опере и перевыпустить ключи.",
        },
    ],
}

test_state = {}  # user_id → (section_id, current_q_index, correct_count)
test_messages = {}  # user_id → [message_id1, message_id2, ...]


def register_test_handlers(app: Client):
    @app.on_callback_query(filters.regex(r"^start_test_(\d+)$"), group=2)
    async def start_test(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        section_id = int(callback_query.data.split("_")[2])
        print(f"[test] пользователь {user_id} начал тест по разделу {section_id}")

        if section_id not in tests:
            await callback_query.message.edit_text("Тест не найден.")
            return

        test_state[user_id] = (section_id, 0, 0)
        test_messages[user_id] = []  # инициализация списка сообщений

        await callback_query.message.delete()
        await send_question(client, callback_query.message.chat.id, user_id)

    @app.on_callback_query(filters.regex(r"^answer_(\d+)_(\d+)$"), group=2)
    async def handle_answer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        section_id, current_q, correct = test_state.get(user_id, (None, None, None))

        if section_id is None:
            await callback_query.answer("Ошибка состояния.")
            return

        selected = int(callback_query.data.split("_")[2])
        if selected == tests[section_id][current_q]["correct_index"]:
            correct += 1
        current_q += 1

        if current_q >= len(tests[section_id]):
            # Сначала отправляем результат
            result_msg = await callback_query.message.edit_text(
                f"✅ Тест завершён!\nПравильных ответов: {correct} из {len(tests[section_id])}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔁 Пройти заново",
                                callback_data=f"start_test_{section_id}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔙 Назад", callback_data="open_section_menu"
                            )
                        ],
                    ]
                ),
            )

            # Добавляем небольшую задержку перед удалением
            import asyncio

            await asyncio.sleep(1)

            # Удаляем все предыдущие сообщения с вопросами, кроме последнего
            if user_id in test_messages and len(test_messages[user_id]) > 1:
                for msg_id in test_messages[user_id][:-1]:
                    try:
                        await client.delete_messages(
                            callback_query.message.chat.id, msg_id
                        )
                    except Exception as e:
                        print(f"[ошибка удаления] {user_id}: {e}")

            # Очищаем состояние
            test_state.pop(user_id, None)
            test_messages.pop(user_id, None)
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

    sent = await client.send_message(
        chat_id,
        f"❓ Вопрос {q_index+1}/{len(tests[section_id])}\n\n{question}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # сохраняем ID вопроса
    if user_id in test_messages:
        test_messages[user_id].append(sent.id)
    else:
        test_messages[user_id] = [sent.id]


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
