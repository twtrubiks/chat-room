(function () {
    const Cropper = window.Cropper.default;
    const fileInput = document.getElementById('cropInput');
    const image = document.getElementById('cropImage');
    const confirmBtn = document.getElementById('cropConfirm');
    let cropper = null;

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        image.src = URL.createObjectURL(file);
        image.onload = () => {
            cropper = new Cropper(image);
            const selection = cropper.getCropperSelection();
            if (selection) {
                selection.aspectRatio = 1;
            }
            confirmBtn.disabled = false;
        };
    });

    confirmBtn.addEventListener('click', async () => {
        if (!cropper) return;
        confirmBtn.disabled = true;
        try {
            const selection = cropper.getCropperSelection();
            const canvas = await selection.$toCanvas({ width: 256, height: 256 });
            canvas.toBlob((blob) => {
                const fd = new FormData();
                fd.append('image', blob, 'avatar.png');
                fetch('/croppic', { method: 'POST', body: fd })
                    .then((r) => r.json())
                    .then((res) => {
                        if (res.status === 'success') {
                            location.reload();
                        } else {
                            alert('上傳失敗:' + (res.message || 'unknown'));
                            confirmBtn.disabled = false;
                        }
                    })
                    .catch((err) => {
                        alert('上傳失敗:' + err);
                        confirmBtn.disabled = false;
                    });
            }, 'image/png');
        } catch (err) {
            alert('裁切失敗:' + err);
            confirmBtn.disabled = false;
        }
    });
})();
