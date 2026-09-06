import os
import hmac
import hashlib
import time
import json
import urllib.parse
import random

from flask import Flask, request, jsonify
from flask_cors import CORS

from database import (
    initialize_database,
    get_or_create_user,
    get_user,
    get_balance,
    change_balance
)

app = Flask(__name__)

CORS(app)

initialize_database()


# ==========================================
# DATABASE ROW -> JSON
# ==========================================

def row_to_dict(row):

    if row is None:
        return None

    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "balance": row["balance"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


# ==========================================
# TELEGRAM AUTHENTICATION
# ==========================================

def validate_telegram_init_data(init_data):

    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if not bot_token:
        print(
            "ERROR: TELEGRAM_BOT_TOKEN is not configured."
        )
        return None

    if not init_data:
        return None

    try:

        parsed = urllib.parse.parse_qs(
            init_data,
            keep_blank_values=True
        )

        received_hash = parsed.get(
            "hash",
            [None]
        )[0]

        if not received_hash:
            return None

        data_pairs = []

        for key in sorted(parsed.keys()):

            if key == "hash":
                continue

            value = parsed[key][0]

            data_pairs.append(
                f"{key}={value}"
            )

        data_check_string = "\n".join(
            data_pairs
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode("utf-8"),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        auth_date = parsed.get(
            "auth_date",
            [None]
        )[0]

        if auth_date:

            try:

                auth_timestamp = int(
                    auth_date
                )

                if (
                    time.time()
                    - auth_timestamp
                    > 86400
                ):
                    return None

            except ValueError:

                return None

        user_json = parsed.get(
            "user",
            [None]
        )[0]

        if not user_json:
            return None

        user_data = json.loads(
            user_json
        )

        return user_data

    except Exception as error:

        print(
            "Telegram authentication error:",
            error
        )

        return None


# ==========================================
# HOME
# ==========================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Game Zone backend is running."
    })


# ==========================================
# CREATE / GET USER
# ==========================================

@app.route(
    "/api/user",
    methods=["POST"]
)
def create_or_get_user():

    data = request.get_json(
        silent=True
    ) or {}

    init_data = data.get(
        "initData"
    )

    telegram_user = (
        validate_telegram_init_data(
            init_data
        )
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error":
                "Invalid Telegram authentication data"
        }), 401

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        return jsonify({
            "success": False,
            "error":
                "Telegram user ID not found"
        }), 400

    username = telegram_user.get(
        "username",
        ""
    )

    first_name = telegram_user.get(
        "first_name",
        ""
    )

    last_name = telegram_user.get(
        "last_name",
        ""
    )

    user = get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )

    return jsonify({
        "success": True,
        "user": row_to_dict(user)
    })


# ==========================================
# BALANCE
# ==========================================

@app.route(
    "/api/balance/<int:telegram_id>",
    methods=["GET"]
)
def balance(telegram_id):

    user = get_user(
        telegram_id
    )

    if not user:

        return jsonify({
            "success": False,
            "error": "User not found"
        }), 404

    return jsonify({
        "success": True,
        "telegram_id":
            telegram_id,
        "balance":
            get_balance(telegram_id)
    })


# ==========================================
# TEST USER
# ==========================================

@app.route(
    "/api/test-user/<int:telegram_id>",
    methods=["GET"]
)
def test_user(telegram_id):

    user = get_or_create_user(
        telegram_id=telegram_id,
        username="demo_user",
        first_name="Demo",
        last_name="User"
    )

    return jsonify({
        "success": True,
        "user":
            row_to_dict(user)
    })


# ==========================================
# SLOTS GAME
# ==========================================

@app.route(
    "/api/game/slots",
    methods=["POST"]
)
def play_slots():

    data = request.get_json(
        silent=True
    ) or {}

    # --------------------------------------
    # VERIFY TELEGRAM USER
    # --------------------------------------

    init_data = data.get(
        "initData"
    )

    telegram_user = (
        validate_telegram_init_data(
            init_data
        )
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error":
                "Invalid Telegram authentication data"
        }), 401

    telegram_id = telegram_user.get(
        "id"
    )

    if not telegram_id:

        return jsonify({
            "success": False,
            "error":
                "Telegram user ID not found"
        }), 400


    # --------------------------------------
    # READ BET
    # --------------------------------------

    try:

        bet_amount = int(
            data.get(
                "bet_amount",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "error":
                "bet_amount must be a number"
        }), 400


    # --------------------------------------
    # VALIDATE BET
    # --------------------------------------

    if bet_amount <= 0:

        return jsonify({
            "success": False,
            "error":
                "Bet must be greater than zero"
        }), 400


    # Demo limits.
    if bet_amount > 1000:

        return jsonify({
            "success": False,
            "error":
                "Maximum demo bet is 1000 credits"
        }), 400


    # --------------------------------------
    # CHECK USER
    # --------------------------------------

    user = get_user(
        telegram_id
    )

    if not user:

        user = get_or_create_user(
            telegram_id=telegram_id,
            username=telegram_user.get(
                "username",
                ""
            ),
            first_name=telegram_user.get(
                "first_name",
                ""
            ),
            last_name=telegram_user.get(
                "last_name",
                ""
            )
        )


    current_balance = get_balance(
        telegram_id
    )


    # --------------------------------------
    # CHECK BALANCE
    # --------------------------------------

    if current_balance is None:

        return jsonify({
            "success": False,
            "error":
                "User balance could not be found"
        }), 500


    if current_balance < bet_amount:

        return jsonify({
            "success": False,
            "error":
                "Insufficient demo balance",
            "balance":
                current_balance
        }), 400


    # --------------------------------------
    # SLOTS SYMBOLS
    # --------------------------------------

    symbols = [
        "🍒",
        "🍋",
        "🍊",
        "🔔",
        "⭐",
        "💎"
    ]

    reels = [
        random.choice(symbols),
        random.choice(symbols),
        random.choice(symbols)
    ]


    # --------------------------------------
    # PAYOUT
    # --------------------------------------

    win_amount = 0

    if (
        reels[0] == reels[1]
        and reels[1] == reels[2]
    ):

        # Three matching symbols.
        win_amount = bet_amount * 5

    elif (
        reels[0] == reels[1]
        or reels[1] == reels[2]
        or reels[0] == reels[2]
    ):

        # Two matching symbols.
        win_amount = bet_amount * 2


    # --------------------------------------
    # REMOVE BET
    # --------------------------------------

    new_balance = change_balance(
        telegram_id,
        -bet_amount,
        "game_bet",
        "Slots demo bet"
    )

    if new_balance is None:

        return jsonify({
            "success": False,
            "error":
                "Could not process bet"
        }), 500


    # --------------------------------------
    # ADD WIN
    # --------------------------------------

    if win_amount > 0:

        new_balance = change_balance(
            telegram_id,
            win_amount,
            "game_win",
            "Slots demo win"
        )

        if new_balance is None:

            return jsonify({
                "success": False,
                "error":
                    "Could not process winnings"
            }), 500


    # --------------------------------------
    # SAVE GAME HISTORY
    # --------------------------------------

    import sqlite3
    from database import DATABASE_FILE

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO game_history (
            telegram_id,
            game,
            bet_amount,
            result,
            win_amount,
            balance_after
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            "slots",
            bet_amount,
            " ".join(reels),
            win_amount,
            new_balance
        )
    )

    connection.commit()
    connection.close()


    # --------------------------------------
    # RESULT
    # --------------------------------------

    return jsonify({

        "success": True,

        "game": "slots",

        "symbols": reels,

        "bet": bet_amount,

        "win": win_amount,

        "balance": new_balance,

        "message":
            "Three matching symbols!"
            if win_amount ==
            bet_amount * 5
            else
            "Winning combination!"
            if win_amount > 0
            else
            "No winning combination."

    })


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )