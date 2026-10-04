/**
 * Show the eye-tracking sections of a trial inline that suit its trial type:
 * regular trials get the dwell check, calibration trials get the calibration
 * points, attention getters get neither. Values are never cleared here (so
 * switching back restores them); the server clears dwell values on non-regular
 * trials. Sections missing from the page (experiments
 * without eye-tracking) are ignored. Server-side validation remains the real guard.
 */
const SELECTOR = 'select[name$="-trial_type"]';

/**
 * Apply one trial type select to its inline's sections.
 * @param {HTMLSelectElement} select
 */
export function sync(select) {
    // Not .grp-dynamic-form: Grappelli only adds that class after DOM ready, i.e.
    // after our init has run.
    const row = select.closest('.inline-related');
    const dwell = row?.querySelector('.dwell-check');
    const calibration = row?.querySelector('.eye-calibration');
    const type = select.value;
    if (dwell) dwell.style.display = type === 'REG' ? '' : 'none';
    if (calibration) calibration.style.display = type === 'CAL' ? '' : 'none';
}

/** Sync every trial type select and watch for later changes. */
export function init() {
    document.querySelectorAll(SELECTOR).forEach(sync);
    // Delegated, so inline rows added later ("Add another Trial") are covered
    document.addEventListener('change', event => {
        if (event.target.matches?.(SELECTOR)) sync(event.target);
    });
}

document.addEventListener('DOMContentLoaded', init);
