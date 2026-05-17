const subjectForm = document.getElementById('subjectForm');
if (subjectForm) {
    const recaptchaSiteKey = subjectForm.dataset.recaptchaSiteKey;
    if (recaptchaSiteKey) {
        window.grecaptcha.ready(() => {
            subjectForm.addEventListener('submit', (e) => {
                e.preventDefault();
                window.grecaptcha.execute(recaptchaSiteKey, { action: 'submit' }).then((token) => {
                    document.getElementById('g-recaptcha-response').value = token;
                    subjectForm.submit();
                });
            });
        });
    }
}
