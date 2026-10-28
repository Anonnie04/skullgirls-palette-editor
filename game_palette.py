"""Read embedded FOIT gradient colors and patch only their existing byte spans."""
import struct
import numpy as np
from decoder import Reader


def metadata_version(metadata):
    if len(metadata) < 12:
        raise ValueError('Truncated character metadata; cannot read gameplay palettes.')
    if metadata[4:8] != b'VRSN':
        raise ValueError('This game build uses legacy embedded palettes. This editor requires a DDS-based game build with supported character metadata.')
    version = struct.unpack_from('<I', metadata, 8)[0]
    if version not in (3, 9):
        raise ValueError(f'Character metadata layout version {version} is unsupported. This editor supports layouts 3 and 9.')
    return version


def layout(metadata):
    try:
        metadata_version(metadata)
        start = struct.unpack_from('<I', metadata)[0]
        if not 12 <= start < len(metadata):
            raise ValueError('Invalid embedded palette offset.')
        reader = Reader(metadata, start)
        reader.read(reader.num('B'))  # Character label.
        reader.read(4)
        if reader.num('B') != 1:
            raise ValueError('Unsupported embedded palette table.')
        slots, rows = reader.num('H'), reader.num('B')
        if not 1 <= slots <= 256 or not rows:
            raise ValueError('Invalid palette dimensions.')
        counts = []
        for _ in range(rows):
            count = reader.num('B')
            if not 1 <= count <= 16:
                raise ValueError('Unsupported number of gradient points.')
            counts.append(count)
            reader.read(2)  # Material lighting flags.
            label = reader.read(reader.num('B'))
            if not label or any(c < 32 for c in label):
                raise ValueError('Invalid material label.')
        mappings = reader.num('B')
        reader.read(mappings * 8)
        if reader.pos + sum(counts) * 4 + 8 > len(metadata):
            raise ValueError('Truncated embedded palette colors.')
        return slots, counts, reader.pos
    except (AssertionError, struct.error, IndexError) as exc:
        raise ValueError('Cannot read the embedded gameplay palette table.') from exc


def weights(count):
    x = np.linspace(0, count - 1, 16)
    lo = x.astype(int)
    hi = np.minimum(lo + 1, count - 1)
    result = np.zeros((16, count))
    result[np.arange(16), lo] += 1 - (x - lo)
    result[np.arange(16), hi] += x - lo
    return result


def expand(metadata, start, counts):
    rows = []
    for count in counts:
        points = np.frombuffer(metadata, np.uint8, count * 4, start).reshape(count, 4)[:, [2, 1, 0, 3]][::-1]
        rows.append(np.clip(np.floor(weights(count) @ points), 0, 255).astype(np.uint8))
        start += count * 4
    return np.array(rows)


def locate(metadata, slot, reference):
    slots, counts, first = layout(metadata)
    if not 1 <= slot <= slots or reference.shape != (len(counts), 16, 4):
        raise ValueError('Gameplay palette dimensions or slot do not match the DDS.')
    if slot == 1:
        return counts, first
    # Palette records have variable effect expressions between their color spans.
    # Match the entire reference gradient rather than assuming a fixed slot stride.
    candidates = set()
    markers = []
    row_offset = 0
    size = sum(counts) * 4
    fitted = [np.clip(np.rint(np.linalg.lstsq(weights(count), reference[row].astype(float), rcond=None)[0]), 0, 255).astype(np.uint8)
              for row, count in enumerate(counts)]
    for row, count in enumerate(counts):
        for shade, point in ((15, 0), (0, count - 1)):
            color = reference[row, shade]
            if color[3] == 0:
                continue
            for marker in (color[[2, 1, 0, 3]].tobytes(), fitted[row][count - 1 - point, [2, 1, 0, 3]].tobytes()):
                frequency = metadata.count(marker)
                if 0 < frequency <= 256:
                    markers.append((frequency, marker, row_offset + point * 4))
        row_offset += count * 4
    for _, marker, relative in sorted(markers)[:8]:
        at = first + 1
        while True:
            at = metadata.find(marker, at)
            if at < 0:
                break
            candidate = at - relative
            if first + size <= candidate <= len(metadata) - size - 8:
                candidates.add(candidate)
            at += 1
    matches = []
    for candidate in sorted(candidates):
        colors = expand(metadata, candidate, counts)
        error = np.abs(colors.astype(int) - reference.astype(int))
        # Fully transparent RGB channels can differ in generated menu DDS files.
        error[:, :, :3][(colors[:, :, 3] == 0) & (reference[:, :, 3] == 0)] = 0
        point_errors = []
        pos = candidate
        for row, count in enumerate(counts):
            points = np.frombuffer(metadata, np.uint8, count * 4, pos).reshape(count, 4)[:, [2, 1, 0, 3]][::-1]
            delta = np.abs(points.astype(int) - fitted[row].astype(int))
            delta[:, :3][(points[:, 3] == 0) & (fitted[row][:, 3] == 0)] = 0
            point_errors.append(np.max(delta))
            pos += count * 4
        if np.max(error) <= 2 or max(point_errors) <= 2:
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError('Cannot uniquely identify this gameplay palette. Load an unmodified game palette, then import your saved palette PNG or DDS.')
    return counts, matches[0]


def patch(metadata, slot, original, edited):
    counts, start = locate(metadata, slot, original)
    result = bytearray(metadata)
    existing = expand(metadata, start, counts)
    position = start
    changed = []
    for row, count in enumerate(counts):
        error = np.abs(existing[row].astype(int) - edited[row].astype(int))
        error[:, :3][(existing[row, :, 3] == 0) & (edited[row, :, 3] == 0)] = 0
        if not np.array_equal(original[row], edited[row]) or np.max(error) > 2:
            # Gameplay stores a few gradient points per material, not 16 samples.
            points = np.linalg.lstsq(weights(count), edited[row].astype(float), rcond=None)[0]
            points = np.clip(np.rint(points), 0, 255).astype(np.uint8)
            if np.array_equal(original[row, :, 3], edited[row, :, 3]) and np.max(error[:, 3]) <= 2:
                points[:, 3] = np.frombuffer(metadata, np.uint8, count * 4, position).reshape(count, 4)[::-1, 3]
            payload = points[::-1, [2, 1, 0, 3]].tobytes()
            result[position:position + count * 4] = payload
            changed.append((position, count * 4))
        position += count * 4
    if len(result) != len(metadata):
        raise ValueError('Gameplay metadata size changed unexpectedly.')
    return bytes(result), changed
