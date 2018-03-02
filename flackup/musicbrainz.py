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
        disc = MusicBrainzDisc(cuesheet)
        return self.releases_by_disc(disc)

    def releases_by_disc(self, disc):
        """Lookup releases by MusicBrainzDisc."""
        discid = disc.discid
        if discid is None:
            discid = '-'
        toc = disc.toc
        if discid == '-' and toc is None:
            return []

        releases = []
        try:
            response = mb_client.get_releases_by_discid(
                discid,
                toc=toc,
                includes=['artist-credits'],
                cdstubs=False
            )
            if 'disc' in response:
                releases = response['disc']['release-list']
            elif 'release-list' in response:
                releases = response['release-list']
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass # no matches
            else:
                raise e
        result = [_parse_release(r) for r in releases]
        return sorted(result, key=_release_key)


# TODO This class doesn't support multi-session CDs
class MusicBrainzDisc(object):
    """Provide disc information suitable for MusicBrainz lookups.

    See also:
    - https://musicbrainz.org/doc/Disc_ID_Calculation
    - https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2#discid
    """
    def __init__(self, cuesheet):
        """Create a MusicBrainzDisc from a CueSheet."""
        self._is_cd = cuesheet.is_cd
        self._lead_in = cuesheet.lead_in // 588
        self._tracks = []
        for track in cuesheet.tracks:
            number = track.number
            offset = track.offset // 588 + self._lead_in
            if number < 100:
                self._tracks.append((number, offset))
            else:
                self._tracks.insert(0, (0, offset)) # lead-out gets index 0
        self.discid = self._create_discid()
        self.toc = self._create_toc()

    @property
    def track_count(self):
        return len(self._tracks) - 1 # ignore lead-out

    def _create_discid(self):
        """Return a disc ID for this disc, or None."""
        if not self._is_cd:
            return None

        offsets = defaultdict(int)
        for number, offset in self._tracks:
            offsets[number] = offset

        first_track = self._tracks[1][0]
        last_track = self._tracks[-1][0]
        sha1 = hashlib.sha1()
        sha1.update(b'%02X' % first_track)
        sha1.update(b'%02X' % last_track)
        for i in range(100):
            sha1.update(b'%08X' % offsets[i])

        discid = base64.b64encode(sha1.digest(), b'._').decode('UTF-8')
        discid = discid.replace('=', '-')
        return discid

    def _create_toc(self):
        """Return a TOC string for this disc, or None."""
        if not self._is_cd:
            return None

        first_track = self._tracks[1][0]
        offsets = [str(t[1]) for t in self._tracks]
        return '%s %s %s' % (
            first_track,
            self.track_count,
            ' '.join(offsets)
        )


def _parse_release(release):
    """Parse a MusicBrainz release."""
    if 'artist-credit-phrase' in release:
        release['artist'] = release['artist-credit-phrase']
    result = {k: release[k] for k in release if k in RELEASES_KEYS}
    return result


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
