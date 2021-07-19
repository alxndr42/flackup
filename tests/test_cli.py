from click.testing import CliRunner

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
