GAME ZONE — KENO SERVER
========================

No server.py change is required for this step.

The Keno endpoint already successfully added/deployed is:

POST /api/game/keno

The new app.js sends:
{
    "initData": tg.initData,
    "bet_amount": bet,
    "numbers": selected
}

It reads the existing response fields:
success, game, bet, selected, draw, matched, matches,
multiplier, win, balance, message.

KEEP THE EXISTING KENO ENDPOINT IN server.py UNCHANGED.

This remains a virtual/demo-credit game only.
