import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from core.config import config
from core.agent import PersonalAgent
from core.tools import get_system_info, get_notes, get_todos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramBot")

bot_agent = PersonalAgent()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name if update.effective_user else "Friend"
    welcome_msg = (
        f"👋 Hello {user}! I am **Aegis**, your personal AI assistant running on your laptop.\n\n"
        "You can chat with me directly, or use these commands:\n"
        "• `/system` - Check laptop battery, RAM & CPU status\n"
        "• `/notes` - View your recent notes\n"
        "• `/todos` - View your active tasks\n"
        "• Just send me any message, question, or task!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def system_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_system_info()
    text = (
        "💻 **Laptop Health Status**\n"
        f"• CPU Usage: {info.get('cpu_usage_percent')}%\n"
        f"• RAM: {info.get('ram_used_gb')}GB / {info.get('ram_total_gb')}GB ({info.get('ram_percent')}%)\n"
        f"• Battery: {info.get('battery', {}).get('percent')}%\n"
        f"• Disk Free: {info.get('disk_free_gb')} GB\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = get_notes()
    if not notes:
        await update.message.reply_text("📝 You have no saved notes yet.")
        return
    text = "📝 **Your Saved Notes:**\n"
    for n in notes[:5]:
        text += f"• **{n['title']}**: {n['content'][:80]}...\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def todos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    todos = get_todos(status="pending")
    if not todos:
        await update.message.reply_text("✅ All tasks complete! No pending to-dos.")
        return
    text = "📋 **Your Pending Tasks:**\n"
    for t in todos[:8]:
        text += f"• `[#{t['id']}]` {t['task']} (Priority: {t['priority']})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_text = update.message.text
    await update.message.chat.send_action("typing")

    full_answer = ""
    # Run agent in thread
    loop = asyncio.get_event_loop()
    def _run_agent():
        res = ""
        for event in bot_agent.run(user_text):
            if event["type"] == "done":
                res = event["full_answer"]
        return res

    answer = await loop.run_in_executor(None, _run_agent)
    await update.message.reply_text(answer or "Done.")

def run_bot():
    token = config.TELEGRAM_BOT_TOKEN
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Telegram bot token not configured in .env. Skipping Telegram Bot.")
        return
    print("Starting Telegram Bot...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("system", system_cmd))
    app.add_handler(CommandHandler("notes", notes_cmd))
    app.add_handler(CommandHandler("todos", todos_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    run_bot()
