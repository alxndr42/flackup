from click.testing import CliRunner

from flackup import NAME, VERSION
from flackup.cli import flackup
from flackup.fileinfo import FileInfo


class TestTag(object):
    """Test the tag command."""

    def test_hide(self, datadir):
        """Test the --hide option."""
        path = datadir / 'tagged.flac'
        runner = CliRunner()
        result = runner.invoke(flackup, ['tag', '--hide', str(path)])
        info = FileInfo(path)
        assert result.exit_code == 0
        assert info.tags.album_tags().get('HIDE') == 'true'

    def test_unhide(self, datadir):
        """Test the --unhide option."""
        path = datadir / 'tagged.flac'
        runner = CliRunner()
        result = runner.invoke(flackup, ['tag', '--hide', str(path)])
        result = runner.invoke(flackup, ['tag', '--unhide', str(path)])
        info = FileInfo(path)
        assert result.exit_code == 0
        assert info.tags.album_tags().get('HIDE') is None

    def test_hide_track(self, datadir):
        """Test the --hide-track option."""
        path = datadir / 'tagged.flac'
        runner = CliRunner()
        result = runner.invoke(flackup, ['tag', '-t', 1, str(path)])
        info = FileInfo(path)
        assert result.exit_code == 0
        assert info.tags.track_tags(1).get('HIDE') == 'true'
        assert info.tags.track_tags(2).get('HIDE') is None
        assert info.tags.track_tags(3).get('HIDE') == 'true'

    def test_unhide_track(self, datadir):
        """Test the --unhide-track option."""
        path = datadir / 'tagged.flac'
        runner = CliRunner()
        result = runner.invoke(flackup, ['tag', '-T', 3, str(path)])
        info = FileInfo(path)
        assert result.exit_code == 0
        assert info.tags.track_tags(3).get('HIDE') is None


class TestVersion(object):
    """Test the version command."""

    def test_version(self):
        """Test the version command."""
        runner = CliRunner()
        result = runner.invoke(flackup, ['version'])
        assert result.exit_code == 0
        assert result.output.strip() == f'{NAME} {VERSION}'
