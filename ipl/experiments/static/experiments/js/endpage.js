var approve = $("#end_page_step_1 button.btn-primary");
var disapprove = $("#end_page_step_1 button.btn-danger");
approve.click(function(){
    $("#end_page_step_1").removeClass("active");
    $("#end_page_approve").addClass("active");
});
disapprove.click(function(){
    $("#end_page_step_1").removeClass("active");
    $("#end_page_disapprove").addClass("active");
});