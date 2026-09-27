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
    } else if (provider === 'altcha') {
        // Reveal the widget so participants see it verifying. Done on its own
        // event: the widget stops propagation of the submit it intercepts, so
        // the submit listener below never sees the first click.
        const widget = subjectForm.querySelector('.captcha-badge');
        widget.addEventListener('statechange', (e) => {
            if (e.detail.state === 'verifying') widget.style.display = 'block';
        });
        // The widget only intercepts submits while unverified, so a second click
        // during the solve would post an empty solution. Its own re-submit after
        // solving carries the payload and passes through.
        subjectForm.addEventListener('submit', (e) => {
            if (!new FormData(subjectForm).get('altcha')) e.preventDefault();
        });
    }
}
