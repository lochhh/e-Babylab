window.onCaptchaVerified = () => {
    document.getElementById('subjectForm').submit();
};

const subjectForm = document.getElementById('subjectForm');
if (subjectForm) {
    const provider = subjectForm.dataset.captchaProvider;
    if (provider === 'turnstile') {
        subjectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const badge = subjectForm.querySelector('.captcha-badge');
            if (badge) badge.style.display = 'block';
            turnstile.execute();
        });
    }
}
