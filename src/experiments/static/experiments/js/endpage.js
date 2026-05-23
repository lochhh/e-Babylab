export function init() {
    const approve = document.querySelector('#end_page_step_1 button.btn-primary');
    const disapprove = document.querySelector('#end_page_step_1 button.btn-danger');
    if (!approve || !disapprove) return;
    approve.addEventListener('click', () => {
        document.getElementById('end_page_step_1').classList.remove('active');
        document.getElementById('end_page_approve').classList.add('active');
    });
    disapprove.addEventListener('click', () => {
        document.getElementById('end_page_step_1').classList.remove('active');
        document.getElementById('end_page_disapprove').classList.add('active');
    });
}

init();
