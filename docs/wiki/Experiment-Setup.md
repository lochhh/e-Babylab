## Experiment Wizard
The experiment setup process can be broken down into six parts: 
* [General Settings](#general-settings)
* [HTML Templates](#html-templates)
* [CDI Administration](#cdi-administration)
* [Consent Form](#consent-form)
* [Participant Form](#participant-form)
* [Experimental Task](#experimental-task)

*Experiment Wizard*
![Experiment wizard](https://github.com/user-attachments/assets/ed77ea48-236d-4ebc-809d-b7c936cebdee)

> [!NOTE] 
> Fields in boldface are mandatory.

### General Settings
* **``Experiment name``**
* **``Sharing options``** allow an experiment, including its 
participants and results to be made accessible to:
  * owner only (private), 
  * everyone (all registered users), or 
  * group members only.
* ``Sharing groups``
* **``List selection strategy``** determines how lists (different versions of an experiment) are distributed among participants. The options include:
  * least played (select the list with the least participants),
  * sequential (select lists according to the order they are added to an experiment), and 
  * random.
* **``Wait to enable key/click response (ms)``** defines the duration from the onset of each trial for which key presses/click responses should be disabled (i.e., how long to wait until responses can be accepted)
* **``Recording option``** defines the type of responses to be captured in each trial. The options include: 
  * key presses or clicks only, 
  * audio and key presses or clicks,
  * video and key presses or clicks, 
  * eye-tracking and key presses or clicks, or
  * eye-tracking, video, and key presses or clicks
* ``Loading image`` is an optional field, for specifying the image to be shown before the end page of an experiment, while media uploads are still in progress. This can be an image with a message asking participants to keep their browser windows open while the captured media are still being uploaded. 
* ``Include pause page`` provides the option to redirect participants to a pause page 
when they fail to complete an experiment within a given time or when the exit button is clicked during an experiment, instead of ending an experiment immediately. Pause events are recorded in the results.
* ``Show gaze estimations`` allows WebGazer estimations to be visualised as a red dot to check if eye-tracking is working properly. This is typically used for debugging purposes but should be disabled in actual experiments.

### HTML Templates

![Templates](https://github.com/user-attachments/assets/ce8a2775-377f-4084-9672-688d664940a2)

The "Templates" section provides a "What You See Is What You Get" (_WYSIWYG editor_) for customising the looks and text (e.g., language, instructions) of the experiment webpages, including the welcome page, browser compatibility check page, consent, participant, and CDI forms, webcam and microphone check pages, experimental task page, pause page, error page, and end pages. These fields are pre-populated with default HTML code that works as is. Alternatively, users can change the text as needed. Some elements (e.g., button labels, error messages, success messages) are not visible in the WYSIWYG editor. To change these texts, use the _source code editor_ accessed via the "<>" icon on the toolbar. 

### CDI Administration

![cdi](https://github.com/user-attachments/assets/aa72e32a-af68-4871-a711-486f611f223f)

The "CDI Administration" section allows users to optionally administer adaptive, short-form CDIs ([Chai et al., 2020](https://doi.org/10.1044/2020_JSLHR-20-00361); [Mayor & Mani, 2019](https://doi.org/10.3758/s13428-018-1146-0)) alongside an experimental task, or as an experiment itself (without an experimental task). Two **``Assessment types``** are available: production or comprehension. This should match the selected CDI ``Instrument``. **``Vocabulary checklist length``** determines how many CDI items will be administered. See also [Instrument Administration](https://github.com/lochhh/e-Babylab/wiki/Instrument-Administration) for how to add an Instrument. 

> [!IMPORTANT]
> It is necessary to obtain information on the participant's age and sex in the participant form (configured in Demographic Information) as this is required to compute CDI estimates for the participant. The accepted age range must also match what is in the data files of the selected Instrument. 

### Consent Form

![Consent form](https://github.com/user-attachments/assets/5a04ce4d-2ac7-4fff-9c0f-3899cd60d984)

The "Consent Questions" section allows users to add consent questions (**``text``**) in the consent form. These consent questions will appear on the consent form as mandatory yes-no questions, according to the order specified in the **``position``** field. There is no need to fill the **``position``** fields as these are automatically updated upon saving. To reorder the questions, users can simply drag and drop the questions without needing to manually update the **``position``** fields. The **``yes``** and **``no``** fields are the button labels in the consent form and should be updated according to the language of your experiment. 

> [!IMPORTANT]
> Participants are only allowed to proceed with an experiment when all consent questions are responded with yeses, otherwise they will be redirected to the "Failed to obtain consent" page, which serves to provide an explanation to why they are unable to proceed with the experiment as well as the option to return to the consent form to make any changes.

### Participant Form

![Participant form](https://github.com/user-attachments/assets/fc377aa8-8c48-4ea1-b793-bf083b856cd6)

The "Demographic Information" section allows users to add form items to the participant form.
* **``Text``** 
* ``Required``: questions must be answered before the participant form can be submitted. 
* **``Question type``** and ``Choices``
  * ``text`` field 
  * ``radio`` buttons: options must be specified in ``Choices`` as a comma-separated list
  * ``select``: drop-down list; options must be specified in ``Choices`` as a comma-separated list
  * ``select multiple``: checkboxes; options must be specified in ``Choices`` as a comma-separated list
  * ``integer`` field 
  * ``integer range``: requires min and max allowed values to be specified in ``Choices`` as a comma-separated list and min must precede max in this list; appears on the participant form as an integer field but checks that the response falls within the specified range
  * ``age`` (months): requires min and max allowed **age in months** to be specified in ``Choices`` as a comma-separated list and min must precede max in this list; must be included and marked as a required question for experiments that administer CDIs; appears on the participant form as a Date field with an automatic check that ensures the participant falls within the required age range
  * ``sex``: must be included and marked as a required question for experiments that administer CDIs; requires female and male values to be specified in ``Choices`` as a comma-separated list and female must precede male in this list;
* **``Position``** fields determine the order in which the form fields or questions appear on the participant form and are automatically updated. Items can be reordered using drag and drop as well.

### Experimental Task

An experimental task design is made up of four layers:
* lists,
* outer-blocks,
* inner-blocks,
* and trials.

In general, experiments have lists, lists have outer-blocks, outer-blocks have inner-blocks, and inner-blocks have trials.

#### Lists

![List](https://github.com/user-attachments/assets/fd8784ba-df95-4636-938f-b2f2241026ff)

Each list may represent different versions of the experiment or different conditions of a between-subjects experiment. As each experiment has its own unique URL, an added benefit of having multiple lists instead of having multiple experiments is that only a single URL needs to be sent to all participants or parents of participants and e-Babylab automates the distribution of participants among different versions of an experiment.
* **``List name``**
* **``Global timeout``** is the maximum duration allowed for participants to complete the entire 
experimental task. If no time limit is required, this can simply be a very large number. 
* ``Do not include this list`` temporarily "disables" a list (i.e. prevents a list from being distributed to future participants) 

#### Outer-Blocks

![Outer block](https://github.com/user-attachments/assets/5f386369-4a92-464b-b289-8a342fa3e9b5)

Outer-blocks are presented in a **fixed order** according to the **``Position``** field (automatically updated; use drag and drop to reorder). Having outer-blocks allow inner-blocks to either be ``randomised`` or presented in a fixed order, thereby increasing the flexibility in designing experimental tasks.

#### Inner-Blocks

![Inner block](https://github.com/user-attachments/assets/174bf69a-cc02-4955-830c-121e5b065d13)

Inner-blocks allow users to organise different phases of an experimental task into different blocks, such as training, familiarisation, and test. 
* **``Label``**
* ``Comment``
* **``Background colour``** sets the background colour of all trials within the inner-block; use either hex colour codes or the colour picker provided
* ``Randomise trials`` determines whether trials within the inner-block should be presented in a random order
* **``Position``** determines the order in which the inner block is presented within its outer-block, unless inner-blocks are set to be randomised. Users can also drag and drop to reorder inner-blocks.

#### Trials

![Trial](https://github.com/user-attachments/assets/8832a29e-4547-4cdc-bbaf-4eb53c3c4109)

* **``Label``**
* **``Code``** 
* **``Visual onset (ms)``** determines the onset of the visual stimulus during a trial; when set at 0, the stimulus will be presented as soon as a trial begins.
* **``Visual file``**
* **``Audio onset (ms)``** determines the onset of the audio stimulus during a trial; when set at 0, the stimulus will be presented as soon as a trial begins.
* ``Audio file``
* **``User input``** determines whether a participant's response is required to proceed to the next trial.
* ``Response key(s)`` define as a comma-separated list, the types of responses or specific keys that are accepted if a response is required (e.g., click, up, down, left, right, a, b, c, space, enter).
* **``Maximum duration (ms)``** is the time limit given to participants to respond in a trial or if a response is not required, the duration of a trial. If the visual stimulus is a video, this value is disregarded. If there is no time limit to respond, this can simply be a very large number. 
* ``Record media`` determines whether media (and depending on the experiment-level _recording option_) should be recorded for a trial. 
* ``Enable eye-tracking`` determines whether eye-tracking data (and depending on the experiment-level _recording option_) should be recorded for a trial.
* ``Calibrate eye-tracker`` determines whether this is an eye-tracker calibration trial.
* **``Calibration points``** defines an **ordered list** of points in [x,y] coordinates (specified as a percentage of the screen width and height, from the left and top edge) at which the visual stimulus will be presented one after another. The default provided is a grid containing 9 points for calibration. The duration for which each calibration point is shown is determined by dividing the ``maximum duration`` with the number of calibration points. See also the [eye-tracking video tutorial](https://www.youtube.com/watch?v=CXf7JDdxEj0).
* **``Rows``** and **``Columns``** allow users to set an invisible grid layout with _x_ rows and _y_ columns so that the position of a click/touch/eye-gaze on the screen (row, col) can be determined in addition to the coordinates.  
* **``Position``** determines the order in which a trial is presented within its inner-block, except when trials are set to be randomised; trials can be reordered by using drag-and-drop.