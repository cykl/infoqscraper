
`infoqmedia` allows to download presentations from [InfoQ](http://infoq.com).


InfoQ hosts a lot of great presentations, unfortunately it is not possible to watch them outside of the browser.
The video cannot simply be downloaded because the audio stream and the slide stream are not in the same media. By
downloading the video you only get the audio track and a video of the presenter but you don't get the slide.
`infoqmedia` downloads both the original video and the slides to build a new video containing the audio track
and the slides.

## Usage

The following command automatically creates a `Distributed-Systems-with-ZeroMQ-and-gevent.avi` file
in the current directory.

 `./infoqmedia Distributed-Systems-with-ZeroMQ-and-gevent`

## Dependencies

`infoqmedia` relies on theses tools:

1. ffmpeg
2. swftools
3. rtmpdump

The path of the tools can be customized, use `-h` to learn more.
