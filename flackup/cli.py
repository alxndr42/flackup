import os.path

import click

import flackup.convert as fc
from flackup.fileinfo import FileInfo
from flackup.musicbrainz import MusicBrainz, MusicBrainzError


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
RELEASE_URL = 'https://musicbrainz.org/release/{}'


@click.group(context_settings=CONTEXT_SETTINGS)
def flackup():
    """FLAC CD Backup Manager"""
    pass


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
        click.echo('{} {}'.format(info.summary, path))


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
def tag(flac):
    """Tag FLAC files."""
    mb = MusicBrainz()
    for path in flac:
        info = FileInfo(path)
        summary = info.summary
        click.echo('{} {}'.format(summary, path))
        if not summary.parse_ok or not summary.cuesheet:
            click.echo('- Unsuitable file')
            continue
        # TODO Add picture tagging "and summary.pictures"
        if summary.album_tags and summary.track_tags:
            continue
        try:
            release = find_release(mb, info)
        except MusicBrainzError:
            click.echo('- Error while querying MusicBrainz.')
            continue
        if release is None:
            continue
        album_changed = update_album_tags(info, release)
        track_changed = update_track_tags(info, release)
        if album_changed or track_changed:
            info.update()


def find_release(musicbrainz, fileinfo):
    """Retrieve a known release or search for candidates."""
    release = None
    album_tags = fileinfo.tags.album_tags()
    if 'RELEASE_MBID' in album_tags:
        mbid = album_tags['RELEASE_MBID']
    else:
        releases = musicbrainz.releases_by_cuesheet(fileinfo.cuesheet)
        if not releases:
            click.echo('- No releases found')
            return None
        while True:
            value = prompt_releases(releases)
            if value.isdecimal():
                pick = int(value)
                if pick >= 0 and pick < len(releases):
                    mbid = releases[pick]['id']
                    break
            elif value.lower() == 's':
                return None
            elif value.lower() == 'q':
                click.get_current_context().exit()
    return musicbrainz.release_by_id(mbid, fileinfo.cuesheet)


def prompt_releases(candidates):
    """Show candidate releases and prompt for a choice."""
    for index, release in enumerate(candidates):
        parts = [release['artist']]
        status = release.get('status', 'Unknown')
        if status == 'Official':
            parts.append(release['title'])
        else:
            parts.append('{} ({})'.format(release['title'], status))
        media = release['medium-count']
        if media > 1:
            parts.append('Media: {}'.format(media))
        barcode = release.get('barcode')
        if barcode:
            parts.append(barcode)
        parts.append(RELEASE_URL.format(release['id']))
        click.echo('- {:2d}: {}'.format(index, ', '.join(parts)))
    return click.prompt('## = Pick, [S]kip or [Q]uit')


def update_album_tags(fileinfo, release):
    """Return True if the album tags were changed."""
    tags = fileinfo.tags.album_tags()
    tags['RELEASE_MBID'] = release['id']
    tags['ALBUM'] = release['title']
    tags['ARTIST'] = release['artist']
    if 'date' in release:
        tags['DATE'] = release['date']
    if release['medium-count'] > 1:
        tags['DISC'] = release['media'][0]['position']
    return fileinfo.tags.update_album(tags)


def update_track_tags(fileinfo, release):
    """Return True if the track tags were changed."""
    changed = False
    for track in release['media'][0]['tracks']:
        track_number = track['number']
        tags = fileinfo.tags.track_tags(track_number)
        tags['TITLE'] = track['title']
        if 'artist' in track:
            tags['ARTIST'] = track['artist']
        if fileinfo.tags.update_track(track_number, tags):
            changed = True
    return changed


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option('-d', '--output-dir',
              help='Output directory',
              type=click.Path(exists=True, file_okay=False, writable=True),
              default='.')
def convert(flac, output_dir):
    """Convert FLAC files."""
    for path in flac:
        info = FileInfo(path)
        summary = info.summary
        click.echo('========================================')
        click.echo('{} {}'.format(summary, path))
        if not summary.cuesheet or not summary.album_tags:
            click.echo('- Unsuitable file')
            continue
        album_tags = info.tags.album_tags()
        if album_tags.get('HIDE') == 'true':
            click.echo('- Hidden album')
            continue
        if 'ARTIST' not in album_tags or 'ALBUM' not in album_tags:
            click.echo('- Insufficient album tags')
            continue
        tracks = fc.prepare_tracks(info, output_dir, 'ogg')
        if not tracks:
            click.echo('- No tracks to convert')
            continue
        if any(map(lambda t: os.path.exists(t.path), tracks)):
            click.echo('- Existing tracks found')
            continue
        try:
            click.echo('----- Decoding tracks ------------------')
            tempdir = fc.decode_tracks(info, path)
            click.echo('----- Encoding tracks ------------------')
            fc.encode_tracks(tracks, tempdir, 'ogg')
        except fc.ConversionError as e:
            click.echo('ERROR {}'.format(e))
            click.get_current_context().exit(1)
