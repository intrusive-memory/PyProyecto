"""Variant property resolution.

Follows ``VariantResolver.resolve`` field by field. ``title``, ``author``, and
``created`` always come from the master. Most fields resolve variant -> master;
the ones a season can override resolve variant -> season -> master.
"""

from __future__ import annotations

from .models import ProjectFrontMatter, SeasonDefinition


def _first(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def resolve_variant(
    variant: ProjectFrontMatter,
    master: ProjectFrontMatter,
    season: int,
) -> ProjectFrontMatter:
    """Resolve ``variant`` against ``master`` for a given season number."""
    season_def: SeasonDefinition | None = None
    if master.seasons:
        season_def = next((s for s in master.seasons if s.number == season), None)

    tags = master.tags if not variant.tags else variant.tags
    extra = master.extra if not variant.extra else variant.extra

    return ProjectFrontMatter(
        type=variant.type,
        title=master.title,
        author=master.author,
        created=master.created,
        updated=variant.updated if variant.updated is not None else master.updated,
        description=_first(  # type: ignore[arg-type]
            variant.description,
            season_def.description if season_def else None,
            master.description,
        ),
        genre=variant.genre if variant.genre is not None else master.genre,
        tags=tags,
        episodes_dir=_first(  # type: ignore[arg-type]
            variant.episodes_dir,
            season_def.episodes_dir if season_def else None,
            master.episodes_dir,
        ),
        audio_dir=(
            variant.audio_dir if variant.audio_dir is not None else master.audio_dir
        ),
        file_pattern=_first(  # type: ignore[arg-type]
            variant.file_pattern,
            season_def.file_pattern if season_def else None,
            master.file_pattern,
        ),
        export_format=(
            variant.export_format
            if variant.export_format is not None
            else master.export_format
        ),
        intro_file=_first(  # type: ignore[arg-type]
            variant.intro_file,
            season_def.intro_file if season_def else None,
            master.intro_file,
        ),
        outro_file=_first(  # type: ignore[arg-type]
            variant.outro_file,
            season_def.outro_file if season_def else None,
            master.outro_file,
        ),
        pre_generate_hook=(
            variant.pre_generate_hook
            if variant.pre_generate_hook is not None
            else master.pre_generate_hook
        ),
        post_generate_hook=(
            variant.post_generate_hook
            if variant.post_generate_hook is not None
            else master.post_generate_hook
        ),
        tts=_first(  # type: ignore[arg-type]
            variant.tts,
            season_def.tts if season_def else None,
            master.tts,
        ),
        schema_version=master.schema_version,
        project_type=(
            variant.project_type
            if variant.project_type is not None
            else master.project_type
        ),
        seasons=master.seasons,
        languages=master.languages,
        variants=master.variants,
        episode_path=(
            variant.episode_path
            if variant.episode_path is not None
            else master.episode_path
        ),
        extra=extra,
    )
