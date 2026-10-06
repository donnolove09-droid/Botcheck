# -*- coding: utf-8 -*-
"""app.py — Web hiển thị ID Telegram. Đọc env trực tiếp từ Render."""

import os
import threading
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ===== ĐỌC ENV TRỰC TIẾP =====
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "").strip()
PORT = int(os.getenv("PORT", 8080))

# ===== LƯU TRỮ RAM =====
# {code: {"telegram_id": int, "name": str, "username": str}}
ID_STORE = {}
LOCK = threading.Lock()

print(f"🌐 Web khởi động")
print(f"   BOT_USERNAME    : {BOT_USERNAME or '(chưa điền)'}")
print(f"   INTERNAL_SECRET : {'✅ có' if INTERNAL_SECRET else '❌ thiếu'}")
print(f"   PORT            : {PORT}")


@app.route("/")
def index():
    return render_template(
        "index.html",
        bot_username=BOT_USERNAME or "your_bot"
    )


@app.route("/api/verify", methods=["POST"])
def verify():
    code = ((request.json or {}).get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "error": "Chưa nhập mã"})

    with LOCK:
        info = ID_STORE.pop(code, None)  # pop = xóa luôn, dùng 1 lần

    if not info:
        return jsonify({
            "ok": False,
            "error": "Mã không tồn tại hoặc đã dùng rồi"
        })

    return jsonify({
        "ok": True,
        "telegram_id": info["telegram_id"],
        "name": info.get("name", ""),
        "username": info.get("username", ""),
    })


@app.route("/api/store", methods=["POST"])
def store():
    # Verify secret
    if not INTERNAL_SECRET:
        return jsonify({"ok": False, "error": "Server chưa cấu hình INTERNAL_SECRET"}), 500

    if request.headers.get("X-Internal-Secret") != INTERNAL_SECRET:
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    data = request.json or {}
    code = (data.get("code") or "").strip()
    tg_id = data.get("telegram_id")
    name = data.get("name", "")
    username = data.get("username", "")

    if not code or tg_id is None:
        return jsonify({"ok": False, "error": "Thiếu code hoặc telegram_id"}), 400

    try:
        tg_id = int(tg_id)
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "telegram_id không hợp lệ"}), 400

    with LOCK:
        ID_STORE[code] = {
            "telegram_id": tg_id,
            "name": name,
            "username": username,
        }
        # Giới hạn 1000 mã (tránh tràn RAM)
        if len(ID_STORE) > 1000:
            oldest = list(ID_STORE.keys())[:100]
            for k in oldest:
                ID_STORE.pop(k, None)

    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "stored": len(ID_STORE),
        "bot_username": BOT_USERNAME,
        "has_secret": bool(INTERNAL_SECRET),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
