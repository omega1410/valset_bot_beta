from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from db.statistics import get_user_stats
import sqlite3
import asyncio

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
            "question": "Какой документ принимается для заселения граждан РФ?",
            "options": [
                "Заграничный паспорт",
                "Внутренний паспорт",
                "Водительские права",
            ],
            "correct_index": 1,
        },
        {
            "question": "Что нужно для заселения ребенка до 14 лет без родителей?",
            "options": [
                "Только свидетельство о рождении",
                "Согласие родителя + скан паспорта",
                "Заявление от ребенка",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какие документы нужны иностранному гостю?",
            "options": [
                "Только заграничный паспорт",
                "Паспорт, миграционная карта и виза",
                "Внутренний паспорт страны",
            ],
            "correct_index": 1,
        },
    ],
    3: [
        {
            "question": "Когда ранний заезд может быть предоставлен бесплатно?",
            "options": [
                "До 06:00 утра",
                "В 11-12 утра и номер уже готов",
                "Гость заплатил половину стоимости",
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
                "Продлить ключи, проставить C/O Time",
                "Ничего не делать",
            ],
            "correct_index": 1,
        },
    ],
    6: [
        {
            "question": "Какой номер PM обычно используют для GRAB&GO в 3 корпусе?",
            "options": ["29009", "29020", "30001"],
            "correct_index": 1,
        },
        {
            "question": "Для чего в основном создают PM в системе бронирования?",
            "options": [
                "Для оформления новых гостей",
                "Для обработки ежедневных оплат",
                "Для бронирования конференц-залов",
            ],
            "correct_index": 1,
        },
    ],
    8: [
        {
            "question": "Что предложить гостю при первичном отказе от номера?",
            "options": [
                "Сразу оформить возврат",
                "Альтернативный номер той же категории",
                "Доплату за апгрейд",
            ],
            "correct_index": 1,
        },
        {
            "question": "Когда возможен возврат средств на ресепшн?",
            "options": [
                "При любой оплате",
                "Только при оплате через агента",
                "Только при оплате на ресепшн",
            ],
            "correct_index": 2,
        },
        {
            "question": "Как оформить доплату за апгрейд?",
            "options": [
                "Устной договорённостью",
                "Через Fixed Charges в Opera",
                "Не фиксировать в системе",
            ],
            "correct_index": 1,
        },
    ],
    20: [
        {
            "question": "Где гости могут взять таблетки для посудомоечной машины?",
            "options": [
                "В ближайшем магазине",
                "На ресепшене (50 рублей / штука)",
                "Предоставляются бесплатно",
            ],
            "correct_index": 1,
        },
        {
            "question": "В каком корпусе находится бесплатная финская сауна для гостей?",
            "options": [
                "В корпусе Центр",
                "В корпусе Freestyle",
                "В спа-комплексе Mountain Spa",
            ],
            "correct_index": 1,
        },
        {
            "question": "До какого времени работает детская комната?",
            "options": [
                "До 20:00",
                "До 22:00",
                "До 18:00",
            ],
            "correct_index": 0,
        },
        {
            "question": "Как часто производится уборка в номерах корпуса Центр?",
            "options": [
                "По графику",
                "Раз в три дня",
                "Ежедневно",
            ],
            "correct_index": 2,
        },
    ],
    9: [
        {
            "question": "Что нужно сделать в первую очередь при запросе гостя на переезд?",
            "options": [
                "Сразу оформить Room Move в Опере",
                "Предупредить в рабочем чате",
                "Выписать новые ключи",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какие действия выполняются при одобренном переезде?",
            "options": [
                "Только перевыпуск ключей",
                "Room Move в Опере и перевыпуск ключей",
                "Только внесение Fixed Charges",
            ],
            "correct_index": 1,
        },
    ],
    23: [
        {
            "question": "В каком типе апартаментов есть балкон во всех номерах?",
            "options": [
                "APA",
                "APABL",
                "AP2A",
            ],
            "correct_index": 1,
        },
        {
            "question": "Где можно разместить дополнительного гостя на раскладном диване?",
            "options": [
                "APA и APABL",
                "APPSA и APABL",
                "APKA и AP2A",
            ],
            "correct_index": 2,
        },
        {
            "question": "В каких апартаментах есть камин?",
            "options": [
                "APPSA",
                "APABL",
                "APKA",
            ],
            "correct_index": 0,
        },
    ],
    24: [
        {
            "question": "В каких апартаментах стандартно предусмотрен двуспальный диван?",
            "options": [
                "Только в AP4C",
                "Во всех, кроме APC",
                "Только в APCL и AP2C",
            ],
            "correct_index": 1,
        },
        {
            "question": "Сколько человек комфортно разместятся в AP2C?",
            "options": [
                "5 человек",
                "4 человека",
                "3 человека",
            ],
            "correct_index": 2,
        },
    ],
    25: [
        {
            "question": "В каких апартаментах есть два балкона и вид на озеро?",
            "options": ["APKDBV", "APD", "APDX"],
            "correct_index": 0,
        },
        {
            "question": "В каких апартаментах балкон есть во всех номерах категории?",
            "options": ["APD", "APKD", "APDX"],
            "correct_index": 2,
        },
        {
            "question": "Какая категория самая большая по площади?",
            "options": ["APKD", "APKDX", "APDX"],
            "correct_index": 1,
        },
    ],
    7: [
        {
            "question": "Что нужно сделать перед оформлением апгрейда?",
            "options": [
                "Рассчитать разницу в стоимости",
                "Просто переселить гостя",
                "Позвать руководителя",
            ],
            "correct_index": 0,
        },
        {
            "question": "Как оформить доплату за апгрейд?",
            "options": [
                "Через Fixed Charges",
                "Устной договорённостью",
                "Не фиксировать в системе",
            ],
            "correct_index": 0,
        },
        {
            "question": "Что важно сделать после апгрейда?",
            "options": [
                "Только перевыпустить ключи",
                "Обновить данные бронирования и ключи",
                "Ничего не менять в системе",
            ],
            "correct_index": 1,
        },
    ],
    10: [
        {
            "question": "Как запустить отчет для сверки кассы?",
            "options": [
                "Miscellaneous → Reports → ввести 'j'",
                "Front Desk → Cashier → Report",
                "Management → Financial Reports",
            ],
            "correct_index": 0,
        },
        {
            "question": "Какой код используется для сверки наличных?",
            "options": ["8000", "9000", "9200"],
            "correct_index": 1,
        },
        {
            "question": "Как найти коды безналичных платежей?",
            "options": [
                "Ввести '90' в поиск",
                "Ввести '92' в поиск",
                "Выбрать все коды вручную",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какие платежи нужно проверять?",
            "options": [
                "Только наличные",
                "Только безналичные",
                "И наличные, и безналичные",
            ],
            "correct_index": 2,
        },
    ],
    16: [
        {
            "question": "Что сделать в первую очередь при ухудшении состояния гостя?",
            "options": [
                "Дать лекарства из аптечки",
                "Оценить состояние гостя",
                "Перенести в другое помещение",
            ],
            "correct_index": 1,
        },
        {
            "question": "Как вызвать скорую для гостя без сознания?",
            "options": [
                "Ждать, пока кто-то другой позвонит",
                "Немедленно набрать 903/9103",
                "Сначала найти руководителя",
            ],
            "correct_index": 1,
        },
        {
            "question": "Что запрещено делать до приезда медиков?",
            "options": [
                "Давать воду",
                "Давать любые медикаменты",
                "Разговаривать с гостем",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какую информацию сообщать диспетчеру?",
            "options": [
                "Только номер комнаты",
                "Состояние гостя и адрес отеля",
                "Личные данные гостя без согласия",
            ],
            "correct_index": 1,
        },
        {
            "question": "Что обязательно зафиксировать после вызова?",
            "options": [
                "Только время вызова",
                "Время вызова и действия сотрудников",
                "Ничего не записывать",
            ],
            "correct_index": 1,
        },
    ],
    5: [
        {
            "question": "Что такое Walk-in бронирование?",
            "options": [
                "Бронирование через сайт",
                "Бронирование через агентство",
                "Бронирование на стойке",
            ],
            "correct_index": 2,
        },
        {
            "question": "Какое вознаграждение получает сотрудник?",
            "options": ["3% от стоимости", "5% от стоимости", "10% от стоимости"],
            "correct_index": 1,
        },
        {
            "question": "Что указать в поле Source?",
            "options": ["WEB", "WLK", "AGT"],
            "correct_index": 1,
        },
        {
            "question": "Куда внести информацию о бронировании?",
            "options": ["В бумажный журнал", "В Google-таблицу", "Только в Opera"],
            "correct_index": 1,
        },
        {
            "question": "Чем отличаются Walk-in бронирования?",
            "options": [
                "Стоимостью проживания",
                "Источником бронирования",
                "Категорией номера",
            ],
            "correct_index": 1,
        },
    ],
    14: [
        {
            "question": "Какой формат названия задачи в Treema?",
            "options": [
                "Номер комнаты → Суть проблемы",
                "Суть проблемы → Номер комнаты",
                "Только суть проблемы",
            ],
            "correct_index": 1,
        },
        {
            "question": "Кого обязательно добавить в наблюдатели?",
            "options": [
                "Технического специалиста",
                "Горничную",
                "Координатора",
            ],
            "correct_index": 2,
        },
        {
            "question": "Что важно указать в описании задачи?",
            "options": [
                "Детали проблемы и статус гостя",
                "Только номер комнаты",
                "ФИО сотрудника на смене",
            ],
            "correct_index": 0,
        },
        {
            "question": "Куда нужно перейти для создания заявки?",
            "options": ["В Google Таблицу", "В Opera", "На сайт Treema"],
            "correct_index": 2,
        },
        {
            "question": "Что нажать для создания новой задачи?",
            "options": [
                "Кнопку «Создать отчет»",
                "Кнопку «+ Задача»",
                "Кнопку «Новый тикет»",
            ],
            "correct_index": 1,
        },
    ],
    17: [
        {
            "question": "Кто первым проверяет объект при срабатывании тревоги?",
            "options": ["Охранник", "Дежурный администратор", "Технический специалист"],
            "correct_index": 0,
        },
        {
            "question": "Что обязательно сделать после проверки?",
            "options": [
                "Ничего, если угрозы нет",
                "Позвонить в МЧС",
                "Только записать в отчет",
            ],
            "correct_index": 1,
        },
        {
            "question": "Какую фразу использовать при звонке в МЧС?",
            "options": [
                "«Ложная тревога, угрозы нет»",
                "«Всё нормально»",
                "«Ничего страшного»",
            ],
            "correct_index": 0,
        },
        {
            "question": "Куда внести запись о срабатывании?",
            "options": ["В гостевой профиль", "В книгу жалоб", "В отчёт за смену"],
            "correct_index": 2,
        },
        {
            "question": "Что запрещено делать при срабатывании?",
            "options": [
                "Игнорировать сигнал",
                "Сообщать в рабочий чат",
                "Проверять помещение",
            ],
            "correct_index": 0,
        },
    ],
}

test_state = {}
test_messages = {}


def register_test_handlers(app: Client):
    @app.on_callback_query(filters.regex(r"^start_test_(\d+)$"), group=2)
    async def start_test(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        try:
            section_id = int(callback_query.data.split("_")[2])
            print(f"[test] пользователь {user_id} начал тест по разделу {section_id}")

            if section_id not in tests:
                await callback_query.message.edit_text("Тест не найден.")
                return
            test_state[user_id] = (section_id, 0, 0)
            test_messages[user_id] = []

            await callback_query.message.delete()
            await send_question(client, callback_query.message.chat.id, user_id)
        except Exception as e:
            print(f"[ОШИБКА] в start_test: {e}")
            await callback_query.answer("Произошла ошибка", show_alert=True)

    @app.on_callback_query(filters.regex(r"^answer_(\d+)_(\d+)$"), group=2)
    async def handle_answer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        try:
            section_id, current_q, correct = test_state.get(user_id, (None, None, None))

            if section_id is None:
                await callback_query.answer("Ошибка состояния.")
                return

            selected = int(callback_query.data.split("_")[2])
            if selected == tests[section_id][current_q]["correct_index"]:
                correct += 1
            current_q += 1

            if current_q >= len(tests[section_id]):
                await save_test_stats(
                    user_id, section_id, correct, len(tests[section_id])
                )

                await show_test_results(client, callback_query, section_id, correct)

                await cleanup_test_messages(
                    client, callback_query.message.chat.id, user_id
                )

                test_state.pop(user_id, None)
                test_messages.pop(user_id, None)
            else:
                test_state[user_id] = (section_id, current_q, correct)
                await send_question(client, callback_query.message.chat.id, user_id)

            await callback_query.answer()
        except Exception as e:
            print(f"[ОШИБКА] в handle_answer: {e}")
            await callback_query.answer("Произошла ошибка", show_alert=True)

    @app.on_message(filters.command("stats") & filters.private, group=1)
    async def show_stats(client: Client, message: Message):
        try:
            user_id = message.from_user.id
            print(f"[DEBUG] Обработка /stats для {user_id}")

            stats = get_user_stats(user_id)
            print(f"[DEBUG] Данные из БД: {stats}")

            if not stats:
                await message.reply("📊 У вас пока нет статистики по тестам.")
                return

            lines = ["📊 Ваша статистика:"]
            for section_id, correct, total in stats:
                accuracy = round(correct / total * 100) if total else 0
                lines.append(f"• Раздел {section_id}: {correct}/{total} ({accuracy}%)")

            await message.reply("\n".join(lines))

        except Exception as e:
            import traceback

            print(f"[CRITICAL] Ошибка в show_stats: {e}\n{traceback.format_exc()}")
            await message.reply("❌ Произошла внутренняя ошибка. Попробуйте позже.")


async def send_question(client: Client, chat_id: int, user_id: int):
    try:
        section_id, q_index, _ = test_state[user_id]
        question_data = tests[section_id][q_index]
        question = question_data["question"]
        options = question_data["options"]

        keyboard = [
            [InlineKeyboardButton(opt, callback_data=f"answer_{section_id}_{i}")]
            for i, opt in enumerate(options)
        ]

        sent = await client.send_message(
            chat_id, f"❓ {question}", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        test_messages[user_id].append(sent.id)
    except Exception as e:
        print(f"[ОШИБКА] в send_question: {e}")
        raise


async def save_test_stats(user_id: int, section_id: int, correct: int, total: int):
    try:
        conn = sqlite3.connect("db/data.db")
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO test_stats (user_id, section_id, correct, total)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, section_id) DO UPDATE SET
                correct = excluded.correct,
                total = excluded.total
            """,
            (user_id, section_id, correct, total),
        )
        conn.commit()
        conn.close()
        print(f"[СТАТИСТИКА] Записан результат: user={user_id}, correct={correct}")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статистику: {e}")


async def show_test_results(
    client: Client, callback_query: CallbackQuery, section_id: int, correct: int
):
    try:
        await callback_query.message.edit_text(
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
    except Exception as e:
        print(f"[ОШИБКА] при показе результатов: {e}")


async def cleanup_test_messages(client: Client, chat_id: int, user_id: int):
    try:
        if user_id in test_messages:
            await asyncio.sleep(1)
            for msg_id in test_messages[user_id][:-1]:
                try:
                    await client.delete_messages(chat_id, msg_id)
                except Exception as e:
                    print(f"[ошибка удаления] {user_id}: {e}")
    except Exception as e:
        print(f"[ОШИБКА] при очистке сообщений: {e}")


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


def get_user_stats(user_id: int):
    try:
        conn = sqlite3.connect("db/data.db")
        c = conn.cursor()
        c.execute(
            """
            SELECT section_id, correct, total 
            FROM test_stats 
            WHERE user_id = ?
            ORDER BY section_id
        """,
            (user_id,),
        )
        stats = c.fetchall()
        conn.close()
        return stats
    except Exception as e:
        print(f"[ОШИБКА] при получении статистики: {e}")
        return None
