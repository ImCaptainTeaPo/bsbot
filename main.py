
import json
import threading
import time
from telegram.ext import Updater, CommandHandler
from telegram import ParseMode
from config import TOKEN, ADMIN_ID
import requests
import datetime

USERS_FILE = 'users.json'
EVENTS_FILE = 'events.json'

# Загрузка событий
def load_events():
    try:
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить события: {e}")
        return []

# Загрузка пользователей
def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

# Сохранение пользователей
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# Сохранение событий
def save_events(events):
    with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

# Команды
def start(update, context):
    update.message.reply_text("👋 Привет! Я напомню тебе о событиях Blood and Soul.\nНапиши /help для списка команд.")

def help_command(update, context):
    update.message.reply_text(
        "📜 Команды:\n"
        "/subscribe — включить все уведомления\n"
        "/unsubscribe — отключить все уведомления\n"
        "/events — список событий на сутки\n"
        "/enable <название> — включить уведомление\n"
        "/disable <название> — отключить\n"
        "/my — твои активные напоминания\n"
        "/add_event \"Название\" ВРЕМЯ — добавить событие (админ)\n"
        "/edit_event \"Старое\" \"Новое\" ВРЕМЯ — изменить событие (админ)\n"
        "/delete_event \"Название\" — удалить событие (админ)\n"
        "/reset — сброс настроек")

def subscribe(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    events = load_events()
    users[user_id] = [event["name"] for event in events]
    save_users(users)
    update.message.reply_text("✅ Подписка оформлена. Все события активированы.")

def unsubscribe(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    users[user_id] = []
    save_users(users)
    update.message.reply_text("❌ Все уведомления отключены.")

def events(update, context):
    events = load_events()
    if not events:
        update.message.reply_text("📭 Список событий пуст.")
        return

    def get_sort_key(e):
        if "time" in e:
            return e["time"]
        elif "start" in e:
            return e["start"]
        else:
            return "99:99"  # на крайний случай

    # Сортировка
    sorted_events = sorted(events, key=get_sort_key)

    message = "🗓 <b>События на сутки:</b>\n\n"
    for e in sorted_events:
        if "time" in e:
            message += f"{e['time']} — {e['name']}\n"
        elif "start" in e and "end" in e:
            message += f"{e['start']}–{e['end']} — {e['name']}\n"

    update.message.reply_text(message.strip(), parse_mode=ParseMode.HTML)


def my(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    active = users.get(user_id, [])
    if not active:
        update.message.reply_text("❌ У тебя нет включённых уведомлений.")
    else:
        msg = "🔔 Включённые уведомления:\n" + "\n".join(f"• {name}" for name in active)
        update.message.reply_text(msg)

def enable(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    events = load_events()
    name = " ".join(context.args).strip()
    all_names = [e["name"] for e in events]
    if name not in all_names:
        update.message.reply_text("❌ Событие не найдено.")
        return
    users.setdefault(user_id, [])
    if name not in users[user_id]:
        users[user_id].append(name)
    save_users(users)
    update.message.reply_text(f"✅ Напоминание для «{name}» включено.")

def disable(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    name = " ".join(context.args).strip()
    if name in users.get(user_id, []):
        users[user_id].remove(name)
        save_users(users)
        update.message.reply_text(f"❌ Напоминание для «{name}» отключено.")
    else:
        update.message.reply_text("⚠️ У тебя оно и так было отключено.")

def reset(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()
    users[user_id] = []
    save_users(users)
    update.message.reply_text("🔄 Настройки сброшены.")

def is_admin(user_id):
    return user_id == ADMIN_ID

def add_event(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔ Только администратор может добавлять события.")
        return
    try:
        name = context.args[0].strip('"“”')
        time_str = context.args[1]
        events = load_events()
        events.append({"name": name, "time": time_str})
        save_events(events)
        update.message.reply_text(f"✅ Событие «{name}» в {time_str} добавлено.")
    except:
        update.message.reply_text('❌ Формат: /add_event "Название" ВРЕМЯ')

def edit_event(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔ Только админ может редактировать события.")
        return
    try:
        old_name = context.args[0].strip('"“”')
        new_name = context.args[1].strip('"“”')
        new_time = context.args[2]
        events = load_events()
        for e in events:
            if e["name"] == old_name:
                e["name"] = new_name
                e["time"] = new_time
                save_events(events)
                update.message.reply_text("✅ Событие обновлено.")
                return
        update.message.reply_text("❌ Событие не найдено.")
    except:
        update.message.reply_text('❌ Формат: /edit_event "Старое" "Новое" ВРЕМЯ')

def delete_event(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔ Только админ может удалять события.")
        return
    try:
        name = " ".join(context.args).strip('"“”')
        events = load_events()
        events = [e for e in events if e["name"] != name]
        save_events(events)
        update.message.reply_text(f"🗑 Событие «{name}» удалено.")
    except:
        update.message.reply_text("❌ Не удалось удалить событие.")



# 🔔 Планировщик уведомлений
def notification_loop(bot):
    while True:
        now = time.strftime("%H:%M")
        print(f"[Планировщик] Сейчас: {now}")
        events = load_events()
        users = load_users()

        for event in events:
            try:
                name = event.get("name")

                if "time" in event:
                    # Одиночное событие
                    h, m = map(int, event["time"].split(":"))
                    total_minutes = h * 60 + m - 10
                    notify_time = f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
                elif "start" in event:
                    # Продолжительное событие — уведомляем перед началом
                    h, m = map(int, event["start"].split(":"))
                    total_minutes = h * 60 + m - 10
                    notify_time = f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
                else:
                    continue

                if now == notify_time:
                    print(f"[Уведомление] Через 10 минут: {name}")
                    for user_id, enabled in users.items():
                        if name in enabled:
                            bot.send_message(chat_id=user_id, text=f"⏰ Через 10 минут: {name}")
            except Exception as e:
                print(f"[Ошибка уведомления]: {e}")
        time.sleep(60)


def self_ping_loop():
    url = "https://<ТВОЙ-АДРЕС>.onrender.com"  # вставь позже
    while True:
        try:
            response = requests.get(url)
            print(f"[Самопинг] {datetime.datetime.now().strftime('%H:%M:%S')} — статус {response.status_code}")
        except Exception as e:
            print(f"[Самопинг] Ошибка: {e}")
        time.sleep(600)  # каждые 10 минут

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))
    dp.add_handler(CommandHandler("events", events))
    dp.add_handler(CommandHandler("my", my))
    dp.add_handler(CommandHandler("enable", enable))
    dp.add_handler(CommandHandler("disable", disable))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CommandHandler("add_event", add_event))
    dp.add_handler(CommandHandler("edit_event", edit_event))
    dp.add_handler(CommandHandler("delete_event", delete_event))

    print("✅ Бот запущен...")

    # 🔁 Запуск планировщика уведомлений
    notify_thread = threading.Thread(target=notification_loop, args=(updater.bot,), daemon=True)
    notify_thread.start()

    # 🔁 Запуск самопинга
    ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
    ping_thread.start()

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
