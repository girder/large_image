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

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import loadmodel
from girder.api.v1.item import Item
from girder.constants import AccessType, TokenScope


class InternalMetadataItemResource(Item):
    def __init__(self, apiRoot):
        super().__init__()
        apiRoot.item.route(
            'GET', (':itemId', 'internal_metadata', ':key'), self.getMetadataKey
        )
        apiRoot.item.route(
            'PUT', (':itemId', 'internal_metadata', ':key'), self.updateMetadataKey
        )
        apiRoot.item.route(
            'DELETE', (':itemId', 'internal_metadata', ':key'), self.deleteMetadataKey
        )

    @describeRoute(
        Description('Get the value for a single internal metadata key on this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key to retrieve.',
            paramType='path',
            default='meta',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.user(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getMetadataKey(self, item, key, params):
        if key not in item:
            return None
        return item[key]

    @describeRoute(
        Description(
            'Overwrite the value for a single internal metadata key on this item.'
        )
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key which should have a new value. \
                The default key, "meta" is equivalent to the external metadata. \
                Editing the "meta" key is equivalent to using PUT /item/{id}/metadata.',
            paramType='path',
            default='meta',
        )
        .param(
            'value',
            'The new value that should be written for the chosen metadata key',
            paramType='body',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def updateMetadataKey(self, item, key, params):
        item[key] = self.getBodyJson()
        self._model.save(item)

    @describeRoute(
        Description('Delete a single internal metadata key on this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key to delete.',
            paramType='path',
            default='meta',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def deleteMetadataKey(self, item, key, params):
        if key in item:
            del item[key]
        self._model.save(item)
