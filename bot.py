import json
import random
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("TOKEN")

with open("questions.json", "r") as f:
    QUESTIONS = json.load(f)

quiz_data = {}

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type.endswith("group"):
        await update.message.reply_text("This command works only in groups.")
        return

    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.reply_text("Only admins can start the quiz.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /startquiz 5 10")
        return

    num_questions = int(context.args[0])
    time_per_question = int(context.args[1])

    selected_questions = random.sample(QUESTIONS, min(num_questions, len(QUESTIONS)))

    quiz_data[update.effective_chat.id] = {
        "questions": selected_questions,
        "current": 0,
        "answers": {},
        "time": time_per_question
    }

    await send_question(update.effective_chat.id, context)

async def send_question(chat_id, context):
    data = quiz_data.get(chat_id)
    if not data:
        return

    if data["current"] >= len(data["questions"]):
        await end_quiz(chat_id, context)
        return

    question = data["questions"][data["current"]]

    keyboard = []
    for i, option in enumerate(question["options"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=str(i))])

    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Question {data['current'] + 1}:\n\n{question['question']}",
        reply_markup=markup
    )

    await asyncio.sleep(data["time"])

    data["current"] += 1
    await send_question(chat_id, context)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id

    data = quiz_data.get(chat_id)
    if not data:
        return

    if user_id not in data["answers"]:
        data["answers"][user_id] = []

    data["answers"][user_id].append(int(query.data))

async def end_quiz(chat_id, context):
    data = quiz_data.get(chat_id)
    if not data:
        return

    scores = {}

    for user_id, answers in data["answers"].items():
        score = 0
        for i, user_answer in enumerate(answers):
            if user_answer == data["questions"][i]["answer"]:
                score += 1
        scores[user_id] = score

    leaderboard = "🏆 Quiz Finished!\n\n"

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for rank, (user_id, score) in enumerate(sorted_scores, start=1):
        user = await context.bot.get_chat_member(chat_id, user_id)
        leaderboard += f"{rank}. {user.user.first_name} - {score}/{len(data['questions'])}\n"

    await context.bot.send_message(chat_id=chat_id, text=leaderboard)

    del quiz_data[chat_id]

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("startquiz", start_quiz))
app.add_handler(CallbackQueryHandler(handle_answer))

app.run_polling()
