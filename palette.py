"""Palette documents and read-only game previews; exports target Mod Manager."""
from pathlib import Path
import colorsys
import hashlib
import io
import json
import re
import struct
import zipfile
import numpy as np
from PIL import Image
from decoder import GFS, NAMES, data_folder, parse_frames_data, decode_image, colorize
from game_palette import patch as patch_game_palette
from mod_info import validate_details


def palette_source(game):
    """Follow the same verified data02 redirect as Mod Manager, when active."""
    game = Path(game).expanduser().resolve()
    loader = game / 'CoreMessaging.dll'
    if (game / 'data02').is_dir() and loader.is_file():
        digest = hashlib.sha256(loader.read_bytes()).hexdigest()
        if digest == '014bfb8c48fa7afbcd585a34d814011b96b289c742482a01376f56aafa1e11d3':
            return data_folder(game / 'data02')
    return data_folder(game)


def palette_slots(game, character):
    source = palette_source(game)
    with GFS(source / 'sprites.gfs') as archive:
        pattern = re.compile(r'(?:sprites|temp/true_color_sprites)/' + re.escape(character) + r'_(\d+)p\.dds$')
        return sorted({int(m[1]) for path in archive.entries if (m := pattern.fullmatch(path))})


class PaletteDocument:
    def __init__(self, game, character, slot):
        if character not in NAMES or not isinstance(slot, int) or slot < 1:
            raise ValueError('Choose a character and palette slot.')
        self.source = palette_source(game)
        self.character, self.slot = character, slot
        self.mod_details = dict(name=f'{NAMES[character]} palette {slot}',
                                desc='Custom character-select and gameplay palette. Requires the game version used for export.',
                                version='1.1.0')
        with GFS(self.source / 'sprites.gfs') as archive:
            key = f'sprites/{character}_{slot}p.dds'
            location = archive.entries[key]
            self.internal = next(path for path, value in archive.entries.items() if value == location)
            self.dds = archive.read(key)
        with Image.open(io.BytesIO(self.dds)) as image:
            if image.width != 16 or not 1 <= image.height <= 256:
                raise ValueError('Expected a palette with 16 shades per material and at most 256 materials.')
            self.original = np.array(image.convert('RGBA'), dtype=np.uint8)
        # Preserve the installed texture header, channel masks, alpha and flags.
        header = struct.unpack_from('<31I', self.dds, 4)
        if (header[18] != 32 or header[19] & 0x41 != 0x41 or header[20] != 0
                or header[21:26] != (32, 0xff0000, 0xff00, 0xff, 0xff000000)
                or header[6] not in (0, 1) or header[27] != 0
                or header[4] != 64 or len(self.dds) != 128 + self.original.size):
            raise ValueError('This palette texture format is not supported for lossless editing.')
        self.colors = self.original.copy()
        self.undo_stack, self.redo_stack = [], []
        self.saved = self.colors.copy()
        with GFS(self.source / 'characters-foits.gfs') as foits, GFS(self.source / 'characters-art.gfs') as art, GFS(self.source / 'characters-art-pt.gfs') as pt:
            metadata = foits.read(f'characters/{character}.foit')
            self.metadata = metadata
            location = foits.entries[f'characters/{character}.foit']
            self.metadata_internal = next(path for path, value in foits.entries.items() if value == location)
            if metadata[4:8] != b'VRSN':
                raise ValueError('This depot uses embedded legacy palettes. Select a game version with DDS palettes.')
            self.frames = parse_frames_data(character, metadata, art.entries[f'characters/{character}.art'][1])
            self.banks = {5: art.read(f'characters/{character}.art'), 4: pt.read(f'characters/{character}.art-pt')}
        self.frame_indices = [i for i, frame in enumerate(self.frames)
                              if any(k in (0, 1) and m['offset'] >= 0 and m['used'] for k, m in frame['images'].items())]
        if not self.frame_indices:
            raise ValueError('No previewable sprite frames found.')
        self.cache = {}

    @property
    def dirty(self):
        return not np.array_equal(self.colors, self.saved)

    def replace(self, colors):
        colors = np.asarray(colors)
        if colors.shape != self.original.shape or colors.dtype != np.uint8:
            raise ValueError(f'Palette must be an RGBA image of size 16 × {len(self.original)}.')
        if np.array_equal(colors, self.colors):
            return
        self.undo_stack.append(self.colors.copy())
        del self.undo_stack[:-100]
        self.redo_stack.clear()
        self.colors = colors.copy()

    def set_color(self, row, shade, rgba):
        if not 0 <= row < len(self.colors) or not 0 <= shade < 16:
            raise ValueError('Choose a valid material and shade.')
        if len(rgba) != 4 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in rgba):
            raise ValueError('RGBA values must be integers from 0 to 255.')
        colors = self.colors.copy()
        colors[row, shade] = rgba
        self.replace(colors)

    def recolor(self, row, rgb, shade=None):
        """Shift a material's hue while retaining its shading and encoded alpha."""
        self.replace(self.recolored(self.colors, row, rgb, shade))

    @staticmethod
    def recolored(baseline, row, rgb, shade=None):
        """Always derive a drag preview from its starting ramp, avoiding drift."""
        colors = baseline.copy()
        ramp = colors[row, :, :3] / 255.
        anchor = (colorsys.rgb_to_hsv(*ramp[shade]) if shade is not None else
                  max((colorsys.rgb_to_hsv(*c) for c in ramp), key=lambda c: c[2]))
        target = colorsys.rgb_to_hsv(*(c / 255. for c in rgb))
        for i, color in enumerate(ramp):
            h, s, v = colorsys.rgb_to_hsv(*color)
            shifted = colorsys.hsv_to_rgb((h + target[0] - anchor[0]) % 1,
                                         min(1, s * target[1] / anchor[1]) if anchor[1] else min(1, s + target[1]),
                                         min(1, v * target[2] / anchor[2]) if anchor[2] else min(1, v + target[2]))
            colors[row, i, :3] = np.rint(np.array(shifted) * 255).astype(np.uint8)
        return colors

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.colors.copy())
            self.colors = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.colors.copy())
            self.colors = self.redo_stack.pop()

    def layers(self, index):
        if index not in self.cache:
            frame = self.frames[index]
            layers = [decode_image(frame['images'][k], self.banks[frame['art_bank']])
                      for k in (0, 1) if k in frame['images'] and frame['images'][k]['offset'] >= 0]
            self.cache.clear()  # One decoded frame can be large.
            self.cache[index] = layers
        return self.cache[index]

    def render(self, index, original=False, palette=None):
        layers = self.layers(index)
        if palette is None:
            palette = self.original if original else self.colors
        result = Image.new('RGBA', (max(a.shape[1] for a in layers), max(a.shape[0] for a in layers)))
        for raw in layers:
            result.alpha_composite(colorize(raw, palette))
        return result

    def sample(self, index, x, y):
        for raw in reversed(self.layers(index)):
            if 0 <= y < raw.shape[0] and 0 <= x < raw.shape[1]:
                pixel = raw[y, x]
                row, shade = min(int(pixel[2]), len(self.colors) - 1), round(int(pixel[1] % 32) * 15 / 31)
                if colorize(raw[y:y+1, x:x+1], self.colors).getpixel((0, 0))[3]:
                    return row, shade
        return None

    def texture(self):
        return self.dds[:128] + self.colors[:, :, [2, 1, 0, 3]].tobytes()

    def output_path(self, path):
        path = Path(path).resolve()
        game = self.source.parent if self.source.name.lower() in ('data01', 'data02') else self.source
        if path.is_relative_to(game):
            raise ValueError('Save outside the game folder, then import the ZIP in Mod Manager.')
        return path

    def export(self, path, kind, mod_details=None, mark_saved=True):
        path = self.output_path(path)
        data = self.texture()
        buffer = io.BytesIO()
        if kind == 'zip':
            details = validate_details(self.mod_details if mod_details is None else mod_details)
            metadata, _ = patch_game_palette(self.metadata, self.slot, self.original, self.colors)
            identity = hashlib.sha256(self.internal.encode() + data + metadata).hexdigest()[:16]
            info = dict(id=f'paletteeditor.{self.character}.{self.slot}.{identity}',
                        author='Palette Editor', url=None, **details)
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('mod.json', json.dumps(info, indent=2))
                archive.writestr('sprites.gfs/' + self.internal, data)
                archive.writestr('characters-foits.gfs/' + self.metadata_internal, metadata)
            with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Mod ZIP verification failed.')
        elif kind == 'png':
            Image.fromarray(self.colors).save(buffer, format='PNG')
        elif kind == 'dds':
            buffer.write(data)
        else:
            raise ValueError('Unsupported export type.')
        path.write_bytes(buffer.getvalue())
        if kind == 'zip' and mark_saved:
            self.mod_details = details.copy()
        if mark_saved:
            self.saved = self.colors.copy()

    def import_image(self, path):
        with Image.open(path) as image:
            if image.size != (16, len(self.original)):
                raise ValueError(f'Expected a palette image of size 16 × {len(self.original)}.')
            self.replace(np.array(image.convert('RGBA'), dtype=np.uint8))


class ColorPreview:
    """One live picker session becomes one undo step, or cancels exactly."""
    def __init__(self, document, row, shade, material=False):
        self.document = document
        self.row, self.shade, self.material = row, shade, material
        self.baseline = document.colors.copy()
        self.closed = False

    def preview(self, rgb):
        if self.closed:
            return
        if self.material:
            colors = self.document.recolored(self.baseline, self.row, rgb, self.shade)
        else:
            colors = self.baseline.copy()
            colors[self.row, self.shade, :3] = rgb
        self.document.colors = colors

    def finish(self, commit):
        if self.closed:
            return
        self.closed = True
        final = self.document.colors.copy()
        self.document.colors = self.baseline.copy()
        if commit:
            self.document.replace(final)
