import base64
from collections import defaultdict
import hashlib
from urllib.error import HTTPError

import musicbrainzngs as mb_client

from flackup import VERSION


"""Attribute keys to return when looking up releases.

See also: https://github.com/alastair/python-musicbrainzngs/blob/v0.6/musicbrainzngs/mbxml.py#L426
"""
RELEASES_KEYS = [
    'artist', # copy of artist-credit-phrase
    'barcode',
    'date',
    'id',
    'medium-count',
    'status',
    'title',
]


class MusicBrainz(object):
    """Perform MusicBrainz queries."""

    def __init__(self):
        mb_client.set_useragent('flackup', VERSION)

    def releases_by_cuesheet(self, cuesheet):
        """Lookup releases by CueSheet."""
        discid = self._create_discid(cuesheet)
        toc = self._create_toc(cuesheet)
        return self.releases_by_discid(discid, toc)

    def releases_by_discid(self, discid, toc=None):
        """Lookup releases by MusicBrainz disc ID or TOC string."""
        if not discid and not toc:
            return []

        result = []
        if not discid:
            discid = '-'
        if not toc:
            toc = None
        try:
            response = mb_client.get_releases_by_discid(
                discid,
                toc=toc,
                includes=['artists'],
                cdstubs=False
            )
            result = self._parse_releases(response)
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass # no matches
            else:
                raise e
        return sorted(result, key=_release_key)

    # TODO This doesn't work for multi-session CDs
    # https://musicbrainz.org/doc/Disc_ID_Calculation
    @staticmethod
    def _create_discid(cuesheet):
        """Create a MusicBrainz disc ID from a CueSheet."""
        if not cuesheet.is_cd:
            return None

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
    def _create_toc(cuesheet):
        """Create a MusicBrainz TOC string from a CueSheet."""
        if not cuesheet.is_cd:
            return None

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
    def _parse_releases(response):
        """Parse MusicBrainz releases from the response."""
        def release(dict_):
            if 'artist-credit-phrase' in dict_:
                dict_['artist'] = dict_['artist-credit-phrase']
            return {k: dict_[k] for k in dict_ if k in RELEASES_KEYS}

        releases = []
        if 'disc' in response:
            releases = response['disc']['release-list']
        elif 'release-list' in response:
            releases = response['release-list']
        return [release(r) for r in releases]


def _release_key(release):
    """Create a comparison key from a release."""
    key = []
    key.append(release['artist'].casefold())
    key.append(release['title'].casefold())
    status = release.get('status', 'Unknown')
    if status == 'Official':
        key.append(0)
    elif status == 'Bootleg':
        key.append(2)
    else:
        key.append(1)
    key.append(release.get('medium-count', 99))
    key.append(release.get('date', '9999'))
    key.append(release.get('barcode', '9999999999999'))
    return tuple(key)
