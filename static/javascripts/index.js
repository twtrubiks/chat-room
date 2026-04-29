(function () {
    const messages = document.querySelector('.messages-content');
    const messageInput = document.querySelector('.message-input');
    const messageSubmit = document.querySelector('.message-submit');

    const socket = io();

    socket.on('connect', () => {
        socket.emit('join', { room: 'A_Room' });
    });

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHTML(s) {
        const div = document.createElement('div');
        div.textContent = s == null ? '' : String(s);
        return div.innerHTML;
    }

    function appendMessage(data) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message new';
        wrapper.innerHTML =
            '<figure class="avatar"><img src="/static/mugshot/' + escapeHTML(data.PictureUrl) + '"></figure>' +
            escapeHTML(data.msg) +
            '<div class="timestamp">' + escapeHTML(data.time) + '</div>';
        messages.appendChild(wrapper);
        scrollToBottom();
    }

    function insertMessage() {
        const msg = (messageInput.value || '').trim();
        if (!msg) return;
        socket.emit('sendInquiry', { msg: msg, room: 'A_Room' });
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

    window.addEventListener('load', scrollToBottom);
})();
