from bot.commands import BOT_COMMANDS


def test_bot_commands_cover_all_user_facing_commands():
    names = {c.command for c in BOT_COMMANDS}
    assert names == {"add_to_spam", "list_spam", "remove_from_spam"}


def test_bot_commands_have_non_empty_descriptions():
    for command in BOT_COMMANDS:
        assert command.description.strip() != ""
