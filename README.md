
`infoqmedia` allows to download presentations from [InfoQ](http://infoq.com).


InfoQ hosts a lot of great presentations, unfortunately it is not possible to watch them outside of the browser.
The video cannot simply be downloaded because the audio stream and the slide stream are not in the same media. By
downloading the video you only get the audio track and a video of the presenter but you don't get the slide.
`infoqmedia` downloads both the original video and the slides to build a new video containing the audio track
and the slides.

`infoqlisting` allows to list the latest presentations or search for a specific presentation or topic using a regex. 
You no longer have to follow the RSS feed or go to the website to discover interesting presentations.

## infoqmedia usage

The following command automatically downloads the presentation and creates a `Distributed-Systems-with-ZeroMQ-and-gevent.avi` 
file in the current directory.

 `./infoqmedia Distributed-Systems-with-ZeroMQ-and-gevent`

## infoqlisting usage

The following command display the fifteen latest presentations.
 `./infoqlisting -n 15`

You can also search for a specific topic.
 `./infoqlisting -p agile`

By default `infoqlisting` displays at most 10 hits and runs the query on the latest 80 entries. 
The `-n` and `-m` options can be used to display more hits or to query more entries.  Please be a good web citizen 
and avoid to set `-m` to a very large value. Using a search engine or the website could be a better idea. 


## Dependencies

`infoqmedia` relies on theses tools:

1. ffmpeg
2. swftools
3. rtmpdump

The path of the tools can be customized, use `-h` to learn more.
