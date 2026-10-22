# Release checklist

1. Update `version.py` and `CHANGELOG.md`.
2. Install `requirements-dev.txt` with Python 3.12 on Windows x64.
3. Build the compatible Mod Manager source revision documented in the README.
4. Set `PALETTE_MANAGER_ROOT` if it is not the sibling `Skullgirls Mod Manager`.
5. Run `python scripts/build_release.py`. Tests use synthetic games only.
6. Check `release/`: the Windows ZIP, matching source ZIP and `SHA256SUMS.txt`.
   Release archives use explicit file lists; installed game data, mods,
   backups, local paths and operation logs must stay excluded.
7. Create a GitHub release tagged `v<version>` and attach those three files.
   The Windows workflow also produces downloadable build artifacts on main
   pushes, version tags and manual runs. It does not publish releases automatically.

Ship the entire portable ZIP with notices and `manager_bridge/source.zip`.
The separate GPL bridge's corresponding source must accompany its binary.
The installed Mod Manager runtime remains external. Never bundle game assets
or a compatibility loader. See the README for end-user prerequisites.
