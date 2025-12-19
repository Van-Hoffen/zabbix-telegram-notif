#!/bin/bash

# Установочный скрипт для настройки Telegram уведомлений Zabbix с очисткой сообщений

set -e  # Выход при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HANDLER_SCRIPT="zabbix_telegram_handler.py"
CONFIG_FILE="zabbix_telegram_config.md"

echo "Установка Zabbix Telegram уведомлений с очисткой сообщений..."

# Проверяем, запущен ли скрипт из правильной директории
if [ ! -f "$HANDLER_SCRIPT" ]; then
    echo "Ошибка: Файл $HANDLER_SCRIPT не найден в текущей директории."
    echo "Запустите скрипт из директории, где находится файл $HANDLER_SCRIPT"
    exit 1
fi

# Устанавливаем зависимости Python
echo "Устанавливаем зависимости Python..."
if command -v pip3 &>/dev/null; then
    pip3 install requests
else
    echo "pip3 не найден, пытаемся установить через apt..."
    sudo apt-get update && sudo apt-get install -y python3-pip
    pip3 install requests
fi

# Определяем возможную директорию установки
ZABBIX_ALERTSCRIPTS_DIRS=("/usr/lib/zabbix/alertscripts" "/usr/local/share/zabbix/alertscripts" "/opt/zabbix/alertscripts")

ZABBIX_DIR=""
for dir in "${ZABBIX_ALERTSCRIPTS_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        ZABBIX_DIR="$dir"
        break
    fi
done

if [ -z "$ZABBIX_DIR" ]; then
    echo "Не удалось найти стандартную директорию alertscripts Zabbix."
    read -p "Введите путь к директории alertscripts Zabbix: " ZABBIX_DIR
    if [ ! -d "$ZABBIX_DIR" ]; then
        echo "Директория $ZABBIX_DIR не существует."
        exit 1
    fi
fi

echo "Найдена директория Zabbix alertscripts: $ZABBIX_DIR"

# Копируем скрипт в директорию Zabbix
echo "Копируем скрипт в $ZABBIX_DIR..."
sudo cp "$HANDLER_SCRIPT" "$ZABBIX_DIR/"
sudo chmod +x "$ZABBIX_DIR/$HANDLER_SCRIPT"

echo "Скрипт успешно установлен в $ZABBIX_DIR/$HANDLER_SCRIPT"

# Предлагаем пользователю настроить переменные окружения
echo ""
echo "Теперь необходимо настроить переменные окружения для работы скрипта:"
echo "1. Создайте Telegram бот через @BotFather и получите токен"
echo "2. Определите ID чата, в который будут отправляться уведомления"
echo ""
echo "После получения этих данных выполните следующие команды:"
echo "  export TELEGRAM_BOT_TOKEN='ваш_токен_бота'"
echo "  export TELEGRAM_CHAT_ID='ваш_chat_id'"
echo ""
echo "Для постоянной настройки добавьте эти переменные в /etc/environment или в systemd сервис zabbix:"
echo "  sudo sh -c 'echo \"TELEGRAM_BOT_TOKEN=ваш_токен_бота\" >> /etc/environment'"
echo "  sudo sh -c 'echo \"TELEGRAM_CHAT_ID=ваш_chat_id\" >> /etc/environment'"

# Копируем конфигурационный файл в домашнюю директорию пользователя
cp "$CONFIG_FILE" ~/
echo ""
echo "Файл инструкций $CONFIG_FILE скопирован в вашу домашнюю директорию ~/ для ознакомления."

echo ""
echo "Установка завершена!"
echo ""
echo "Для проверки работоспособности выполните тестовый запуск:"
echo "TELEGRAM_BOT_TOKEN='ваш_токен' TELEGRAM_CHAT_ID='ваш_chat_id' $ZABBIX_DIR/$HANDLER_SCRIPT 'test_event' 'test_key' 'Тестовое сообщение' 'PROBLEM'"