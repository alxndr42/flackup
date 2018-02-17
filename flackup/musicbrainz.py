import base64
from collections import defaultdict
import hashlib
from urllib.error import HTTPError

import musicbrainzngs as mb_client

from flackup import VERSION


class MusicBrainz(object):
    """Perform MusicBrainz queries."""

    def __init__(self):
        mb_client.set_useragent('flackup', VERSION)

    def lookup_releases(self, cuesheet):
        """Lookup releases by MusicBrainz disc ID or TOC string."""
        result = []
        discid = MusicBrainz.create_discid(cuesheet)
        toc = MusicBrainz.create_toc(cuesheet)
        if discid or toc:
            try:
                response = mb_client.get_releases_by_discid(discid, toc=toc)
                result = MusicBrainz.parse_releases(response)
            except Exception as e:
                if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                    pass # no matches
                else:
                    raise e
        return result

    # TODO This doesn't work for multi-session CDs
    # https://musicbrainz.org/doc/Disc_ID_Calculation
    @staticmethod
    def create_discid(cuesheet):
        """Create a MusicBrainz disc ID from a CueSheet."""
        if not cuesheet.is_cd:
            return ''

        first_track = cuesheet.tracks[0].number
        last_track = cuesheet.tracks[-2].number # ignore lead-out
        lead_in_blocks = cuesheet.lead_in // 588
        offsets = defaultdict(int)
        for track in cuesheet.tracks:
            number = track.number
            offset = track.offset // 588 + lead_in_blocks
            if track.number != 170:
                offsets[number] = offset
            else:
                offsets[0] = offset # lead-out gets index 0

        sha1 = hashlib.sha1()
        sha1.update(b'%02X' % first_track)
        sha1.update(b'%02X' % last_track)
        for i in range(100):
            sha1.update(b'%08X' % offsets[i])

        discid = base64.b64encode(sha1.digest(), b'._').decode('UTF-8')
        discid = discid.replace('=', '-')
        return discid

    # TODO This doesn't work for multi-session CDs
    # https://musicbrainz.org/doc/Disc_ID_Calculation
    @staticmethod
    def create_toc(cuesheet):
        """Create a MusicBrainz TOC string from a CueSheet."""
        if not cuesheet.is_cd:
            return ''

        first_track = cuesheet.tracks[0].number
        track_count = len(cuesheet.tracks) - 1 # ignore lead-out
        lead_in_blocks = cuesheet.lead_in // 588
        offsets = []
        for track in cuesheet.tracks:
            number = track.number
            offset = track.offset // 588 + lead_in_blocks
            if track.number != 170:
                offsets.append(str(offset))
            else:
                offsets.insert(0, str(offset)) # lead-out gets index 0

        return '%s %s %s' % (first_track, track_count, ' '.join(offsets))

    @staticmethod
    def parse_releases(response):
        """Parse MusicBrainz matches to (title, mbid) tuples."""
        releases = []
        if 'disc' in response:
            releases = response['disc']['release-list']
        elif 'release-list' in response:
            releases = response['release-list']
        return [(r['title'], r['id']) for r in releases]
