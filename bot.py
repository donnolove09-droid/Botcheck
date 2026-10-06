# -*- coding: utf-8 -*-
"""bot.py — Bot trả mã + ID. Đọc env trực tiếp từ Render."""

import os
import random
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== ĐỌC ENV TRỰC TIẾP =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
WEB_URL = os.getenv("WEB_URL", "").strip().rstrip("/")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "").strip()

# ===== LOG =====
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# In config khi khởi động (che token)
log.info("═══════════ BOT CONFIG ═══════════")
log.info(f"BOT_TOKEN       : {'✅ có' if BOT_TOKEN else '❌ THIẾU'}")
log.info(f"BOT_USERNAME    : {BOT_USERNAME or '❌ THIẾU'}")
log.info(f"WEB_URL         : {WEB_URL or '❌ THIẾU'}")
log.info(f"INTERNAL_SECRET : {'✅ có' if INTERNAL_SECRET else '❌ THIẾU'}")
log.info("═══════════════════════════════════")


def gen_code() -> str:
    return f"{random.randint(100000, 999999)}"


def push_id_to_web(code, telegram_id, name, username) -> tuple[bool, str]:
    """Gửi ID lên Flask. Trả (ok, error_msg)."""
    if not WEB_URL:
        return False, "WEB_URL chưa cấu hình"
    if not INTERNAL_SECRET:
        return False, "INTERNAL_SECRET chưa cấu hình"

    try:
        r = requests.post(
            f"{WEB_URL}/api/store",
            json={
                "code": code,
                "telegram_id": telegram_id,
                "name": name,
                "username": username,
            },
            headers={"X-Internal-Secret": INTERNAL_SECRET},
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            return True, ""
        return False, data.get("error", f"HTTP {r.status_code}")
    except requests.exceptions.Timeout:
        return False, "Web timeout"
    except Exception as e:
        return False, f"{e}"


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start — luôn trả lời dù lỗi."""
    try:
        user = update.effective_user
        uid = user.id
        code = gen_code()

        log.info(f"📨 /start từ {uid} ({user.full_name}) — code {code}")

        ok, err = push_id_to_web(
            code, uid,
            user.first_name or "",
            user.username or ""
        )

        if ok:
            text = (
                f"👋 Xin chào *{user.first_name}*!\n\n"
                f"🆔 ID Telegram của bạn:\n"
                f"`{uid}`\n\n"
                f"📋 *Mã tra cứu*: `{code}`\n\n"
                f"👉 Vào web để xác nhận ID:\n"
                f"{WEB_URL}\n\n"
                f"Nhập mã `{code}` vào web."
            )
            kb = [[InlineKeyboardButton("🌐 Mở web", url=WEB_URL)]] if WEB_URL else None
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb) if kb else None,
            )
        else:
            # Web lỗi → vẫn trả ID trực tiếp cho user
            log.error(f"❌ push web fail: {err}")
            text = (
                f"👋 Xin chào *{user.first_name}*!\n\n"
                f"🆔 ID Telegram của bạn:\n"
                f"`{uid}`\n\n"
                f"⚠️ Web tạm lỗi (`{err}`).\n"
                f"Copy ID ở trên dùng luôn."
            )
            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        log.exception(f"❌ Lỗi /start: {e}")
        try:
            await update.message.reply_text(
                f"❌ Có lỗi xảy ra: {e}\nVui lòng thử lại."
            )
        except Exception:
            pass


async def id_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    log.info(f"📨 /id từ {uid}")
    await update.message.reply_text(
        f"🆔 ID Telegram của bạn:\n\n`{uid}`",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Hướng dẫn*\n\n"
        "• /start — Nhận mã + ID\n"
        "• /id — Xem ID trực tiếp\n"
        "• /help — Trợ giúp",
        parse_mode="Markdown"
    )


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    """Bắt mọi lỗi không mong đợi."""
    log.error(f"⚠️ Exception: {ctx.error}", exc_info=ctx.error)


def main():
    if not BOT_TOKEN:
        log.critical("❌ THIẾU BOT_TOKEN — bot không thể chạy!")
        raise SystemExit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_error_handler(error_handler)

    log.info("🤖 Bot đang chạy (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
