from flackup.metadata import FileInfo


class TestFileInfo(object):
    """Test the FileInfo class."""

    def test_init(self, datadir):
        """Call the constructor with a valid FLAC file."""
        info = FileInfo(datadir / 'test.flac')
        assert info.parse_ok == True
        assert info.parse_exception is None
        assert info.cuesheet is not None

    def test_init_empty(self, datadir):
        """Call the constructor with an empty FLAC file."""
        info = FileInfo(datadir / 'empty.flac')
        assert info.parse_ok == True
        assert info.parse_exception is None
        assert info.cuesheet is None

    def test_init_invalid(self, datadir):
        """Call the constructor with an invalid FLAC file."""
        info = FileInfo(datadir / 'invalid.flac')
        assert info.parse_ok == False
        assert info.parse_exception is not None
        assert info.cuesheet is None


class TestCueSheet(object):
    """Test the CueSheet class."""

    def test_cuesheet(self, datadir):
        """Test with a valid FLAC file."""
        info = FileInfo(datadir / 'test.flac')
        cuesheet = info.cuesheet
        assert cuesheet is not None
        assert cuesheet.is_cd
        assert cuesheet.lead_in == 88200
        tracks = cuesheet.tracks
        assert tracks is not None
        track_numbers = [t.number for t in tracks]
        assert track_numbers == [1, 2, 3, 170]
