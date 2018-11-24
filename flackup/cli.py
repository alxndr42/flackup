import sys

import click

from flackup.fileinfo import FileInfo
from flackup.musicbrainz import MusicBrainz


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def flackup():
    """FLAC CD Backup Manager"""
    pass


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
def lookup(flac):
    """Lookup FLAC cuesheets in MusicBrainz."""
    mb = MusicBrainz()
    for path in flac:
        click.echo(path)
        info = FileInfo(path)
        if not info.parse_ok:
            click.echo('- Parse error (%s)' % info.parse_exception)
            continue
        if info.cuesheet is None:
            click.echo('- No cuesheet')
            continue

        matches = None
        try:
            matches = mb.releases_by_cuesheet(info.cuesheet)
        except Exception as e:
            click.echo('- Lookup error (%s)' % e)
            continue

        if not matches:
            click.echo('- No matches')
            continue

        for match in matches:
            parts = [match['id'], match['artist']]
            status = match.get('status', 'Unknown')
            if status == 'Official':
                parts.append(match['title'])
            else:
                parts.append('%s (%s)' % (match['title'], status))
            barcode = match.get('barcode')
            if barcode:
                parts.append(barcode)
            click.echo('- %s' % ' | '.join(parts))


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
def analyze(flac):
    """Analyze FLAC files.

    For each file, prints a list of flags followed by the filename.

    \b
    Flags:
    - O: The file parsed successfully.
    - C: A cue sheet is present.
    - A: Album-level tags are present (any number).
    - T: Track-level tags are present (any number).
    - P: Pictures are present (any number).
    """
    for path in flac:
        info = FileInfo(path)
        click.echo('%s %s' % (info.summary, path))
