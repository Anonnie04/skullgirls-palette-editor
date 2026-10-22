"""Preview installed palette slots using the currently selected sprite."""
import io
import numpy as np
from PIL import Image
from decoder import GFS
from palette import palette_slots


class PaletteCatalog:
    def __init__(self, document, frame):
        self.document, self.frame = document, frame
        self.frame_indices = palette_slots(document.source, document.character)
        self.colors = {}
        with GFS(document.source / 'sprites.gfs') as archive:
            for slot in self.frame_indices:
                with Image.open(io.BytesIO(archive.read(f'sprites/{document.character}_{slot}p.dds'))) as image:
                    self.colors[slot] = np.array(image.convert('RGBA'), dtype=np.uint8)
        self.colors[document.slot] = document.colors.copy()

    def render(self, slot, original=False):
        return self.document.render(self.frame, palette=self.colors[slot])
