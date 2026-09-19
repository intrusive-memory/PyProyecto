---
schemaVersion: 4
type: overview
title: "lingua-matra — Polyglot Language Lessons"
author: Tom Stovall
created: 2025-06-01T00:00:00Z
description: Daily language lessons teaching English, Spanish, and French through immersive storytelling and cultural context.
genre: Educational
tags: [language, learning, education, culture]

seasons:
  - number: 1
    title: "Beginner's Journey"
    description: "Foundation vocabulary and phrase patterns"
    episodes: 365
    releaseDate: 2025-06-01T00:00:00Z
    episodesDir: episodes/season-1

languages:
  - code: en
    name: English
    locale: en-US
  - code: es
    name: Español
    locale: es-MX
  - code: fr
    name: Français
    locale: fr-FR

variants:
  - season: 1
    language: en
    path: episodes/season-1/PROJECT_en.md
    status: published
  - season: 1
    language: es
    path: episodes/season-1/PROJECT_es.md
    status: published
  - season: 1
    language: fr
    path: episodes/season-1/PROJECT_fr.md
    status: in_progress

audioDir: audio
exportFormat: m4a

cast:
  - character: INSTRUCTOR
    gender: M
    voiceDescription: Native speaker, patient teaching voice
    voices:
      apple: {}  # Language-specific voices defined in variants

  - character: STUDENT
    gender: F
    voiceDescription: Learner voice, asking questions
    voices:
      apple: {}  # Language-specific voices defined in variants

tts:
  provider: apple
  voiceLanguage: en-US
---

# lingua-matra — Polyglot Lessons

Learn languages through engaging, culturally-rich stories.

## Master File Overview

This is the **master index** file. Each language version has its own `PROJECT.md`:

- **English**: `episodes/season-1/PROJECT_en.md`
- **Spanish**: `episodes/season-1/PROJECT_es.md`
- **French**: `episodes/season-1/PROJECT_fr.md`

Each variant file contains language-specific metadata, voice selections, and episode paths.
