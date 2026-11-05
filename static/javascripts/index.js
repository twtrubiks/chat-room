(function () {
    const messages = document.querySelector('.messages-content');
    const messageInput = document.querySelector('.message-input');
    const messageSubmit = document.querySelector('.message-submit');

    // 登入後伺服器會自動把連線加進聊天室
    const socket = io();

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    // 伺服器給的是帶時區的 ISO 時間，換成瀏覽器當地時間顯示
    function formatTime(iso) {
        const d = new Date(iso);
        if (isNaN(d)) return iso;
        const pad = (n) => String(n).padStart(2, '0');
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
            ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }

    // 用 DOM API 組訊息，不拼 HTML 字串，使用者輸入的內容一律當純文字
    function appendMessage(data) {
        const img = document.createElement('img');
        img.src = '/static/mugshot/' + data.PictureUrl;
        const avatar = document.createElement('figure');
        avatar.className = 'avatar';
        avatar.appendChild(img);

        const time = document.createElement('time');
        time.dateTime = data.time;
        time.textContent = formatTime(data.time);
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.appendChild(time);

        const wrapper = document.createElement('div');
        wrapper.className = 'message new';
        wrapper.append(avatar, document.createTextNode(data.msg), timestamp);
        messages.appendChild(wrapper);
        scrollToBottom();
    }

    function insertMessage() {
        const msg = (messageInput.value || '').trim();
        if (!msg) return;
        socket.emit('sendInquiry', { msg: msg });
        messageInput.value = '';
    }

    socket.on('getInquiry', appendMessage);

    messageSubmit.addEventListener('click', insertMessage);

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            insertMessage();
        }
    });

    messages.querySelectorAll('time[datetime]').forEach((el) => {
        el.textContent = formatTime(el.dateTime);
    });

    window.addEventListener('load', scrollToBottom);
})();
