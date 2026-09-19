---
schemaVersion: 4
type: project
title: "lingua-matra — English Lessons"
author: Tom Stovall
created: 2025-06-01T00:00:00Z
language: en

seasons:
  - number: 1
    episodes: 365
    episodesDir: episodes/season-1

episodePath: "episodes/season-{season}/episode-{number:03d}.{language}.fountain"

cast:
  - character: NARRATOR
    actor: Tom Stovall
    language: en-US
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron

tts:
  provider: apple
  voiceLanguage: en-US
---
