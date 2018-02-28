from flackup.musicbrainz import MusicBrainz


class TestMusicBrainz(object):
    """Test the MusicBrainz class."""

    def test_discid_lookup(self):
        """Test a lookup by disc ID."""
        mb = MusicBrainz()
        releases = mb.lookup_by_discid('RHNAnAo97C4V.gbmOWsLQwXfTOA-')
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
        toc = '1 10 176790 150 20543 41300 53113 75608 91578 103028 120483 143800 159908'
        releases = mb.lookup_by_discid(None, toc)
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
            barcode=None,
            media=1,
            status='Official'):
        release = None
        for r in releases:
            if r['id'] == id_:
                release = r
                break
        assert release is not None
        assert release.get('artist') == artist
        assert release.get('title') == title
        assert release.get('date') == date
        assert release.get('barcode') == barcode
        assert release.get('medium-count') == media
        assert release.get('status') == status
