from collections import namedtuple

from mutagen.flac import FLAC


"""Tag names supported for albums and tracks."""
FLACKUP_TAGS = ['TITLE', 'ARTIST', 'PERFORMER', 'GENRE', 'DATE', 'HIDE']


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

    @property
    def audio_track_numbers(self):
        def is_audio(track):
            return track.type == 0 and track.number != 170

        return [t.number for t in self.tracks if is_audio(t)]


class Tags(object):
    """Flackup album and track tags.

    Supported tag names for albums and tracks:
    - TITLE
    - ARTIST
    - PERFORMER
    - GENRE
    - DATE
    - HIDE ('yes' to ignore for conversion/playback)

    This class supports only one string value per tag.

    See also: https://www.xiph.org/vorbis/doc/v-comment.html
    """

    def __init__(self, vorbis_tags):
        if vorbis_tags is not None:
            self._tags = vorbis_tags
        else:
            self._tags = {}

    def album_tags(self):
        return self._collect_tags('', *FLACKUP_TAGS)

    def track_tags(self, number):
        prefix = 'TRACK_%02d_' % number
        return self._collect_tags(prefix, *FLACKUP_TAGS)

    def _collect_tags(self, prefix, *args):
        result = {}
        for name in args:
            key = prefix + name
            if key in self._tags:
                result[name] = self._tags[key][0]
        return result


class FileInfo():
    """Read and write FLAC metadata."""

    def __init__(self, filename):
        self.filename = str(filename)
        self.parse_ok = False
        self.parse_exception = None
        self.cuesheet = None
        self.tags = None
        self.parse()

    def parse(self):
        try:
            self._flac = FLAC(self.filename)
            if self._flac.cuesheet is not None:
                self.cuesheet = CueSheet(self._flac.cuesheet)
                self.tags = Tags(self._flac.tags)
            else:
                self.cuesheet = None
                self.tags = None
            self.parse_ok = True
            self.parse_exception = None
        except Exception as e:
            self.parse_ok = False
            self.parse_exception = e
            self.cuesheet = None
            self.tags = None
