# Flackup

Flackup manages audio CD backups as single FLAC files with [embedded cue
sheets][cuesheet], adds metadata from [MusicBrainz][] and converts albums to
individual [Ogg Vorbis][] tracks.

[cuesheet]: https://xiph.org/flac/format.html#format_overview
[musicbrainz]: https://musicbrainz.org/
[ogg vorbis]: https://xiph.org/vorbis/

## Requirements

- FLAC files with embedded cue sheets
- `flac`, `oggenc` and `vorbisgain`
- Python 3.8

## Installation

Using pip (or [pipx][]):

```bash
pip install flackup
```

[pipx]: https://pypa.github.io/pipx/

## Usage

You can get help for all commands with the `--help` parameter.

To tag a number of FLAC files with embedded cue sheets:

```bash
flackup tag *.flac
```

If there are multiple releases matching the cue sheet (and there probably will
be), Flackup will show you some release details, including the barcode, and let
you pick the correct one.

To add cover images to a number of tagged FLAC files:

```bash
flackup cover *.flac
```

To convert a number of tagged FLAC files to Ogg Vorbis in the `$HOME/Music`
directory:

```bash
flackup convert -d $HOME/Music *.flac
```
