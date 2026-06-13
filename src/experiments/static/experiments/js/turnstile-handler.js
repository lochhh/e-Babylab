window.onTurnstileVerified = () => {
    document.getElementById('subjectForm').submit();
};

const subjectForm = document.getElementById('subjectForm');
if (subjectForm && subjectForm.dataset.turnstileSiteKey) {
    subjectForm.addEventListener('submit', (e) => {
        e.preventDefault();
        turnstile.execute();
    });
}
