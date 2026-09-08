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
    create_mines_game,
    get_active_mines_game,
    get_mines_game,
    update_mines_game,
    finish_mines_game,
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

    # --------------------------------------
    # GET BOT TOKEN FROM RENDER
    # --------------------------------------

    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    if not bot_token:

        print(
            "AUTH ERROR 1: TELEGRAM_BOT_TOKEN is missing."
        )

        return None

    # Remove accidental spaces/newlines
    bot_token = bot_token.strip()

    # --------------------------------------
    # CHECK INIT DATA
    # --------------------------------------

    if not init_data:

        print(
            "AUTH ERROR 2: Telegram initData is empty."
        )

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

        received_hash = data.get(
            "hash"
        )

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

            bot_token.encode(
                "utf-8"
            ),

            hashlib.sha256

        ).digest()

        # ----------------------------------
        # CALCULATE TELEGRAM HASH
        # ----------------------------------

        calculated_hash = hmac.new(

            secret_key,

            data_check_string.encode(
                "utf-8"
            ),

            hashlib.sha256

        ).hexdigest()

        # ----------------------------------
        # COMPARE HASHES
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

        auth_date = data.get(
            "auth_date"
        )

        if not auth_date:

            print(
                "AUTH ERROR 5: auth_date is missing."
            )

            return None

        try:

            auth_timestamp = int(
                auth_date
            )

        except (
            TypeError,
            ValueError
        ):

            print(
                "AUTH ERROR 6: Invalid auth_date."
            )

            return None

        # ----------------------------------
        # CHECK AUTH DATA AGE
        # ----------------------------------

        age = time.time() - auth_timestamp

        print(
            "AUTH DEBUG: auth data age =",
            int(age),
            "seconds"
        )

        # Authentication data older than
        # 24 hours is rejected.

        if age > 86400:

            print(
                "AUTH ERROR 7: Telegram initData expired."
            )

            return None

        # Prevent obviously future-dated data.

        if age < -60:

            print(
                "AUTH ERROR 8: Telegram auth_date is in the future."
            )

            return None

        # ----------------------------------
        # GET TELEGRAM USER
        # ----------------------------------

        user_json = data.get(
            "user"
        )

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
        # CHECK TELEGRAM USER ID
        # ----------------------------------

        telegram_id = user_data.get(
            "id"
        )

        if not telegram_id:

            print(
                "AUTH ERROR 11: Telegram user ID missing."
            )

            return None

        # ----------------------------------
        # AUTHENTICATION SUCCESS
        # ----------------------------------

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


    # ==========================================
# MINES - CASH OUT
# ==========================================

@app.route(
    "/api/game/mines/cashout",
    methods=["POST"]
)
def cashout_mines():

    data = request.get_json(
        silent=True
    ) or {}

    # --------------------------------------
    # AUTHENTICATE TELEGRAM USER
    # --------------------------------------

    init_data = data.get(
        "initData"
    )

    telegram_user = validate_telegram_init_data(
        init_data
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error": "Telegram authentication failed."
        }), 401

    telegram_id = telegram_user.get("id")

    if not telegram_id:

        return jsonify({
            "success": False,
            "error": "Telegram user ID not found."
        }), 400

    # --------------------------------------
    # READ GAME ID
    # --------------------------------------

    try:

        game_id = int(
            data.get(
                "game_id",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "error": "Invalid game ID."
        }), 400

    if game_id <= 0:

        return jsonify({
            "success": False,
            "error": "Invalid game ID."
        }), 400

    # --------------------------------------
    # GET GAME
    # --------------------------------------

    game = get_mines_game(
        game_id,
        telegram_id
    )

    if not game:

        return jsonify({
            "success": False,
            "error": "Mines game not found."
        }), 404

    # --------------------------------------
    # CHECK GAME STATUS
    # --------------------------------------

    if game["status"] != "active":

        return jsonify({
            "success": False,
            "error": "This Mines game is no longer active."
        }), 400

    # --------------------------------------
    # LOAD REVEALED TILES
    # --------------------------------------

    try:

        revealed_tiles = json.loads(
            game["revealed_json"]
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):

        revealed_tiles = []

    # --------------------------------------
    # REQUIRE AT LEAST ONE SAFE TILE
    # --------------------------------------

    if len(revealed_tiles) < 1:

        return jsonify({
            "success": False,
            "error":
                "Reveal at least one safe tile before cashing out."
        }), 400

    # --------------------------------------
    # GET STORED POTENTIAL WIN
    # --------------------------------------

    potential_win = int(
        game["potential_win"]
    )

    multiplier = float(
        game["multiplier"]
    )

    bet_amount = int(
        game["bet_amount"]
    )

    # --------------------------------------
    # SAFETY CHECK
    # --------------------------------------

    if potential_win <= 0:

        return jsonify({
            "success": False,
            "error":
                "Invalid potential win amount."
        }), 400

    # --------------------------------------
    # PAY DEMO WIN
    # --------------------------------------

    new_balance = change_balance(

        telegram_id,

        potential_win,

        "game_win",

        "Mines demo cash out"

    )

    if new_balance is None:

        return jsonify({
            "success": False,
            "error":
                "Could not process demo cash out."
        }), 500

    # --------------------------------------
    # MARK GAME AS CASHED OUT
    # --------------------------------------

    finished = finish_mines_game(

        game_id,

        telegram_id,

        "cashed_out"

    )

    if not finished:

        # IMPORTANT:
        # The balance has already been credited.
        #
        # We don't deduct it again here.
        #
        # This should only occur in an
        # unexpected database-state situation.

        print(
            "MINES WARNING: Balance paid but "
            "game status was not updated."
        )

    # --------------------------------------
    # RETURN RESULT
    # --------------------------------------

    return jsonify({

        "success": True,

        "result": "cashout",

        "game_id": game_id,

        "status": "cashed_out",

        "bet": bet_amount,

        "revealed_count":
            len(revealed_tiles),

        "multiplier":
            multiplier,

        "win_amount":
            potential_win,

        "balance":
            new_balance,

        "message":
            "Demo winnings successfully cashed out."

    })
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
# MINES - START GAME
# ==========================================

@app.route(
    "/api/game/mines/start",
    methods=["POST"]
)
def start_mines():

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
    # VALIDATE BET
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
    # READ MINE COUNT
    # --------------------------------------

    try:

        mine_count = int(
            data.get(
                "mine_count",
                5
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "success": False,

            "error":
                "Invalid mine count."

        }), 400


    # --------------------------------------
    # VALIDATE MINE COUNT
    # --------------------------------------

    if mine_count < 1:

        return jsonify({

            "success": False,

            "error":
                "There must be at least 1 mine."

        }), 400


    if mine_count > 20:

        return jsonify({

            "success": False,

            "error":
                "Maximum is 20 mines."

        }), 400


    # --------------------------------------
    # CHECK FOR ACTIVE MINES GAME
    # --------------------------------------

    active_game = get_active_mines_game(
        telegram_id
    )


    if active_game:

        return jsonify({

            "success": False,

            "error":
                "You already have an active Mines game."

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


    # --------------------------------------
    # CHECK BALANCE
    # --------------------------------------

    current_balance = get_balance(
        telegram_id
    )


    if current_balance is None:

        return jsonify({

            "success": False,

            "error":
                "Balance could not be found."

        }), 500


    if current_balance < bet_amount:

        return jsonify({

            "success": False,

            "error":
                "Insufficient demo balance.",

            "balance":
                current_balance

        }), 400


    # --------------------------------------
    # GENERATE HIDDEN MINES
    # --------------------------------------
    #
    # The Mines are generated ONLY on the
    # backend.
    #
    # The browser never receives this list.
    #
    # Grid positions:
    #
    # 0  1  2  3  4
    # 5  6  7  8  9
    # 10 11 12 13 14
    # 15 16 17 18 19
    # 20 21 22 23 24
    #
    # --------------------------------------

    import secrets

    all_positions = list(
        range(25)
    )


    mines = secrets.SystemRandom().sample(
        all_positions,
        mine_count
    )


    # --------------------------------------
    # REMOVE BET FROM BALANCE
    # --------------------------------------

    new_balance = change_balance(

        telegram_id,

        -bet_amount,

        "game_bet",

        "Mines demo bet"

    )


    if new_balance is None:

        return jsonify({

            "success": False,

            "error":
                "Could not process demo bet."

        }), 500


    # --------------------------------------
    # SAVE MINES GAME
    # --------------------------------------

    try:

        game_id = create_mines_game(

            telegram_id=telegram_id,

            bet_amount=bet_amount,

            mine_count=mine_count,

            mines=mines

        )

    except Exception as error:

        print(
            "MINES ERROR: Could not create game:",
            repr(error)
        )


        # Refund the demo bet if game
        # creation fails.

        change_balance(

            telegram_id,

            bet_amount,

            "game_refund",

            "Mines demo game creation failed"

        )


        return jsonify({

            "success": False,

            "error":
                "Could not create Mines game."

        }), 500


    # --------------------------------------
    # RETURN SAFE GAME INFORMATION
    # --------------------------------------
    #
    # IMPORTANT:
    # Do NOT return "mines" here.
    #
    # The mine locations must remain
    # secret on the server.
    #
    # --------------------------------------

    return jsonify({

        "success": True,

        "game":
            "mines",

        "game_id":
            game_id,

        "grid_size":
            25,

        "mine_count":
            mine_count,

        "bet":
            bet_amount,

        "balance":
            new_balance,

        "revealed":
            [],

        "multiplier":
            1.0,

        "potential_win":
            bet_amount,

        "status":
            "active"

    })



# ==========================================
# MINES - REVEAL TILE
# ==========================================

@app.route(
    "/api/game/mines/reveal",
    methods=["POST"]
)
def reveal_mines_tile():

    data = request.get_json(
        silent=True
    ) or {}

    # --------------------------------------
    # AUTHENTICATE TELEGRAM USER
    # --------------------------------------

    init_data = data.get(
        "initData"
    )

    telegram_user = validate_telegram_init_data(
        init_data
    )

    if not telegram_user:

        return jsonify({
            "success": False,
            "error": "Telegram authentication failed."
        }), 401

    telegram_id = telegram_user.get("id")

    if not telegram_id:

        return jsonify({
            "success": False,
            "error": "Telegram user ID not found."
        }), 400

    # --------------------------------------
    # READ GAME ID
    # --------------------------------------

    try:

        game_id = int(
            data.get(
                "game_id",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "error": "Invalid game ID."
        }), 400

    if game_id <= 0:

        return jsonify({
            "success": False,
            "error": "Invalid game ID."
        }), 400

    # --------------------------------------
    # READ TILE
    # --------------------------------------

    try:

        tile = int(
            data.get(
                "tile",
                -1
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "error": "Invalid tile."
        }), 400

    # --------------------------------------
    # VALIDATE TILE
    # --------------------------------------

    if tile < 0 or tile > 24:

        return jsonify({
            "success": False,
            "error": "Tile must be between 0 and 24."
        }), 400

    # --------------------------------------
    # GET ACTIVE GAME
    # --------------------------------------

    game = get_mines_game(
        game_id,
        telegram_id
    )

    if not game:

        return jsonify({
            "success": False,
            "error": "Mines game not found."
        }), 404

    if game["status"] != "active":

        return jsonify({
            "success": False,
            "error": "This Mines game is no longer active."
        }), 400

    # --------------------------------------
    # LOAD HIDDEN MINES
    # --------------------------------------

    try:

        mines = json.loads(
            game["mines_json"]
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):

        return jsonify({
            "success": False,
            "error": "Mines game data is corrupted."
        }), 500

    # --------------------------------------
    # LOAD REVEALED TILES
    # --------------------------------------

    try:

        revealed_tiles = json.loads(
            game["revealed_json"]
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):

        revealed_tiles = []

    # --------------------------------------
    # PREVENT DOUBLE REVEAL
    # --------------------------------------

    if tile in revealed_tiles:

        return jsonify({
            "success": False,
            "error": "Tile has already been revealed."
        }), 400

    # --------------------------------------
    # CHECK FOR MINE
    # --------------------------------------

    if tile in mines:

        # ----------------------------------
        # PLAYER HIT A MINE
        # ----------------------------------

        finish_mines_game(
            game_id,
            telegram_id,
            "lost"
        )

        current_balance = get_balance(
            telegram_id
        )

        return jsonify({

            "success": True,

            "result": "mine",

            "tile": tile,

            "game_id": game_id,

            "status": "lost",

            "balance": current_balance,

            "message": "Mine hit. Game over.",

            # The frontend can use these to
            # display the mine positions after
            # the game has ended.
            "mines": mines

        })

    # --------------------------------------
    # SAFE TILE
    # --------------------------------------

    revealed_tiles.append(
        tile
    )

    # --------------------------------------
    # CALCULATE MULTIPLIER
    # --------------------------------------
    #
    # This is a DEMO game using virtual
    # credits only.
    #
    # More safe tiles = larger multiplier.
    #
    # --------------------------------------

    safe_tiles = len(
        revealed_tiles
    )

    mine_count = int(
        game["mine_count"]
    )

    safe_tile_count = 25 - mine_count

    if safe_tile_count <= 0:

        safe_tile_count = 1

    # Simple progressive multiplier.
    #
    # Example with 5 mines:
    #
    # 1 safe tile  -> 1.20x
    # 2 safe tiles -> 1.44x
    # 3 safe tiles -> 1.73x
    #
    multiplier = round(
        1.0 + (
            safe_tiles * 0.20
        ),
        2
    )

    # --------------------------------------
    # CALCULATE POTENTIAL WIN
    # --------------------------------------

    bet_amount = int(
        game["bet_amount"]
    )

    potential_win = int(
        bet_amount * multiplier
    )

    # --------------------------------------
    # CHECK IF ALL SAFE TILES ARE REVEALED
    # --------------------------------------

    if safe_tiles >= safe_tile_count:

        # ----------------------------------
        # AUTOMATIC WIN
        # ----------------------------------

        new_balance = change_balance(

            telegram_id,

            potential_win,

            "game_win",

            "Mines demo automatic win"

        )

        if new_balance is None:

            return jsonify({
                "success": False,
                "error": "Could not process demo win."
            }), 500

        update_mines_game(

            game_id,

            telegram_id,

            revealed_tiles,

            multiplier,

            potential_win

        )

        finish_mines_game(

            game_id,

            telegram_id,

            "won"

        )

        return jsonify({

            "success": True,

            "result": "safe",

            "tile": tile,

            "game_id": game_id,

            "status": "won",

            "multiplier": multiplier,

            "potential_win": potential_win,

            "win_amount": potential_win,

            "balance": new_balance,

            "revealed": revealed_tiles,

            "mines": mines,

            "message": "All safe tiles revealed. You won!"

        })

    # --------------------------------------
    # SAVE SAFE TILE
    # --------------------------------------

    updated = update_mines_game(

        game_id,

        telegram_id,

        revealed_tiles,

        multiplier,

        potential_win

    )

    if not updated:

        return jsonify({
            "success": False,
            "error": "Could not update Mines game."
        }), 500

    # --------------------------------------
    # GET CURRENT BALANCE
    # --------------------------------------

    current_balance = get_balance(
        telegram_id
    )

    # --------------------------------------
    # RETURN SAFE RESULT
    # --------------------------------------

    return jsonify({

        "success": True,

        "result": "safe",

        "tile": tile,

        "game_id": game_id,

        "status": "active",

        "multiplier": multiplier,

        "potential_win": potential_win,

        "balance": current_balance,

        "revealed": revealed_tiles,

        "message": "Safe! Continue or cash out."

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
