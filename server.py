from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from database import Database
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ایجاد پوشه آپلود
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=16 * 1024 * 1024)
db = Database()

# ذخیره کاربران آنلاین
online_users = {}  # {user_id: sid}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    result = db.register_user(
        data['username'],
        data['password'],
        data['first_name'],
        data['last_name'],
        data['position'],
        data.get('is_manager', 0)
    )
    return jsonify(result)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    result = db.login_user(data['username'], data['password'])
    return jsonify(result)

@app.route('/api/users', methods=['GET'])
def get_users():
    users = db.get_all_users()
    # اضافه کردن وضعیت آنلاین
    for user in users:
        user['online'] = user['id'] in online_users
    return jsonify(users)

@app.route('/api/public-messages', methods=['GET'])
def get_public_messages():
    messages = db.get_public_messages()
    return jsonify(messages)

@app.route('/api/private-messages/<int:user1_id>/<int:user2_id>', methods=['GET'])
def get_private_messages(user1_id, user2_id):
    messages = db.get_private_messages(user1_id, user2_id)
    return jsonify(messages)

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    announcements = db.get_announcements()
    return jsonify(announcements)

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    results = db.search_messages(data['user_id'], data['query'])
    return jsonify(results)

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    # حذف کاربر از لیست آنلاین‌ها
    user_id = None
    for uid, sid in online_users.items():
        if sid == request.sid:
            user_id = uid
            break
    
    if user_id:
        del online_users[user_id]
        emit('user_status', {'user_id': user_id, 'online': False}, broadcast=True)
    
    print(f'Client disconnected: {request.sid}')

@socketio.on('user_online')
def handle_user_online(data):
    user_id = data['user_id']
    online_users[user_id] = request.sid
    join_room(f'user_{user_id}')
    
    # اطلاع به همه کاربران
    emit('user_status', {'user_id': user_id, 'online': True}, broadcast=True)
    
    # ارسال لیست کاربران آنلاین به کاربر جدید
    emit('online_users', {'user_ids': list(online_users.keys())})

@socketio.on('typing')
def handle_typing(data):
    if data['type'] == 'private':
        # ارسال به کاربر مقصد
        receiver_id = data['receiver_id']
        if receiver_id in online_users:
            emit('user_typing', {
                'user_id': data['user_id'],
                'username': data['username'],
                'typing': data['typing']
            }, room=f'user_{receiver_id}')
    else:
        # ارسال به همه (چت عمومی)
        emit('user_typing', {
            'user_id': data['user_id'],
            'username': data['username'],
            'typing': data['typing']
        }, broadcast=True, include_self=False)

@socketio.on('send_public_message')
def handle_public_message(data):
    message = db.save_public_message(
        data['user_id'],
        data['username'],
        data['message'],
        data.get('formatted_message', data['message']),
        data.get('file_path'),
        data.get('file_name')
    )
    emit('new_public_message', message, broadcast=True)

@socketio.on('send_private_message')
def handle_private_message(data):
    message = db.save_private_message(
        data['sender_id'],
        data['receiver_id'],
        data['sender_username'],
        data['message'],
        data.get('formatted_message', data['message']),
        data.get('file_path'),
        data.get('file_name')
    )
    
    # ارسال به فرستنده
    emit('new_private_message', message)
    
    # ارسال به گیرنده اگر آنلاین است
    if data['receiver_id'] in online_users:
        emit('new_private_message', message, room=f'user_{data["receiver_id"]}')
    
    # ارسال تعداد پیام‌های خوانده نشده
    unread_count = db.get_unread_count(data['receiver_id'], data['sender_id'])
    if data['receiver_id'] in online_users:
        emit('unread_count', {
            'sender_id': data['sender_id'],
            'count': unread_count
        }, room=f'user_{data["receiver_id"]}')

@socketio.on('mark_read')
def handle_mark_read(data):
    db.mark_messages_as_read(data['receiver_id'], data['sender_id'])

@socketio.on('send_announcement')
def handle_announcement(data):
    announcement = db.save_announcement(
        data['manager_id'],
        data['manager_name'],
        data['message'],
        data.get('formatted_message', data['message'])
    )
    emit('new_announcement', announcement, broadcast=True)

@socketio.on('upload_file')
def handle_file_upload(data):
    try:
        file_data = data['file']
        filename = secure_filename(data['filename'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # ذخیره فایل
        import base64
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(file_data.split(',')[1]))
        
        emit('file_uploaded', {
            'success': True,
            'file_path': f'/uploads/{unique_filename}',
            'file_name': filename
        })
    except Exception as e:
        emit('file_uploaded', {'success': False, 'error': str(e)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5767, debug=True, use_reloader=False)
