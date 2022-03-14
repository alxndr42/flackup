import os.path

import click

from flackup import VERSION
import flackup.convert as fc
from flackup.fileinfo import FileInfo
from flackup.musicbrainz import MusicBrainz, MusicBrainzError


FRONT_COVER_TYPE = 3

RELEASE_URL = 'https://musicbrainz.org/release/{}'


@click.group()
def flackup():
    """FLAC CD Backup Manager"""
    pass


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option('-v', '--verbose', help='Show more information.', is_flag=True)
@click.option('--hidden',
              help='Show only albums with a HIDE=true tag.',
              is_flag=True)
def analyze(flac, verbose, hidden):
    """Analyze FLAC files.

    For each file, shows a list of flags followed by the filename.

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
        if info.parse_ok:
            album_tags = info.tags.album_tags()
        else:
            album_tags = {}
        if album_tags.get('HIDE') != 'true' and hidden:
            continue
        if not verbose:
            click.echo('{} {}'.format(info.summary, path))
        else:
            img = '|                 |'
            url = ''
            if info.parse_ok:
                front = info.get_picture(FRONT_COVER_TYPE)
                if front is not None:
                    width = front.width
                    height = front.height
                    type_ = fc.picture_ext(front).upper()
                    img = '| {:4d} x {:4d} {} |'.format(width, height, type_)
                mbid = album_tags.get('RELEASE_MBID')
                if mbid is not None:
                    url = ' | ' + RELEASE_URL.format(mbid)
            click.echo('{} {} {}{}'.format(info.summary, img, path, url))


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option('--mbid',
              help='Use this MBID for release metadata.')
@click.option('--hide',
              help='Add an album-level HIDE tag.',
              is_flag=True)
@click.option('--unhide',
              help='Remove an album-level HIDE tag.',
              is_flag=True)
@click.option('-t', '--hide-track',
              help='Add a track-level HIDE tag.',
              type=int,
              multiple=True)
@click.option('-T', '--unhide-track',
              help='Remove a track-level HIDE tag.',
              type=int,
              multiple=True)
def tag(flac, mbid, hide, unhide, hide_track, unhide_track):
    """Tag FLAC files.

    Files with a cue sheet but no album/track-level tags will be tagged using
    metadata from MusicBrainz.
    """
    mb = MusicBrainz()
    for path in flac:
        info = FileInfo(path)
        summary = info.summary
        if not summary.parse_ok or not summary.cuesheet:
            continue
        tagged = summary.album_tags or summary.track_tags
        album_edit = hide or unhide
        track_edit = hide_track or unhide_track
        if tagged and not (album_edit or track_edit):
            continue
        click.echo('{} {}'.format(summary, path))
        album_changed = False
        track_changed = False
        # Query MusicBrainz
        if not tagged:
            try:
                if mbid is None:
                    release = find_release(mb, info)
                else:
                    release = mb.release_by_id(mbid, info.cuesheet)
                if release is None:
                    continue
                original_date = mb.first_release_date(release['group-id'])
            except MusicBrainzError:
                click.echo('- Error while querying MusicBrainz')
                continue
            album_changed |= update_album_tags(info, release, original_date)
            track_changed |= update_track_tags(info, release)
        # Hide or unhide album
        tags = info.tags.album_tags()
        if hide:
            tags['HIDE'] = 'true'
        if unhide:
            tags.pop('HIDE', None)
        album_changed |= info.tags.update_album(tags)
        # Hide or unhide tracks
        for number in hide_track:
            tags = info.tags.track_tags(number)
            tags['HIDE'] = 'true'
            track_changed |= info.tags.update_track(number, tags)
        for number in unhide_track:
            tags = info.tags.track_tags(number)
            tags.pop('HIDE', None)
            track_changed |= info.tags.update_track(number, tags)
        # Save any changes
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
        if len(releases) > 1:
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
        else:
            mbid = releases[0]['id']
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
        country = release.get('country')
        if country:
            parts.append(country)
        parts.append(RELEASE_URL.format(release['id']))
        click.echo('- {:2d}: {}'.format(index, ', '.join(parts)))
    return click.prompt('## = Pick, [S]kip or [Q]uit')


def update_album_tags(fileinfo, release, original_date):
    """Return True if the album tags were changed."""
    tags = fileinfo.tags.album_tags()
    tags['RELEASE_MBID'] = release['id']
    tags['ALBUM'] = release['title']
    tags['ARTIST'] = release['artist']
    date = release.get('date')
    if date is not None:
        tags['DATE'] = release['date']
    if use_original_date(original_date, date):
        tags['DATE_ORIGINAL'] = original_date
    if release['medium-count'] > 1:
        tags['DISC'] = release['media'][0]['position']
    return fileinfo.tags.update_album(tags)


def use_original_date(original_date, release_date):
    """Return True if the original date should be used in tags."""
    if original_date is None:
        return False
    if release_date is None:
        return True
    original_year = original_date[:4]
    release_year = release_date[:4]
    if original_year == release_year:
        return False
    return True


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
def cover(flac):
    """Add cover images to tagged FLAC files."""
    mb = MusicBrainz()
    for path in flac:
        info = FileInfo(path)
        if not info.parse_ok:
            continue
        album_tags = info.tags.album_tags()
        mbid = album_tags.get('RELEASE_MBID')
        if mbid is None:
            continue
        front = info.get_picture(FRONT_COVER_TYPE)
        if front is not None:
            continue
        click.echo('{} {}'.format(info.summary, path))
        try:
            release = mb.release_by_id(mbid)
            data = mb.front_cover(release)
            if data is not None:
                front = fc.parse_picture(data, FRONT_COVER_TYPE)
                if info.set_picture(front):
                    info.update()
                width = front.width
                height = front.height
                type_ = fc.picture_ext(front).upper()
                click.echo('- {} x {} {}'.format(width, height, type_))
            else:
                click.echo('- No image found')
        except MusicBrainzError:
            click.echo('- Error while querying MusicBrainz')
            continue
        except Exception as e:
            click.echo('- Error while processing image ({})'.format(e))
            continue


@flackup.command()
@click.argument('flac', type=click.Path(exists=True, dir_okay=False), nargs=-1)
@click.option('-d', '--output-dir',
              help='Output directory',
              type=click.Path(exists=True, file_okay=False, writable=True),
              default='.')
@click.option('--hidden',
              help='Convert only albums with a HIDE=true tag.',
              is_flag=True)
def convert(flac, output_dir, hidden):
    """Convert FLAC files."""
    for path in flac:
        info = FileInfo(path)
        summary = info.summary
        if not summary.parse_ok or not summary.cuesheet:
            continue
        album_tags = info.tags.album_tags()
        if album_tags.get('HIDE') == 'true' and not hidden:
            continue
        if 'ARTIST' not in album_tags or 'ALBUM' not in album_tags:
            continue
        tracks = fc.prepare_tracks(info, output_dir, 'ogg')
        if not tracks:
            continue
        if any(map(lambda t: os.path.exists(t.path), tracks)):
            continue
        click.echo('{} {}'.format(summary, path))
        try:
            click.echo('- Decoding tracks')
            tempdir = fc.decode_tracks(info)
            click.echo('- Encoding tracks')
            fc.encode_tracks(tracks, tempdir, 'ogg')
        except fc.ConversionError as e:
            click.echo('ERROR {}'.format(e))
            click.get_current_context().exit(1)
        front = info.get_picture(FRONT_COVER_TYPE)
        if front is not None:
            dst_base = os.path.dirname(tracks[0].path)
            fc.export_cover(front, dst_base)


@flackup.command()
def version():
    """Show the version number."""
    click.echo(VERSION)


if __name__ == '__main__':
    flackup()
