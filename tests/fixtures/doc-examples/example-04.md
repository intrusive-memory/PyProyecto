---
schemaVersion: 4
type: project
title: "lingua-matra — English Lessons"
author: Tom Stovall
created: 2025-06-01T00:00:00Z
description: Daily English language lessons with cultural context and engaging characters.
language: en

seasons:
  - number: 1
    title: "Beginner's Journey"
    description: "Foundation vocabulary and phrase patterns"
    episodes: 365
    releaseDate: 2025-06-01T00:00:00Z
    episodesDir: .
    filePattern: "*.en.fountain"

audioDir: ../audio/en
exportFormat: m4a

cast:
  - character: INSTRUCTOR
    actor: Tom Stovall
    gender: M
    language: en-US
    voiceDescription: Native English speaker, patient teaching voice
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron

  - character: STUDENT
    gender: F
    language: en-US
    voiceDescription: English learner, asking clarifying questions
    voices:
      apple:
        - com.apple.voice.compact.en-US.Victoria

tts:
  provider: apple
  voiceLanguage: en-US
---

# lingua-matra — English Lessons

## Episode Files

Episodes in this directory follow the naming pattern: `lesson-NNN.en.fountain`
