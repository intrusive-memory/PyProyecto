---
schemaVersion: 4
type: project
title: "Complete Meditations"
author: Tom Stovall
created: 2025-01-25T00:00:00Z
description: Four-year exploration of all twelve books of Marcus Aurelius' Meditations, released seasonally with new perspectives each year.
genre: Documentary
tags: [philosophy, stoicism, education]

seasons:
  - number: 1
    title: "Year One: Books I-IV"
    description: "Foundation and virtue"
    episodes: 365
    releaseDate: 2025-01-25T00:00:00Z
    episodesDir: episodes/season-1
    filePattern: "*.fountain"

  - number: 2
    title: "Year Two: Books V-VIII"
    description: "Mind and action"
    episodes: 365
    releaseDate: 2026-01-25T00:00:00Z
    episodesDir: episodes/season-2
    filePattern: "*.fountain"

  - number: 3
    title: "Year Three: Books IX-X"
    description: "Adversity and wisdom"
    episodes: 365
    releaseDate: 2027-01-25T00:00:00Z
    episodesDir: episodes/season-3
    filePattern: "*.fountain"

  - number: 4
    title: "Year Four: Books XI-XII"
    description: "Legacy and acceptance"
    episodes: 365
    releaseDate: 2028-01-25T00:00:00Z
    episodesDir: episodes/season-4
    filePattern: "*.fountain"

audioDir: audio
exportFormat: m4a

cast:
  - character: NARRATOR
    actor: Tom Stovall
    gender: M
    voiceDescription: Primary narrator, warm and thoughtful
    voices:
      apple:
        - com.apple.voice.compact.en-US.Aaron

  - character: MARCUS AURELIUS
    voiceDescription: Roman emperor, introspective
    voices:
      apple:
        - com.apple.voice.compact.en-US.Moira

  - character: HISTORIAN
    voiceDescription: Classical scholar, authoritative
    voices:
      apple:
        - com.apple.voice.compact.en-US.Victoria

tts:
  provider: apple
  voiceLanguage: en-US
---

# Complete Meditations

A comprehensive four-year journey through Marcus Aurelius' teachings...

## Directory Structure

Each season is organized in its own directory:
