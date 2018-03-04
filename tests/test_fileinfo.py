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
        assert file.pictures() is not None

    def test_init_empty(self, datadir):
        """Call the constructor with an empty FLAC file."""
        file = FileInfo(datadir / 'empty.flac')
        assert file.parse_ok == True
        assert file.parse_exception is None
        assert file.cuesheet is None
        assert file.tags is not None
        assert file.pictures() is not None

    def test_init_invalid(self, datadir):
        """Call the constructor with an invalid FLAC file."""
        file = FileInfo(datadir / 'invalid.flac')
        assert file.parse_ok == False
        assert file.parse_exception is not None
        assert file.cuesheet is None
        assert file.tags is None
        assert file.pictures() is None

    def test_read_picture(self, datadir):
        """Test reading a picture."""
        file = FileInfo(datadir / 'tagged.flac')
        with open(str(datadir / 'cover.png'), 'rb') as cover:
            data = cover.read()
        self.assert_picture(file, 3, 'image/png', 128, 128, 24, data)

    def test_set_picture(self, datadir):
        """Test setting a picture."""
        file = FileInfo(datadir / 'empty.flac')
        with open(str(datadir / 'cover.png'), 'rb') as cover:
            data = cover.read()
        assert file.set_picture(3, 'image/png', 128, 128, 24, data)
        assert not file.set_picture(3, 'image/png', 128, 128, 24, data)
        file.update()
        self.assert_picture(file, 3, 'image/png', 128, 128, 24, data)

    def test_remove_picture(self, datadir):
        """Test removing a picture."""
        file = FileInfo(datadir / 'tagged.flac')
        assert file.remove_picture(3)
        assert not file.remove_picture(3)
        file.update()
        assert file.get_picture(3) is None

    @staticmethod
    def assert_picture(fileinfo, type_, mime, width, height, depth, data):
        picture = fileinfo.get_picture(type_)
        assert picture is not None
        assert picture.type == type_
        assert picture.mime == mime
        assert picture.width == width
        assert picture.height == height
        assert picture.depth == depth
        assert picture.data == data


class TestCueSheet(object):
    """Test the CueSheet class."""

    def test_cuesheet(self, datadir):
        """Test with a valid FLAC file."""
        file = FileInfo(datadir / 'test.flac')
        cuesheet = file.cuesheet
        assert cuesheet is not None
        assert cuesheet.is_cd
        assert cuesheet.lead_in == 88200
        track_numbers = [t.number for t in cuesheet.tracks]
        assert track_numbers == [1, 2, 3, 170]
        audio_track_numbers = [t.number for t in cuesheet.audio_tracks]
        assert audio_track_numbers == [1, 2, 3]


class TestTags(object):
    """Test the Tags class."""

    def test_untagged(self, datadir):
        """Test reading an untagged FLAC file."""
        file = FileInfo(datadir / 'test.flac')
        tags = file.tags
        assert not tags.album_tags()
        track_numbers = [t.number for t in file.cuesheet.audio_tracks]
        for number in track_numbers:
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
