window.onTurnstileVerified = () => {
    document.getElementById('subjectForm').submit();
};

const subjectForm = document.getElementById('subjectForm');
if (subjectForm && subjectForm.dataset.turnstileSiteKey) {
    subjectForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const widget = subjectForm.querySelector('.turnstile-badge');
        if (widget) widget.style.display = 'block';
        turnstile.execute();
    });
}
