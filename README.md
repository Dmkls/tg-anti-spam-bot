# Antispam Telegram Bot

Deletes messages whose text exactly matches a spam text an admin has
flagged, and bans the sender in that chat.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its
   token.
2. Copy `.env.example` to `.env` and paste the token into `BOT_TOKEN`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Add the bot to your group as an **administrator** with these two rights
   enabled: **Delete messages** and **Ban users**. Without them, spam
   detection will save entries but cannot delete/ban.
5. Run the bot:
   ```bash
   python -m bot
   ```

## Commands (admins/owner only)

- `/add_to_spam` — reply to a message with this command to save its exact
  text as spam. The message is deleted and its author is banned (unless the
  author is an admin, in which case only the message is deleted).
- `/list_spam` — list saved spam texts for this chat.
- `/remove_from_spam <id>` — remove a saved spam text by its number from
  `/list_spam`.

## How automoderation works

Every non-command text message is compared byte-for-byte (case, spaces, and
line breaks all matter) against this chat's saved spam texts. A match is
deleted and the sender is banned, silently — nothing is posted to the
group. If the person who added the bot to the chat has ever pressed
**Start** in a private chat with the bot, they get a DM about the action;
otherwise it's just logged.

## Manual verification checklist

Automated tests cover the logic; Telegram's real API behavior must be
checked by hand in a test group:

- [ ] Bot joins a test group as admin with Delete messages + Ban users.
- [ ] Non-admin's `/add_to_spam` is ignored.
- [ ] Admin replies `/add_to_spam` to a regular user's message → message
      deleted, user banned, confirmation reply shown.
- [ ] Admin replies `/add_to_spam` to another admin's message → message
      deleted, admin NOT banned.
- [ ] A second, unrelated user sends the exact same spam text → deleted +
      banned automatically, no message posted to the group.
- [ ] The same text with different case/whitespace is NOT auto-deleted.
- [ ] `/list_spam` shows the saved entry; `/remove_from_spam <id>` removes
      it and it no longer triggers automod.
- [ ] The user who added the bot receives a DM after an automod action
      (having pressed Start beforehand).
