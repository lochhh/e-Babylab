/**
 * Hide (and clear) a trial inline's dwell-check fieldset while the trial is
 * marked as an attention getter, since attention getters cannot have one.
 * Server-side validation remains the real guard.
 */
const FLAG_SELECTOR = 'input[type="checkbox"][name$="-is_attention_getter"]';

/**
 * Show or hide the dwell fieldset belonging to one flag checkbox.
 * @param {HTMLInputElement} checkbox
 */
export function sync(checkbox) {
    const fieldset = checkbox.closest('.grp-dynamic-form')?.querySelector('fieldset.dwell-check');
    if (!fieldset) return;
    fieldset.style.display = checkbox.checked ? 'none' : '';
    if (!checkbox.checked) return;
    fieldset.querySelectorAll('input, select').forEach(el => {
        el.value = el.name.endsWith('-dwell_target_type') ? 'ANY' : '';
    });
}

/** Sync every flag checkbox and watch for later changes. */
export function init() {
    document.querySelectorAll(FLAG_SELECTOR).forEach(sync);
    // Delegated, so inline rows added later ("Add another Trial") are covered
    document.addEventListener('change', event => {
        if (event.target.matches?.(FLAG_SELECTOR)) sync(event.target);
    });
}

document.addEventListener('DOMContentLoaded', init);
