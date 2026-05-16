'use strict';

const approve = $("#end_page_step_1 button.btn-primary");
const disapprove = $("#end_page_step_1 button.btn-danger");

approve.click(() => {
    $("#end_page_step_1").removeClass("active");
    $("#end_page_approve").addClass("active");
});

disapprove.click(() => {
    $("#end_page_step_1").removeClass("active");
    $("#end_page_disapprove").addClass("active");
});
