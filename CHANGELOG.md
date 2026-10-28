# Changelog

## 0.2.0 — 28 October 2026

- Explain PNG/DDS/ZIP contents, source compatibility and character metadata conflicts before export.
- Check ZIP compatibility before choosing a destination and explain unsupported legacy/layout versions.
- Save and reopen editable palette projects with colors, source identity and export details.
- Recover atomic local drafts as separate unsaved projects and review changed game sources.
- Keep project saving separate from image/mod export and direct apply.
- Preserve fresh unrelated metadata and slots during ZIP export; reject changed target palettes.
- Compare requested colors with stored gameplay colors and a difference view.
- Highlight materials with fitting differences and show the largest RGBA errors.

## 0.1.0

- Preview a character's sprites beside its editable palette.
- Browse installed palette slots and sprites using thumbnails.
- Edit colors and materials with a live color wheel, undo and redo.
- Import and export PNG/DDS palettes.
- Edit mod name, description and version before exporting a Mod Manager ZIP.
- Include both menu and gameplay palettes in mod exports.
- Apply directly through Mod Manager with backups, verification and stale-file checks.
- Preserve earlier direct edits to other slots and detect changed character mods.
