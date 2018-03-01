import sys

from flackup.fileinfo import FileInfo
from flackup.musicbrainz import MusicBrainz


def main():
    """Perform MusicBrainz lookups using FLAC cuesheets.

    Usage: flackup <flac_file> ...
    """
    if len(sys.argv) == 1:
        print(main.__doc__)
        return

    mb = MusicBrainz()
    for filename in sys.argv[1:]:
        print(filename)
        file = FileInfo(filename)
        if not file.parse_ok:
            print('- Parse error (%s)' % file.parse_exception)
            continue
        if file.cuesheet is None:
            print('- No cuesheet')
            continue

        matches = None
        try:
            matches = mb.releases_by_cuesheet(file.cuesheet)
        except Exception as e:
            print('- Lookup error (%s)' % e)
            continue

        if not matches:
            print('- No matches')
            continue

        for match in matches:
            parts = [match['id'], match['artist']]
            status = match.get('status', 'Unknown')
            if status == 'Official':
                parts.append(match['title'])
            else:
                parts.append('%s (%s)' % (match['title'], status))
            barcode = match.get('barcode')
            if barcode:
                parts.append(barcode)
            print('-', ' | '.join(parts))
