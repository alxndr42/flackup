from collections import namedtuple

from mutagen.flac import FLAC, Picture as MutagenPicture


"""Tag names for both albums and tracks."""
_COMMON_TAGS = ['ARTIST', 'GENRE', 'HIDE', 'PERFORMER']

"""Album-level tag names."""
ALBUM_TAGS = _COMMON_TAGS + [
    'ALBUM',
    'DATE',
    'DATE_ORIGINAL',
    'DISC',
    'RELEASE_MBID',
]

"""Track-level tag names."""
TRACK_TAGS = _COMMON_TAGS + ['TITLE']

"""Flackup tags version number."""
_VERSION_NUMBER = 1

"""Tag name of the Flackup tags version number."""
_VERSION_TAG = 'FLACKUP_VERSION'


"""A subset of FLAC stream information data.

See: https://xiph.org/flac/format.html#metadata_block_streaminfo
"""
StreamInfo = namedtuple(
    'StreamInfo', 'channels sample_bits sample_rate sample_count')


"""A subset of FLAC cue sheet track data.

See: https://xiph.org/flac/format.html#cuesheet_track
"""
CueSheetTrack = namedtuple('CueSheetTrack', 'number offset type')


class CueSheet(object):
    """A subset of FLAC cue sheet data.

    Variables:
    - tracks: List of CueSheetTrack instances, including lead-out.

    See: https://xiph.org/flac/format.html#metadata_block_cuesheet
    """

    def __init__(self, mutagen_cuesheet):
        def track(t):
            return CueSheetTrack(t.track_number, t.start_offset, t.type)

        self._mcs = mutagen_cuesheet
        self.tracks = [track(t) for t in mutagen_cuesheet.tracks]

    @property
    def is_cd(self):
        """Return True if this is an audio CD cue sheet."""
        return self._mcs.compact_disc

    @property
    def lead_in(self):
        """Return the number of lead-in samples."""
        return self._mcs.lead_in_samples

    @property
    def audio_tracks(self):
        """Return a list of audio tracks, excluding lead-out."""
        return [t for t in self.tracks if t.type == 0 and t.number < 100]


class Tags(object):
    """Flackup album and track tags.

    This class supports only one string value per tag.

    See: https://www.xiph.org/vorbis/doc/v-comment.html
    """

    def __init__(self, mutagen_tags):
        if mutagen_tags is not None:
            self._tags = mutagen_tags
        else:
            self._tags = {}

    def album_tags(self):
        """Return a dictionary of album-level tags."""
        return self._collect_tags('', *ALBUM_TAGS)

    def track_tags(self, number):
        """Return a dictionary of track-level tags."""
        num = int(number)
        if num < 1 or num > 99:
            raise Exception(f'Invalid track number: {number}')
        prefix = 'TRACK_{:02d}_'.format(num)
        return self._collect_tags(prefix, *TRACK_TAGS)

    def update_album(self, tags):
        """Update album-level tags.

        Returns True if anything changed.
        """
        return self._update_tags(tags, '', *ALBUM_TAGS)

    def update_track(self, number, tags):
        """Update track-level tags.

        Returns True if anything changed.
        """
        num = int(number)
        if num < 1 or num > 99:
            raise Exception(f'Invalid track number: {number}')
        prefix = 'TRACK_{:02d}_'.format(num)
        return self._update_tags(tags, prefix, *TRACK_TAGS)

    def _collect_tags(self, prefix, *args):
        result = {}
        for name in args:
            key = prefix + name
            if key in self._tags:
                result[name] = self._tags[key][0]
        return result

    def _update_tags(self, tags, prefix, *args):
        changed = False
        for name in args:
            key = prefix + name
            if name not in tags and key not in self._tags:
                continue
            elif name in tags and key not in self._tags:
                self._tags[key] = tags[name]
                changed = True
            elif name not in tags and key in self._tags:
                del self._tags[key]
                changed = True
            elif tags[name] != self._tags[key][0]:
                del self._tags[key]
                self._tags[key] = tags[name]
                changed = True
        if changed and _VERSION_TAG not in self._tags:
            self._tags[_VERSION_TAG] = str(_VERSION_NUMBER)
        return changed


"""A subset of FLAC picture data.

See: https://xiph.org/flac/format.html#metadata_block_picture
"""
Picture = namedtuple('Picture', 'type mime width height depth data')


class Summary():
    """A summary for a FileInfo object.

   Flags:
   - parse_ok: The file parsed successfully.
   - cuesheet: A cue sheet is present.
   - album_tags: Album-level tags are present (any number).
   - track_tags: Track-level tags are present (any number).
   - pictures: Pictures are present (any number).

   The string representation uses the following flags:
    - O: The file parsed successfully.
    - C: A cue sheet is present.
    - A: Album-level tags are present (any number).
    - T: Track-level tags are present (any number).
    - P: Pictures are present (any number).
    """

    def __init__(self, fileinfo):
        self.parse_ok = fileinfo.parse_ok
        self.cuesheet = False
        self.album_tags = False
        self.track_tags = False
        self.pictures = False
        if self.parse_ok:
            if fileinfo.cuesheet is not None:
                self.cuesheet = True
                cs = fileinfo.cuesheet
                track_numbers = [t.number for t in cs.audio_tracks]
                for number in track_numbers:
                    if fileinfo.tags.track_tags(number):
                        self.track_tags = True
                        break
            if fileinfo.tags.album_tags():
                self.album_tags = True
            if fileinfo.pictures():
                self.pictures = True

    def __repr__(self):
        def flag_or_dash(status, flag):
            if status:
                return flag
            else:
                return '-'
        status = (
            self.parse_ok,
            self.cuesheet,
            self.album_tags,
            self.track_tags,
            self.pictures
        )
        return ''.join(map(flag_or_dash, status, 'OCATP'))


class FileInfo(object):
    """Read and write FLAC metadata.

    Variables:
    - path: The FLAC file.
    - parse_ok: True if the file was parsed successfully.
                If False, most other variables will be None.
    - parse_exception: The exception raised during parsing, or None.
    - streaminfo: The file's StreamInfo.
    - cuesheet: The file's CueSheet.
    - tags: The file's Tags.

    This class supports only one picture per type.
    """

    def __init__(self, path):
        self.path = str(path)
        self.parse()

    @property
    def summary(self):
        """Return a Summary for this FileInfo."""
        return Summary(self)

    def parse(self):
        """Read the FLAC file and update the variables."""
        try:
            self._flac = FLAC(self.path)
            info = self._flac.info
            self.streaminfo = StreamInfo(
                info.channels,
                info.bits_per_sample,
                info.sample_rate,
                info.total_samples
            )
            if self._flac.cuesheet is not None:
                self.cuesheet = CueSheet(self._flac.cuesheet)
            else:
                self.cuesheet = None
            self.tags = Tags(self._flac.tags)
            self.parse_ok = True
            self.parse_exception = None
        except Exception as e:
            self.parse_ok = False
            self.parse_exception = e
            self.streaminfo = None
            self.cuesheet = None
            self.tags = None

    def update(self):
        """Save the current metadata and re-parse the FLAC file."""
        self._flac.save()
        self.parse()

    def pictures(self):
        """Return a tuple of Pictures, or None."""
        if self.parse_ok:
            return tuple(self._picture_m2f(p) for p in self._flac.pictures)
        else:
            return None

    def get_picture(self, type_):
        """Return the Picture of the given type, or None."""
        result = None
        if self.parse_ok:
            matches = [p for p in self._flac.pictures if p.type == type_]
            if matches:
                result = self._picture_m2f(matches[0])
        return result

    def set_picture(self, picture):
        """Set or replace the Picture of its type.

        Returns True if anything changed.
        """
        changed = False
        old = self.get_picture(picture.type)
        if old != picture:
            self.remove_picture(picture.type)
            self._flac.add_picture(self._picture_f2m(picture))
            changed = True
        return changed

    def remove_picture(self, type_):
        """Remove the picture of the given type.

        Returns True if anything changed.
        """
        changed = False
        pics = self._flac.pictures
        keep = [p for p in pics if p.type != type_]
        if len(pics) != len(keep):
            self._flac.clear_pictures()
            for picture in keep:
                self._flac.add_picture(picture)
            changed = True
        return changed

    @staticmethod
    def _picture_m2f(mutagen_picture):
        """Create a Flackup Picture from a Mutagen Picture."""
        return Picture(
            mutagen_picture.type,
            mutagen_picture.mime,
            mutagen_picture.width,
            mutagen_picture.height,
            mutagen_picture.depth,
            mutagen_picture.data
        )

    @staticmethod
    def _picture_f2m(flackup_picture):
        """Create a Mutagen Picture from a Flackup Picture."""
        picture = MutagenPicture()
        picture.type = flackup_picture.type
        picture.mime = flackup_picture.mime
        picture.width = flackup_picture.width
        picture.height = flackup_picture.height
        picture.depth = flackup_picture.depth
        picture.data = flackup_picture.data
        return picture
