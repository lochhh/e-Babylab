export function init() {
    const approve = document.querySelector('#end_page_step_1 button.btn-primary');
    const disapprove = document.querySelector('#end_page_step_1 button.btn-danger');
    if (!approve || !disapprove) return;
    approve.addEventListener('click', () => {
        document.getElementById('end_page_step_1').style.display = 'none';
        document.getElementById('end_page_approve').style.display = 'block';
    });
    disapprove.addEventListener('click', () => {
        document.getElementById('end_page_step_1').style.display = 'none';
        document.getElementById('end_page_disapprove').style.display = 'block';
    });
}

init();
