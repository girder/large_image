# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import cherrypy
import time

from girder.api.rest import getCurrentToken
from girder.utility.model_importer import ModelImporter

LoadModelCache = {}
LoadModelCacheMaxEntries = 100
LoadModelCacheExpiryDuration = 300  # seconds


def invalidateLoadModelCache(*args, **kwargs):
    """
    Empty the LoadModelCache.
    """
    LoadModelCache.clear()


def loadModel(resource, model, plugin='_core', id=None, allowCookie=False,
              level=None):
    """
    Load a model based on id using the current cherrypy token parameter for
    authentication, caching the results.  This must be called in a cherrypy
    context.

    :param resource: the resource class instance calling the function.  Used
        for access to the current user and model importer.
    :param model: the model name, e.g., 'item'.
    :param plugin: the plugin name when loading a plugin model.
    :param id: a string id of the model to load.
    :param allowCookie: true if the cookie authentication method is allowed.
    :param level: access level desired.
    :returns: the loaded model.
    """
    key = tokenStr = None
    if 'token' in cherrypy.request.params:  # Token as a parameter
        tokenStr = cherrypy.request.params.get('token')
    elif 'Girder-Token' in cherrypy.request.headers:
        tokenStr = cherrypy.request.headers['Girder-Token']
    elif 'girderToken' in cherrypy.request.cookie and allowCookie:
        tokenStr = cherrypy.request.cookie['girderToken'].value
    key = (model, tokenStr, id)
    cacheEntry = LoadModelCache.get(key)
    if cacheEntry and cacheEntry['expiry'] > time.time():
        entry = cacheEntry['result']
        cacheEntry['hits'] += 1
    else:
        # we have to get the token separately from the user if we are using
        # cookies.
        if allowCookie:
            getCurrentToken(allowCookie)
            cherrypy.request.girderAllowCookie = True
        entry = ModelImporter.model(model, plugin).load(
            id=id, level=level, user=resource.getCurrentUser())
        # If the cache becomes too large, just dump it -- this is simpler
        # than dropping the oldest values and avoids having to add locking.
        if len(LoadModelCache) > LoadModelCacheMaxEntries:
            LoadModelCache.clear()
        LoadModelCache[key] = {
            'id': id,
            'model': model,
            'tokenId': tokenStr,
            'expiry': time.time() + LoadModelCacheExpiryDuration,
            'result': entry,
            'hits': 0
        }
    return entry
