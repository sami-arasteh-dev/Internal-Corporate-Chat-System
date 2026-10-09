# Internal Corporate Chat System

A lightweight, real-time internal communication platform built with Python, Flask, and Socket.IO. Designed for small to medium-sized enterprises, this system facilitates public discussions, private messaging, and manager-led announcements with file sharing capabilities.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Database Schema](#-database-schema)
- [API & Socket.IO Endpoints](#-api--socketio-endpoints)
- [Security Notes](#-security-notes)
- [License](#-license)

## ✨ Features

*   **Authentication:** User registration and login system with role management (Manager vs. Employee).
*   **Real-Time Communication:**
    *   Public chat room visible to all users.
    *   Private 1-on-1 messaging with read receipts.
    *   Typing indicators for both public and private chats.
    *   Online/Offline user status tracking.
*   **Announcements:** Managers can broadcast messages to all users.
*   **File Sharing:** Support for uploading and sharing files (images, documents) up to 16MB.
*   **Rich Text Editor:** Basic formatting options (Bold, Italic, Underline, Font, Color, Alignment) for messages.
*   **Search:** Search functionality across private and public message history.
*   **Concurrency:** Optimized for concurrent access using SQLite WAL mode.

## 🏗 Architecture & Tech Stack

The application follows a standard MVC-like pattern adapted for a Flask-SocketIO application:

*   **Backend:** Python 3.x
*   **Web Framework:** Flask
*   **Real-Time Engine:** Flask-SocketIO
*   **Database:** SQLite (via `sqlite3` standard library)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript
*   **File Handling:** `werkzeug.utils.secure_filename` for safe file storage

## 📦 Prerequisites

*   Python 3.6 or higher
*   `pip` (Python Package Installer)

## 🛠 Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd chat-system
    ```

2.  **Install dependencies:**
    ```bash
    pip install flask flask-socketio
    ```
    *Note: The project uses standard libraries for database (`sqlite3`) and file handling, so no additional packages are strictly required for those components.*

3.  **Run the application:**
    ```bash
    python server.py
    ```

4.  **Access the application:**
    Open your browser and navigate to `http://localhost:5767`.

## ⚙️ Configuration

The application configuration is located in `server.py`. Key settings include:

*   **Secret Key:** Change `app.config['SECRET_KEY']` to a secure, random string for production use.
*   **Upload Folder:** Files are stored in the `uploads/` directory. Ensure this directory has write permissions.
*   **Max File Size:** Set via `app.config['MAX_CONTENT_LENGTH']` (default: 16MB).
*   **Database:** The SQLite database (`chat_system.db`) is created automatically in the root directory upon first run.
*   **Server Host/Port:** The server runs on `0.0.0.0:5767` by default. Modify `socketio.run()` arguments in `server.py` to change this.

## 🚀 Usage

### 1. Registration & Login
*   Navigate to the home page.
*   Click "Register" to create a new account.
*   **Manager Role:** Check the "I am a manager" checkbox during registration to enable announcement privileges.
*   Log in with your credentials.

### 2. Public Chat
*   The main chat area displays public messages.
*   Use the toolbar to format text or attach files.
*   See typing indicators of other users in real-time.

### 3. Private Messaging
*   Select a user from the "Colleagues" sidebar to open a private chat.
*   Unread message counts are displayed and updated automatically.
*   Messages are marked as read automatically when viewed.

### 4. Announcements (Managers Only)
*   Managers see an "Announcements" section in the sidebar.
*   Type a message and click "Send Announcement" to broadcast it to all users.

### 5. Search
*   Use the search bar in the sidebar to find messages by keyword. Results include both public and private messages involving the current user.

## 🗄 Database Schema

The system uses a single SQLite database with the following tables:

*   **`users`**: Stores user credentials and profile info (`id`, `username`, `password`, `first_name`, `last_name`, `position`, `is_manager`).
*   **`public_messages`**: Stores messages sent to the general channel (`id`, `user_id`, `username`, `message`, `file_path`, `created_at`).
*   **`private_messages`**: Stores 1-on-1 messages (`id`, `sender_id`, `receiver_id`, `message`, `is_read`, `created_at`).
*   **`announcements`**: Stores manager broadcasts (`id`, `manager_id`, `manager_name`, `message`, `created_at`).

## 🔌 API & Socket.IO Endpoints

### REST API (JSON)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/register` | Register a new user. |
| `POST` | `/api/login` | Authenticate user. |
| `GET` | `/api/users` | Get list of all users (with online status). |
| `GET` | `/api/public-messages` | Retrieve public chat history. |
| `GET` | `/api/private-messages/<u1>/<u2>` | Retrieve private messages between two users. |
| `GET` | `/api/announcements` | Retrieve announcement history. |
| `POST` | `/api/search` | Search messages by query. |

### Socket.IO Events

| Event | Direction | Description |
| :--- | :--- | :--- |
| `connect` | Client → Server | Establishes WebSocket connection. |
| `disconnect` | Client → Server | Handles user disconnection. |
| `user_online` | Client → Server | Registers user as online. |
| `typing` | Client → Server | Broadcasts typing status. |
| `send_public_message` | Client → Server | Sends a message to the public channel. |
| `send_private_message` | Client → Server | Sends a message to a specific user. |
| `mark_read` | Client → Server | Marks messages as read. |
| `send_announcement` | Client → Server | Sends an announcement (Manager only). |
| `upload_file` | Client → Server | Uploads a file via base64 encoding. |

## 🔒 Security Notes

*   **Password Storage:** Currently, passwords are stored in plain text. **For production use, implement password hashing (e.g., using `werkzeug.security` or `bcrypt`).**
*   **Secret Key:** The default `SECRET_KEY` is insecure. Always change this in production.
*   **File Uploads:** The system uses `secure_filename` to prevent directory traversal attacks. However, validate file types and sizes strictly in production.
*   **CORS:** CORS is enabled for all origins (`*`). Restrict this to your domain in production.

## 📄 License

This project is provided as-is. For commercial use or further development, please consult the project owner.
