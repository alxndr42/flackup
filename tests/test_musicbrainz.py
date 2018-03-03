from flackup.fileinfo import CueSheetTrack
from flackup.musicbrainz import MusicBrainz


class TestMusicBrainz(object):
    """Test the MusicBrainz class."""

    def test_discid_lookup(self):
        """Test a lookup by disc ID."""
        mb = MusicBrainz()
        discid = 'RHNAnAo97C4V.gbmOWsLQwXfTOA-'
        releases = mb.releases_by_disc(FakeDisc(discid))
        self.assert_release(
            releases,
            '7542431b-0fab-4443-a994-5fa98593da02',
            'Zoë Keating',
            'Into the Trees',
            '2010-06-19',
            '700261301921'
        )

    def test_toc_lookup(self):
        """Test a lookup by TOC string."""
        mb = MusicBrainz()
        toc = '1 12 178475 150 12289 27294 41177 56350 74389 87462 100844 114867 133013 148708 157085'
        releases = mb.releases_by_disc(FakeDisc(None, toc, 12))
        self.assert_release(
            releases,
            '43607a9a-54cd-4346-88db-50d7bcbfbd33',
            'All India Radio',
            'The Silent Surf',
            '2010-12-06',
            '884502818352'
        )

    def test_cuesheet_lookup(self):
        """Test a lookup by CueSheet."""
        mb = MusicBrainz()
        offsets = [
            0,
            11991084,
            24196200,
            31142244,
            44369304,
            53759664,
            60492264,
            70755804,
            84466200,
            93937704,
            103864320,
        ]
        releases = mb.releases_by_cuesheet(FakeCueSheet(offsets))
        self.assert_release(
            releases,
            '2c62e70e-5f2a-4aaf-913f-e29d212cc64c',
            'Van Morrison',
            'Moondance',
            '1989-03-09',
            '075992732628'
        )

    @staticmethod
    def assert_release(
            releases,
            id_,
            artist,
            title,
            date=None,
            barcode=None):
        release = None
        for r in releases:
            if r['id'] == id_:
                release = r
                break
        assert release is not None
        assert release.get('artist') == artist
        assert release.get('barcode') == barcode
        assert release.get('date') == date
        assert release.get('medium-count') == 1
        assert release.get('status') == 'Official'
        assert release.get('title') == title
        media = release.get('media')
        assert media is not None
        assert len(media) == 1
        assert media[0]['format'] == 'CD'


class FakeDisc(object):
    """Fake the MusicBrainzDisc class for tests."""
    def __init__(self, discid, toc=None, track_count=0):
        self.discid = discid
        self.toc = toc
        self.track_count = track_count

    def offset_distance(self, offsets):
        return 0


class FakeCueSheet(object):
    """Fake the CueSheet class for tests."""
    def __init__(self, offsets):
        self.is_cd = True
        self.lead_in = 88200
        self.tracks = []
        for number, offset in enumerate(offsets[:-1], start=1):
            self.tracks.append(CueSheetTrack(number, offset, 0))
        self.tracks.append(CueSheetTrack(170, offsets[-1], 0))
