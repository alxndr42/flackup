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
            matches = mb.lookup_releases(file.cuesheet)
        except Exception as e:
            print('- Lookup error (%s)' % e)
            continue

        if matches:
            for match in matches:
                print('- %s (%s)' % match)
        else:
            print('- No matches')
