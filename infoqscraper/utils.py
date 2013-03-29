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
import os
import subprocess
import sys

import Image
import subprocess
import tempfile

if sys.hexversion >= 0x02070000:
	check_output = subprocess.check_output
else:
	def _check_output_backport(*popenargs, **kwargs):
		r"""Run command with arguments and return its output as a byte string.
	 
		Backported from Python 2.7 as it's implemented as pure python on stdlib.
	 
		>>> check_output(['/usr/bin/python', '--version'])
		Python 2.6.2
		"""
		process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
		output, unused_err = process.communicate()
		retcode = process.poll()
		if retcode:
			cmd = kwargs.get("args")
			if cmd is None:
				cmd = popenargs[0]
			error = subprocess.CalledProcessError(retcode, cmd)
			error.output = output
			raise error
		return output
	
	check_output = _check_output_backport


class SwfConverter(object):
    """Convert SWF slides into an images

    Require swfrender (from swftools: http://www.swftools.org/)
    """

    # Currently rely on swftools
    #
    # Would be great to have a native python dependency to convert swf into png or jpg.
    # However it seems that pyswf  isn't flawless. Some graphical elements (like the text!) are lost during
    # the export.

    def __init__(self, swfrender_path='swfrender'):
        self.swfrender = swfrender_path
        self._stdout = None
        self._stderr = None

    def to_png(self, swf_path, png_path=None):
        """ Convert a slide into a PNG image.

        OSError is raised if swfrender is not available.
        An exception is raised if image cannot be created.
        """
        if not png_path:
            png_path = swf_path.replace(".swf", ".png")

        try:
            cmd = [self.swfrender, swf_path, '-o', png_path]
            check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception(u"Failed to convert SWF file %s.\n"
                            u"\tExit status: %s.\n\tOutput:\n%s" % (swf_path, e.returncode, e.output))

        return png_path

    def to_jpeg(self, swf_path, jpg_path=None):
        """ Convert a slide into a PNG image.

        OSError is raised if swfrender is not available.
        An exception is raised if image cannot be created.
        """
        if not jpg_path:
            jpg_path = swf_path.replace(".swf", ".jpg")

        png_path = tempfile.mktemp(suffix=".png")
        self.to_png(swf_path, png_path)
        Image.open(png_path).convert('RGB').save(jpg_path, 'jpeg')
        os.remove(png_path)
        return jpg_path

