'use strict';

$(function () {
    var subjectForm = $('#subjectForm');
    var recaptchaSiteKey = subjectForm.data('recaptchaSiteKey');

    if (subjectForm.length && recaptchaSiteKey) {
        grecaptcha.ready(function () {
            subjectForm.submit(function (e) {
                var form = this;
                e.preventDefault();
                grecaptcha.execute(recaptchaSiteKey, { action: 'submit' }).then(function (token) {
                    $('#g-recaptcha-response').val(token);
                    form.submit();
                });
            });
        });
    }
});
