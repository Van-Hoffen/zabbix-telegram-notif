#!/usr/bin/env python3
"""
Telegram notification handler for Zabbix with message cleanup functionality.
This script handles sending notifications and cleaning up resolved problem messages.
"""

import os
import sys
import json
import requests
import sqlite3
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/zabbix_telegram_handler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramMessageManager:
    """
    Manages Telegram messages for Zabbix notifications.
    Handles sending messages and deleting resolved problem messages.
    """
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.db_path = "/tmp/telegram_messages.db"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database to store message mappings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table to store message mappings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zabbix_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                message_id INTEGER,
                problem_key TEXT,
                status TEXT,  -- 'active' or 'resolved'
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_message_mapping(self, event_id, message_id, problem_key, status):
        """Save the mapping between Zabbix event and Telegram message ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO zabbix_messages 
                (event_id, message_id, problem_key, status, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (event_id, message_id, problem_key, status))
            
            conn.commit()
            logger.info(f"Saved message mapping: event_id={event_id}, message_id={message_id}")
        except Exception as e:
            logger.error(f"Failed to save message mapping: {e}")
        finally:
            conn.close()
    
    def get_active_problem_message(self, problem_key):
        """Get the message ID of an active problem for the given key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT message_id FROM zabbix_messages
                WHERE problem_key = ? AND status = 'active'
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (problem_key,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get active problem message: {e}")
            return None
        finally:
            conn.close()
    
    def update_message_status(self, event_id, status):
        """Update the status of a stored message."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE zabbix_messages
                SET status = ?, timestamp = CURRENT_TIMESTAMP
                WHERE event_id = ?
            ''', (status, event_id))
            
            conn.commit()
            logger.info(f"Updated message status: event_id={event_id}, status={status}")
        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
        finally:
            conn.close()
    
    def delete_message(self, message_id):
        """Delete a message from Telegram chat."""
        url = f"{self.api_url}/deleteMessage"
        payload = {
            "chat_id": self.chat_id,
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Successfully deleted message: {message_id}")
                return True
            else:
                logger.error(f"Failed to delete message {message_id}: {result.get('description')}")
                return False
        except Exception as e:
            logger.error(f"Exception occurred while deleting message {message_id}: {e}")
            return False
    
    def send_message(self, text, parse_mode="HTML"):
        """Send a message to Telegram chat."""
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                message_id = result["result"]["message_id"]
                logger.info(f"Successfully sent message: {message_id}")
                return message_id
            else:
                logger.error(f"Failed to send message: {result.get('description')}")
                return None
        except Exception as e:
            logger.error(f"Exception occurred while sending message: {e}")
            return None

def main():
    """
    Main function to handle Zabbix notification.
    Expected arguments:
    sys.argv[1] - Event ID
    sys.argv[2] - Problem Key (unique identifier for the problem)
    sys.argv[3] - Message text
    sys.argv[4] - Status ('PROBLEM' or 'OK' for resolved)
    """
    
    if len(sys.argv) < 5:
        print("Usage: zabbix_telegram_handler.py <event_id> <problem_key> <message_text> <status>")
        sys.exit(1)
    
    event_id = sys.argv[1]
    problem_key = sys.argv[2]
    message_text = sys.argv[3]
    status = sys.argv[4]  # PROBLEM or OK
    
    # Get configuration from environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables")
        sys.exit(1)
    
    # Initialize message manager
    manager = TelegramMessageManager(bot_token, chat_id)
    
    if status == "OK":
        # This is a resolution message - find and delete the original problem message
        active_message_id = manager.get_active_problem_message(problem_key)
        
        if active_message_id:
            # Delete the original problem message
            success = manager.delete_message(active_message_id)
            
            if success:
                # Update the stored status to resolved
                manager.update_message_status(event_id, "resolved")
                
                # Also update the original problem's status
                manager.update_message_status(f"PROBLEM_{problem_key}", "resolved")
                
                print(f"Deleted original problem message {active_message_id} for problem {problem_key}")
            else:
                print(f"Failed to delete original problem message {active_message_id}")
        else:
            print(f"No active problem message found for {problem_key}, sending resolution notification anyway")
            # Even if we don't find the original message, we might still want to send a resolution notice
            # Or just log that the problem was resolved
            message_id = manager.send_message(message_text)
            if message_id:
                manager.save_message_mapping(event_id, message_id, problem_key, "resolved")
    elif status == "PROBLEM":
        # This is a problem notification - send the message and save the mapping
        message_id = manager.send_message(message_text)
        if message_id:
            manager.save_message_mapping(event_id, message_id, problem_key, "active")
            print(f"Sent problem message {message_id} for event {event_id}")
        else:
            print(f"Failed to send problem message for event {event_id}")
    else:
        logger.error(f"Unknown status: {status}")
        sys.exit(1)

if __name__ == "__main__":
    main()