#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
##############################################################################

import os
import subprocess
import unittest


class LargeImageExamplesTest(unittest.TestCase):
    def testAverageColor(self):
        # Test running the program
        testDir = os.path.dirname(os.path.realpath(__file__))
        examplesDir = os.path.join(testDir, '../examples')

        prog = 'average_color.py'
        imagePath = os.path.join(os.environ['LARGE_IMAGE_DATA'],
                                 'sample_image.ptif')
        process = subprocess.Popen(
            ['python', prog, imagePath, '-m', '1.25'],
            shell=False, stdout=subprocess.PIPE, cwd=examplesDir)
        results = process.stdout.readlines()
        self.assertEqual(len(results), 19)
        finalColor = [float(val) for val in results[-1].split()[-3:]]
        self.assertEqual(round(finalColor[0]), 245)
        self.assertEqual(round(finalColor[1]), 247)
        self.assertEqual(round(finalColor[2]), 247)
