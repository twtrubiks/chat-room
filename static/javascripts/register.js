(function () {
    const form = document.querySelector('form.needs-validation');
    const username = document.getElementById('username');
    const feedback = document.getElementById('usernameFeedback');
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    // 最近一次的檢查 { value, promise }；同一個名稱還在檢查中時，送出要等它跑完
    let lastCheck = null;

    async function requestCheck(value) {
        try {
            const fd = new FormData();
            fd.append('username', value);
            const resp = await fetch('/API_check_UserNameExist', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: fd,
            });
            const ok = await resp.json();
            // 檢查期間名稱又被改掉了，這個結果不算數
            if (username.value.trim() !== value) return;
            if (ok) {
                username.setCustomValidity('');
            } else {
                username.setCustomValidity('exists');
                feedback.textContent = 'UserName already exists.';
            }
        } catch (err) {
            username.setCustomValidity('');
        }
    }

    function checkUsername() {
        const value = username.value.trim();
        if (!value) return Promise.resolve();
        if (!lastCheck || lastCheck.value !== value) {
            lastCheck = { value, promise: requestCheck(value) };
        }
        return lastCheck.promise;
    }

    username.addEventListener('blur', checkUsername);
    username.addEventListener('input', () => {
        username.setCustomValidity('');
        feedback.textContent = 'Please enter a username.';
        lastCheck = null;
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await checkUsername();
        form.classList.add('was-validated');
        if (form.checkValidity()) {
            form.submit();
        }
    });
})();
