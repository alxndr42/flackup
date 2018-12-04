# Flackup

Flackup manages audio CD backups as single FLAC files with [embedded cue
sheets][cuesheet]. Add metadata from [MusicBrainz][] and convert albums to
individual [Ogg Vorbis][] tracks.

## Requirements

* FLAC files with embedded cue sheets
* `flac`, `oggenc` and `vorbisgain`
* Python 3

## Installation

Using pip (or [pipsi][]):

    pip install flackup

## Usage

To tag a number of FLAC files with embedded cue sheets:

    flackup tag *.flac

If there are multiple releases matching the cue sheet (and there probably will
be), Flackup will show you some release details, including the barcode, and let
you pick the correct one.

To convert a number of tagged FLAC files to Ogg Vorbis in the */var/ogg*
directory:

    flackup convert -d /var/ogg *.flac

You can get help for all commands with the `-h` parameter:

    flackup -h

  [cuesheet]: https://xiph.org/flac/documentation_tools_flac.html#encoding_options
  [MusicBrainz]: https://musicbrainz.org/
  [Ogg Vorbis]: https://xiph.org/vorbis/
  [pipsi]: https://github.com/mitsuhiko/pipsi
