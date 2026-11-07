/**
 * Ask for confirmation before saving an experiment whose recording option no
 * longer includes eye-tracking, since the server then clears the experiment's
 * eye-tracking trial settings. The server puts the initial option, the
 * eye-tracking options and the affected trial counts on the select as data-*.
 */
const SELECT = 'select[name="recording_option"]';

/**
 * Return the confirmation text, or null if no confirmation is needed.
 * @param {HTMLSelectElement|null} select
 * @returns {string|null}
 */
export function message(select) {
    const d = select?.dataset;
    if (!d?.initial) return null;
    const eye = (d.eyeValues || '').split(',');
    if (!eye.includes(d.initial) || eye.includes(select.value)) return null;
    const dwell = Number(d.dwellCount);
    const ags = Number(d.attentionGetterCount);
    const cals = Number(d.calibrationCount);
    if (!dwell && !ags && !cals) return null;
    const n = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;
    const parts = [];
    if (dwell) parts.push(`clear gaze dwell time checks on ${n(dwell, 'trial')}`);
    const resets = [[ags, 'attention getter'], [cals, 'calibration trial']]
        .filter(([count]) => count)
        .map(([count, noun]) => n(count, noun));
    if (resets.length) parts.push(`reset ${resets.join(' and ')} to Regular`);
    return (
        'Changing the recording option to one without eye-tracking will ' +
        `${parts.join(' and ')}. This cannot be undone. Continue?`
    );
}

/** Guard the form's submit event (covers every save button). */
export function init() {
    const select = document.querySelector(SELECT);
    select?.form?.addEventListener('submit', event => {
        const text = message(select);
        if (text && !window.confirm(text)) event.preventDefault();
    });
}

document.addEventListener('DOMContentLoaded', init);
