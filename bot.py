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
    MessageHandler, ContextTypes, filters, JobQueue
)
from telegram.constants import ParseMode

from config import config
from game_manager import game_manager
from rendering import render_angle

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown V2 formatting."""
    # Characters that need escaping in Markdown V2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, '\\' + char)
    return escaped_text


class GangleBot:
    """Main bot class handling all Telegram interactions."""
    
    def __init__(self):
        """Initialize the bot."""
        # Build application with job queue enabled
        if not config.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        # Build application with job queue explicitly enabled
        self.app = (
            Application.builder()
            .token(config.telegram_bot_token)
            .build()
        )
        
        # Check if job queue is available
        print(f"DEBUG: Job queue available after init: {self.app.job_queue is not None}")
        
        self.user_guess_states: Dict[str, Dict[str, Any]] = {}  # "chat_id:user_id" -> guess state
        self.status_update_jobs: Dict[int, Any] = {}  # chat_id -> job for status updates
        self.completion_monitor_jobs: Dict[int, Any] = {}  # chat_id -> job for completion monitoring
        self.status_message_ids: Dict[int, int] = {}  # chat_id -> status message_id
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up all command and message handlers."""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_bot))
        self.app.add_handler(CommandHandler("start_round", self.start_round))
        self.app.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
        self.app.add_handler(CommandHandler("forfeit", self.forfeit_player))
        self.app.add_handler(CommandHandler("reset_leaderboard", self.reset_leaderboard))
        self.app.add_handler(CommandHandler("end_round", self.end_round))
        self.app.add_handler(CommandHandler("help", self.show_help))
        
        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for guess submissions
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_guess_message
        ))
    
    async def _is_user_admin(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
        """Check if a user is an admin in the chat."""
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            return chat_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
    
    async def start_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update.message or not update.message.from_user:
            return
        
        user_name = update.message.from_user.first_name or "there"
        
        if update.message.chat.type == 'private':
            # Private chat - welcome message
            await update.message.reply_text(
                f"👋 Hi {user_name}! Welcome to **Gangle - Guess the Angle Game**!\n\n"
                "🎯 I'm a group game bot. Add me to a group chat and use `/start_round` to begin playing!\n\n"
                "✨ **New!** No private messaging needed - all interactions happen in the group using inline buttons!\n\n"
                "📝 Use `/help` to see all available commands.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Group chat - redirect to start_round
            await update.message.reply_text(
                "🎯 Use `/start_round` to begin a new angle guessing game!\n\n"
                "💡 **New!** Everything happens right here in the group - no private messaging required!"
            )
    
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
            if not update.effective_user:
                await update.message.reply_text("❌ Unable to identify user. Please try again.")
                return
            
            round_obj = game_manager.create_round(chat_id, message.message_id, update.effective_user.id)
            
            # Try to get an estimate of chat members (for better round management)
            try:
                member_count = await context.bot.get_chat_member_count(chat_id)
                # Store estimated member count (excluding bots, we'll estimate ~80% are real users)
                estimated_players = max(2, min(20, int(member_count * 0.8)))
                game_manager.set_estimated_players(chat_id, estimated_players)
                logger.info(f"Estimated {estimated_players} potential players for group {chat_id} (total members: {member_count})")
            except Exception as e:
                logger.warning(f"Could not get member count for group {chat_id}: {e}")
                game_manager.set_estimated_players(chat_id, 5)  # Default estimate
            
            # Generate and send angle image
            angle_image = render_angle(round_obj.angle, show_label=False)
            
            # Create inline keyboard
            keyboard = [[InlineKeyboardButton("🎯 Guess the Angle", callback_data=f"guess_{chat_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the image with guess button
            angle_message = await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(angle_image, filename="angle.png"),
                caption="📐 **Guess the angle!** (0-359 degrees)\n\nClick the button below to submit your guess privately.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Store the angle image message ID for later cleanup
            game_manager.set_angle_image_message_id(chat_id, angle_message.message_id)
            
            # Update the initial message
            await message.edit_text(
                "🎯 **New Gangle Round Active!**\n\n"
                "📐 The angle image has been posted below. Click **Guess** to participate!\n\n"
                "👥 **Status:** Waiting for players...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Start completion monitoring (check every 10 seconds)
            self._start_completion_monitoring(chat_id, context)
            
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
        elif query.data.startswith("pick_"):
            await self._handle_number_picker(update, context)
        elif query.data.startswith("confirm_"):
            await self._handle_guess_confirmation(update, context)
        elif query.data.startswith("cancel_"):
            await self._handle_guess_cancellation(update, context)
        elif query.data == "completed":
            await self._handle_completed_round_button(update, context)
    
    async def _handle_guess_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle initial guess button press."""
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
            await query.answer(
                "❌ This round has ended. Use /start_round to begin a new round.",
                show_alert=True
            )
            return
        
        # Check if round is still accepting guesses
        if round_obj.status != 'waiting_for_guesses':
            await query.answer(
                "✅ This round has completed. Use /start_round to begin a new round.",
                show_alert=True
            )
            return
        
        # Add player to round
        game_manager.add_player(chat_id, user_id, username, first_name)
        
        # Check if player already submitted
        if user_id in round_obj.players and round_obj.players[user_id].guess is not None:
            await query.answer(
                "✅ You've already submitted your guess!",
                show_alert=True
            )
            return
        
        # Check if player already has an active guess session
        state_key = f"{chat_id}:{user_id}"
        if state_key in self.user_guess_states:
            await query.answer(
                "🎯 You already have an active guess session! Check your previous message or cancel it first.",
                show_alert=True
            )
            return
        
        # Initialize guess state for this user
        state_key = f"{chat_id}:{user_id}"
        self.user_guess_states[state_key] = {
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'guess': [None, None, None],  # [hundreds, tens, units]
            'step': 0  # 0=hundreds, 1=tens, 2=units
        }
        
        # Show number picker for hundreds digit
        keyboard = self._create_number_picker_keyboard(state_key, step=0)
        
        # Send a temporary message for this user's guess selection
        try:
            temp_message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 {first_name}, select your angle guess:\n\nStep 1/3: Choose hundreds digit (0-3)\n⚠️ Only you can interact with these buttons!",
                reply_markup=keyboard
            )
            
            # Store the temporary message ID for cleanup
            self.user_guess_states[state_key]['temp_message_id'] = temp_message.message_id
            
            await query.answer("🎯 Use the number picker below to select your guess!", show_alert=False)
            
        except Exception as e:
            logger.error(f"Failed to send number picker message: {e}")
            await query.answer(
                "🎯 Starting number picker... Choose hundreds digit (0-3)",
                show_alert=True
            )
    
    def _create_number_picker_keyboard(self, state_key: str, step: int, max_digit: Optional[int] = None) -> InlineKeyboardMarkup:
        """Create number picker keyboard for current step."""
        state = self.user_guess_states[state_key]
        chat_id, user_id = state_key.split(':')
        
        if max_digit is None:
            if step == 0:  # Hundreds digit (0-3)
                max_digit = 3
            elif step == 1:  # Tens digit (0-5 if hundreds is 3, else 0-9)
                max_digit = 5 if state['guess'][0] == 3 else 9
            else:  # Units digit (0-5 if angle would be > 359, else 0-9)
                current_value = (state['guess'][0] or 0) * 100 + (state['guess'][1] or 0) * 10
                max_digit = 5 if current_value >= 350 else 9
        
        # Create number buttons
        keyboard = []
        row = []
        for digit in range(min(max_digit + 1, 10)):
            callback_data = f"pick_{chat_id}_{user_id}_{step}_{digit}"
            row.append(InlineKeyboardButton(str(digit), callback_data=callback_data))
            if len(row) == 5:  # 5 buttons per row
                keyboard.append(row)
                row = []
        if row:  # Add remaining buttons
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}_{user_id}")])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _handle_number_picker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle number picker button selection."""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        
        # Parse callback data: pick_{chat_id}_{user_id}_{step}_{digit}
        parts = query.data.split('_')
        if len(parts) < 5:
            await query.answer("❌ Invalid callback data", show_alert=True)
            return
        
        chat_id = int(parts[1])
        user_id = int(parts[2]) 
        step = int(parts[3])
        digit = int(parts[4])
        
        # Validate that the person clicking the button is the intended user
        if query.from_user.id != user_id:
            await query.answer("🚫 These buttons are for another player!", show_alert=True)
            return
        
        state_key = f"{chat_id}:{user_id}"
        
        if state_key not in self.user_guess_states:
            await query.answer("⚠️ Session expired. Please click Guess again.", show_alert=True)
            return
        
        state = self.user_guess_states[state_key]
        state['guess'][step] = digit
        state['step'] = step + 1
        
        # Determine next step and update keyboard
        if step == 0:  # Just selected hundreds, now select tens
            next_step = 1
            max_digit = 5 if digit == 3 else 9
            next_keyboard = self._create_number_picker_keyboard(state_key, next_step, max_digit)
            message = f"🎯 Step 2/3: Choose tens digit (0-{max_digit})\n\nYour guess so far: {digit}__"
            
        elif step == 1:  # Just selected tens, now select units
            next_step = 2
            current_value = state['guess'][0] * 100 + digit * 10
            max_digit = 5 if current_value >= 350 else 9
            next_keyboard = self._create_number_picker_keyboard(state_key, next_step, max_digit)
            message = f"🎯 Step 3/3: Choose units digit (0-{max_digit})\n\nYour guess so far: {state['guess'][0]}{digit}_"
            
        else:  # Just selected units - show confirmation
            final_guess = state['guess'][0] * 100 + state['guess'][1] * 10 + digit
            confirmation_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{user_id}_{final_guess}")],
                [InlineKeyboardButton("🔄 Start Over", callback_data=f"guess_{chat_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}_{user_id}")]
            ])
            message = f"🎯 Confirm your guess: {final_guess}°\n\nClick ✅ to submit or 🔄 to start over."
            
            try:
                # Get the temporary message ID from state
                temp_message_id = state.get('temp_message_id')
                if temp_message_id:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=temp_message_id,
                        text=message,
                        reply_markup=confirmation_keyboard
                    )
                else:
                    # Fallback: send new message
                    new_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        reply_markup=confirmation_keyboard
                    )
                    self.user_guess_states[state_key]['temp_message_id'] = new_message.message_id
                
                await query.answer()
            except Exception as e:
                logger.error(f"Failed to show confirmation: {e}")
                await query.answer("🎯 Click confirm to submit your guess!", show_alert=True)
            return
        
        # Continue to next digit selection
        try:
            # Get the temporary message ID from state
            temp_message_id = state.get('temp_message_id')
            if temp_message_id:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=temp_message_id,
                    text=message,
                    reply_markup=next_keyboard
                )
            else:
                # Fallback: send new message
                new_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=next_keyboard
                )
                self.user_guess_states[state_key]['temp_message_id'] = new_message.message_id
            
            await query.answer()
        except Exception as e:
            logger.error(f"Failed to update number picker: {e}")
            await query.answer(message, show_alert=True)
    
    async def _handle_guess_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle guess confirmation."""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        
        # Parse callback data: confirm_{chat_id}_{user_id}_{guess}
        parts = query.data.split('_')
        if len(parts) < 4:
            await query.answer("❌ Invalid confirmation data", show_alert=True)
            return
        
        chat_id = int(parts[1])
        user_id = int(parts[2])
        guess = int(parts[3])
        
        # Validate that the person clicking the button is the intended user
        if query.from_user.id != user_id:
            await query.answer("🚫 This confirmation is for another player!", show_alert=True)
            return
        
        state_key = f"{chat_id}:{user_id}"
        
        if state_key not in self.user_guess_states:
            await query.answer("⚠️ Session expired.", show_alert=True)
            return
        
        # Submit the guess
        success = game_manager.submit_guess(chat_id, user_id, guess)
        if not success:
            await query.answer("❌ Failed to submit guess. Round may have ended.", show_alert=True)
            return
        
        # Get the temporary message ID before cleaning up state
        state = self.user_guess_states[state_key]
        temp_message_id = state.get('temp_message_id')
        
        # Clean up state
        del self.user_guess_states[state_key]
        
        # Clean up the temporary message (delete it to maintain privacy)
        if temp_message_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=temp_message_id)
            except Exception as e:
                logger.error(f"Failed to delete temporary message: {e}")
        
        # Send private confirmation (only visible to the user who clicked)
        await query.answer("✅ Guess submitted successfully! Waiting for other players...", show_alert=True)
        
        # Update group status
        await self._update_round_status(chat_id, context)
        
        # Check if round should end (but don't wait for return value since monitoring handles it)
        await self._check_round_completion(chat_id, context)
    
    async def _handle_guess_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle guess cancellation."""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        
        # Parse callback data: cancel_{chat_id}_{user_id}
        parts = query.data.split('_')
        if len(parts) < 3:
            await query.answer("❌ Invalid cancellation data", show_alert=True)
            return
        
        chat_id = int(parts[1])
        user_id = int(parts[2])
        
        # Validate that the person clicking the button is the intended user
        if query.from_user.id != user_id:
            await query.answer("🚫 This cancellation is for another player!", show_alert=True)
            return
        
        state_key = f"{chat_id}:{user_id}"
        
        if state_key in self.user_guess_states:
            del self.user_guess_states[state_key]
        
        try:
            await query.edit_message_text(
                "❌ Guess Cancelled\n\n"
                "Click the 'Guess' button again to restart."
            )
        except Exception as e:
            logger.error(f"Failed to update cancellation message: {e}")
        
        await query.answer("❌ Guess cancelled. Click Guess again to restart.", show_alert=False)
    
    async def _handle_completed_round_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clicks on the disabled button from completed rounds."""
        query = update.callback_query
        if not query:
            return
        
        await query.answer("✅ This round has already completed! Use /start_round to begin a new round.", show_alert=True)
    
    async def handle_guess_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (no longer needed for guess submission)."""
        # This method is kept for backward compatibility but doesn't process guesses anymore
        # All guess submission now happens via inline buttons
        pass
    
    async def _update_round_status(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Update the round status message in the group."""
        status = game_manager.get_round_status(chat_id)
        if not status:
            return
        
        status_text = (
            f"🎯 *Round Status*\n\n"
            f"👥 *Active Players:* {status['active_players']}\n"
            f"✅ *Submitted:* {status['players_submitted']}\n"
            f"⏳ *Pending:* {status['players_pending']}\n"
        )
        
        if status['players_forfeited'] > 0:
            status_text += f"❌ *Forfeited:* {status['players_forfeited']}\n"
        
        # Add timing information - show remaining time instead of elapsed time
        if status['can_complete_in'] > 0:
            status_text += f"⏰ *Time until auto\\-complete:* {int(status['can_complete_in'])}s remaining\n"
        elif status['all_submitted']:
            status_text += "✨ *Round ready to complete\\!*\n"
        else:
            # Show time remaining until max wait time
            from config import config
            max_wait_remaining = max(0, config.max_wait_time - status['time_elapsed'])
            if max_wait_remaining > 0:
                status_text += f"⏰ *Max wait time:* {int(max_wait_remaining)}s remaining\n"
            else:
                status_text += f"⏰ *Time elapsed:* {int(status['time_elapsed'])}s\n"
        
        try:
            # Try to update existing status message first
            if chat_id in self.status_message_ids:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=self.status_message_ids[chat_id],
                        text=status_text,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    return  # Successfully updated existing message
                except Exception as edit_error:
                    # Message might be deleted or not found, remove from tracking and send new one
                    logger.warning(f"Failed to edit status message in group {chat_id}: {edit_error}")
                    del self.status_message_ids[chat_id]
            
            # Send new status message if no existing one or edit failed
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            # Track the new status message
            self.status_message_ids[chat_id] = message.message_id
            
        except Exception as e:
            logger.error(f"Failed to update round status in group {chat_id}: {e}")
    
    async def _check_round_completion(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if round should be completed and handle completion.
        
        Returns:
            True if round was completed, False otherwise
        """
        status = game_manager.get_round_status(chat_id)
        if not status:
            print(f"DEBUG: No status for chat {chat_id}")
            return False
            
        print(f"DEBUG: Round status for chat {chat_id}: all_submitted={status['all_submitted']}, can_complete={status['can_complete']}, time_elapsed={status['time_elapsed']}")
        
        # Check if round can be completed (either all submitted + min wait time, or max wait time reached)
        if not status['can_complete']:
            print(f"DEBUG: Round not ready to complete for chat {chat_id}")
            return False
        
        print(f"DEBUG: Attempting to complete round for chat {chat_id}")
        
        # Complete the round
        results = game_manager.complete_round(chat_id)
        if not results:
            print(f"DEBUG: Failed to complete round for chat {chat_id}")
            return False

        print(f"DEBUG: Round completed successfully for chat {chat_id}, preparing results...")
        
        # Create reveal image with the correct angle
        reveal_image = render_angle(results['angle'], show_label=True)
        
        # Prepare results text
        results_text = "🎉 *Round Complete\\!*\n\n"
        results_text += f"🎯 *Correct Angle:* {results['angle']}°\n\n"
        
        if results['scores']:
            results_text += "🏆 *Results:*\n"
            for i, (player, points, accuracy) in enumerate(results['scores'][:5], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}\\."
                # Show username with @ prefix, fallback to first_name if no username
                raw_display_name = f"@{player.username}" if player.username else player.first_name
                display_name = escape_markdown(raw_display_name)
                results_text += f"{emoji} {display_name}: {player.guess}° \\({points} pts, ±{accuracy}°\\)\n"
            
            if len(results['scores']) > 5:
                results_text += f"\n\\.\\.\\. and {len(results['scores']) - 5} more players"
        else:
            results_text += "😔 No valid submissions this round\\."
        
        results_text += f"\n\n👥 *Participation:* {results['players_participated']}/{results['total_players']} players"
        
        # Send reveal image and results
        try:
            print(f"DEBUG: Sending results photo for chat {chat_id}")
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=InputFile(reveal_image, filename="reveal.png"),
                caption=results_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            print(f"DEBUG: Results sent, sending leaderboard for chat {chat_id}")
            # Send leaderboard after results
            await self._send_leaderboard_to_chat(chat_id, context)
            
            # Disable the guess button to prevent further interactions
            await self._disable_guess_button(chat_id, context)
            
            # Stop completion monitoring
            self._stop_completion_monitoring(chat_id)
            
            # Cancel any scheduled status updates
            if hasattr(self, 'status_update_jobs') and chat_id in self.status_update_jobs:
                self.status_update_jobs[chat_id].schedule_removal()
                del self.status_update_jobs[chat_id]
            
            # Clean up status message tracking
            if chat_id in self.status_message_ids:
                del self.status_message_ids[chat_id]
            
            logger.info(f"Round completed in group {chat_id} with {results['players_participated']} participants")
            print(f"DEBUG: Round completion finished for chat {chat_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send round results in group {chat_id}: {e}")
            print(f"DEBUG: Error sending results for chat {chat_id}: {e}")
            return False
    
    async def _send_leaderboard_to_chat(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Send leaderboard to a specific chat."""
        leaderboard = game_manager.get_leaderboard(chat_id, limit=10)
        
        if not leaderboard:
            await context.bot.send_message(
                chat_id=chat_id,
                text="📊 *Leaderboard*\n\nNo games played yet\\!",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        text = "🏆 *Leaderboard* \\(Top 10\\)\n\n"
        for i, player in enumerate(leaderboard, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}\\."
            # Show username with @ prefix, fallback to first_name if no username
            raw_display_name = f"@{player['username']}" if player.get('username') else player['first_name']
            display_name = escape_markdown(raw_display_name)
            text += f"{emoji} {display_name}: {player['total_points']} pts \\({player['games_played']} games\\)\n"

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def _disable_guess_button(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Disable the guess button from the angle image when round completes."""
        round_obj = game_manager.get_active_round(chat_id)
        if not round_obj or not round_obj.angle_image_message_id:
            return
        
        try:
            # Edit the message to remove the inline keyboard
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=round_obj.angle_image_message_id,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Round Completed", callback_data="completed")
                ]])
            )
            logger.info(f"Disabled guess button for completed round in group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to disable guess button in group {chat_id}: {e}")
    
    def _schedule_status_updates(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Schedule periodic status updates every 10 seconds."""
        try:
            # Debug logging
            print(f"DEBUG: _schedule_status_updates called for chat {chat_id}")
            
            # Use self.app.job_queue instead of context.job_queue
            job_queue = self.app.job_queue
            
            # Cancel existing job if any
            if chat_id in self.status_update_jobs:
                self.status_update_jobs[chat_id].schedule_removal()
                del self.status_update_jobs[chat_id]
            
            # Schedule new job if job_queue is available
            if job_queue:
                job = job_queue.run_repeating(
                    callback=self._periodic_status_update_callback,
                    interval=10.0,  # 10 seconds
                    first=10.0,  # Start after 10 seconds
                    name=f"status_update_{chat_id}",
                    data=chat_id  # Pass chat_id as data
                )
                self.status_update_jobs[chat_id] = job
                print(f"DEBUG: Scheduled periodic updates for chat {chat_id}")
            else:
                print(f"DEBUG: No job queue available, periodic updates disabled for chat {chat_id}")
        except Exception as e:
            print(f"DEBUG: Error scheduling status updates for chat {chat_id}: {e}")
            logger.error(f"Error scheduling status updates for chat {chat_id}: {e}")
    
    async def _periodic_status_update_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Job queue callback for periodic status updates."""
        if context.job and context.job.data and isinstance(context.job.data, int):
            chat_id = context.job.data
            await self._periodic_status_update(chat_id, context)
    
    async def _periodic_status_update(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Periodic status update callback."""
        try:
            print(f"DEBUG: Periodic status update for chat {chat_id}")
            await self._update_round_status(chat_id, context)
            await self._check_round_completion(chat_id, context)
        except Exception as e:
            print(f"DEBUG: Error in periodic status update for chat {chat_id}: {e}")
            logger.error(f"Error in periodic status update for chat {chat_id}: {e}")
    
    def _start_completion_monitoring(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Start periodic monitoring for round completion."""
        try:
            # Debug logging
            print(f"DEBUG: _start_completion_monitoring called for chat {chat_id}")
            print(f"DEBUG: context.job_queue is: {context.job_queue}")
            print(f"DEBUG: self.app.job_queue is: {self.app.job_queue}")
            
            # Use self.app.job_queue instead of context.job_queue
            job_queue = self.app.job_queue
            
            # Cancel existing job if any
            if chat_id in self.completion_monitor_jobs:
                self.completion_monitor_jobs[chat_id].schedule_removal()
                del self.completion_monitor_jobs[chat_id]
            
            # Schedule new job to check completion every 10 seconds
            if job_queue:
                job = job_queue.run_repeating(
                    callback=self._monitor_round_completion_callback,
                    interval=10.0,  # Check every 10 seconds
                    first=10.0,  # Start after 10 seconds
                    name=f"completion_monitor_{chat_id}",
                    data=chat_id  # Pass chat_id as data
                )
                self.completion_monitor_jobs[chat_id] = job
                print(f"DEBUG: Started completion monitoring for chat {chat_id}")
            else:
                print(f"DEBUG: No job queue available, completion monitoring disabled for chat {chat_id}")
        except Exception as e:
            print(f"DEBUG: Error starting completion monitoring for chat {chat_id}: {e}")
            logger.error(f"Error starting completion monitoring for chat {chat_id}: {e}")
    
    async def _monitor_round_completion_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Job queue callback for round completion monitoring."""
        if context.job and context.job.data and isinstance(context.job.data, int):
            chat_id = context.job.data
            await self._monitor_round_completion(chat_id, context)
    
    async def _monitor_round_completion(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Monitor for round completion - called periodically."""
        try:
            print(f"DEBUG: Monitoring round completion for chat {chat_id}")
            
            # Update status and check for completion
            await self._update_round_status(chat_id, context)
            completed = await self._check_round_completion(chat_id, context)
            
            # If round completed, stop monitoring
            if completed:
                print(f"DEBUG: Round completed, stopping monitoring for chat {chat_id}")
                self._stop_completion_monitoring(chat_id)
            
        except Exception as e:
            print(f"DEBUG: Error in completion monitoring for chat {chat_id}: {e}")
            logger.error(f"Error in completion monitoring for chat {chat_id}: {e}")
    
    def _stop_completion_monitoring(self, chat_id: int):
        """Stop the completion monitoring for a chat."""
        try:
            if chat_id in self.completion_monitor_jobs:
                self.completion_monitor_jobs[chat_id].schedule_removal()
                del self.completion_monitor_jobs[chat_id]
                print(f"DEBUG: Stopped completion monitoring for chat {chat_id}")
            
            # Also clean up status message tracking when stopping monitoring
            if chat_id in self.status_message_ids:
                del self.status_message_ids[chat_id]
                
        except Exception as e:
            print(f"DEBUG: Error stopping completion monitoring for chat {chat_id}: {e}")
            logger.error(f"Error stopping completion monitoring for chat {chat_id}: {e}")
    
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
                "📊 *Leaderboard is empty\\!*\n\n"
                "Start playing rounds to see player rankings here\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        
        leaderboard_text = "🏆 *Gangle Leaderboard*\n\n"
        
        for player in leaderboard:
            rank_emoji = "🥇" if player['rank'] == 1 else "🥈" if player['rank'] == 2 else "🥉" if player['rank'] == 3 else f"{player['rank']}\\."
            
            # Show username with @ prefix, fallback to first_name if no username
            raw_display_name = f"@{player['username']}" if player.get('username') else player['first_name']
            display_name = escape_markdown(raw_display_name)
            
            leaderboard_text += (
                f"{rank_emoji} *{display_name}*\n"
                f"    💯 {player['total_points']} points\n"
                f"    🎮 {player['rounds_played']} rounds\n"
                f"    🎯 Best: ±{player['best_guess']}°\n\n"
            )
        
        await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN_V2)
    
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
    
    async def end_round(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /end_round command (admin or starter only)."""
        if not update.message or not update.message.chat or not update.message.from_user:
            return
        
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id
        
        # Check if there's an active round
        round_obj = game_manager.get_active_round(chat_id)
        if not round_obj:
            await update.message.reply_text("❌ No active round to end.")
            return
        
        # Check if user is admin or the starter of the round
        is_admin = await self._is_user_admin(context, chat_id, user_id)
        is_starter = round_obj.starter_user_id == user_id
        
        if not is_admin and not is_starter:
            await update.message.reply_text(
                "🚫 Only group admins or the player who started this round can end it."
            )
            return
        
        # End the round
        results = game_manager.end_round(chat_id, user_id, is_admin)
        if results:
            # Create reveal image with the correct angle
            reveal_image = render_angle(results['angle'], show_label=True)
            
            # Prepare results text
            results_text = "⏹️ *Round Ended Early\\!*\n\n"
            results_text += f"🎯 *Correct Angle:* {results['angle']}°\n\n"
            
            if results['scores']:
                results_text += "🏆 *Results:*\n"
                for i, (player, points, accuracy) in enumerate(results['scores'][:5], 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}\\."
                    # Show username with @ prefix, fallback to first_name if no username
                    raw_display_name = f"@{player.username}" if player.username else player.first_name
                    display_name = escape_markdown(raw_display_name)
                    results_text += f"{emoji} {display_name}: {player.guess}° \\({points} pts, ±{accuracy}°\\)\n"
                
                if len(results['scores']) > 5:
                    results_text += f"\n\\.\\.\\. and {len(results['scores']) - 5} more players"
            else:
                results_text += "😔 No valid submissions this round\\."
            
            results_text += f"\n\n👥 *Participation:* {results['players_participated']}/{results['total_players']} players"
            
            # Send reveal image and results
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=InputFile(reveal_image, filename="reveal.png"),
                    caption=results_text,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
                # Disable the guess button to prevent further interactions
                await self._disable_guess_button(chat_id, context)
                
                # Stop completion monitoring
                self._stop_completion_monitoring(chat_id)
                
                # Clean up status message tracking
                if chat_id in self.status_message_ids:
                    del self.status_message_ids[chat_id]
                
                logger.info(f"Round ended early in group {chat_id} by user {user_id}")
            
            except Exception as e:
                logger.error(f"Failed to send round results in group {chat_id}: {e}")
        else:
            await update.message.reply_text("❌ Failed to end round.")
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not update.message:
            return
        
        help_text = (
            "🎯 *Gangle \\- Guess the Angle Game*\n\n"
            "*How to Play:*\n"
            "1\\. Use `/start_round` in a group to begin a new round\n"
            "2\\. Click the 'Guess' button on the angle image\n"
            "3\\. Use the inline number picker to select your angle \\(0\\-359°\\)\n"
            "4\\. Confirm your guess \\- it stays private until round ends\\!\n"
            "5\\. Wait for results and see the leaderboard\\!\n\n"
            "*Commands:*\n"
            "• `/start_round` \\- Start a new game round\n"
            "• `/leaderboard` \\- View current rankings\n"
            "• `/help` \\- Show this help message\n\n"
            "*Admin Commands:*\n"
            "• `/forfeit @username` \\- Remove player from round\n"
            "• `/reset_leaderboard` \\- Reset all scores\n"
            "• `/end_round` \\- End current round early \\(admin or starter only\\)\n\n"
            "*Scoring:*\n"
            "• Perfect guess \\(0° off\\): 100 points\n"
            "• Points decrease with accuracy\n"
            "• 180° off or more: 0 points\n\n"
            "✨ *New\\!* No private messaging required \\- everything happens in the group\\!\n\n"
            "🎮 *Have fun guessing angles\\!*"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)
    
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
    
    def _cleanup_all_jobs(self):
        """Clean up all scheduled jobs."""
        try:
            # Clean up completion monitoring jobs
            for chat_id in list(self.completion_monitor_jobs.keys()):
                self._stop_completion_monitoring(chat_id)
            
            # Clean up status update jobs
            for chat_id, job in list(self.status_update_jobs.items()):
                try:
                    job.schedule_removal()
                    del self.status_update_jobs[chat_id]
                except Exception as e:
                    logger.error(f"Error cleaning up status job for {chat_id}: {e}")
            
            # Clear status message tracking
            self.status_message_ids.clear()
            
            logger.info("All scheduled jobs cleaned up")
        except Exception as e:
            logger.error(f"Error during job cleanup: {e}")
    
    def run(self):
        """Run the bot."""
        logger.info("Starting Gangle bot...")
        try:
            self.app.run_polling(drop_pending_updates=True)
        finally:
            self._cleanup_all_jobs()


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
