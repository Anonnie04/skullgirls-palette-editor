"""Versioned local palette projects and atomic, per-document recovery drafts."""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import tempfile
import uuid
import numpy as np
from decoder import NAMES
from mod_info import validate_details


FORMAT = 'skullgirls-palette-project'
DRAFT_FORMAT = 'skullgirls-palette-draft'
MAX_FILE_SIZE = 2 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    """Flush a sibling temporary file, then replace; failure leaves the old file."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_FILE_SIZE + 1)
    if len(raw) > MAX_FILE_SIZE:
        raise ValueError('Palette project or draft is too large (maximum 2 MiB).')
    try:
        return json.loads(raw), digest(raw)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError('Cannot read this palette project or draft: invalid JSON.') from exc


def palette_array(value):
    try:
        if (not isinstance(value, list)
                or any(not isinstance(row, list) or any(not isinstance(color, list)
                       or any(type(channel) is not int for channel in color) for color in row) for row in value)):
            raise ValueError()
        array = np.asarray(value)
        if (array.ndim != 3 or not 1 <= array.shape[0] <= 256 or array.shape[1:] != (16, 4)
                or array.dtype.kind not in 'iu' or np.any(array < 0) or np.any(array > 255)):
            raise ValueError()
        return array.astype(np.uint8)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('Project colors must be 1–256 rows of 16 RGBA byte values.') from exc


def validate_project(data):
    if (not isinstance(data, dict) or data.get('format') != FORMAT
            or type(data.get('version')) is not int or data['version'] != 1):
        raise ValueError('Unsupported palette project format or version.')
    if (not isinstance(data.get('character'), str) or data['character'] not in NAMES or type(data.get('slot')) is not int
            or not 1 <= data['slot'] <= 256):
        raise ValueError('Invalid project character or palette slot.')
    source = data.get('source')
    if (not isinstance(source, dict) or not isinstance(source.get('folder'), str)
            or not Path(source['folder']).is_absolute()):
        raise ValueError('The project needs its source game data folder.')
    for name in ('dds_sha256', 'metadata_sha256'):
        value = source.get(name)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Invalid project source fingerprint.')
    original, colors = palette_array(data.get('original')), palette_array(data.get('colors'))
    if original.shape != colors.shape:
        raise ValueError('Project source and edited palette dimensions differ.')
    validate_details(data.get('mod_details'))
    return original, colors


def project_data(document):
    return dict(format=FORMAT, version=1, character=document.character, slot=document.slot,
                source=dict(folder=str(document.source), dds_sha256=digest(document.dds),
                            metadata_sha256=digest(document.metadata)),
                original=document.original.tolist(), colors=document.colors.tolist(),
                mod_details=validate_details(document.mod_details))


def mark_saved(document):
    document.saved = document.colors.copy()
    document.saved_details = document.mod_details.copy()
    document.saved_baseline = (document.dds, document.metadata)


def save_project(document, path):
    path = document.output_path(path)
    if path == document.project_path and document.project_digest is not None:
        if not path.is_file() or digest(path.read_bytes()) != document.project_digest:
            raise ValueError('This project changed or was removed outside the editor. Use Save project as to keep both versions.')
    payload = encode(project_data(document))
    if len(payload) > MAX_FILE_SIZE:
        raise ValueError('Project is too large (maximum 2 MiB). Shorten the export description.')
    atomic_write(path, payload)
    document.project_path, document.project_digest = path, digest(payload)
    mark_saved(document)


@dataclass
class ProjectOpening:
    document: object
    data: dict
    path: Path
    file_digest: str
    source_changed: bool
    recovered: bool = False

    def finish(self, reapply=True):
        """Rebase only explicitly edited pixels when the source has changed."""
        doc = self.document
        original, colors = validate_project(self.data)
        if reapply:
            mask = np.any(original != colors, axis=2)
            doc.colors = np.where(mask[:, :, None], colors, doc.original).astype(np.uint8)
            doc.mod_details = validate_details(self.data['mod_details'])
        if not self.recovered and reapply:
            doc.project_path, doc.project_digest = self.path, self.file_digest
        if not self.recovered and not self.source_changed and reapply:
            mark_saved(doc)
        elif self.recovered or (self.source_changed and reapply):
            # A recovered/rebased document needs an explicit save even if its
            # colors happen to equal today's source palette.
            doc.saved_baseline = (b'', b'')
        if self.recovered:
            doc.recovery_origin = (self.path, self.file_digest)
        return doc


def open_project(path, game=None, recovered=False):
    from palette import PaletteDocument
    path = Path(path).resolve()
    data, file_digest = read_json(path)
    if recovered:
        if (not isinstance(data, dict) or data.get('format') != DRAFT_FORMAT
                or type(data.get('version')) is not int or data['version'] != 1):
            raise ValueError('Unsupported recovery draft format or version.')
        data = data.get('document')
    original, _ = validate_project(data)
    doc = PaletteDocument(game or data['source']['folder'], data['character'], data['slot'])
    if original.shape != doc.original.shape:
        raise ValueError('The source has different material dimensions; edits were not loaded. '
                         'Choose the matching game folder above, then use Open project → '
                         'Open project using selected game folder.')
    changed = (digest(doc.dds) != data['source']['dds_sha256']
               or digest(doc.metadata) != data['source']['metadata_sha256']
               or not np.array_equal(original, doc.original))
    return ProjectOpening(doc, data, path, file_digest, changed, recovered)


class DraftStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.last_payload = {}

    def path_for(self, document):
        if not hasattr(document, 'recovery_id'):
            document.recovery_id = uuid.uuid4().hex
        return self.directory / (document.recovery_id + '.sgdraft')

    def pending(self):
        return sorted(self.directory.glob('*.sgdraft'), key=lambda path: path.stat().st_mtime, reverse=True)

    def write(self, document):
        path = self.path_for(document)
        snapshot = project_data(document)
        content = encode(snapshot)
        if self.last_payload.get(path) == content and path.is_file():
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        envelope = dict(format=DRAFT_FORMAT, version=1,
                        written_at=datetime.now(timezone.utc).isoformat(), document=snapshot,
                        project_path=str(document.project_path) if document.project_path else None,
                        project_digest=document.project_digest)
        payload = encode(envelope)
        if len(payload) > MAX_FILE_SIZE:
            raise ValueError('Draft is too large (maximum 2 MiB). Shorten the export description.')
        atomic_write(path, payload)
        self.last_payload[path] = content

    def remove(self, document):
        path = self.path_for(document)
        path.unlink(missing_ok=True)
        self.last_payload.pop(path, None)
        origin = getattr(document, 'recovery_origin', None)
        if origin and origin[0].is_file() and digest(origin[0].read_bytes()) == origin[1]:
            origin[0].unlink()
            document.recovery_origin = None

    def recovery_note(self, path):
        data, _ = read_json(path)
        if (not isinstance(data, dict) or data.get('format') != DRAFT_FORMAT
                or type(data.get('version')) is not int or data['version'] != 1):
            raise ValueError('Choose a palette recovery draft.')
        validate_project(data.get('document'))
        project = data.get('project_path')
        if project is not None and not isinstance(project, str):
            raise ValueError('Invalid recovery project path.')
        changed = project and (not Path(project).is_file()
                               or digest(Path(project).read_bytes()) != data.get('project_digest'))
        name = NAMES[data['document']['character']]
        return (f"{name} · palette {data['document']['slot']}\nDraft: {data.get('written_at', 'unknown time')}\n" +
                ('The linked project has changed or is missing.\n' if changed else '') +
                'Recover as a separate unsaved project? The linked project will not be overwritten.')
