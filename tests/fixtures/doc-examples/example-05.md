---
schemaVersion: 4
type: project
title: "lingua-matra — Lecciones de Español"
author: Tom Stovall
created: 2025-06-01T00:00:00Z
description: Lecciones diarias de español con contexto cultural y personajes atractivos.
language: es

seasons:
  - number: 1
    title: "Viaje del Principiante"
    description: "Vocabulario fundamental y patrones de frases"
    episodes: 365
    releaseDate: 2025-06-01T00:00:00Z
    episodesDir: .
    filePattern: "*.es.fountain"

audioDir: ../audio/es
exportFormat: m4a

cast:
  - character: INSTRUCTOR
    actor: Tom Stovall
    gender: M
    language: es-MX
    voiceDescription: Hablante nativo de español mexicano
    voices:
      apple:
        - com.apple.voice.compact.es-MX.Juan

  - character: STUDENT
    gender: F
    language: es-MX
    voiceDescription: Estudiante de español
    voices:
      apple:
        - com.apple.voice.compact.es-MX.Paulina

tts:
  provider: apple
  voiceLanguage: es-MX
---

# lingua-matra — Lecciones de Español

## Estructura de Archivos

Los episodios siguen el patrón: `lesson-NNN.es.fountain`
