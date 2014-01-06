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

import errno
import os
import shutil


class Error(Exception):
    pass


class XDGCache(object):
    """A disk cache for resources.

    Remote resources can be cached to avoid to fetch them several times from the web server.
    The resources are stored into the XDG_CACHE_HOME_DIR.

    Attributes:
        dir: Where to store the cached resources

    """

    def __init__(self):
        self.dir = self._find_dir()

    def _find_dir(self):
        home = os.path.expanduser("~")
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        return os.path.join(xdg_cache_home, "infoqscraper", "resources")

    def _url_to_path(self, url):
        return os.path.join(self.dir, url)

    def get_content(self, url):
        """Returns the content of a cached resource.

        Args:
            url: The url of the resource

        Returns:
            The content of the cached resource or None if not in the cache
        """
        cache_path = self._url_to_path(url)
        try:
            with open(cache_path, 'rb') as f:
                return f.read()
        except IOError:
            return None

    def get_path(self, url):
        """Returns the path of a cached resource.

        Args:
            url: The url of the resource

        Returns:
            The path to the cached resource or None if not in the cache
        """
        cache_path = self._url_to_path(url)
        if os.path.exists(cache_path):
            return cache_path

        return None

    def put_content(self, url, content):
        """Stores the content of a resource into the disk cache.

        Args:
            url: The url of the resource
            content: The content of the resource

        Raises:
            CacheError: If the content cannot be put in cache
        """
        cache_path = self._url_to_path(url)

        # Ensure that cache directories exist
        try:
            dir = os.path.dirname(cache_path)
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise Error('Failed to create cache directories for ' % cache_path)

        try:
            with open(cache_path, 'wb') as f:
                f.write(content)
        except IOError:
            raise Error('Failed to cache content as %s for %s' % (cache_path, url))

    def put_path(self, url, path):
        """Puts a resource already on disk into the disk cache.

        Args:
            url: The original url of the resource
            path: The resource already available on disk

        Raises:
            CacheError: If the file cannot be put in cache
        """
        cache_path = self._url_to_path(url)

        # Ensure that cache directories exist
        try:
            dir = os.path.dirname(cache_path)
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise Error('Failed to create cache directories for ' % cache_path)

        # Remove the resource already exist
        try:
            os.unlink(cache_path)
        except OSError:
            pass

        try:
            # First try hard link to avoid wasting disk space & overhead
            os.link(path, cache_path)
        except OSError:
            try:
                # Use file copy as fallaback
                shutil.copyfile(path, cache_path)
            except IOError:
                raise Error('Failed to cache %s as %s for %s' % (path, cache_path, url))

    def clear(self):
        """Delete all the cached resources.

        Raises:
            OSError: If some file cannot be delete
        """
        shutil.rmtree(self.dir)

    @property
    def size(self):
        """Returns the size of the cache in bytes."""
        total_size = 0
        for dir_path, dir_names, filenames in os.walk(self.dir):
            for f in filenames:
                fp = os.path.join(dir_path, f)
                total_size += os.path.getsize(fp)
        return total_size
