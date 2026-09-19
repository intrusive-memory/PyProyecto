---
schemaVersion: 4
type: project
title: "Podcast Meditations"
author: Tom Stovall
created: 2025-01-25T00:00:00Z
description: A year-long journey through Marcus Aurelius wisdom
genre: Documentary
tags: [mindfulness, self-care, mental health, meditation]

seasons:
  - number: 1
    episodes: 365
    episodesDir: episodes/season-1
    filePattern: "*.fountain"

audioDir: audio
exportFormat: m4a

cast:
  - character: MARCUS AURELIUS
    actor: Tom Stovall
    gender: M
    voiceDescription: Deep, measured baritone with gravitas
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron

tts:
  provider: apple
  voiceLanguage: en-US
---
