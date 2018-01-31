import base64
from collections import defaultdict
import hashlib
import sys
from urllib.error import HTTPError

from flackup import VERSION
import musicbrainzngs
from mutagen.flac import FLAC


def discid(cuesheet):
    """Create a MusicBrainz disc ID from a Mutagen FLAC cuesheet."""
    result = ''
    if cuesheet.compact_disc:
        first_track = cuesheet.tracks[0].track_number
        last_track = cuesheet.tracks[-2].track_number
        lead_in_blocks = cuesheet.lead_in_samples // 588
        offsets = defaultdict(int)
        for track in cuesheet.tracks:
            number = track.track_number
            offset = track.start_offset // 588 + lead_in_blocks
            if track.track_number != 170:
                offsets[number] = offset
            else:
                offsets[0] = offset # lead-out track gets index 0

        sha1 = hashlib.sha1()
        sha1.update(b'%02X' % first_track)
        sha1.update(b'%02X' % last_track)
        for i in range(100):
            sha1.update(b'%08X' % offsets[i])

        result = base64.b64encode(sha1.digest(), b'._').decode('UTF-8')
        result = result.replace('=', '-')
    return result


def toc(cuesheet):
    """Create a MusicBrainz TOC string from a Mutagen FLAC cuesheet."""
    result = ''
    if cuesheet.compact_disc:
        first_track = cuesheet.tracks[0].track_number
        track_count = len(cuesheet.tracks) - 1
        lead_in_blocks = cuesheet.lead_in_samples // 588
        offsets = []
        for track in cuesheet.tracks:
            number = track.track_number
            offset = track.start_offset // 588 + lead_in_blocks
            if track.track_number != 170:
                offsets.append(str(offset))
            else:
                offsets.insert(0, str(offset)) # lead-out track gets index 0
        result = '%s %s %s' % (first_track, track_count, ' '.join(offsets))
    return result


def parse_matches(response):
    """Parse MusicBrainz matches to (title, mbid) tuples."""
    result = []
    releases = []
    if 'disc' in response:
        releases = response['disc']['release-list']
    elif 'release-list' in response:
        releases = response['release-list']
    for release in releases:
        result.append((release['title'], release['id']))
    return result


def main():
    """Perform MusicBrainz lookups using FLAC cuesheets."""
    if len(sys.argv) == 1:
        print('Usage: flackup.py <flac_file> ...')
        sys.exit(1)

    musicbrainzngs.set_useragent('flackup', VERSION)
    for filename in sys.argv[1:]:
        print(filename)
        flac = FLAC(filename)
        if flac.cuesheet is None:
            print('- No cuesheet')
            continue

        discid_ = discid(flac.cuesheet)
        toc_ = toc(flac.cuesheet)
        response = None
        try:
            response = musicbrainzngs.get_releases_by_discid(discid_, toc=toc_)
        except Exception as e:
            if isinstance(e.cause, HTTPError) and e.cause.code == 404:
                print('- No match')
            else:
                print('- Error (%s)' % e)
            continue

        matches = parse_matches(response)
        for match in matches:
            print('- %s (%s)' % match)
