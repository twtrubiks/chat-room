(function () {
    const form = document.querySelector('form.needs-validation');
    const username = document.getElementById('username');
    const feedback = document.getElementById('usernameFeedback');
    let lastChecked = null;

    async function checkUsername() {
        const value = username.value.trim();
        if (!value) return;
        if (value === lastChecked) return;
        lastChecked = value;
        try {
            const fd = new FormData();
            fd.append('username', value);
            const resp = await fetch('/API_check_UserNameExist', { method: 'POST', body: fd });
            const ok = await resp.json();
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

    username.addEventListener('blur', checkUsername);
    username.addEventListener('input', () => {
        username.setCustomValidity('');
        feedback.textContent = 'Please enter a username.';
        lastChecked = null;
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
