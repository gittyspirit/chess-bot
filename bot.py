"""
Chess Telegram Bot - Two-Player Version
--------------------------------------
A simple Telegram bot that allows two users to play chess.

Key Features:
- Start a new game with another user.
- Handles basic chess moves.
- Displays the chessboard in a user-friendly format.
- Basic move validation.
- Game state management (who's playing, the board, etc.).

Dependencies:
- python-telegram-bot (v20.0 or higher)
- python-chess (v1.9.0 or higher)

Before You Run:
1.  Install the required libraries:
    ```bash
    pip install python-telegram-bot python-chess
    ```
2.  Get your Telegram Bot Token from BotFather:
    -   Open Telegram and search for "BotFather".
    -   Follow the instructions to create a new bot.
    -   BotFather will provide you with a token (a long string of characters).
3.  Replace 'YOUR_BOT_TOKEN' in the code below with your actual bot token.
4.  Run the script.

How to Play:
1.  Start a chat with the bot on Telegram.
2.  Use /start to begin.
3.  To start a new game, use /newgame @opponent_username
    (e.g., /newgame @ChessPlayer2).
4.  The bot will notify both players.
5.  Players make moves using algebraic notation (e.g., e2e4, Nf3, Rd8).
6.  The bot will display the board after each valid move.
7.  The game continues until a checkmate or other ending condition.

Important Notes:
-   This is a basic implementation and does not include all chess rules
    (e.g., castling, en passant).
-   Error handling is basic.
-   The bot stores game data in a dictionary in memory, so games are
    reset if the bot restarts.  For a production bot, you'd want to
    use a database.
-   Make sure you handle exceptions, especially network errors from Telegram.
"""

import logging
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
import chess
import re

# 1. Replace 'YOUR_BOT_TOKEN' with your actual bot token.
BOT_TOKEN = ""  #  <---  PUT YOUR BOT TOKEN HERE!

# 2. Enable logging (helps with debugging).  Good practice to include this.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 3. Store game state.  In a real application, use a database.
games = {}  # Dictionary to store game information.
#   - Key:  A unique game ID (e.g., a combination of user IDs).
#   - Value: A dictionary containing:
#       - 'board':  The chess.Board object.
#       - 'players':  A tuple of Telegram user IDs (player1, player2).
#       - 'turn': The Telegram user ID of the player whose turn it is.
#       - 'start_time':  (Optional)  You could store the start time

# 4. Helper Functions

def get_game_id(user1_id: int, user2_id: int) -> str:
    """
    Generates a unique game ID from two user IDs.  The order
    of the IDs doesn't matter.
    """
    return str(sorted((user1_id, user2_id)))

def display_board(board: chess.Board) -> str:
    """
    Converts a chess.Board object into a string representation that
    can be sent as a Telegram message.  Uses Unicode chess symbols.

    Args:
        board: The chess.Board object to display.

    Returns:
        A string representation of the board.
    """
    # Unicode Chess Symbols
    piece_symbols = {
        'P': '♟', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚',
        'p': '♙', 'r': '♖', 'n': '♘', 'b': '♗', 'q': '♕', 'k': '♔',
        '.': ' '  # Empty square
    }

    board_str = "╔═══╤═══╤═══╤═══╤═══╤═══╤═══╤═══╗\n"
    for row in range(8):
        board_str += "║"
        for col in range(8):
            square = chess.square(col, 7 - row)  # chess.square(col, row)
            piece = board.piece_at(square)
            if piece:
                symbol = piece_symbols[piece.symbol()]
            else:
                symbol = ' '
            board_str += f" {symbol} ║"
        board_str += "\n"
        if row < 7:
            board_str += "╠═══╪═══╪═══╪═══╪═══╪═══╪═══╪═══╣\n"
    board_str += "╚═══╧═══╧═══╧═══╧═══╧═══╧═══╧═══╝\n"
    board_str += "  a   b   c   d   e   f   g   h  \n"  # Add letter labels
    return board_str

# 5. Command Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command.  Introduces the bot and explains how to
    start a new game.
    """
    user = update.effective_user
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hello {user.first_name}!\n\n"
        "Welcome to the Chess Bot!\n"
        "To start a new game, use /newgame @opponent_username\n"
        "For example: /newgame @ChessPlayer2\n",
        reply_markup=ForceReply(selective=True),
    )

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /newgame command.  Starts a new game between two players.
    """
    if not update.message:
        return

    user1 = update.effective_user
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please specify an opponent's username (e.g., /newgame @ChessPlayer2).",
            reply_to_message_id=update.message.message_id,
        )
        return

    opponent_username = context.args[0]
    if not opponent_username.startswith("@"):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid username format.  Please use @username.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Get the opponent's user ID.  This is crucial for identifying the players.
    try:
        opponent = await context.bot.get_chat(username=opponent_username)
        user2_id = opponent.id
    except Exception as e:
        logger.error(f"Error getting opponent's user ID: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error: Could not find user {opponent_username}.  "
                 f"Please make sure the username is correct and the user has"
                 f" started the bot.",
            reply_to_message_id=update.message.message_id,
        )
        return

    user1_id = user1.id
    if user1_id == user2_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You cannot start a game with yourself!",
            reply_to_message_id=update.message.message_id,
        )
        return

    game_id = get_game_id(user1_id, user2_id)  # Generate unique game ID.

    if game_id in games:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="A game is already in progress with this user.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Initialize a new game.
    board = chess.Board()
    # Randomly assign colors (optional, for now, always user1 is white)
    players = (user1_id, user2_id)
    turn = user1_id #  Player 1 starts.

    games[game_id] = {
        'board': board,
        'players': players,
        'turn': turn,
    }

    # Send messages to both players to notify them that the game has started.
    await context.bot.send_message(
        chat_id=user1_id,
        text=f"New game started with {opponent_username}!\n"
             f"You are White.  Your move.",
    )
    await context.bot.send_message(
        chat_id=user2_id,
        text=f"New game started with {user1.username}!\n"
             f"You are Black.  Waiting for White to move.",
    )

    # Display the initial board.
    await context.bot.send_message(
        chat_id=user1_id,
        text=display_board(board),
    )
    await context.bot.send_message(
        chat_id=user2_id,
        text=display_board(board),
    )
    #  Potentially add a message to the group

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles a player's move.  Validates the move, updates the board,
    switches the turn, and sends the updated board to both players.
    """
    if not update.message:
        return
    user = update.effective_user
    move_text = update.message.text

    # Try to find the game.
    game_id = None
    for g_id, game_data in games.items():
        if user.id in game_data['players']:
            game_id = g_id
            break
    if game_id is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not currently in a game.  Use /newgame @opponent_username to start one.",
            reply_to_message_id=update.message.message_id,
        )
        return

    game = games[game_id]
    board = game['board']
    player1_id, player2_id = game['players']
    turn = game['turn']

    if user.id != turn:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="It is not your turn to move.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # 6.  Parse and Validate the move.
    try:
        move = board.parse_san(move_text)  #  Use algebraic notation
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid move format.  Please use algebraic notation (e.g., e2e4, Nf3, Rd8).",
            reply_to_message_id=update.message.message_id,
        )
        return

    if not board.is_legal(move):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Illegal move.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # 7. Make the move and update the game state.
    board.push(move)  # Make the move on the board.

    # Switch the turn to the other player.
    game['turn'] = player2_id if turn == player1_id else player1_id

    # 8. Check for game over (checkmate, stalemate, etc.).
    if board.is_checkmate():
        winner = user.id
        loser = player2_id if winner == player1_id else player1_id
        await context.bot.send_message(
            chat_id=player1_id,
            text=f"Checkmate!  You win!\n{display_board(board)}",
        )
        await context.bot.send_message(
            chat_id=player2_id,
            text=f"Checkmate!  You lose.\n{display_board(board)}",
        )
        del games[game_id]  # Remove the game from the dictionary.
        return
    elif board.is_stalemate():
        await context.bot.send_message(
            chat_id=player1_id,
            text=f"Stalemate!\n{display_board(board)}",
        )
        await context.bot.send_message(
            chat_id=player2_id,
            text=f"Stalemate!\n{display_board(board)}",
        )
        del games[game_id]
        return
    elif board.is_insufficient_material(): #added other end game conditions
        await context.bot.send_message(
            chat_id=player1_id,
            text=f"Insufficient Material!\n{display_board(board)}",
        )
        await context.bot.send_message(
            chat_id=player2_id,
            text=f"Insufficient Material!\n{display_board(board)}",
        )
        del games[game_id]
        return
    elif board.is_seventyfive_moves():
        await context.bot.send_message(
            chat_id=player1_id,
            text=f"75-move rule!\n{display_board(board)}",
        )
        await context.bot.send_message(
            chat_id=player2_id,
            text=f"75-move rule!\n{display_board(board)}",
        )
        del games[game_id]
        return
    elif board.is_repetition():
        await context.bot.send_message(
            chat_id=player1_id,
            text=f"Threefold repetition!\n{display_board(board)}",
        )
        await context.bot.send_message(
            chat_id=player2_id,
            text=f"Threefold repetition!\n{display_board(board)}",
        )
        del games[game_id]
        return

    # 9. Send the updated board to both players.
    await context.bot.send_message(
        chat_id=player1_id,
        text=f"Board after your move:\n{display_board(board)}",
    )
    await context.bot.send_message(
        chat_id=player2_id,
        text=f"Board after opponent's move:\n{display_board(board)}",
    )

    # 10.  Tell the next player it's their turn.
    next_player_id = game['turn']
    await context.bot.send_message(
        chat_id=next_player_id,
        text="It's your turn to move.",
        # reply_to_message_id=update.message.message_id, # Removed this
    )

def main() -> None:
    """
    Main function.  Sets up the bot and starts the Telegram event loop.
    """
    # 11. Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # 12. Register command handlers.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newgame", newgame))

    # 13. Register a message handler to handle moves (and any other text).
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_move))

    # 14. Start the bot.
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

