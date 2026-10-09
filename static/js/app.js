let socket = null;
let currentUser = null;
let currentChat = "public";
let openChats = {};

function showLogin() {
    document.getElementById("register-form").style.display = "none";
    document.getElementById("login-form").style.display = "block";
}

function showRegister() {
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form").style.display = "block";
}

function register() {
    const username = document.getElementById("reg-username").value;
    const password = document.getElementById("reg-password").value;
    const firstname = document.getElementById("reg-firstname").value;
    const lastname = document.getElementById("reg-lastname").value;
    const position = document.getElementById("reg-position").value;
    const isManager = document.getElementById("reg-manager").checked ? 1 : 0;

    fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            username: username,
            password: password,
            first_name: firstname,
            last_name: lastname,
            position: position,
            is_manager: isManager
        })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            document.getElementById("login-username").value = username;
            document.getElementById("login-password").value = password;
            login();
        } else {
            document.getElementById("auth-error").innerText = d.error;
        }
    })
    .catch(err => {
        document.getElementById("auth-error").innerText = "خطا در ارتباط با سرور";
        console.error(err);
    });
}

function login() {
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            initUser(d.user);
        } else {
            document.getElementById("auth-error").innerText = d.error;
        }
    })
    .catch(err => {
        document.getElementById("auth-error").innerText = "خطا در ارتباط با سرور";
        console.error(err);
    });
}

function initUser(user) {
    currentUser = user;
    localStorage.setItem("chat_user", JSON.stringify(user));
    
    document.getElementById("auth-page").style.display = "none";
    document.getElementById("chat-page").style.display = "flex";

    document.getElementById("current-user-name").innerText = user.first_name + " " + user.last_name;
    document.getElementById("current-user-position").innerText = user.position;

    if (user.is_manager) {
        document.getElementById("announcement-input").style.display = "block";
    }

    connectSocket();
    loadUsers();
    loadPublicMessages();
    loadAnnouncements();
}

function connectSocket() {
    socket = io();

    socket.on("connect", () => {
        console.log("Connected to server");
        socket.emit("user_online", { user_id: currentUser.id });
    });

    socket.on("new_public_message", (msg) => {
        renderMessage("public", msg);
    });

    socket.on("new_private_message", (msg) => {
        let chatId = msg.sender_id == currentUser.id ? msg.receiver_id : msg.sender_id;
        if (!openChats[chatId]) {
            let username = msg.sender_id == currentUser.id ? "شما" : msg.sender_username;
            createPrivateTab(chatId, username);
        }
        renderMessage("private_" + chatId, msg);
    });

    socket.on("user_status", (data) => {
        updateUserStatus(data.user_id, data.online);
    });

    socket.on("new_announcement", (announcement) => {
        loadAnnouncements();
    });
}

function loadUsers() {
    fetch("/api/users")
        .then(r => r.json())
        .then(users => {
            const usersList = document.getElementById("users-list");
            usersList.innerHTML = "";
            users.forEach(u => {
                if (u.id == currentUser.id) return;
                let div = document.createElement("div");
                div.className = "user-item";
                div.onclick = () => createPrivateTab(u.id, u.first_name + " " + u.last_name);
                div.innerHTML = `
                    <span>${u.first_name} ${u.last_name}</span>
                    <span class="${u.online ? 'online-dot' : 'offline-dot'}"></span>
                `;
                usersList.appendChild(div);
            });
        });
}

function updateUserStatus(userId, online) {
    loadUsers();
}

function loadPublicMessages() {
    fetch("/api/public-messages")
        .then(r => r.json())
        .then(msgs => {
            msgs.forEach(m => renderMessage("public", m));
        });
}

function renderMessage(chat, msg) {
    let box = document.getElementById("messages-" + chat);
    if (!box) return;

    let div = document.createElement("div");
    div.className = "message " + (msg.user_id == currentUser.id || msg.sender_id == currentUser.id ? "self" : "other");

    let displayName = msg.username || msg.sender_username || "ناشناس";
    let messageContent = msg.formatted_message || msg.message;

    if (msg.file_path) {
        messageContent += `<br><a href="${msg.file_path}" target="_blank">📎 ${msg.file_name}</a>`;
    }

    div.innerHTML = `
        <div class="message-content">${messageContent}</div>
        <div class="message-time">${displayName} - ${new Date(msg.created_at).toLocaleString('fa-IR')}</div>
    `;

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("message-input");
    let text = input.innerHTML.trim();
    if (!text) return;

    if (currentChat == "public") {
        socket.emit("send_public_message", {
            user_id: currentUser.id,
            username: currentUser.username,
            message: text,
            formatted_message: text
        });
    } else {
        let id = currentChat.replace("private_", "");
        socket.emit("send_private_message", {
            sender_id: currentUser.id,
            receiver_id: parseInt(id),
            sender_username: currentUser.username,
            message: text,
            formatted_message: text
        });
    }

    input.innerHTML = "";
}

function createPrivateTab(userId, name) {
    if (openChats[userId]) {
        switchTab("private_" + userId);
        return;
    }

    openChats[userId] = true;

    let tab = document.createElement("div");
    tab.className = "tab";
    tab.dataset.chat = "private_" + userId;
    tab.innerHTML = `${name} <span onclick="event.stopPropagation(); closeTab(${userId})">✕</span>`;
    tab.onclick = () => switchTab("private_" + userId);

    document.querySelector(".chat-tabs").appendChild(tab);

    let box = document.createElement("div");
    box.className = "chat-box";
    box.id = "chat-private_" + userId;
    box.innerHTML = `
        <div class="messages" id="messages-private_${userId}"></div>
        <div class="typing-indicator" id="typing-private_${userId}"></div>
    `;

    document.querySelector(".chat-content").appendChild(box);

    switchTab("private_" + userId);

    fetch(`/api/private-messages/${currentUser.id}/${userId}`)
        .then(r => r.json())
        .then(msgs => msgs.forEach(m => renderMessage("private_" + userId, m)));
}

function switchTab(id) {
    currentChat = id;

    document.querySelectorAll(".tab").forEach(t => {
        t.classList.toggle("active", t.dataset.chat == id);
    });

    document.querySelectorAll(".chat-box").forEach(b => {
        b.classList.remove("active");
    });

    document.getElementById("chat-" + id).classList.add("active");
}

function closeTab(id) {
    delete openChats[id];
    document.querySelector(`[data-chat="private_${id}"]`).remove();
    document.getElementById("chat-private_" + id).remove();
    switchTab("public");
}

function execCommand(cmd, val = null) {
    document.execCommand(cmd, false, val);
    document.getElementById("message-input").focus();
}

function toggleEmojiPicker() {
    const picker = document.getElementById("emoji-picker");
    if (picker.style.display === "none" || !picker.style.display) {
        picker.style.display = "block";
        if (picker.innerHTML === "") {
            const emojis = ["😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗", "😙", "😚", "🙂", "🤗", "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪", "😫", "😴", "😌", "😛", "😜", "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩", "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵", "😡", "😠", "🤬", "👍", "👎", "👌", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆", "👇", "☝️", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💪", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "💔", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "🔥", "✨", "💫", "⭐", "🌟", "💯", "✅", "❌"];
            emojis.forEach(emoji => {
                let span = document.createElement("span");
                span.innerText = emoji;
                span.style.cursor = "pointer";
                span.style.padding = "5px";
                span.onclick = () => {
                    document.getElementById("message-input").innerHTML += emoji;
                    picker.style.display = "none";
                };
                picker.appendChild(span);
            });
        }
    } else {
        picker.style.display = "none";
    }
}

function uploadFile(file) {
    if (!file) return;

    let reader = new FileReader();
    reader.onload = () => {
        socket.emit("upload_file", {
            filename: file.name,
            file: reader.result
        });
    };
    reader.readAsDataURL(file);

    socket.once("file_uploaded", (r) => {
        if (r.success) {
            document.getElementById("message-input").innerHTML += `<a href="${r.file_path}" target="_blank">📎 ${r.file_name}</a>`;
        } else {
            alert("خطا در آپلود فایل: " + r.error);
        }
    });
}

function loadAnnouncements() {
    fetch("/api/announcements")
        .then(r => r.json())
        .then(list => {
            const announcementsList = document.getElementById("announcements-list");
            announcementsList.innerHTML = "";
            list.forEach(a => {
                let div = document.createElement("div");
                div.className = "announcement-item";
                div.innerHTML = `
                    <strong>${a.manager_name}</strong>
                    <p>${a.formatted_message || a.message}</p>
                    <small>${new Date(a.created_at).toLocaleString('fa-IR')}</small>
                    <hr>
                `;
                announcementsList.appendChild(div);
            });
        });
}

function sendAnnouncement() {
    const text = document.getElementById("announcement-text").value.trim();
    if (!text) return;

    socket.emit("send_announcement", {
        manager_id: currentUser.id,
        manager_name: currentUser.first_name + " " + currentUser.last_name,
        message: text,
        formatted_message: text
    });

    document.getElementById("announcement-text").value = "";
}

function logout() {
    localStorage.removeItem("chat_user");
    location.reload();
}

// Event Listeners
window.onload = () => {
    let u = localStorage.getItem("chat_user");
    if (u) {
        initUser(JSON.parse(u));
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById("message-input");
    if (messageInput) {
        messageInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});

// Search functionality
let searchTimeout;
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = e.target.value.trim();
                if (query.length > 2) {
                    searchMessages(query);
                } else {
                    document.getElementById("search-results").innerHTML = "";
                }
            }, 500);
        });
    }
});

function searchMessages(query) {
    fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: currentUser.id,
            query: query
        })
    })
    .then(r => r.json())
    .then(results => {
        const searchResults = document.getElementById("search-results");
        searchResults.innerHTML = "";
        if (results.length === 0) {
            searchResults.innerHTML = "<p>نتیجه‌ای یافت نشد</p>";
        } else {
            results.forEach(r => {
                let div = document.createElement("div");
                div.className = "search-result-item";
                div.innerHTML = `
                    <strong>${r.sender_username}</strong>
                    <p>${r.message.substring(0, 50)}...</p>
                    <small>${new Date(r.created_at).toLocaleString('fa-IR')}</small>
                `;
                searchResults.appendChild(div);
            });
        }
    });
}
