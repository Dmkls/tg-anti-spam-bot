from aiogram.types import BotCommand

BOT_COMMANDS = [
    BotCommand(
        command="add_to_spam",
        description="Добавить в спам-лист (ответом на сообщение)",
    ),
    BotCommand(
        command="list_spam",
        description="Показать список спам-текстов чата",
    ),
    BotCommand(
        command="remove_from_spam",
        description="Удалить запись из спам-листа по номеру",
    ),
]
