#!/usr/bin/env python3
"""
Gangle - Guess the Angle Game Bot
Main bot application with Telegram integration.
"""
import logging
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from config import config
from game_manager import game_manager
from rendering import render_angle

logger = logging.getLogger(__name__)


class GangleBot:
    """Main bot class handling all Telegram interactions."""
    
    def __init__(self):
        """Initialize the bot."""
        self.app = Application.builder().token(config.telegram_bot_token).build()
        self.waiting_for_guesses: Dict[int, Dict[str, Any]] = {}  # chat_id -> {user_id: callback_data}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up all command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start_round", self.start_round))
        self.app.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
        self.app.add_handler(CommandHandler("forfeit", self.forfeit_player))
        self.app.add_handler(CommandHandler("reset_leaderboard", self.reset_leaderboard))
        self.app.add_handler(CommandHandler("help", self.show_help))
        
        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for guess submissions
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_guess_message
        ))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
    
    async def start_round(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_round command."""
        if not update.message or not update.message.chat:
            return
        
        chat_id = update.message.chat.id
        
        # Only allow in group chats
        if update.message.chat.type not in ['group', 'supergroup']:
            await update.message.reply_text(
                "🚫 Gangle can only be played in group chats!"
            )
            return
        
        # Check if round is already active
        if game_manager.get_active_round(chat_id):
            await update.message.reply_text(
                "🎯 A round is already active! Players can still submit guesses."
            )
            return
        
        try:
            # Send initial message
            message = await update.message.reply_text(
                "🎯 **New Gangle Round Starting!**\n\n"
                "📐 An angle image will be posted below. Click the **Guess** button to submit your guess privately.\n\n"
                "⏳ Waiting for the angle image...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Create the round
            round_obj = game_manager.create_round(chat_id, message.message_id)
            
            # Generate and send angle image
            angle_image = render_angle(round_obj.angle, show_label=False)
            
            # Create inline keyboard
            keyboard = [[InlineKeyboardButton("🎯 Guess the Angle", callback_data=f"guess_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the image with guess button
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(angle_image, filename="angle.png"),
                caption="📐 **Guess the angle!** (0-359 degrees)\n\nClick the button below to submit your guess privately.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Update the initial message
            await message.edit_text(
                "🎯 **New Gangle Round Active!**\n\n"
                "📐 The angle image has been posted below. Click **Guess** to participate!\n\n"
                "👥 **Status:** Waiting for players...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Started new round in group {chat_id} with angle {round_obj.angle}°")
        
        except Exception as e:
            logger.error(f"Error starting round in group {chat_id}: {e}")
            await update.message.reply_text(
                "❌ Failed to start round. Please try again."
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        if not query or not query.data:
            return
        
        await query.answer()
        
        if query.data.startswith("guess_"):
            await self._handle_guess_button(update, context)
    
    async def _handle_guess_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle guess button press."""
        query = update.callback_query
        if not query or not query.message or not query.from_user:
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        username = query.from_user.username or f"user_{user_id}"
        first_name = query.from_user.first_name or "Unknown"
        
        # Check if round is active
        round_obj = game_manager.get_active_round(chat_id)
        if not round_obj:
            await query.edit_message_text(
                "❌ No active round found. Use /start_round to begin a new round."
            )
            return
        
        # Add player to round
        game_manager.add_player(chat_id, user_id, username, first_name)
        
        # Check if player already submitted
        if user_id in round_obj.players and round_obj.players[user_id].guess is not None:
            await query.edit_message_text(
                f"✅ You've already submitted your guess for this round!\n\n"
                f"Your guess: **{round_obj.players[user_id].guess}°**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store callback context for guess handling
        self.waiting_for_guesses.setdefault(chat_id, {})[user_id] = {
            'query_id': query.id,
            'username': username,
            'first_name': first_name
        }
        
        # Send private instruction
        await query.edit_message_text(
            "🎯 **Submit your angle guess!**\n\n"
            "📝 Reply to this message with your guess (0-359 degrees).\n"
            "💡 Example: Just type `45` for 45 degrees\n\n"
            "⏱️ This message will timeout in 5 minutes.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_guess_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle guess submissions via text messages."""
        if not update.message or not update.message.from_user:
            return
        
        user_id = update.message.from_user.id
        
        # Find which chat this guess is for
        target_chat_id = None
        for chat_id, waiting_users in self.waiting_for_guesses.items():
            if user_id in waiting_users:
                target_chat_id = chat_id
                break
        
        if target_chat_id is None:
            return  # User is not waiting to submit a guess
        
        # Parse guess
        try:
            guess = int(update.message.text.strip())
            if not 0 <= guess <= 359:
                await update.message.reply_text(
                    "❌ Please enter a number between 0 and 359 degrees."
                )
                return
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number between 0 and 359 degrees."
            )
            return
        
        # Submit guess
        success = game_manager.submit_guess(target_chat_id, user_id, guess)
        if not success:
            await update.message.reply_text(
                "❌ Failed to submit guess. The round may have ended."
            )
            return
        
        # Confirm submission
        await update.message.reply_text(
            f"✅ **Guess submitted successfully!**\n\n"
            f"🎯 Your guess: **{guess}°**\n\n"
            f"⏳ Waiting for other players to submit their guesses...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Remove from waiting list
        del self.waiting_for_guesses[target_chat_id][user_id]
        if not self.waiting_for_guesses[target_chat_id]:
            del self.waiting_for_guesses[target_chat_id]
        
        # Update group status
        await self._update_round_status(target_chat_id, context)
        
        # Check if round should end
        await self._check_round_completion(target_chat_id, context)
    
    async def _update_round_status(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Update the round status message in the group."""
        status = game_manager.get_round_status(chat_id)
        if not status:
            return
        
        status_text = (
            f"🎯 **Round Status**\n\n"
            f"👥 **Players:** {status['total_players']}\n"
            f"✅ **Submitted:** {status['players_submitted']}\n"
            f"⏳ **Pending:** {status['players_pending']}\n"
        )
        
        if status['players_forfeited'] > 0:
            status_text += f"❌ **Forfeited:** {status['players_forfeited']}\n"
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to update round status in group {chat_id}: {e}")
    
    async def _check_round_completion(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Check if round should be completed and handle completion."""
        status = game_manager.get_round_status(chat_id)
        if not status or not status['all_submitted']:
            return
        
        # Complete the round
        results = game_manager.complete_round(chat_id)
        if not results:
            return
        
        # Create reveal image with the correct angle
        reveal_image = render_angle(results['angle'], show_label=True)
        
        # Prepare results text
        results_text = "🎉 **Round Complete!**\n\n"
        results_text += f"🎯 **Correct Angle:** {results['angle']}°\n\n"
        
        if results['scores']:
            results_text += "🏆 **Results:**\n"
            for i, (player, points, accuracy) in enumerate(results['scores'][:5], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                results_text += f"{emoji} {player.first_name}: {player.guess}° ({points} pts, ±{accuracy}°)\n"
            
            if len(results['scores']) > 5:
                results_text += f"\n... and {len(results['scores']) - 5} more players"
        else:
            results_text += "😔 No valid submissions this round."
        
        results_text += f"\n\n👥 **Participation:** {results['players_participated']}/{results['total_players']} players"
        
        # Send reveal image and results
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(reveal_image, filename="reveal.png"),
                caption=results_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Round completed in group {chat_id} with {results['players_participated']} participants")
        
        except Exception as e:
            logger.error(f"Failed to send round results in group {chat_id}: {e}")
    
    async def show_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command."""
        if not update.message or not update.message.chat:
            return
        
        chat_id = update.message.chat.id
        
        # Only allow in group chats
        if update.message.chat.type not in ['group', 'supergroup']:
            await update.message.reply_text(
                "🚫 Leaderboards are only available in group chats!"
            )
            return
        
        leaderboard = game_manager.get_leaderboard(chat_id, limit=10)
        
        if not leaderboard:
            await update.message.reply_text(
                "📊 **Leaderboard is empty!**\n\n"
                "Start playing rounds to see player rankings here.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        leaderboard_text = "🏆 **Gangle Leaderboard**\n\n"
        
        for player in leaderboard:
            rank_emoji = "🥇" if player['rank'] == 1 else "🥈" if player['rank'] == 2 else "🥉" if player['rank'] == 3 else f"{player['rank']}."
            
            leaderboard_text += (
                f"{rank_emoji} **{player['first_name']}**\n"
                f"    💯 {player['total_points']} points\n"
                f"    🎮 {player['rounds_played']} rounds\n"
                f"    🎯 Best: ±{player['best_guess']}°\n\n"
            )
        
        await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN)
    
    async def forfeit_player(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /forfeit command (admin only)."""
        if not update.message or not update.message.chat or not update.message.from_user:
            return
        
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        
        # Check if user is admin
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("🚫 Only group admins can forfeit players.")
                return
        except Exception:
            await update.message.reply_text("❌ Failed to check admin status.")
            return
        
        # Parse target user
        if not context.args:
            await update.message.reply_text(
                "❓ **Usage:** `/forfeit @username`\n\n"
                "Example: `/forfeit @john`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        target_username = context.args[0].lstrip('@')
        
        # Find target user in active round
        round_obj = game_manager.get_active_round(chat_id)
        if not round_obj:
            await update.message.reply_text("❌ No active round to forfeit from.")
            return
        
        target_user_id = None
        for uid, player in round_obj.players.items():
            if player.username.lower() == target_username.lower():
                target_user_id = uid
                break
        
        if target_user_id is None:
            await update.message.reply_text(f"❌ Player @{target_username} not found in current round.")
            return
        
        # Forfeit the player
        success = game_manager.forfeit_player(chat_id, target_user_id)
        if success:
            await update.message.reply_text(
                f"❌ **@{target_username} has been forfeited from the current round.**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Check if round should complete
            await self._check_round_completion(chat_id, context)
        else:
            await update.message.reply_text("❌ Failed to forfeit player.")
    
    async def reset_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset_leaderboard command (admin only)."""
        if not update.message or not update.message.chat or not update.message.from_user:
            return
        
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        
        # Check if user is admin
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("🚫 Only group admins can reset the leaderboard.")
                return
        except Exception:
            await update.message.reply_text("❌ Failed to check admin status.")
            return
        
        # Reset leaderboard
        success = game_manager.reset_leaderboard(chat_id)
        if success:
            await update.message.reply_text(
                "🔄 **Leaderboard has been reset!**\n\n"
                "All player scores have been cleared.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Failed to reset leaderboard.")
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not update.message:
            return
        
        help_text = (
            "🎯 **Gangle - Guess the Angle Game**\n\n"
            "**How to Play:**\n"
            "1. Use `/start_round` to begin a new round\n"
            "2. Click the 'Guess' button on the angle image\n"
            "3. Submit your guess (0-359 degrees) privately\n"
            "4. Wait for results and see the leaderboard!\n\n"
            "**Commands:**\n"
            "• `/start_round` - Start a new game round\n"
            "• `/leaderboard` - View current rankings\n"
            "• `/help` - Show this help message\n\n"
            "**Admin Commands:**\n"
            "• `/forfeit @username` - Remove player from round\n"
            "• `/reset_leaderboard` - Reset all scores\n\n"
            "**Scoring:**\n"
            "• Perfect guess (0° off): 100 points\n"
            "• Points decrease with accuracy\n"
            "• 180° off or more: 0 points\n\n"
            "🎮 **Have fun guessing angles!**"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Exception while handling update {update}: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again or contact support."
                )
            except Exception:
                pass  # Don't raise on error handling
    
    def run(self):
        """Run the bot."""
        logger.info("Starting Gangle bot...")
        self.app.run_polling(drop_pending_updates=True)


def main():
    """Main entry point."""
    try:
        bot = GangleBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
