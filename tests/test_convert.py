from pathlib import Path
import re

import flackup.convert as fc
from flackup.fileinfo import FileInfo


TRACK_WAV_RE = re.compile(r'track-\d\d\.wav')


class TestConvert(object):
    """Test the convert functions."""

    def test_prepare_tracks(self, datadir):
        """Test the prepare_tracks function."""
        info = FileInfo(datadir / 'tagged.flac')
        tracks = fc.prepare_tracks(info, str(datadir), 'ogg')
        assert len(tracks) == 2
        for track in tracks:
            assert len(track.tags) == 5
            assert track.path.endswith('.ogg')

    def test_prepare_tracks_date_original(self, datadir):
        """Test the prepare_tracks function with a DATE_ORIGINAL tag."""
        info = FileInfo(datadir / 'date_original.flac')
        tracks = fc.prepare_tracks(info, str(datadir), 'ogg')
        for track in tracks:
            assert track.tags['DATE'] == '1970'

    def test_decode_tracks(self, datadir):
        """Test the prepare_tracks function."""
        info = FileInfo(datadir / 'tagged.flac')
        tempdir = fc.decode_tracks(info)
        assert tempdir is not None
        path = Path(tempdir.name)
        files = list(path.iterdir())
        assert len(files) == 2
        for file in files:
            assert TRACK_WAV_RE.match(file.name) is not None

    def test_encode_tracks(self, datadir):
        """Test the encode_tracks function."""
        info = FileInfo(datadir / 'tagged.flac')
        tracks = fc.prepare_tracks(info, str(datadir), 'ogg')
        tempdir = fc.decode_tracks(info)
        fc.encode_tracks(tracks, tempdir, 'ogg')
        path = Path(tracks[0].path).parent
        files = list(path.iterdir())
        assert len(files) == 2
        for file in files:
            assert file.name.endswith('.ogg')

    def test_export_cover(self, datadir):
        """Test the export_cover function."""
        info = FileInfo(datadir / 'tagged.flac')
        front = info.get_picture(3)
        fc.export_cover(front, str(datadir))
        path = Path(datadir / 'cover.jpg')
        assert path.is_file()
