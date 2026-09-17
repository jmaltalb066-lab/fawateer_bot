import os
import json
import datetime
import calendar
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ============ الإعدادات ============
TOKEN = os.environ.get('TOKEN')
OWNER_CHAT_ID = os.environ.get('OWNER_CHAT_ID')
DB_FILE = 'restaurants.json'
SAVE_PATH = '/tmp/fawateer' # لينكس بدل C:\الفواتير

os.makedirs(SAVE_PATH, exist_ok=True)

# ============ دوال قاعدة البيانات ============
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_expiry_date(days):
    return (datetime.date.today() + datetime.timedelta(days=int(days))).isoformat()

# ============ أوامر بوت التحكم ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID:
        await update.message.reply_text(
            f'اهلا بك. رقم الـ Chat ID حقك هو:\n\n`{update.effective_chat.id}`\n\nارسله لصاحب النظام عشان يفعلك',
            parse_mode='Markdown'
        )
        return

    text = """
🔥 *بوت التحكم - نظام الفواتير*

`/add ChatID اسم_المطعم 30` → اضافة مطعم
`/stop اسم_المطعم` → ايقاف الارسال
`/run اسم_المطعم` → تشغيل الارسال
`/paid اسم_المطعم 30` → تجديد اشتراك
`/devices اسم_المطعم 3` → توليد ملفات للاجهزة
`/alert` → تنبيه الاشتراكات المنتهية
`/log اسم_المطعم` → تقرير المطعم
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        chat_id, name, days = context.args[0], context.args[1], int(context.args[2])
        db = load_db()
        db[name] = {
            'owner_chat_id': chat_id,
            'status': 'active',
            'expiry': get_expiry_date(days),
            'devices': 1,
            'total_invoices': 0,
            'total_amount': 0.0,
            'today_invoices': 0,
            'today_amount': 0.0,
            'month_invoices': 0,
            'month_amount': 0.0,
            'created_at': datetime.date.today().isoformat()
        }
        save_db(db)
        config = {'restaurant_name': name, 'bot_token': TOKEN, 'owner_chat_id': chat_id, 'status': 'active'}
        filename = f'config_{name}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=f'✅ تم اضافة {name}\nحمّل هذا الملف على جهاز المطعم'
        )
        os.remove(filename)
    except Exception as e:
        await update.message.reply_text(f'غلط بالصيغة\nمثال: /add 123456789 مطعم_الخليج 30\n\nالخطأ: {e}')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        name = context.args[0]
        db = load_db()
        if name not in db:
            await update.message.reply_text('المطعم غير موجود')
            return
        db[name]['status'] = 'stopped'
        save_db(db)
        await update.message.reply_text(f'⛔ تم ايقاف {name}')
    except:
        await update.message.reply_text('مثال: /stop مطعم_الخليج')

async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        name = context.args[0]
        db = load_db()
        if name not in db:
            await update.message.reply_text('المطعم غير موجود')
            return
        db[name]['status'] = 'active'
        save_db(db)
        await update.message.reply_text(f'✅ تم تشغيل {name}')
    except:
        await update.message.reply_text('مثال: /run مطعم_الخليج')

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        name, days = context.args[0], int(context.args[1])
        db = load_db()
        if name not in db:
            await update.message.reply_text('المطعم غير موجود')
            return
        db[name]['expiry'] = get_expiry_date(days)
        db[name]['status'] = 'active'
        save_db(db)
        await update.message.reply_text(f'💰 تم تجديد {name} لمدة {days} يوم\nينتهي: {db[name]["expiry"]}')
    except:
        await update.message.reply_text('مثال: /paid مطعم_الخليج 30')

async def devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        name, count = context.args[0], int(context.args[1])
        db = load_db()
        if name not in db:
            await update.message.reply_text('المطعم غير موجود')
            return
        db[name]['devices'] = count
        save_db(db)
        config = {
            'restaurant_name': name,
            'bot_token': TOKEN,
            'owner_chat_id': db[name]['owner_chat_id'],
            'status': db[name]['status']
        }
        for i in range(1, count + 1):
            filename = f'config_{name}_جهاز{i}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            await update.message.reply_document(document=open(filename, 'rb'))
            os.remove(filename)
        await update.message.reply_text(f'تم توليد {count} ملفات')
    except:
        await update.message.reply_text('مثال: /devices مطعم_الخليج 3')

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    db = load_db()
    today = datetime.date.today()
    msg = "🔔 *اشتراكات قربت تنتهي:*\n\n"
    found = False
    for name, data in db.items():
        days_left = (datetime.date.fromisoformat(data['expiry']) - today).days
        if 0 <= days_left <= 3:
            found = True
            msg += f'{name} | باقي {days_left} يوم\n`/stop {name}`\n\n'
    await update.message.reply_text(msg if found else '✅ كل الاشتراكات تمام', parse_mode='Markdown')

async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id)!= OWNER_CHAT_ID: return
    try:
        name = context.args[0]
        db = load_db()
        if name not in db:
            await update.message.reply_text('المطعم غير موجود')
            return
        d = db[name]
        status = 'شغال ✅' if d['status'] == 'active' else 'متوقف ⛔'
        msg = f"""📊 *{name}*
الحالة: {status}
الاجهزة: {d['devices']}
فواتير اليوم: {d['today_invoices']} | {d['today_amount']:.0f} ريال
فواتير الشهر: {d['month_invoices']} | {d['month_amount']:.0f} ريال
الاجمالي: {d['total_invoices']} | {d['total_amount']:.0f} ريال
ينتهي: {d['expiry']}"""
        await update.message.reply_text(msg, parse_mode='Markdown')
    except:
        await update.message.reply_text('مثال: /log مطعم_الخليج')

async def update_from_exe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name, amount = context.args[0], float(context.args[1])
        db = load_db()
        if name in db and db[name]['status'] == 'active':
            db[name]['total_invoices'] += 1
            db[name]['total_amount'] += amount
            db[name]['today_invoices'] += 1
            db[name]['today_amount'] += amount
            db[name]['month_invoices'] += 1
            db[name]['month_amount'] += amount
            save_db(db)
    except:
        pass

# ============ التقارير التلقائية ============
async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    for name, data in db.items():
        if data['status'] == 'active' and data['today_invoices'] > 0:
            msg = f"📊 تقرير اليوم - {name}\nعدد الفواتير: {data['today_invoices']}\nالمجموع: {data['today_amount']:.0f} ريال"
            try:
                await context.bot.send_message(chat_id=data['owner_chat_id'], text=msg)
            except:
                pass
            data['today_invoices'] = 0
            data['today_amount'] = 0.0
    save_db(db)

async def monthly_report(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    for name, data in db.items():
        if data['status'] == 'active' and data['month_invoices'] > 0:
            msg = f"📊 تقرير الشهر - {name}\nعدد الفواتير: {data['month_invoices']}\nالمجموع: {data['month_amount']:.0f} ريال"
            try:
                await context.bot.send_message(chat_id=data['owner_chat_id'], text=msg)
            except:
                pass
            data['month_invoices'] = 0
            data['month_amount'] = 0.0
    save_db(db)

async def expiry_check(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    today = datetime.date.today()
    for name, data in db.items():
        days_left = (datetime.date.fromisoformat(data['expiry']) - today).days
        if days_left == 3:
            msg = f"⚠️ تنبيه: اشتراك {name} بينتهي بعد 3 ايام\nتاريخ الانتهاء: {data['expiry']}\n/stop {name}"
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg)
        elif days_left <= 0 and data['status'] == 'active':
            data['status'] = 'stopped'
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f'⛔ انتهى اشتراك {name} وتم ايقافه تلقائي'
            )
    save_db(db)

# ============ التشغيل ============
if __name__ == '__main__':
    if not TOKEN or not OWNER_CHAT_ID:
        print('❌ لازم تضيف TOKEN و OWNER_CHAT_ID في متغيرات البيئة')
        exit(1)

    # شيلنا مراقب الطابعات لأنه ويندوز فقط
    # spool_thread = threading.Thread(target=run_spool_monitor, daemon=True)
    # spool_thread.start()

    app = ApplicationBuilder().token(TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add))
    app.add_handler(CommandHandler('stop', stop))
    app.add_handler(CommandHandler('run', run_cmd))
    app.add_handler(CommandHandler('paid', paid))
    app.add_handler(CommandHandler('devices', devices))
    app.add_handler(CommandHandler('alert', alert))
    app.add_handler(CommandHandler('log', log))
    app.add_handler(CommandHandler('update', update_from_exe))

    job_queue.run_daily(daily_report, time=datetime.time(23, 59))
    job_queue.run_monthly(monthly_report, day=calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1], time=datetime.time(23, 50))
    job_queue.run_daily(expiry_check, time=datetime.time(10, 0))

    print('✅ فواتير بوت شغال...')
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, close_loop=False)
