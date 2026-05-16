'use strict';

(function (window) {
    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    window.getCsrfToken = getCsrfToken;
})(window);
