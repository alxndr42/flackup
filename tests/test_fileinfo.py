from flackup.fileinfo import FileInfo


class TestFileInfo(object):
    """Test the FileInfo class."""

    def test_init(self, datadir):
        """Call the constructor with a valid FLAC file."""
        file = FileInfo(datadir / 'test.flac')
        assert file.parse_ok == True
        assert file.parse_exception is None
        assert file.cuesheet is not None
        assert file.tags is not None

    def test_init_empty(self, datadir):
        """Call the constructor with an empty FLAC file."""
        file = FileInfo(datadir / 'empty.flac')
        assert file.parse_ok == True
        assert file.parse_exception is None
        assert file.cuesheet is None
        assert file.tags is not None

    def test_init_invalid(self, datadir):
        """Call the constructor with an invalid FLAC file."""
        file = FileInfo(datadir / 'invalid.flac')
        assert file.parse_ok == False
        assert file.parse_exception is not None
        assert file.cuesheet is None
        assert file.tags is None


class TestCueSheet(object):
    """Test the CueSheet class."""

    def test_cuesheet(self, datadir):
        """Test with a valid FLAC file."""
        file = FileInfo(datadir / 'test.flac')
        cuesheet = file.cuesheet
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
        file = FileInfo(datadir / 'test.flac')
        tags = file.tags
        assert not tags.album_tags()
        for number in file.cuesheet.audio_track_numbers:
            assert not tags.track_tags(number)

    def test_tagged(self, datadir):
        """Test reading a tagged FLAC file."""
        file = FileInfo(datadir / 'tagged.flac')
        tags = file.tags

        album = tags.album_tags()
        assert 'FOO' not in album
        self.assert_album(album, 'Test Album', 'Test Artist', 'Test', '2018')
        self.assert_track(tags.track_tags(1), 'Track 1', None, None)
        self.assert_track(tags.track_tags(2), 'Track 2', None, None)
        self.assert_track(tags.track_tags(3), 'Track 3', 'yes', 'Terrible')

    def test_update_untagged(self, datadir):
        """Test updating an untagged FLAC file."""
        file = FileInfo(datadir / 'test.flac')
        tags = file.tags

        album = tags.album_tags()
        album['TITLE'] = 'Title'
        album['ARTIST'] = 'Artist'
        assert tags.update_album(album)

        track = tags.track_tags(1)
        track['TITLE'] = 'Track One'
        assert tags.update_track(1, track)

        track = tags.track_tags(2)
        assert not tags.update_track(2, track)

        track = tags.track_tags(3)
        track['HIDE'] = 'yes'
        track['PERFORMER'] = 'Terrible'
        assert tags.update_track(3, track)

        file.update()
        file = FileInfo(datadir / 'test.flac')
        tags = file.tags
        self.assert_album(tags.album_tags(), 'Title', 'Artist', None, None)
        self.assert_track(tags.track_tags(1), 'Track One', None, None)
        self.assert_track(tags.track_tags(2), None, None, None)
        self.assert_track(tags.track_tags(3), None, 'yes', 'Terrible')

    def test_update_tagged(self, datadir):
        """Test updating a tagged FLAC file."""
        file = FileInfo(datadir / 'tagged.flac')
        tags = file.tags

        album = tags.album_tags()
        album['TITLE'] = 'Title'
        album['ARTIST'] = 'Artist'
        assert tags.update_album(album)

        track = tags.track_tags(1)
        track['TITLE'] = 'Track One'
        assert tags.update_track(1, track)

        track = tags.track_tags(2)
        assert not tags.update_track(2, track)

        track = tags.track_tags(3)
        del track['TITLE']
        assert tags.update_track(3, track)

        file.update()
        file = FileInfo(datadir / 'tagged.flac')
        tags = file.tags
        self.assert_album(tags.album_tags(), 'Title', 'Artist', 'Test', '2018')
        self.assert_track(tags.track_tags(1), 'Track One', None, None)
        self.assert_track(tags.track_tags(2), 'Track 2', None, None)
        self.assert_track(tags.track_tags(3), None, 'yes', 'Terrible')

    @staticmethod
    def assert_album(tags, title, artist, genre, date):
        assert tags.get('TITLE') == title
        assert tags.get('ARTIST') == artist
        assert tags.get('GENRE') == genre
        assert tags.get('DATE') == date

    @staticmethod
    def assert_track(tags, title, hide, performer):
        assert tags.get('TITLE') == title
        assert tags.get('HIDE') == hide
        assert tags.get('PERFORMER') == performer
