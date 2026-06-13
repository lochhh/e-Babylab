(target-faq-general)=
# General

## Is it possible to change the background colour in an e-Babylab experiment?

Yes, background colour can be changed for each inner block, using the colour picker tool or by entering the hex code. By default, the background colour is white.

:::{figure} https://github.com/user-attachments/assets/bee2a524-21e1-4786-87c5-bb4ab387e589
:alt: Background colour picker
:width: 400px

Background colour picker
:::

## What are the supported file types in e-Babylab?

The supported file types can be found in [File Management](target-file-management).

## What are the recommended file sizes and formats for stimuli?

In general, we recommend that you keep the file sizes as small as possible to ensure quick loading times (i.e. minimise lag in experiments). See [File Management](target-file-management) for more details.

## How do I convert videos into different formats?

You can use [Handbrake](https://handbrake.fr/) to convert videos into different formats.

## What can I do with `label` and `code` in trial settings?

These are fields that you can use to store information about the [trial](target-trials). For example, in a 2-alternative forced choice task, you can use `label` to store the trial condition, and `code` to store information about the stimuli (e.g. `"target-distractor"`, to indicate the target is on the left, and distractor on the right). Together with ROIs (defined using `rows` and `columns` in trial settings), you can then use these information to infer whether the response (click/touch/gaze) falls on the target or the distractor when post-processing your data.

## What is a (gaze) calibration trial?

A (gaze) calibration trial is a special type of trial where the participant is asked to look at a series of points on the screen. This data is then used to calibrate the eye tracker. At the end of the calibration trial, the eye tracker is validated by presenting the first point again. Watch the [eye-tracking video tutorial](https://www.youtube.com/watch?v=CXf7JDdxEj0) for more information.

## Can I validate the eye tracker with multiple points?

Since validation is only performed using a single point at the end of a calibration trial, you will need to create multiple calibration trials, each with a single point, to validate the eye tracker at different locations on the screen. Note that calibration will still be carried out for the defined `max duration`, but you can set this to a very short duration (e.g. 100 ms) to "skip" the calibration process.

## Does e-Babylab support response-contingent designs?

At the moment, there is no option for creating response-contingent designs (e.g., conditionally move to/skip certain trials/blocks based on the participant's response in the current trial). For this, you may want to check out [jsPsych](https://www.jspsych.org/latest/overview/timeline/#conditional-timelines) or [Gorilla](https://support.gorilla.sc/support/tools/experiment-builder/tree-nodes#overview).

## What devices/browsers are e-Babylab experiments compatible with?

e-Babylab experiments are compatible with Google Chrome or Mozilla Firefox on all Android devices as well as desktop and laptop computers running Windows, macOS, or Linux.

Currently, media recording features (requiring webcam and/or microphone) are not supported on iOS devices (iPhone, iPad). However, experiments that only require touch or click responses can still run on these devices, as long as a user response (touch or click) is required in each trial. This means that the trials need to be configured to have long `max duration` and users must provide a response within this defined `max_duration` for the experiments to run.

## Does e-Babylab store participants' IP addresses?

Participants' IP addresses are not stored anywhere.

## How do I share/duplicate an experiment?

Use the **Export** button on the Experiment Admin page. This downloads a `.zip` file that bundles the complete experiment configuration together with all media stimuli (audio, visual, and loading image) and, if applicable, the CDI instrument and its parameter files.

This `.zip` file can then be imported into e-Babylab on the same or a different instance using the **Import** button on the Experiment Admin page. During import, media files are stored under `experiments/<experiment name>/` in the file manager if they do not already exist in the `experiments/` folder. If a CDI instrument with the same name already exists on the target instance it is reused; otherwise a new instrument is created, with parameter files stored under `instruments/<instrument name>/`. If an experiment with the same name already exists, the imported experiment is renamed with a `copy` suffix (e.g. `My Experiment copy`, `My Experiment copy 1`, etc.).

## Can I modify the HTML templates to skip the participant page?

The participant page cannot be skipped as this "creates" the participant on the database by assigning them a unique ID for linking their experiment results. What you can do is to leave the participant page empty (by removing the title of the page in the HTML template, and removing any [participant form questions](target-participant-form)), keeping only the "Next" button.

## Can video controls (play, pause, seek, etc.) be displayed for video stimuli in an experiment?

Yes. You can modify the experiment page HTML template to include JavaScript code that detects new video elements as they are added and enables the HTML `video.controls` for each of these. Here is an example:

```javascript
const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
            if (node.tagName === 'VIDEO') {
                node.controls = true;
            } else if (node.querySelectorAll) {
                node.querySelectorAll('video').forEach(video => {
                    video.controls = true;
                });
            }
        });
    });
});
observer.observe(document.body, { childList: true, subtree: true });
```
