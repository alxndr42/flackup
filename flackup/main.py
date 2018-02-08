import sys

from flackup.metadata import FileInfo, MusicBrainz


def main():
    """Perform MusicBrainz lookups using FLAC cuesheets."""
    if len(sys.argv) == 1:
        print('Usage: flackup.py <flac_file> ...')
        return

    mb = MusicBrainz()
    for filename in sys.argv[1:]:
        print(filename)
        file = FileInfo(filename)
        if not file.parse_ok:
            print('- Parse error (%s)' % file.parse_msg)
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
