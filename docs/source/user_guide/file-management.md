(target-file-management)=
# File Management

e-Babylab also features a file browser which allows users to create folders, upload, and manage their own experiment files, such as audio and visual stimuli, custom HTML and CSS files.

:::{figure} https://github.com/user-attachments/assets/0c430c58-74c9-4128-b2f2-20af01a91019
:alt: File browser

File browser
:::

## Supported File Types

The supported file extensions for each of the allowed file types are as follows:

| Type     | Formats |
| -------- | ------- |
| Audio    | `.mp3`, `.wav` |
| Document | `.css`, `.csv`, `.docx`, `.html`, `.pdf`, `.rtf`, `.tpl`, `.txt`, `.xlsx` |
| Image    | `.gif`, `.jpeg`, `.jpg`, `.png` |
| Video    | `.mp4`, `.ogg`, `.webm` |

## Recommended File Sizes and Formats

The recommended file sizes and formats for different types of stimuli are as follows:

| Media Type | Format | Resolution | Bitrate | File Size | Frame Rate |
|------------|--------|------------|---------|-----------|------------|
| **Video**  | MP4 with H.264 codec | 720p (1280×720) or lower | 2–4 Mbps | Aim for under 10 MB per minute | 30 fps or lower |
| **Images** | JPEG for photographs, PNG for graphics with transparency | 1280×720 pixels or lower | — | Under 200 KB per image | — |
| **Audio**  | MP3 | — | 128–192 kbps | Aim for under 1 MB per minute | — |

:::{tip}
- Use [Handbrake](https://handbrake.fr/) to convert videos into different formats.
- Keep the file sizes as small as possible to ensure quick loading times (i.e. minimise lag in experiments).
:::
