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

## Running behind a proxy

If the server running the bot can't reach Telegram directly (e.g. Telegram
is blocked on that network), set `BOT_PROXY_URL` in `.env` to route all
Telegram API requests through a proxy:

```
BOT_PROXY_URL=socks5://user:pass@1.2.3.4:1080
```

Supported schemes: `socks5://`, `socks4://`, `http://` (with or without
`user:pass@` credentials). Leave `BOT_PROXY_URL` empty (or unset) to connect
directly, which is the default.

### SSL error: "self-signed certificate in certificate chain"

If the bot fails to start with an SSL error like this, it's almost always
caused by local antivirus/security software (Kaspersky and similar are
common in Russia) that intercepts HTTPS traffic and re-signs it with its
own certificate — not by your proxy itself (a real SOCKS proxy is a blind
TCP relay and can't do this). Try, in order:

1. Disable "scan encrypted connections" (or add an exception for
   `python.exe`) in your antivirus, then restart the bot.
2. If that's not possible, set `BOT_TRUST_SYSTEM_CERTS=true` in `.env` so
   the bot also trusts your OS's system certificate store (where the
   antivirus's certificate is installed), in addition to its normal bundled
   certificate list.

## Commands (admins/owner only)

- `/add_to_spam` — reply to a message with this command to save its exact
  text as spam. The message is deleted and its author is banned (unless the
  author is an admin, in which case only the message is deleted). Both the
  `/add_to_spam` command message and the bot's confirmation reply are
  auto-deleted after 10 seconds to keep the chat clean.
- `/list_spam` — list saved spam texts for this chat.
- `/remove_from_spam <id>` — remove a saved spam text by its number from
  `/list_spam`.

These commands, with their descriptions, also show up in Telegram's `/`
autocomplete menu — the bot registers them via `setMyCommands` on startup.

Admins posting anonymously "as the group" (Telegram's `@GroupAnonymousBot`
sender) are recognized as admins too, since only an admin/owner can enable
anonymous posting in the first place.

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
- [ ] Typing `/` in the chat shows the three commands with descriptions.
- [ ] An admin posting anonymously ("send as group") can use `/add_to_spam`,
      `/list_spam`, `/remove_from_spam`, and is exempt from automod.
- [ ] After `/add_to_spam`, both the command message and the confirmation
      reply disappear on their own after about 10 seconds.
