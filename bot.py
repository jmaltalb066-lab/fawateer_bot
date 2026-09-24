import json, random, asyncio, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_FREE = "@wazaif_yemen1"
ADMIN_ID = int(os.getenv("ADMIN_ID", "772765410"))
PAY_NAME = "جمال عبد الناصر ناصر طالب"
PAY_NUMBER = "772765410"
PRICE = "2000 ريال يمني"

with open("jobs.json", "r", encoding="utf-8") as f:
    JOBS = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("💳 اشترك VIP", callback_data="pay")]]
    await update.message.reply_text(
        f"🇾🇪 بوت وظائف اليمن - الخليج\n\n"
        f"💰 الاشتراك: {PRICE}/شهر\n"
        f"💳 جوالي/كريمي: {PAY_NUMBER}\n"
        f"👤 باسم: {PAY_NAME}\n\n"
        f"📸 أرسل صورة الحوالة هنا",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ تم استلام الحوالة، سيتم تفعيلك خلال ساعة")
    await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)

async def post_job(app):
    j = random.choice(JOBS)
    txt = f"💼 {j['title']}\n📍 {j['location']}\n💰 {j['salary']}\n✅ {j['note']}\n\n🔒 للتفاصيل: اشترك VIP\n💳 {PRICE}\n📱 {PAY_NUMBER} ({PAY_NAME})"
    await app.bot.send_message(CHANNEL_FREE, txt)

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    await app.initialize()
    await app.start()
    while True:
        await post_job(app)
        await asyncio.sleep(14400)

if __name__ == "__main__":
    asyncio.run(main())
