(target-faq-troubleshoot)=
# Troubleshooting

## I am unable to access the file browser, and I get a server 500 error. What could be the issue?

A server 500 error could be due to a corrupted file uploaded by the user (e.g. renaming file extensions directly). Please contact your system administrator to check the server logs for more information.

## I get a "Can't find a suitable configuration file in this directory or any parent. Are you in the right directory?" error. What could be the issue?

Docker is unable to locate `docker-compose.yml`. Either create this file (by copying `docker-compose.yml.template`) or run `docker-compose` commands with `-f docker-compose.dev.yml` (e.g., `docker compose -f docker-compose.dev.yml build`).

## I modified the template pages and now I get an error message. What could be the reason? How do I fix this?

It could be that you removed or modified some `<script>` or `<form>` elements, which are necessary for the website to function properly (e.g., button functions, form submissions). The best way to fix this is to restore the original template pages. You can do so by creating a new experiment in a new tab/window. From there, you can copy the original template code and replace your modified code with it. Note also that the URLs in the templates are dynamically generated and look something like `<form action="{% url 'experiments:consentForm' experiment.id %}">`, so you should not hardcode them in `<form action>`.