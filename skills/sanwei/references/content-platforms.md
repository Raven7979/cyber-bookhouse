# Content platform matrix

“Supported” means the workflow can accept a link or file and preserve whatever
the current Agent can legitimately access. It never guarantees media download,
full text, subtitles, or transcript.

## Acquisition order

Use the first method that can satisfy the request:

1. User-provided local file or platform export.
2. Public page, official transcript, subtitles, or RSS.
3. User-authorized browser session for content the user can access.
4. Metadata-only note with the source link and limitation.

Do not bypass login, CAPTCHA, paywalls, DRM, tokenized media controls, rate
limits, robots restrictions, or platform permissions. Do not read browser
cookies or copy private session data into notes, logs, or setup evidence.

## Articles and documents

| Platform or format | Default handling | Common limitation |
| --- | --- | --- |
| Public websites, blogs, news pages | Public-page text and images | Dynamic or blocked pages |
| WeChat public articles | Public page when accessible | Login or anti-automation |
| Zhihu | Public page or authorized browser | Login and folded content |
| Xiaohongshu notes | Authorized browser or user export | Login and dynamic rendering |
| Toutiao, Baijiahao, Sohu | Public page when accessible | Dynamic rendering |
| Weibo posts and articles | Public page or authorized browser | Login and incomplete threads |
| Feishu documents | Authorized user access or official export | Document permission |
| Public Notion pages | Public page or official export | Private workspace permission |
| PDF, Word, Markdown, TXT, PPT | User-provided file | Scans may require OCR |

For a private Feishu or Notion document, process only content the user has
explicitly opened or exported. Never broaden sharing permissions.

## Video

| Platform | Default handling | Transcript rule |
| --- | --- | --- |
| Bilibili | Public metadata, shownotes, visible subtitles, or user file | Use visible subtitles or actual local ASR |
| YouTube | Public metadata, chapters, official subtitles, or user file | Record subtitle language and source |
| Douyin | Share page, authorized browser, or user file | Do not promise direct download |
| WeChat Channels | Share link or user-provided video | Link alone may be metadata-only |
| Xiaohongshu video | Authorized browser or user file | Do not infer speech from caption |
| Kuaishou | Share page, authorized browser, or user file | Do not promise direct download |
| Weibo video | Public post or user file | Separate post text from video speech |
| Local MP4, MOV, MKV, WebM | User-provided file | Local ASR is allowed when requested |

When only a title, caption, or cover is accessible, set `content_status` to
`metadata_only`. Never summarize unseen video content.

## Podcasts and audio

| Platform | Default handling | Transcript rule |
| --- | --- | --- |
| 小宇宙 | Public episode page plus accessible shownotes and timepoints | Use an exposed official transcript, user file, or actual local ASR |
| Apple Podcasts | Public episode metadata, publisher link, or user file | Prefer publisher transcript or user file |
| Spotify podcasts | Public metadata or user file | Login and media access may limit processing |
| Public podcast RSS | RSS metadata and lawful enclosure access | Preserve feed and episode URLs |
| Local MP3, M4A, WAV, FLAC | User-provided file | Local ASR is allowed when requested |

### 小宇宙

For an accessible episode page, preserve:

- episode title and source URL;
- podcast name;
- host or guests only when shown;
- publish time and duration when shown;
- shownotes, chapters, and timepoints actually present on the page.

Create a transcript only when one of these is true:

1. The official page exposes a transcript.
2. The user provides the audio or an authorized export.
3. The current Agent can lawfully access the audio, the user requests
   transcription, and processing stays within the declared privacy boundary.

Do not discover or download hidden media URLs by bypassing tokenized controls.
If audio is unavailable, create a `metadata_only` note instead of guessing.

## Acceptance

Before describing a platform as fully handled for a specific source, verify:

1. The source URL or file is preserved.
2. The note distinguishes page text, subtitle text, and ASR text.
3. Any transcript has real evidence and a recorded status.
4. Obsidian displays the note and any local asset.
5. Access limitations are visible to the reader.
