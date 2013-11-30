
__A Web scraper for [InfoQ](http://infoq.com).__


InfoQ hosts a lot of great presentations, unfortunately it is not possible to watch them outside of the browser
or if you do not have Flash installed. The video cannot simply be downloaded because the audio stream and the
slide stream are not in the same media. By downloading the video you only get the audio track and a video of
the presenter but you don't get the slide.

`infoqscraper` allows you to:
* list and search for presentations
* download the resources (video, audio track, slides)
* build a movie including the slides and the audio track from the resources

Only Python 2.6 or later is currently supported since PIL is not yet available for Python 3.

# Install

Infoqscraper releases can be installed using `pip` and PyPI.

        pip install [--user] infoqscraper

The `infoqscraper` executable should be available in your path. 

If the command cannot be found, you have to add the installation directory 
(usually `$HOME/.local/bin` with `--user`) to the `PATH` environment variable
or specify the full path of the command. 

## Installation on OS X

Install `pip`, `ffmpeg`, `swftools` and `rtmpdump` with [ports](http://www.macports.org/).

        sudo port install py27-pip ffmpeg swftools rtmpdump

Then install Infoqscraper with

        pip-2.7 install --user infoqscraper
        
After the installation is complete, the binary will be located at `~/Library/Python/2.7/bin`.

Add following to your `.bash_profile` in your user directory:

        export PATH=~/Library/Python/2.7/bin:$PATH
        
And after terminal restart, you should be able to type `infoqscraper` and execute it.

# CLI usage

Overview:

        infoqscraper [global options] module [module options] command [command options]

## presentation module

This module allows to list, search and download presentation from the website

### presentation list

The following command displays the 20 latest presentations.

        infoqscraper presentation list -n 20

You can also search for a specific topic:

        infoqscraper presentation list -p agile

By default at most 10 hits are returned and only the latest 80 entries are fetched from the website.
The `-n` and `-m` options can be used to display more hits or to fetch more entries.
Please be a good web citizen and avoid to set `-m` to a very large value. Using a search engine
or the website could be a better idea.

### presentation download

The following command automatically downloads the presentation and creates a movie file
named `Distributed-Systems-with-ZeroMQ-and-gevent.avi`  in the current directory.

        infoqscraper presentation download Distributed-Systems-with-ZeroMQ-and-gevent


## cache module

This module allows to manage the disk cache.

Disk cache is disabled by default and is only useful if you plan to hack on `infoqscraper`. To avoid fetching
the same resource several time from the server, all fetched resources can be put in cache. This is done by setting
the `-c` global option. The resources are stored in the `XDG_CACHE_DIR/infoqscraper` directory.

The following command show the size of the cache:

        infoqscraper cache size

And the clear command allows to wipe the cache

        infoqscraper cache clear


# Dependencies

`infoqscraper` relies on theses 3rd party tools:

1. ffmpeg
2. swftools
3. rtmpdump

If theses tools are not in the PATH, their location can be specified.
Use `infoqscraper presentation download -h` to learn more.

The following python packages are required:

1. BeautifulSoup4
3. PIL

For normal users, they are automatically installed by `pip`. However, if you plan to hack `infoqscraper` you will
most likely install them using the `requirements.txt` file:

        pip install -r requirements.txt

# Compatibility

`infoqscraper` is known to work on:

  - Arch Linux
  - Fedora 17, 18, 19
  - Ubuntu 12.04.2 LTS
  - Mac OS X 10.8.5
  
`ffmpeg` versions from 0.7 to 2+ are supported. Users of Debian Squeeze or
Ubuntu 10.04 LTS must use a newer `ffmpeg` release than the one provided by
their distro. `ffmpeg` 0.5 is too old to be supported (help wanted).

## Arch linux

Packages `python2`, `swftools`, `rtmpdump` and `ffmpeg` must be installed. 

## Ubuntu 12.04 LTS

Packages `ffmpeg`, `rtmpdump` and `libavcodec-extra-53` must be installed.

`swftools` is not available and must installed manually.

## Ubuntu 12.10 and later

Packages `ffmpeg`, `rtmpdump`, `swftools` and `libavcodec-extra-53` must be installed.

## Fedora

Packages `ffmpeg`, `swftools` and `rtmpdump` from rpmfusion must be installed.

`rtmpdump` from Fedora 19 is [currently broken](https://bugzilla.rpmfusion.org/show_bug.cgi?id=2969).
You have to download rtmpdump [source code](http://rtmpdump.mplayerhq.hu/) and compile it.

## Mac OS X

Packages `pip`, `ffmpeg`, `swftools` and `rtmpdump` can be installed via [ports](http://www.macports.org/).

# Help

Feel free to contact me if you have any question or feature request.

If you find this project useful, any contribution or feedback is welcome. If you are not a developer, improving
the packaging, the documentation or fixing my broken English could be a good start.
