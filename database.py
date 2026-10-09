import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_name='chat_system.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        # اضافه کردن timeout برای جلوگیری از خطای database is locked در محیط های چند نخی
        conn = sqlite3.connect(self.db_name, timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # فعال‌سازی حالت WAL برای پشتیبانی از دسترسی همزمان (Concurrency) بالا
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                position TEXT NOT NULL,
                is_manager INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول پیام‌های عمومی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS public_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                formatted_message TEXT,
                file_path TEXT,
                file_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # جدول پیام‌های خصوصی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                sender_username TEXT NOT NULL,
                message TEXT NOT NULL,
                formatted_message TEXT,
                file_path TEXT,
                file_name TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        ''')
        
        # جدول اعلانات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id INTEGER NOT NULL,
                manager_name TEXT NOT NULL,
                message TEXT NOT NULL,
                formatted_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, username, password, first_name, last_name, position, is_manager=0):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password, first_name, last_name, position, is_manager)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password, first_name, last_name, position, is_manager))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return {'success': True, 'user_id': user_id}
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'نام کاربری قبلاً استفاده شده است'}
    
    def login_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'position': user['position'],
                    'is_manager': user['is_manager']
                }
            }
        return {'success': False, 'error': 'نام کاربری یا رمز عبور اشتباه است'}
    
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, first_name, last_name, position, is_manager FROM users ORDER BY first_name')
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def save_public_message(self, user_id, username, message, formatted_message, file_path=None, file_name=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO public_messages (user_id, username, message, formatted_message, file_path, file_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, message, formatted_message, file_path, file_name))
        conn.commit()
        message_id = cursor.lastrowid
        cursor.execute('SELECT * FROM public_messages WHERE id = ?', (message_id,))
        msg = dict(cursor.fetchone())
        conn.close()
        return msg
    
    def get_public_messages(self, limit=100):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM public_messages ORDER BY created_at DESC LIMIT ?', (limit,))
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return list(reversed(messages))
    
    def save_private_message(self, sender_id, receiver_id, sender_username, message, formatted_message, file_path=None, file_name=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO private_messages (sender_id, receiver_id, sender_username, message, formatted_message, file_path, file_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (sender_id, receiver_id, sender_username, message, formatted_message, file_path, file_name))
        conn.commit()
        message_id = cursor.lastrowid
        cursor.execute('SELECT * FROM private_messages WHERE id = ?', (message_id,))
        msg = dict(cursor.fetchone())
        conn.close()
        return msg
    
    def get_private_messages(self, user1_id, user2_id, limit=100):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM private_messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at DESC LIMIT ?
        ''', (user1_id, user2_id, user2_id, user1_id, limit))
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return list(reversed(messages))
    
    def mark_messages_as_read(self, receiver_id, sender_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE private_messages 
            SET is_read = 1 
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (receiver_id, sender_id))
        conn.commit()
        conn.close()
    
    def get_unread_count(self, receiver_id, sender_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as count FROM private_messages 
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (receiver_id, sender_id))
        count = cursor.fetchone()['count']
        conn.close()
        return count
    
    def save_announcement(self, manager_id, manager_name, message, formatted_message):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO announcements (manager_id, manager_name, message, formatted_message)
            VALUES (?, ?, ?, ?)
        ''', (manager_id, manager_name, message, formatted_message))
        conn.commit()
        announcement_id = cursor.lastrowid
        cursor.execute('SELECT * FROM announcements WHERE id = ?', (announcement_id,))
        announcement = dict(cursor.fetchone())
        conn.close()
        return announcement
    
    def get_announcements(self, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM announcements ORDER BY created_at DESC LIMIT ?', (limit,))
        announcements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return list(reversed(announcements))
    
    def search_messages(self, user_id, query):
        conn = self.get_connection()
        cursor = conn.cursor()
        search_term = f'%{query}%'
        
        # جستجو در پیام‌های خصوصی
        cursor.execute('''
            SELECT 'private' as type, sender_username, receiver_id, sender_id, message, created_at
            FROM private_messages 
            WHERE (sender_id = ? OR receiver_id = ?) AND message LIKE ?
            ORDER BY created_at DESC
        ''', (user_id, user_id, search_term))
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
