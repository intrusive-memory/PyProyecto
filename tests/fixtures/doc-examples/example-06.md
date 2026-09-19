---
schemaVersion: 4
type: project
title: "Daily Languages"
author: Tom Stovall
created: 2025-06-01T00:00:00Z
description: Single PROJECT.md supporting multiple languages via episode path templating.
language: null  # Multi-language support

seasons:
  - number: 1
    episodes: 365
    episodesDir: episodes

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

# Template for episode file paths with language variable
episodePath: "episodes/season-{season}/lesson-{number:03d}.{language}.fountain"

cast:
  - character: INSTRUCTOR
    gender: M
    voiceDescription: Native speaker
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron
        - com.apple.voice.compact.es-MX.Juan
        - com.apple.voice.compact.fr-FR.Bernard

  - character: STUDENT
    gender: F
    voices:
      apple:
        - com.apple.voice.compact.en-US.Victoria
        - com.apple.voice.compact.es-MX.Paulina
        - com.apple.voice.compact.fr-FR.Chloe

tts:
  provider: apple
  voiceLanguage: en-US
---

# Daily Languages

## Episode Path Resolution

The `episodePath` template dynamically resolves episode paths based on season and language:

### Template: `episodes/season-{season}/lesson-{number:03d}.{language}.fountain`

### Examples:

| Season | Episode | Language | Resolved Path |
|--------|---------|----------|---------------|
| 1 | 1 | en | `episodes/season-1/lesson-001.en.fountain` |
| 1 | 15 | en | `episodes/season-1/lesson-015.en.fountain` |
| 1 | 1 | es | `episodes/season-1/lesson-001.es.fountain` |
| 1 | 365 | fr | `episodes/season-1/lesson-365.fr.fountain` |

## Directory Structure
