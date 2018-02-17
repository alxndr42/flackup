from flackup.fileinfo import FileInfo


class TestFileInfo(object):
    """Test the FileInfo class."""

    def test_init(self, datadir):
        """Call the constructor with a valid FLAC file."""
        info = FileInfo(datadir / 'test.flac')
        assert info.parse_ok == True
        assert info.parse_exception is None
        assert info.cuesheet is not None
        assert info.tags is not None

    def test_init_empty(self, datadir):
        """Call the constructor with an empty FLAC file."""
        info = FileInfo(datadir / 'empty.flac')
        assert info.parse_ok == True
        assert info.parse_exception is None
        assert info.cuesheet is None
        assert info.tags is None

    def test_init_invalid(self, datadir):
        """Call the constructor with an invalid FLAC file."""
        info = FileInfo(datadir / 'invalid.flac')
        assert info.parse_ok == False
        assert info.parse_exception is not None
        assert info.cuesheet is None
        assert info.tags is None


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
        assert cuesheet.audio_track_numbers == [1, 2, 3]


class TestTags(object):
    """Test the Tags class."""

    def test_untagged(self, datadir):
        """Test reading an untagged FLAC file."""
        info = FileInfo(datadir / 'test.flac')
        tags = info.tags
        assert not tags.album_tags()
        for number in info.cuesheet.audio_track_numbers:
            assert not tags.track_tags(number)

    def test_tagged(self, datadir):
        """Test reading a tagged FLAC file."""
        def assert_track(tags, title, hide, performer):
            assert tags.get('TITLE') == title
            assert tags.get('HIDE') == hide
            assert tags.get('PERFORMER') == performer

        info = FileInfo(datadir / 'tagged.flac')
        tags = info.tags

        album = tags.album_tags()
        assert album.get('TITLE') == 'Test Album'
        assert album.get('ARTIST') == 'Test Artist'
        assert album.get('GENRE') == 'Test'
        assert album.get('DATE') == '2018'
        assert 'FOO' not in album

        assert_track(tags.track_tags(1), 'Track 1', None, None)
        assert_track(tags.track_tags(2), 'Track 2', None, None)
        assert_track(tags.track_tags(3), 'Track 3', 'yes', 'Terrible')
