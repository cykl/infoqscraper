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

import contextlib
import os

from six.moves import http_cookiejar
from six.moves import urllib

from infoqscraper import cache
from infoqscraper import  AuthenticationError, DownloadError


def get_url(path, scheme="http"):
    """ Return the full InfoQ URL """
    return scheme + "://www.infoq.com" + path

INFOQ_404_URL = 'http://www.infoq.com/error?sc=404'


class InfoQ(object):
    """ InfoQ web client entry point

    Attributes:
        authenticated:       If logged in or not
        cache:              None if caching is disable. A Cache object otherwise
    """

    def __init__(self, cache_enabled=False):
        self.authenticated = False
        # InfoQ requires cookies to be logged in. Use a dedicated urllib opener
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http_cookiejar.CookieJar()))
        self.cache = None
        if cache_enabled:
            self.enable_cache()

    def enable_cache(self):
        if not self.cache:
            self.cache = cache.XDGCache()

    def login(self, username, password):
        """ Log in.

        AuthenticationFailedException exception is raised if authentication fails.
        """
        url = get_url("/login.action", scheme="https")
        params = {
            'username': username,
            'password': password,
            'submit-login': '',
        }
        with contextlib.closing(self.opener.open(url, urllib.parse.urlencode(params))) as response:
            if not "loginAction.jsp" in response.url:
                raise AuthenticationError("Login failed. Unexpected redirection: %s" % response.url)
            if not "resultMessage=success" in response.url:
                raise AuthenticationError("Login failed.")

        self.authenticated = True

    def fetch(self, url):
        if self.cache:
            content = self.cache.get_content(url)
            if not content:
                content = self.fetch_no_cache(url)
                self.cache.put_content(url, content)
        else:
            content = self.fetch_no_cache(url)

        return content

    def fetch_no_cache(self, url):
        """ Fetch the resource specified and return its content.

            DownloadError is raised if the resource cannot be fetched.
        """
        try:

            with contextlib.closing(self.opener.open(url)) as response:
                # InfoQ does not send a 404 but a 302 redirecting to a valid URL...
                if response.code != 200 or response.url == INFOQ_404_URL:
                    raise DownloadError("%s not found" % url)
                return response.read()
        except urllib.error.URLError as e:
            raise DownloadError("Failed to get %s: %s" % (url, e))

    def download(self, url, dir_path, filename=None):
        """ Download the resources specified by url into dir_path. The resulting
            file path is returned.

            DownloadError is raised the resources cannot be downloaded.
        """
        if not filename:
            filename = url.rsplit('/', 1)[1]
        path = os.path.join(dir_path, filename)

        content = self.fetch(url)
        with open(path, "wb") as f:
            f.write(content)

        return path

    def download_all(self, urls, dir_path):
        """ Download all the resources specified by urls into dir_path. The resulting
            file paths is returned.

            DownloadError is raised if at least one of the resources cannot be downloaded.
            In the case already downloaded resources are erased.
        """
        # TODO: Implement parallel download
        filenames = []

        try:
            for url in urls:
                filenames.append(self.download(url, dir_path))
        except DownloadError as e:
            for filename in filenames:
                os.remove(filename)
            raise e

        return filenames
