import base64
from collections import defaultdict
import hashlib
from urllib.error import HTTPError

import musicbrainzngs as mb_client

from flackup import VERSION


"""Properties to return for a release.

See also: https://github.com/alastair/python-musicbrainzngs/blob/v0.6/musicbrainzngs/mbxml.py#L406
"""  # noqa
RELEASE_KEYS = [
    'artist',  # copy of artist-credit-phrase
    'barcode',
    'country',
    'date',
    'group-id',
    'id',
    'medium-count',
    'status',
    'title',
]

"""Properties to return for a medium.

See also: https://github.com/alastair/python-musicbrainzngs/blob/v0.6/musicbrainzngs/mbxml.py#L460
"""  # noqa
MEDIUM_KEYS = ['format', 'position', 'title']

"""Properties to return for a track.

See also: https://github.com/alastair/python-musicbrainzngs/blob/v0.6/musicbrainzngs/mbxml.py#L691
"""  # noqa
TRACK_KEYS = ['artist', 'number']

"""Properties to return for a recording (merged into track properties).

See also: https://github.com/alastair/python-musicbrainzngs/blob/v0.6/musicbrainzngs/mbxml.py#L498
"""  # noqa
RECORDING_KEYS = ['title']


class MusicBrainz(object):
    """Perform MusicBrainz queries."""

    def __init__(self):
        mb_client.set_useragent('flackup', VERSION)

    def releases_by_cuesheet(self, cuesheet):
        """Lookup releases by CueSheet.

        Does not include track information.
        """
        disc = MusicBrainzDisc(cuesheet)
        return self.releases_by_disc(disc)

    def releases_by_disc(self, disc):
        """Lookup releases by MusicBrainzDisc.

        Does not include track information.
        """
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
                includes=['artist-credits', 'release-groups'],
                cdstubs=False
            )
            if 'disc' in response:
                releases = response['disc']['release-list']
            elif 'release-list' in response:
                releases = response['release-list']
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass  # no matches
            else:
                raise MusicBrainzError from e
        result = [_parse_release(r, disc) for r in releases]
        return sorted(result, key=_release_key)

    def release_by_id(self, mbid, cuesheet=None):
        """Return a release by MusicBrainz ID, or None.

        If cuesheet is present, return only the medium with a disc ID or TOC
        match. Includes track information.
        """
        release = None
        try:
            response = mb_client.get_release_by_id(
                mbid,
                includes=[
                    'artist-credits',
                    'discids',
                    'recordings',
                    'release-groups',
                ]
            )
            release = response['release']
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass  # no matches
            else:
                raise MusicBrainzError from e
        if release is not None:
            if cuesheet is not None:
                disc = MusicBrainzDisc(cuesheet)
            else:
                disc = None
            return _parse_release(release, disc)
        else:
            return None

    def first_release_date(self, group_id):
        """Return the first release date in the release group, or None."""
        dates = []
        limit = 25
        offset = 0
        while True:
            try:
                response = mb_client.browse_releases(
                    release_group=group_id,
                    limit=limit,
                    offset=offset)
                releases = response['release-list']
                dates.extend([r['date'] for r in releases if 'date' in r])
                if len(releases) < limit:
                    break
                else:
                    offset += limit
            except mb_client.ResponseError as e:
                raise MusicBrainzError from e
        if dates:
            return min(dates)
        else:
            return None

    def front_cover(self, release):
        """Return the front cover, or None.

        Tries the release first, then the release group. Returns the image's
        bytes.
        """
        try:
            return mb_client.get_image_front(release['id'])
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass  # no front cover
            else:
                raise MusicBrainzError from e
        try:
            return mb_client.get_release_group_image_front(release['group-id'])
        except mb_client.ResponseError as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                pass  # no front cover
            else:
                raise MusicBrainzError from e
        return None


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
                self._tracks.insert(0, (0, offset))  # lead-out gets index 0
        self.discid = self._create_discid()
        self.toc = self._create_toc()

    @property
    def track_count(self):
        return len(self._tracks) - 1  # ignore lead-out

    def offset_distance(self, offsets):
        """Return a "distance" between the lists of track offsets.

        A value of 0 means identical track offsets.
        """
        my_offsets = [t[1] for t in self._tracks[1:]]
        distances = map(lambda a, b: abs(a - b), my_offsets, offsets)
        return sum(distances) / self.track_count

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
        sha1.update('{:02X}'.format(first_track).encode())
        sha1.update('{:02X}'.format(last_track).encode())
        for i in range(100):
            sha1.update('{:08X}'.format(offsets[i]).encode())

        discid = base64.b64encode(sha1.digest(), b'._').decode('UTF-8')
        discid = discid.replace('=', '-')
        return discid

    def _create_toc(self):
        """Return a TOC string for this disc, or None."""
        if not self._is_cd:
            return None

        first_track = self._tracks[1][0]
        offsets = [str(t[1]) for t in self._tracks]
        return '{} {} {}'.format(
            first_track, self.track_count, ' '.join(offsets))


class MusicBrainzError(Exception):
    """Exception for MusicBrainz error responses."""
    pass


def _parse_release(release, disc=None):
    """Parse a MusicBrainz release.

    If disc is present, return only the medium with a disc ID or TOC match.
    """
    result = _copy_dict(release, RELEASE_KEYS)
    result['group-id'] = release['release-group']['id']
    medium = None
    if disc is not None:
        medium = _find_medium_by_disc(release, disc)
    if medium is not None:
        result['media'] = [_parse_medium(medium)]
    else:
        result['media'] = [_parse_medium(m) for m in release['medium-list']]
    # Remove redundant track artists
    release_artist = result['artist']
    for m in result['media']:
        for t in m['tracks']:
            if t.get('artist') == release_artist:
                del t['artist']
    return result


def _parse_medium(medium):
    """Parse a MusicBrainz medium."""
    result = _copy_dict(medium, MEDIUM_KEYS)
    tracks = medium['track-list']
    result['tracks'] = [_parse_track(t) for t in tracks]
    return result


def _parse_track(track):
    """Parse a MusicBrain track (including recording keys)."""
    result = _copy_dict(track, TRACK_KEYS)
    recording = track['recording']
    result.update(_copy_dict(recording, RECORDING_KEYS))
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
    key.append(release['medium-count'])
    key.append(release.get('barcode', '9999999999999').lstrip('0'))
    key.append(release.get('date', '9999'))
    return tuple(key)


def _find_medium_by_disc(release, disc):
    """Return the best matching medium, or None."""
    media = release['medium-list']

    # Look for a disc ID match
    for m in media:
        for d in m['disc-list']:
            if d['id'] == disc.discid:
                return m

    # Look for the closest TOC match
    media = [m for m in media if m['track-count'] == disc.track_count]

    def medium_key(medium):
        discs = medium['disc-list']
        dists = [disc.offset_distance(d['offset-list']) for d in discs]
        if dists:
            return min(dists)
        else:
            return 999999
    media.sort(key=medium_key)
    if media:
        return media[0]
    else:
        return None


def _copy_dict(dict_, keys):
    """Copy the mappings for keys from dict_.

    Copies "artist-credit-phrase" to "artist".
    """
    result = {k: dict_[k] for k in keys if k in dict_}
    if 'artist' in keys and 'artist-credit-phrase' in dict_:
        result['artist'] = dict_['artist-credit-phrase']
    return result
