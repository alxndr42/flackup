from collections import namedtuple

from mutagen.flac import FLAC


"""A subset of FLAC cue sheet track data.

See: https://xiph.org/flac/format.html#cuesheet_track
"""
CueSheetTrack = namedtuple('CueSheetTrack', 'number offset type')


class CueSheet():
    """A subset of FLAC cue sheet data.

    See: https://xiph.org/flac/format.html#metadata_block_cuesheet
    """

    def __init__(self, mutagen_cuesheet):
        def track(t):
            return CueSheetTrack(t.track_number, t.start_offset, t.type)

        self._mcs = mutagen_cuesheet
        self.tracks = [track(t) for t in mutagen_cuesheet.tracks]

    @property
    def is_cd(self):
        return self._mcs.compact_disc

    @property
    def lead_in(self):
        return self._mcs.lead_in_samples


class FileInfo():
    """Read and write FLAC metadata."""

    def __init__(self, filename):
        self.filename = str(filename)
        self.parse_ok = False
        self.parse_exception = None
        self.cuesheet = None
        self.comments = None
        self.parse()

    def parse(self):
        try:
            self._flac = FLAC(self.filename)
            if self._flac.cuesheet is not None:
                self.cuesheet = CueSheet(self._flac.cuesheet)
            else:
                self.cuesheet = None
            self.parse_ok = True
            self.parse_exception = None
        except Exception as e:
            self.parse_ok = False
            self.parse_exception = e
            self.cuesheet = None
