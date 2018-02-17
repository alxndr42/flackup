import sys

from flackup.fileinfo import FileInfo


def main():
    """Analyze FLAC files."""
    if len(sys.argv) == 1:
        print('Usage: flackup-analyze.py <flac_file> ...')
        return

    for filename in sys.argv[1:]:
        flag_parse_ok = '-'
        flag_cuesheet = '-'
        flag_album_tags = '-'
        flag_track_tags = '-'
        flag_pictures = '-'

        file = FileInfo(filename)
        if file.parse_ok:
            flag_parse_ok = 'O'
            if file.cuesheet is not None:
                flag_cuesheet = 'C'
                if file.tags.album_tags():
                    flag_album_tags = 'A'
                for number in file.cuesheet.audio_track_numbers:
                    if file.tags.track_tags(number):
                        flag_track_tags = 'T'
                        break

        result = '%s%s%s%s%s %s' % (
            flag_parse_ok,
            flag_cuesheet,
            flag_album_tags,
            flag_track_tags,
            flag_pictures,
            filename
        )
        print(result)
