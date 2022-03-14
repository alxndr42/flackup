from collections import namedtuple
import io
import os
import os.path
import re
import shutil
import tempfile
import wave

from PIL import Image

from flackup.fileinfo import Picture


ESC_RE = re.compile(r'[^-\w ,&()]')
TRACK_WAV = 'track-{:02d}.wav'


Track = namedtuple('Track', 'number path tags')


class ConversionError(Exception):
    """Exception for decode/encode errors."""
    pass


def prepare_tracks(fileinfo, base_dir, fmt):
    """Return a list of Tracks to be encoded."""
    def esc(filename):
        """Escape non-whitelisted characters in the filename."""
        filename = ESC_RE.sub('_', filename)
        filename = filename.strip(' _')
        return filename

    tracks = []
    cuesheet = fileinfo.cuesheet
    album_tags = fileinfo.tags.album_tags()
    if 'DATE_ORIGINAL' in album_tags:
        album_tags['DATE'] = album_tags['DATE_ORIGINAL']
    if 'DATE' in album_tags:
        album_tags['DATE'] = album_tags['DATE'][:4]
    album_artist = album_tags['ARTIST']
    album_title = album_tags['ALBUM']
    dst_base = os.path.join(base_dir, esc(album_artist), esc(album_title))
    set_album_artist = False
    for track in cuesheet.audio_tracks:
        track_tags = fileinfo.tags.track_tags(track.number)
        if track_tags.get('HIDE') == 'true':
            continue
        track_title = track_tags.get('TITLE')
        if track_title is None:
            track_title = 'Untitled'
        dst_name = '{:02d} {}.{}'.format(track.number, esc(track_title), fmt)
        if 'DISC' in album_tags:
            dst_name = '{}-{}'.format(album_tags['DISC'], dst_name)
        dst_path = os.path.join(dst_base, dst_name)
        tags = dict(album_tags)
        track_artist = track_tags.get('ARTIST')
        if track_artist is not None and track_artist != album_artist:
            set_album_artist = True
        tags.update(track_tags)
        tracks.append(Track(track.number, dst_path, tags))
    if set_album_artist:
        for track in tracks:
            track.tags['ALBUMARTIST'] = album_artist
    return tracks


def decode_tracks(fileinfo):
    """Decode the FLAC file into individual WAV files.

    WAV file names follow the pattern "track-NN.wav".
    Tracks with a "HIDE" tag set to "true" are skipped.

    Returns a TemporaryDirectory with the WAV files, or None.
    """
    executable = shutil.which('flac')
    if executable is None:
        raise ConversionError('flac executable not found.')

    tempdir = tempfile.TemporaryDirectory(prefix='flackup-')
    flac = fileinfo.path
    wav = os.path.join(tempdir.name, 'flackup.wav')
    res = os.system('flac -s -d {} -o {}'.format(quote(flac), quote(wav)))
    exit = res >> 8
    if exit != 0:
        raise ConversionError('Non-zero exit status.')

    stream = fileinfo.streaminfo
    tracks = fileinfo.cuesheet.audio_tracks
    numbers = [t.number for t in tracks]
    starts = [t.offset for t in tracks]
    ends = starts[1:] + [stream.sample_count]
    sample_bytes = stream.channels * (stream.sample_bits // 8)

    with wave.open(wav, 'rb') as wave_in:
        for number, start, end in zip(numbers, starts, ends):
            tags = fileinfo.tags.track_tags(number)
            if tags.get('HIDE') == 'true':
                continue
            out_name = TRACK_WAV.format(number)
            out_path = os.path.join(tempdir.name, out_name)
            wave_in.setpos(start)
            with wave.open(out_path, 'wb') as wave_out:
                wave_out.setnchannels(stream.channels)
                wave_out.setsampwidth(stream.sample_bits // 8)
                wave_out.setframerate(stream.sample_rate)
                copy(wave_in, wave_out, end - start, sample_bytes)

    os.remove(wav)
    return tempdir


def encode_tracks(tracks, tempdir, fmt):
    """Encode the Tracks from WAV files in tempdir."""
    for track in tracks:
        dst_base = os.path.dirname(track.path)
        os.makedirs(dst_base, exist_ok=True)
        src_name = TRACK_WAV.format(track.number)
        src_path = os.path.join(tempdir.name, src_name)
        encode_ogg(track, src_path)
    replaygain_ogg(tracks)


def encode_ogg(track, src_path):
    """Encode the Track as Ogg Vorbis."""
    executable = shutil.which('oggenc')
    if executable is None:
        raise ConversionError('oggenc executable not found.')

    tags = track.tags
    cmd = [
        'oggenc',
        '-Q',
        '-q 6',
        '-o {}'.format(quote(track.path)),
        '--utf8',
        '-t {}'.format(quote(tags.get('TITLE', ''))),
        '-a {}'.format(quote(tags.get('ARTIST', ''))),
        '-l {}'.format(quote(tags.get('ALBUM', ''))),
        '-d {}'.format(quote(tags.get('DATE', ''))),
        '-G {}'.format(quote(tags.get('GENRE', ''))),
        '-N {}'.format(track.number),
    ]
    disc = tags.get('DISC')
    if disc is not None:
        cmd.append('-c DISCNUMBER={}'.format(disc))
    album_artist = tags.get('ALBUMARTIST')
    if album_artist is not None:
        cmd.append('-c ALBUMARTIST={}'.format(quote(album_artist)))
    cmd.append(src_path)
    res = os.system(' '.join(cmd))
    exit = res >> 8
    if exit != 0:
        raise ConversionError('Non-zero exit status.')


def replaygain_ogg(tracks):
    """Add ReplayGain information to the Tracks."""
    executable = shutil.which('vorbisgain')
    if executable is None:
        raise ConversionError('vorbisgain executable not found.')

    cmd = [
        'vorbisgain',
        '-q',
        '-a',
    ]
    for track in tracks:
        cmd.append(quote(track.path))
    res = os.system(' '.join(cmd))
    exit = res >> 8
    if exit != 0:
        raise ConversionError('Non-zero exit status.')


def parse_picture(bytes_, type_):
    """Return a Picture created from the given bytes and type.

    Throws an exception in case of errors or unsupported formats.
    """
    image = Image.open(io.BytesIO(bytes_))
    if image.format == 'JPEG':
        mime = 'image/jpeg'
    elif image.format == 'PNG':
        mime = 'image/png'
    else:
        raise Exception('Unsupported format: {}'.format(image.format))
    if image.mode == 'RGB':
        depth = 24
    elif image.mode == 'RGBA':
        depth = 32
    elif image.mode == 'CMYK':
        depth = 32
    else:
        raise Exception('Unsupported mode: {}'.format(image.mode))
    return Picture(type_, mime, image.width, image.height, depth, bytes_)


def picture_ext(picture):
    """Return a file extension for the Picture's MIME type."""
    if picture.mime == 'image/jpeg':
        return 'jpg'
    elif picture.mime == 'image/png':
        return 'png'
    else:
        return 'bin'


def export_cover(picture, dst_base, max_width=500):
    """Export the Picture as a size-constrained cover.ext file."""
    cover_path = os.path.join(dst_base, 'cover.jpg')
    image = Image.open(io.BytesIO(picture.data))
    if picture.width > max_width:
        factor = max_width / picture.width
        height = int(picture.height * factor)
        image = image.resize((max_width, height), Image.LANCZOS)
        if image.mode != 'RGB':
            image = image.convert(mode='RGB')
        image.save(cover_path, quality=90, optimize=True)
    else:
        with open(cover_path, 'wb') as f:
            f.write(picture.data)


def copy(wave_in, wave_out, sample_count, sample_bytes):
    """Copy samples between WAV objects."""
    b_size = 65536 // sample_bytes
    while sample_count:
        b = wave_in.readframes(min(b_size, sample_count))
        b_samples = len(b) // sample_bytes
        sample_count -= b_samples
        wave_out.writeframes(b)


def quote(string):
    """Return the string in double quotes, escaped."""
    return '"{}"'.format(string.replace('"', '\\"'))
