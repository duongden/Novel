// 复制功能
document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const url = btn.dataset.url;

        try {
            await navigator.clipboard.writeText(url);

            // 按钮状态
            const originalText = btn.textContent;
            btn.textContent = '已复制';
            btn.classList.add('copied');

            // 显示 Toast
            showToast('链接已复制到剪贴板');

            // 恢复按钮
            setTimeout(() => {
                btn.textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        } catch (err) {
            // 降级方案
            const textarea = document.createElement('textarea');
            textarea.value = url;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);

            showToast('链接已复制到剪贴板');
        }
    });
});

// Toast 提示
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}
