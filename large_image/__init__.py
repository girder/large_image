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

try:
    from . import server   # Works in non-editable install
    from .server import tilesource
    from .server import cache_util
    from .server.cache_util import cachefactory as config
except ImportError:
    import server          # Works in editable install
    from server import tilesource
    from server import cache_util
    from server.cache_util import cachefactory as config

getTileSource = tilesource.getTileSource  # noqa

__all__ = ['server', 'tilesource', 'getTileSource', 'cache_util', 'config']
