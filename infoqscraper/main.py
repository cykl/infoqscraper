# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import argparse
import os
import pkg_resources
import re
import six
import subprocess
import sys

from infoqscraper import client
from infoqscraper import convert
from infoqscraper import scrap
from infoqscraper import DownloadError, ConversionError

app_name = "infoqscraper"
try:
    app_version = pkg_resources.require(app_name)[0].version
except pkg_resources.DistributionNotFound:
    app_version = "unknown-version"


class ArgumentError(Exception):
    pass


class CommandError(Exception):
    pass


class Module(object):
    """Regroups  a set of commands by topic."""

    def main(self, infoq_client, args):
        """Invoke the right Command according to given arguments.

        Args:
            infoq_client: The web client
            args: Argument list

        Returns:
            The command exit code.

        Raises:
            ParameterError: In case of missing or bad arguments
        """
        raise NotImplementedError


class Command(object):
    """A command to execute."""

    def main(self, infoq_client, args):
        """Runs the command.

        Args:
            infoq_client: The web client
            args: Argument list

        Returns:
            The command exit code.

        Raises:
            ParameterError: In case of missing or bad arguments
        """
        raise NotImplementedError


class CacheModule(Module):
    """All commands related to the disk cache go here.

    New commands must be registered into the commands attribute.

    Attributes:
        commands: A dictionary of available commands. Keys are command names. Value are commands.
    """
    name = "cache"

    def __init__(self):
        self.commands = {
            CacheModule.Size.name: CacheModule.Size,
            CacheModule.Clear.name: CacheModule.Clear,
            }

    def main(self, infoq_client, args):
        parser = argparse.ArgumentParser(prog="%s %s" % (app_name, self.name))
        parser.add_argument('command', choices = list(self.commands.keys()))
        parser.add_argument('command_args', nargs=argparse.REMAINDER)
        args = parser.parse_args(args=args)

        try:
            command_class = self.commands[args.command]
        except KeyError:
            raise ArgumentError("%s is not a %s %s command" % (args.command, app_name, self.name))

        command = command_class()
        return command.main(infoq_client, args.command_args)

    class Clear(Command):
        """Clears the cache."""
        name = "clear"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, CacheModule.name, CacheModule.Clear.name))
            args = parser.parse_args(args=args)

            infoq_client.enable_cache()
            try:
                infoq_client.cache.clear()
            except OSError as e:
                raise CommandError("Failed to clean the disk cache: %s" % e, 3)

            return 0

    class Size(Command):
        """Gives information about the disk cache"""
        name = "size"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, CacheModule.name, CacheModule.Size.name))
            args = parser.parse_args(args=args)

            infoq_client.enable_cache()
            size = infoq_client.cache.size
            human_size = self.__humanize(size, 2)
            print("%s" % human_size)

        def __humanize(self, bytes, precision=2):
            suffixes = (
                (1 << 50, 'PB'),
                (1 << 40, 'TB'),
                (1 << 30, 'GB'),
                (1 << 20, 'MB'),
                (1 << 10, 'kB'),
                (1, 'bytes')
            )
            if bytes == 1:
                return '1 byte'
            for factor, suffix in suffixes:
                if bytes >= factor:
                    break
            return '%.*f %s' % (precision, bytes / factor, suffix)


class PresentationModule(Module):
    """All commands related to presentations go here.

    New commands must be registered into the commands attribute.

    Attributes:
        commands: A dictionary of available commands. Keys are command names. Value are commands.
    """
    name = "presentation"

    def __init__(self):
        self.commands = {
            PresentationModule.PresentationList.name: PresentationModule.PresentationList,
            PresentationModule.PresentationDownload.name: PresentationModule.PresentationDownload,
        }

    def main(self, infoq_client, args):
        parser = argparse.ArgumentParser(prog="%s %s" % (app_name, PresentationModule.name))
        parser.add_argument('command', choices = list(self.commands.keys()))
        parser.add_argument('command_args', nargs=argparse.REMAINDER)
        args = parser.parse_args(args=args)

        try:
            command_class = self.commands[args.command]
        except KeyError:
            raise ArgumentError("%s is not a %s %s command" % (args.command, app_name, self.name))

        command = command_class()
        return command.main(infoq_client, args.command_args)

    class PresentationList(Command):
        """List available presentations."""
        name = "list"

        class _Filter(scrap.MaxPagesFilter):
            """Filter summary according to a pattern.

            The number of results and fetched pages can be bounded.
            """

            def __init__(self, pattern=None, max_hits=20, max_pages=5):
                """
                Args:
                    pattern: A regex to filter result
                    max_hits: number of results upper bound
                    max_pages: fetch pages upper bound
                """
                super(PresentationModule.PresentationList._Filter, self).__init__(max_pages)

                self.pattern = pattern
                self.max_hits = max_hits
                self.hits = 0

            def filter(self, p_summaries):

                if self.hits >= self.max_hits:
                    raise StopIteration

                s = super(PresentationModule.PresentationList._Filter, self).filter(p_summaries)
                s = list(filter(self._do_match, s))
                s = s[:(self.max_hits - self.hits)]  # Remove superfluous items
                self.hits += len(s)
                return s

            def _do_match(self, summary):
                """ Return true whether the summary match the filtering criteria """
                if summary is None:
                    return False

                if self.pattern is None:
                    return True

                search_txt = summary['desc'] + " " + summary['title']
                return re.search(self.pattern, search_txt, flags=re.I)


        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, PresentationModule.name, PresentationModule.PresentationList.name))
            parser.add_argument('-m', '--max-pages', type=int, default=10,   help='maximum number of pages to fetch (~10 presentations per page)')
            parser.add_argument('-n', '--max-hits',  type=int, default=10,   help='maximum number of hits')
            parser.add_argument('-p', '--pattern',   type=str, default=None, help='filter hits according to this pattern')
            parser.add_argument('-s', '--short',     action="store_true",    help='short output, only ids are displayed')
            args = parser.parse_args(args=args)

            filter = PresentationModule.PresentationList._Filter(pattern=args.pattern, max_hits=args.max_hits, max_pages=args.max_pages)
            summaries = scrap.get_summaries(infoq_client, filter=filter)
            if args.short:
                self.__short_output(summaries)
            else:
                self.__standard_output(summaries)

            return 0

        def __standard_output(self, results):
            from textwrap import fill

            index = 0
            for result in results:
                tab = ' ' * 8
                date = result['date'].strftime("%Y-%m-%d")
                print(six.u(""))
                print(six.u("{0:>3}. Title: {1} ({2})").format(index, result['title'], date))
                print(six.u("     Id: {0}").format(result['id']))
                print(six.u("     Desc: \n{0}{1}").format(tab, fill(result['desc'], width=80, subsequent_indent=tab)))
                index += 1

        def __short_output(self, results):
            for result in results:
                print(result['id'])

    class PresentationDownload(Command):
        """Download a presentation"""
        name = "download"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, PresentationModule.name, PresentationModule.PresentationDownload.name))
            parser.add_argument('-f', '--ffmpeg',    nargs="?", type=str, default="ffmpeg",    help='ffmpeg binary')
            parser.add_argument('-s', '--swfrender', nargs="?", type=str, default="swfrender", help='swfrender binary')
            parser.add_argument('-r', '--rtmpdump',  nargs="?", type=str, default="rtmpdump" , help='rtmpdump binary')
            parser.add_argument('-o', '--output',    nargs="?", type=str, help='output file')
            parser.add_argument('-y', '--overwrite', action="store_true", help='Overwrite existing video files')
            parser.add_argument('-t', '--type',      nargs="?", type=str, default="legacy",
                                help='output type: legacy, h264, h264_overlay')
            parser.add_argument('identifier', help='name of the presentation or url')
            args = parser.parse_args(args)

            # Check required tools are available before doing any useful work
            self.__check_dependencies([args.ffmpeg, args.swfrender, args.rtmpdump])

            # Process arguments
            id = self.__extract_id(args.identifier)
            output = self.__chose_output(args.output, id)

            try:
                pres = scrap.Presentation(infoq_client, id)
            except client.DownloadError as e:
                return warn("Presentation %s not found. Please check your id or url" % id, 2)

            kwargs = {
                "ffmpeg":    args.ffmpeg,
                "rtmpdump":  args.rtmpdump,
                "swfrender": args.swfrender,
                "overwrite": args.overwrite,
                "type":      args.type,
            }

            with convert.Converter(pres, output, **kwargs) as builder:
                try:
                    builder.create_presentation()
                except (DownloadError, ConversionError) as e:
                    return warn("Failed to create presentation %s: %s" % (output, e), 2)

        def __check_dependencies(self, dependencies):
            for cmd in dependencies:
                try:
                    with open(os.devnull, 'w') as null:
                        subprocess.call(cmd, stdout=null, stderr=null)
                except OSError:
                    raise ArgumentError("%s not found. Please install required dependencies or specify the binary location" % cmd)

        def __extract_id(self, name):
            mo = re.search("^https?://www.infoq.com/presentations/([^/#?]+)", name)
            if mo:
                return mo.group(1)

            return name

        def __chose_output(self, output, id):
            if output:
                return output

            return "%s.avi" % id


def warn(str, code=1):
    six.print_(str, file=sys.stderr)
    return code


def main():
    # Required when stdout is piped
    if not sys.stdout.encoding:
        import codecs
        import locale
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

    modules = {
        PresentationModule.name: PresentationModule,
        CacheModule.name: CacheModule
    }

    parser = argparse.ArgumentParser(prog="infoqscraper")
    parser.add_argument('-c', '--cache'    , action="store_true", help="Enable disk caching.")
    parser.add_argument('-V', '--version'  , action="version",    help="Display version",
                        version="%s %s" % (app_name, app_version))
    parser.add_argument('module', choices=list(modules.keys()))
    parser.add_argument('module_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    infoq_client = client.InfoQ(cache_enabled=args.cache)

    try:
        module_class = modules[args.module]
    except KeyError:
        return warn("%s: '%s' is not a module. See '%s --help'" % (app_name, args.module, app_name))

    module = module_class()
    try:
        return module.main(infoq_client, args.module_args)
    except (ArgumentError, CommandError) as e:
        return warn(e)

if __name__ == "__main__":
    sys.exit(main())

