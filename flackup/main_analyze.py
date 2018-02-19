import sys

from flackup.fileinfo import FileInfo


def main():
    """Analyze FLAC files.

    Usage: flackup-analyze <flac_file> ...

    For each file, prints a list of flags followed by the filename.

    Flags:
    - O: The file parsed successfully.
    - C: A cue sheet is present.
    - A: Album-level tags are present (any number).
    - T: Track-level tags are present (any number).
    - P: Pictures are present (any number).
    """
    if len(sys.argv) == 1:
        print(main.__doc__)
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
                for number in file.cuesheet.audio_track_numbers:
                    if file.tags.track_tags(number):
                        flag_track_tags = 'T'
                        break
            if file.tags.album_tags():
                flag_album_tags = 'A'
            if file.pictures():
                flag_pictures = 'P'

        result = '%s%s%s%s%s %s' % (
            flag_parse_ok,
            flag_cuesheet,
            flag_album_tags,
            flag_track_tags,
            flag_pictures,
            filename
        )
        print(result)
