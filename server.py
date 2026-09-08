import os
import hmac
import hashlib
import time
import json
import urllib.parse
import random
import sqlite3

from flask import Flask, request, jsonify
from flask_cors import CORS

from database import (
    initialize_database,
    get_or_create_user,
    get_user,
    get_balance,
    change_balance,
    DATABASE_FILE
)


# ==========================================
# FLASK APPLICATION
# ==========================================

app = Flask(__name__)

CORS(app)

initialize_database()


# ==========================================
# DATABASE ROW TO DICTIONARY
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
# TELEGRAM INIT DATA VALIDATION
# ==========================================

def validate_telegram_init_data(init_data):

    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if not bot_token:

        print(
            "ERROR: TELEGRAM_BOT_TOKEN is missing."
        )

        return None


    if not init_data:

        print(
            "ERROR: initData is empty."
        )

        return None


    try:

        # Parse the raw Telegram query string.
        parsed = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )


        # Convert to dictionary while preserving
        # the decoded Telegram values.
        data = {}

        for key, value in parsed:

            data[key] = value


        # Telegram's bot-token validation uses hash.
        received_hash = data.get(
            "hash"
        )


        if not received_hash:

            print(
                "ERROR: Telegram hash is missing."
            )

            return None


        # --------------------------------------
        # CREATE DATA CHECK STRING
        # --------------------------------------

        data_check_items = []


        for key in sorted(data.keys()):

            if key == "hash":

                continue


            data_check_items.append(
                f"{key}={data[key]}"
            )


        data_check_string = "\n".join(
            data_check_items
        )


        # --------------------------------------
        # CREATE TELEGRAM SECRET KEY
        # --------------------------------------

        secret_key = hmac.new(

            b"WebAppData",

            bot_token.encode(
                "utf-8"
            ),

            hashlib.sha256

        ).digest()


        # --------------------------------------
        # CALCULATE EXPECTED HASH
        # --------------------------------------

        calculated_hash = hmac.new(

# ==========================================
# TELEGRAM INIT DATA VALIDATION
# ==========================================

def validate_telegram_init_data(init_data):

    # --------------------------------------
    # GET BOT TOKEN FROM RENDER
    # --------------------------------------

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("AUTH ERROR 1: TELEGRAM_BOT_TOKEN is missing.")
        return None

    # Remove accidental spaces/newlines
    bot_token = bot_token.strip()

    # --------------------------------------
    # CHECK INIT DATA
    # --------------------------------------

    if not init_data:
        print("AUTH ERROR 2: Telegram initData is empty.")
        return None

    print(
        "AUTH DEBUG: initData received, length =",
        len(init_data)
    )

    try:

        # ----------------------------------
        # PARSE TELEGRAM INIT DATA
        # ----------------------------------

        parsed = urllib.parse.parse_qsl(
            init_data,
            keep_blank_values=True
        )

        data = {}

        for key, value in parsed:
            data[key] = value

        # ----------------------------------
        # CHECK HASH
        # ----------------------------------

        received_hash = data.get("hash")

        if not received_hash:

            print(
                "AUTH ERROR 3: Telegram hash is missing."
            )

            print(
                "AUTH DEBUG: received fields =",
                sorted(data.keys())
            )

            return None

        print(
            "AUTH DEBUG: Telegram hash received."
        )

        # ----------------------------------
        # CREATE DATA CHECK STRING
        # ----------------------------------

        data_check_items = []

        for key in sorted(data.keys()):

            if key == "hash":
                continue

            data_check_items.append(
                f"{key}={data[key]}"
            )

        data_check_string = "\n".join(
            data_check_items
        )

        # ----------------------------------
        # CREATE SECRET KEY
        # ----------------------------------

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode("utf-8"),
            hashlib.sha256
        ).digest()

        # ----------------------------------
        # CALCULATE TELEGRAM HASH
        # ----------------------------------

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # ----------------------------------
        # COMPARE HASH
        # ----------------------------------

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):

            print(
                "AUTH ERROR 4: Telegram hash validation failed."
            )

            print(
                "AUTH DEBUG: initData length =",
                len(init_data)
            )

            print(
                "AUTH DEBUG: fields =",
                sorted(data.keys())
            )

            return None

        print(
            "AUTH DEBUG: Telegram hash validation PASSED."
        )

        # ----------------------------------
        # CHECK AUTH DATE
        # ----------------------------------

        auth_date = data.get("auth_date")

        if not auth_date:

            print(
                "AUTH ERROR 5: auth_date is missing."
            )

            return None

        try:

            auth_timestamp = int(auth_date)

        except (TypeError, ValueError):

            print(
                "AUTH ERROR 6: Invalid auth_date."
            )

            return None

        # ----------------------------------
        # CHECK 24-HOUR EXPIRATION
        # ----------------------------------

        age = time.time() - auth_timestamp

        print(
            "AUTH DEBUG: auth data age =",
            int(age),
            "seconds"
        )

        if age > 86400:

            print(
                "AUTH ERROR 7: Telegram initData expired."
            )

            return None

        if age < -60:

            print(
                "AUTH ERROR 8: Telegram auth_date is in the future."
            )

            return None

        # ----------------------------------
        # GET TELEGRAM USER
        # ----------------------------------

        user_json = data.get("user")

        if not user_json:

            print(
                "AUTH ERROR 9: Telegram user data missing."
            )

            return None

        try:

            user_data = json.loads(
                user_json
            )

        except json.JSONDecodeError:

            print(
                "AUTH ERROR 10: Telegram user JSON is invalid."
            )

            return None

        # ----------------------------------
        # CHECK USER ID
        # ----------------------------------

        telegram_id = user_data.get("id")

        if not telegram_id:

            print(
                "AUTH ERROR 11: Telegram user ID missing."
            )

            return None

        print(
            "AUTH SUCCESS: Telegram user authenticated."
        )

        print(
            "AUTH DEBUG: Telegram user ID =",
            telegram_id
        )

        return user_data

    except Exception as error:

        print(
            "AUTH ERROR 12: Unexpected authentication exception:",
            repr(error)
        )

        return None


# ==========================================
# HOME
# ==========================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "success": True,

        "message":
            "Game Zone backend is running."

    })


# ==========================================
# USER
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
                "Telegram authentication failed."

        }), 401


    telegram_id = telegram_user.get(
        "id"
    )


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

        "user":
            row_to_dict(user)

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

            "error":
                "User not found"

        }), 404


    return jsonify({

        "success": True,

        "telegram_id":
            telegram_id,

        "balance":
            get_balance(
                telegram_id
            )

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
# SLOTS
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
    # AUTHENTICATE TELEGRAM USER
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
                "Telegram authentication failed."

        }), 401


    telegram_id = telegram_user.get(
        "id"
    )


    if not telegram_id:

        return jsonify({

            "success": False,

            "error":
                "Telegram user ID not found."

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
                "Invalid bet amount."

        }), 400


    # --------------------------------------
    # BET VALIDATION
    # --------------------------------------

    if bet_amount <= 0:

        return jsonify({

            "success": False,

            "error":
                "Bet must be greater than zero."

        }), 400


    if bet_amount > 1000:

        return jsonify({

            "success": False,

            "error":
                "Maximum demo bet is 1000 credits."

        }), 400


    # --------------------------------------
    # GET USER
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


    if current_balance is None:

        return jsonify({

            "success": False,

            "error":
                "Balance could not be found."

        }), 500


    # --------------------------------------
    # CHECK BALANCE
    # --------------------------------------

    if current_balance < bet_amount:

        return jsonify({

            "success": False,

            "error":
                "Insufficient demo balance.",

            "balance":
                current_balance

        }), 400


    # ======================================
    # GENERATE SLOTS RESULT
    # ======================================

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


    # ======================================
    # CALCULATE WIN
    # ======================================

    win_amount = 0


    # Three identical symbols.
    if (
        reels[0] == reels[1]
        and
        reels[1] == reels[2]
    ):

        win_amount = (
            bet_amount * 5
        )


    # Two identical symbols.
    elif (
        reels[0] == reels[1]
        or
        reels[1] == reels[2]
        or
        reels[0] == reels[2]
    ):

        win_amount = (
            bet_amount * 2
        )


    # ======================================
    # REMOVE BET
    # ======================================

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
                "Could not process demo bet."

        }), 500


    # ======================================
    # ADD WIN
    # ======================================

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
                    "Could not process demo winnings."

            }), 500


    # ======================================
    # SAVE GAME HISTORY
    # ======================================

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


    # ======================================
    # RETURN RESULT
    # ======================================

    if win_amount > 0:

        if win_amount == bet_amount * 5:

            message = (
                "🎉 Three of a kind!"
            )

        else:

            message = (
                "🎉 Winning combination!"
            )

    else:

        message = (
            "No winning combination."
        )


    return jsonify({

        "success": True,

        "game":
            "slots",

        "symbols":
            reels,

        "bet":
            bet_amount,

        "win":
            win_amount,

        "balance":
            new_balance,

        "message":
            message

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
