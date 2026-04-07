(target-experiment-administration)=
# Experiment Administration

The experiments a user has access to (i.e. has permission to change or delete) are shown in the Experiment Admin.

:::{figure} https://github.com/user-attachments/assets/9b130c55-4934-4cb7-a2e8-2c9fbaa341f1
:alt: Experiment Admin

Experiment Admin
:::

A normal user has access to experiments they own and those shared within the group(s) they belong to. On the other hand, a site administrator has access to all experiments on e-Babylab, and hence is shown the full list of experiments stored in the database.

Clicking on **Add experiment** redirects users to the setup page of a new experiment. In order to access an experiment webpage or to obtain the URL of an experiment (e.g., to be sent to participants), users can click on **Go to experiment** and the experiment will open in a new tab.

Clicking the **Download results** button allows users to download a `.zip` file containing the participant data and results as well as any media recordings of an experiment. The results from each participant are output to an `.xlsx` file with its name taking the form `participant number_experiment name_participation date_unique ID`. This file contains the following worksheets:

1. **Participant** — contains the participant form responses, aspect ratio and resolution of their screen, consent and CDI form responses.
2. **Trials** — contains the details of every trial (e.g., stimuli presented, start time, finish time), the response time and responses given (e.g., keys pressed, mouse click coordinates), as well as the file names of any media recordings taking the form `participant number_trial number_trial label_unique ID`.
3. **EyeTrackingData** _(optional)_ — contains the trial details (i.e., trial number, trial label, trial code, grid layout (nrows, ncols)), time t, gaze location (x,y), gaze area (row,col).
4. **EyeTrackingValidation** _(optional)_ — contains the last 50 gaze locations (x,y) for each _calibration_ trial, trial details (i.e., trial number, trial label, trial code, target location (target_x,target_y)), accuracy, precision root mean square, precision standard deviation (x,y). See [Validation Measures](#validation-measures) for the definitions.

The options to **import** and **export** experiment setups are also provided and may be useful when a user wishes to share an experiment setup but not their participant data and results, or when a user needs to duplicate an experiment setup.

(target-validation-measures)=
## Validation Measures

**Accuracy**
: The mean Euclidean distance between gaze locations (x,y) and the centre position of the target (target_x,target_y).

**Precision RMS**
: The root mean square of the distance between successive gaze locations (x,y).

**Precision SD x and Precision SD y**
: The deviation from the mean location of all gaze locations (x,y) in the horizontal and vertical directions respectively.
