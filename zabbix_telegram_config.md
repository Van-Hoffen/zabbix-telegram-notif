# Настройка Zabbix для использования Telegram-уведомлений с очисткой сообщений

## Установка и настройка

1. Убедитесь, что скрипт `zabbix_telegram_handler.py` находится в доступной директории на сервере Zabbix (например, `/usr/lib/zabbix/alertscripts/`).

2. Установите права на выполнение:
```bash
chmod +x /usr/lib/zabbix/alertscripts/zabbix_telegram_handler.py
```

3. Установите зависимости Python:
```bash
pip3 install requests
```

## Настройка вебхука Telegram бота

1. Создайте Telegram бот через @BotFather
2. Получите токен бота
3. Установите переменные окружения на сервере Zabbix:
```bash
export TELEGRAM_BOT_TOKEN="ваш_токен_бота"
export TELEGRAM_CHAT_ID="ID_чата_для_уведомлений"
```

Рекомендуется добавить эти переменные в системный профиль, например в `/etc/environment` или в файл сервиса Zabbix.

## Настройка в Zabbix

### 1. Добавление нового типа медиа

1. Перейдите в Administration → Media Types
2. Нажмите "Create media type"
3. Заполните поля:
   - Name: "Telegram with Cleanup"
   - Type: Script
   - Script name: `zabbix_telegram_handler.py`
   - Script parameters:
     - `{ALERT.SENDTO}` (если используется для указания чата, иначе можно опустить)
     - `{EVENT.ID}`
     - `{ITEM.KEY1}` или уникальный ключ проблемы
     - `{ALERT.MESSAGE}`
     - `{EVENT.STATUS}`

### 2. Настройка действий (Actions)

Создайте новое действие (Configuration → Actions):

**Name:** Telegram Notifications with Cleanup

**Conditions:**
- Maintenance status not in maintenance
- Event type = Problem or Recovery

**Operations:**
- Operation type: Send message
- Send to: ваш Telegram ID
- Subject: (оставьте пустым или используйте для дополнительной информации)
- Message:
```
{HOST.NAME} - {TRIGGER.SEVERITY} - {TRIGGER.NAME}
Status: {EVENT.STATUS}
Time: {EVENT.TIME}
```

## Параметры вызова скрипта

Скрипт принимает следующие параметры:
- `$1` - Event ID
- `$2` - Problem Key (уникальный идентификатор проблемы)
- `$3` - Текст сообщения
- `$4` - Статус события (`PROBLEM` или `OK`)

## Примеры использования в шаблонах уведомлений

Для события проблемы:
```
Event ID: {EVENT.ID}
Problem Key: {ITEM.KEY1}/{TRIGGER.ID}
Message: {HOST.NAME} - {TRIGGER.SEVERITY} - {TRIGGER.NAME}
Status: PROBLEM
```

Для события восстановления:
```
Event ID: {EVENT.RECOVERY.ID}
Problem Key: {ITEM.KEY1}/{TRIGGER.ID}
Message: {HOST.NAME} - {TRIGGER.SEVERITY} - {TRIGGER.NAME} - RESOLVED
Status: OK
```

## Важные замечания

1. Для корректной работы очистки сообщений важно использовать стабильный уникальный идентификатор проблемы (Problem Key). Рекомендуется использовать комбинацию `{ITEM.KEY1}/{TRIGGER.ID}` или другое уникальное значение.

2. Скрипт хранит сопоставления сообщений в локальной базе данных SQLite по пути `/tmp/telegram_messages.db`.

3. Убедитесь, что пользователь, от имени которого работает Zabbix, имеет доступ к базе данных и к скрипту.

4. В целях безопасности рекомендуется ограничить права доступа к файлу базы данных:
```bash
chmod 600 /tmp/telegram_messages.db
chown zabbix:zabbix /tmp/telegram_messages.db
```

## Тестирование

Для тестирования работы скрипта можно выполнить его вручную с тестовыми параметрами:
```bash
TELEGRAM_BOT_TOKEN="ваш_токен" TELEGRAM_CHAT_ID="ваш_chat_id" \
/usr/lib/zabbix/alertscripts/zabbix_telegram_handler.py \
"test_event_123" "test_problem_key" "Test message" "PROBLEM"

TELEGRAM_BOT_TOKEN="ваш_токен" TELEGRAM_CHAT_ID="ваш_chat_id" \
/usr/lib/zabbix/alertscripts/zabbix_telegram_handler.py \
"test_event_123_resolved" "test_problem_key" "Test message resolved" "OK"
```