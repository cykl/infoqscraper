#!/usr/bin/env python
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

from distutils.core import setup
import sys

install_requires=[
    "BeautifulSoup4",
    "html5lib",
    "six",
]

if sys.version_info < (2, 7):
    install_requires += ['argparse']


setup(
    version="0.1.1",
    name="infoqscraper",

    description="A Web scraper for www.InfoQ.com",
    long_description="""
InfoQ hosts a lot of great presentations, unfortunately it is not possible to watch them outside of the browser.
The video cannot simply be downloaded because the audio stream and the slide stream are not in the same media.

infoqscraper allows to scrap the website, download the required resources and build a movie from them.
""",

    author="Clément MATHIEU",
    author_email="clement@unportant.info",
    url="https://github.com/cykl/infoqscraper",
    license="License :: OSI Approved :: BSD License",
    classifiers=[
      "Programming Language :: Python",
      "Programming Language :: Python :: 2",
      "Programming Language :: Python :: 3",
      "Topic :: Internet :: WWW/HTTP",
    ],

    packages=["infoqscraper"],
    scripts=["bin/infoqscraper"],
    install_requires=install_requires,
)

