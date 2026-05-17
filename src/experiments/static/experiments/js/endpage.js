'use strict';

const approve = document.querySelector('#end_page_step_1 button.btn-primary');
const disapprove = document.querySelector('#end_page_step_1 button.btn-danger');

approve.addEventListener('click', () => {
    document.querySelector('#end_page_step_1').classList.remove('active');
    document.querySelector('#end_page_approve').classList.add('active');
});

disapprove.addEventListener('click', () => {
    document.querySelector('#end_page_step_1').classList.remove('active');
    document.querySelector('#end_page_disapprove').classList.add('active');
});
