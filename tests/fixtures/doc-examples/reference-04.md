---
schemaVersion: 4
type: project
title: "Complete Meditations"
author: Tom Stovall
created: 2025-01-25T00:00:00Z
description: Stoic philosophy for modern life

seasons:
  - number: 1
    title: "Year One"
    description: "Books I-IV"
    episodes: 365
    releaseDate: 2025-01-25T00:00:00Z
    episodesDir: episodes/season-1
    filePattern: "*.fountain"

  - number: 2
    title: "Year Two"
    description: "Books V-VIII"
    episodes: 365
    releaseDate: 2026-01-25T00:00:00Z
    episodesDir: episodes/season-2
    filePattern: "*.fountain"

audioDir: audio
exportFormat: m4a

cast:
  - character: NARRATOR
    actor: Tom Stovall
    gender: M
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron

tts:
  provider: apple
  voiceLanguage: en-US
---
