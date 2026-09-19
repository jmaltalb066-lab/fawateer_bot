import sqlite3
import os
import random
import string
import configparser
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ===== متغيرات البيئة - لا تعدل هنا، عدلها في Railway =====
TOKEN = os.getenv("TOKEN") # ← ياخذه من Railway
ADMIN_ID = int(os.getenv("ADMIN_ID", "5690562040")) # ← ياخذه من Railway أو القيمة الافتراضية
# ======================================================

BRANCH_PATH = "/data" # ← هذا المجلد الوحيد اللي Railway يحفظه
DB_FILE = os.path.join(BRANCH_PATH, "factory.db")

# يتأكد المجلد موجود
os.makedirs(BRANCH_PATH, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS branches (
        id TEXT PRIMARY KEY,
        chat_id TEXT,
        status TEXT DEFAULT 'pending',
        activation_code TEXT,
        created_at TEXT,
        activated_at TEXT,
        last_seen TEXT
    )''')
    conn.commit()
    conn.close()

def generate_activation_code():
    """يسوي كود تفعيل عشوائي زي: JML-78-A9F2"""
    return f"JML-{random.randint(10,99)}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    await update.message.reply_text(
        "🤖 **بوت إدارة المصنع - جمال**\n\n"
        "الأوامر:\n"
        "/new رقم - إنشاء فرع + كود تفعيل\n"
        "/list - عرض الفروع بالتاريخ\n"
        "/active - الفروع المفعلة فقط\n"
        "/pending - الفروع اللي ما تفعلت\n"
        "/stop رقم - إيقاف فرع\n"
        "/start رقم - تشغيل فرع\n"
        "/del رقم - حذف فرع\n"
        "/notify رقم الرسالة - إرسال رسالة للفرع\n"
        "/stats - إحصائيات عامة\n"
        "مثال: `/new 78`\n\n"
        "💡 **للتفعيل:** شغل print.py وارسل كود التفعيل هنا"
    )

async def new_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("اكتب: /new 78")
        return

    branch_id = context.args[0]
    activation_code = generate_activation_code()

    # يسوي مجلد الفرع
    branch_folder = os.path.join(BRANCH_PATH, f"branch_{branch_id}")
    os.makedirs(branch_folder, exist_ok=True)

    # ملف config.ini
    config_content = f"""[Bot]
MasterBot={TOKEN}
ChatID=TO_BE_FILLED
ActivationCode={activation_code}

[Branch]
ID={branch_id}
Name=فرع {branch_id}

[Features]
Enable_Send=1
"""
    config_file = os.path.join(branch_folder, f"config_{branch_id}.ini")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(config_content)

    # يحفظ في القاعدة
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO branches
                 (id, activation_code, status, created_at) VALUES (?,?,?,?)""",
              (branch_id, activation_code, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    await update.message.reply_document(
        document=open(config_file, 'rb'),
        caption=f"✅ **تم إنشاء الفرع {branch_id}**\n\n"
                f"🔑 **كود التفعيل:** `{activation_code}`\n\n"
                f"📋 **الخطوات:**\n"
                f"1. نزل الملف هذا\n"
                f"2. شغل `print.py` في الكمبيوتر\n"
                f"3. أول ما يشتغل بيرسل لك كود التفعيل تلقائي\n"
                f"4. أرسل الكود هنا عشان أربطه\n"
                f"⚠️ الفرع ما بيشتغل إلا بعد التفعيل"
    )

# ===== الدالة الجديدة للتفعيل التلقائي =====
async def handle_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستقبل كود التفعيل من print.py ويفعل الفرع تلقائي"""
    if update.effective_user.id!= ADMIN_ID: return

    text = update.message.text.strip()

    # يتأكد انها صيغة كود تفعيل JML-XX-XXXX
    if not text.startswith("JML-") or len(text) < 10:
        return

    activation_code = text
    chat_id = str(update.effective_chat.id)

    # يدور على الفرع بالكود
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, status FROM branches WHERE activation_code=?", (activation_code,))
    row = c.fetchone()

    if not row:
        await update.message.reply_text(f"❌ كود التفعيل `{activation_code}` غلط أو مستخدم من قبل")
        conn.close()
        return

    branch_id, status = row

    if status == 'active':
        await update.message.reply_text(f"⚠️ الفرع {branch_id} مفعل من قبل")
        conn.close()
        return

    # يفعّل الفرع
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("""UPDATE branches SET
                 chat_id=?, status='active', activated_at=?, last_seen=?
                 WHERE id=?""",
              (chat_id, now, now, branch_id))
    conn.commit()
    conn.close()

    # يحدث config.ini ويحط ChatID
    config_file = os.path.join(BRANCH_PATH, f"branch_{branch_id}", f"config_{branch_id}.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        config['Bot']['ChatID'] = chat_id
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    await update.message.reply_text(
        f"✅ **تم تفعيل الفرع {branch_id} بنجاح!**\n\n"
        f"🔓 الحالة: مفعل\n"
        f"🆔 ChatID: `{chat_id}`\n"
        f"📅 وقت التفعيل: {now}\n\n"
        f"الحين تقدر تستخدم:\n"
        f"`/stop {branch_id}` للإيقاف\n"
        f"`/notify {branch_id} رسالة` للإرسال"
    )

async def list_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, status, created_at, activated_at FROM branches ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 لا يوجد فروع")
        return

    msg = "📋 **كل الفروع مرتبة بالأحدث:**\n\n"
    for r in rows:
        bid, status, created, activated = r
        emoji = "✅" if status == 'active' else "⏸️" if status == 'stopped' else "⏳"
        msg += f"{emoji} **فرع {bid}** - {status}\n"
        msg += f" 📅 أنشئ: {created}\n"
        if activated:
            msg += f" 🔓 تفعل: {activated}\n"
        msg += "\n"

    await update.message.reply_text(msg)

async def active_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, activated_at, last_seen FROM branches WHERE status='active' ORDER BY activated_at DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 مافيش فروع مفعلة")
        return

    msg = "✅ **الفروع المفعلة:**\n\n"
    for r in rows:
        msg += f"🟢 فرع {r[0]}\n تفعل: {r[1]}\n آخر ظهور: {r[2] or 'مافيش'}\n\n"

    await update.message.reply_text(msg)

async def pending_branches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, activation_code, created_at FROM branches WHERE status='pending'")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("✅ كل الفروع مفعلة")
        return

    msg = "⏳ **فروع تنتظر التفعيل:**\n\n"
    for r in rows:
        msg += f"🔸 فرع {r[0]}\n الكود: `{r[1]}`\n أنشئ: {r[2]}\n\n"

    await update.message.reply_text(msg)

async def stop_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("اكتب: /stop 78")
        return

    branch_id = context.args[0]
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE branches SET status='stopped' WHERE id=?", (branch_id,))
    conn.commit()
    conn.close()

    # يحدث config.ini
    config_file = os.path.join(BRANCH_PATH, f"branch_{branch_id}", f"config_{branch_id}.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        config['Features']['Enable_Send'] = '0'
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    await update.message.reply_text(f"⏸️ تم إيقاف الفرع {branch_id}\nالفواتير بتتخزن في الطابور")

async def start_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("اكتب: /start 78")
        return

    branch_id = context.args[0]
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE branches SET status='active' WHERE id=?", (branch_id,))
    conn.commit()
    conn.close()

    config_file = os.path.join(BRANCH_PATH, f"branch_{branch_id}", f"config_{branch_id}.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        config['Features']['Enable_Send'] = '1'
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    await update.message.reply_text(f"▶️ تم تشغيل الفرع {branch_id}\nبيرسل الفواتير المتأخرة الحين")

async def delete_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("اكتب: /del 78")
        return

    branch_id = context.args[0]
    keyboard = [
        [InlineKeyboardButton("✅ نعم احذف", callback_data=f"del_yes_{branch_id}"),
         InlineKeyboardButton("❌ لا", callback_data="del_no")]
    ]
    await update.message.reply_text(
        f"⚠️ **تأكيد حذف الفرع {branch_id}**\n\nبيحذف المجلد وكل البيانات!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("del_yes_"):
        branch_id = query.data.split("_")[2]
        # حذف من القاعدة
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM branches WHERE id=?", (branch_id,))
        conn.commit()
        conn.close()

        # حذف المجلد
        import shutil
        branch_folder = os.path.join(BRANCH_PATH, f"branch_{branch_id}")
        if os.path.exists(branch_folder):
            shutil.rmtree(branch_folder)

        await query.edit_message_text(f"🗑️ تم حذف الفرع {branch_id} نهائياً")
    else:
        await query.edit_message_text("❌ تم الإلغاء")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM branches")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM branches WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM branches WHERE status='pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM branches WHERE status='stopped'")
    stopped = c.fetchone()[0]
    conn.close()

    msg = f"📊 **إحصائيات المصنع**\n\n"
    msg += f"📦 إجمالي الفروع: {total}\n"
    msg += f"✅ المفعلة: {active}\n"
    msg += f"⏳ تنتظر تفعيل: {pending}\n"
    msg += f"⏸️ المتوقفة: {stopped}"

    await update.message.reply_text(msg)

async def notify_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("اكتب: /notify 78 الصيانة بكرا")
        return

    branch_id = context.args[0]
    message = ' '.join(context.args[1:])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM branches WHERE id=? AND status='active'", (branch_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        await update.message.reply_text(f"❌ الفرع {branch_id} مش مفعل أو ما ارتبط بعد")
        return

    try:
        await context.bot.send_message(chat_id=row[0], text=f"📢 **رسالة من الإدارة:**\n\n{message}")
        await update.message.reply_text(f"✅ تم الإرسال للفرع {branch_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {e}")

def main():
    if not TOKEN:
        print("❌ لازم تضيف TOKEN في Variables في Railway")
        return

    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_branch))
    app.add_handler(CommandHandler("list", list_branches))
    app.add_handler(CommandHandler("active", active_branches))
    app.add_handler(CommandHandler("pending", pending_branches))
    app.add_handler(CommandHandler("stop", stop_branch))
    app.add_handler(CommandHandler("start", start_branch))
    app.add_handler(CommandHandler("del", delete_branch))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("notify", notify_branch))
    app.add_handler(CallbackQueryHandler(button_handler))
    # يستقبل أي رسالة نص عادية عشان يفحص كود التفعيل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activation))
    print("✅ بوت التحكم شغال")
    app.run_polling()

if __name__ == '__main__':
    main()
