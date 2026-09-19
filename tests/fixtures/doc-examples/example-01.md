---
schemaVersion: 4
type: project
title: "Podcast Meditations"
author: Tom Stovall
created: 2025-01-25T00:00:00Z
description: A year-long daily journey through Marcus Aurelius' Meditations, exploring Stoic philosophy for modern life.
genre: Documentary
tags: [mindfulness, philosophy, stoicism, meditation]

seasons:
  - number: 1
    title: "Year One"
    description: "Books I-IV of Meditations"
    episodes: 365
    releaseDate: 2025-01-25T00:00:00Z
    episodesDir: episodes
    filePattern: "*.fountain"

audioDir: audio
exportFormat: m4a
preGenerateHook: "make validate"
postGenerateHook: "make publish"

cast:
  - character: NARRATOR
    actor: Tom Stovall
    gender: M
    voiceDescription: Warm, measured baritone with philosophical gravitas
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron
      elevenlabs:
        - 21m00Tcm4TlvDq8ikWAM

  - character: MARCUS AURELIUS
    voiceDescription: Ancient Roman emperor, introspective and wise
    voices:
      apple:
        - com.apple.voice.compact.en-US.Moira

tts:
  provider: apple
  voiceLanguage: en-US
  actionLineVoice: null
---

# Podcast Meditations

A daily exploration of Marcus Aurelius' timeless wisdom...

## Project Structure
