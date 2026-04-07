(target-typical-experiment-run)=
# Typical Experiment Run

The flow chart below summarises a typical e-Babylab experiment run.

```{mermaid}
flowchart TD

    A((Welcome page)) --> B[Browser compatibility check]
    B --> C{"Browser
    supported?"}
    C -->|Yes| D[Consent form]
    C -->|No| E((Close browser))
    D --> F{"Consent
    granted?"}
    F -->|Yes| G[Participant form]
    F -->|No| H[Consent failure page]
    H --> I{"Return to
    consent form?"}
    I -->|Yes| D
    I -->|No| E
    G --> J{Form valid?}
    J -->|Yes| K{"Administer
    CDI?"}
    J -->|No| G
    K -->|Yes| L[CDI form]
    K -->|No| M{"Audio/Video
    recording required?"}
    L --> M
    M -->|Yes| N["Microphone/Webcam
    setup page"]
    M -->|No| O["Experiment
    instructions"]
    N --> P{"Setup
    successful?"}
    P -->|Yes| O
    P -->|No| Q{"Repeat
    setup?"}
    Q -->|Yes| N
    Q -->|No| E
    O -->R["Enter
    fullscreen mode"]
    R -->S["Experimental
    task"]
    S -->T{"Exit button
    pressed?"}
    T -->|Yes| U{"Pause
    allowed?"}
    T -->|No| V(("Standard
    end page"))
    U -->|Yes| W[Pause page]
    U -->|No| Y(("End page after
    discontinuation"))
    W --> X{"Return to
    experiment?"}
    X -->|Yes| M
    X -->|No| Y
```

An experiment begins with a welcome page, which also functions as the participant information sheet. This is followed by an automatic browser compatibility check as experiments programmed with this tool can only be run using Google Chrome and Mozilla Firefox for Android and desktop; these two browsers make up about 82% of the browser market share worldwide in 2020. In the next steps, the consent form, participant form, CDI form (if applicable), microphone and/or webcam setup page (if applicable) are presented. During the microphone and/or webcam setup, the browser first requests for participants' permission to access their microphone and/or webcam. When access is given, a 3-second test audio (or test video) is recorded to ensure that both recording and uploading work. This procedure can be repeated, if needed. Upon successful checks, participants are then redirected to the experiment start page, where they are prompted to enter full-screen mode. Throughout the experimental task, a small exit button is shown at the bottom right corner of the screen, allowing participants to quit at any time. If the experiment is configured to allow pauses, participants, upon clicking the exit button, will be redirected to the pause page where they are given the option to resume or terminate the experiment. The end page informs participants that they have reached the end of the experiment.