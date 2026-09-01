import datetime
import json
import logging
import time
import uuid

import orjson
from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.utils import isGeoJSON
from girder_worker.app import app

import large_image.config
from girder.constants import AccessType
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.model_base import Model
from girder.models.user import User

logger = logging.getLogger(__name__)


class RecentIdentifier(Model):
    def initialize(self):
        self.name = 'large_image_annotation_recent_identifier'
        self.ensureIndices(['uuid', 'updated'])

    def validate(self, doc):
        if 'created' not in doc:
            doc['created'] = datetime.datetime.now(datetime.timezone.utc)
        doc['updated'] = datetime.datetime.now(datetime.timezone.utc)
        return doc


def itemFromEvent(event, identifierEnding, itemAccessLevel=AccessType.READ):  # noqa
    """
    If an event has a reference and an associated identifier that ends with a
    specific string, return the associated item, user, and image file.

    :param event: the data.process event.
    :param identifierEnding: the required end of the identifier.
    :returns: a dictionary with item, user, and file if there was a match.
    """
    info = getattr(event, 'info', event)
    identifier = None
    reference = info.get('reference', None)
    if reference is not None:
        try:
            reference = json.loads(reference)
        except (ValueError, TypeError):
            logger.debug('Failed to parse data.process reference: %r', reference)
    if isinstance(reference, dict) and isinstance(reference.get('identifier'), str):
        identifier = reference['identifier']
    if identifier and 'uuid' in reference:
        recent = RecentIdentifier().findOne({'uuid': reference['uuid']}) or {}
        recent['uuid'] = reference['uuid']
        recent[identifier] = info
        reprocessOpts = recent.pop('reprocess', None)
        RecentIdentifier().save(recent)
        if reprocessOpts:
            processAnnotationsTask(**reprocessOpts)
        RecentIdentifier().removeWithQuery({'updated': {
            '$lte': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)}})
    if identifier is not None and identifier.endswith(identifierEnding):
        if identifier == 'LargeImageAnnotationUpload' and 'uuid' not in reference:
            reference['uuid'] = str(uuid.uuid4())
        if 'itemId' not in reference and 'fileId' not in reference:
            logger.error('Reference does not contain required information.')
            return None
        userId = reference.get('userId')
        if not userId:
            if 'itemId' in reference:
                item = Item().load(reference['itemId'], force=True)
            else:
                file = File().load(reference['fileId'], force=True)
                item = Item().load(file['itemId'], force=True)
            if 'folderId' not in item:
                logger.error('Reference does not contain userId.')
                return None
            folder = Folder().load(item['folderId'], force=True)
            userId = folder['creatorId']
        user = User().load(userId, force=True)
        imageId = reference.get('fileId')
        if not imageId:
            item = Item().load(reference['itemId'], force=True)
            if 'largeImage' in item and 'fileId' in item['largeImage']:
                imageId = item['largeImage']['fileId']
        image = File().load(imageId, level=AccessType.READ, user=user)
        item = Item().load(image['itemId'], level=itemAccessLevel, user=user)
        return {'item': item, 'user': user, 'file': image, 'uuid': reference.get('uuid')}


def resolveAnnotationGirderIds(
        event, results, data, possibleGirderIds, referenceName, removeSingularFileItem):
    """
    If an annotation has references to girderIds, resolve them to actual ids.

    :param event: a data.process event.
    :param results: the results from itemFromEvent,
    :param data: annotation data.
    :param possibleGirderIds: a list of annotation elements with girderIds
        needing resolution.
    :param referenceName: reference used for events.
    :param removeSingularFileItem: boolean indicating if file cleanup should
        occur.
    :returns: True if all ids were processed.
    """
    # Exclude actual girderIds from resolution
    girderIds = []
    for element in possibleGirderIds:
        # This will throw an exception if the girderId isn't well-formed as an
        # actual id.
        try:
            if Item().load(element['girderId'], level=AccessType.READ, force=True) is None:
                girderIds.append(element)
        except Exception:
            girderIds.append(element)
    if not len(girderIds):
        return True
    idRecord = RecentIdentifier().findOne({'uuid': results['uuid']}) if 'uuid' in results else None
    if not idRecord:
        return True
    if idRecord and not all(element['girderId'] in idRecord for element in girderIds):
        idRecord['reprocess'] = {
            'event': getattr(event, 'info', event),
            'referenceName': referenceName,
            'removeSingularFileItem': removeSingularFileItem}
        RecentIdentifier().save(idRecord)
        return False
    RecentIdentifier().remove(idRecord)
    for element in girderIds:
        element['girderId'] = str(idRecord[element['girderId']]['file']['itemId'])
        # Currently, all girderIds inside annotations are expected to be
        # large images.  In this case, load them and ask if they can be so,
        # in case they are small images
        from girder_large_image.models.image_item import ImageItem

        try:
            item = ImageItem().load(element['girderId'], force=True)
            ImageItem().createImageItem(
                item, list(ImageItem().childFiles(item=item, limit=1))[0], createJob=False)
        except Exception:
            pass
    return True


@app.task(queue='local')
def processAnnotationsTask(event, referenceName, removeSingularFileItem=False):  # noqa C901
    results = itemFromEvent(event, referenceName)
    if not results:
        return
    item = results['item']
    user = results['user']

    file = File().load(
        getattr(event, 'info', event).get('file', {}).get('_id'),
        level=AccessType.READ, user=user,
    )
    startTime = time.time()

    if not file:
        logger.error('Could not load models from the database')
        return
    try:
        if file['size'] > int(large_image.config.getConfig(
                'max_annotation_input_file_length', 1024 ** 3)):
            msg = ('File is larger than will be read into memory.  If your '
                   'server will permit it, increase the '
                   'max_annotation_input_file_length setting.')
            raise Exception(msg)
        data = []
        with File().open(file) as fptr:
            while True:
                chunk = fptr.read(1024 ** 2)
                if not len(chunk):
                    break
                data.append(chunk)
        data = orjson.loads(b''.join(data).decode())
    except Exception:
        logger.error('Could not parse annotation file')
        if str(file['itemId']) == str(item['_id']):
            File().remove(file)
        raise
    if time.time() - startTime > 10:
        logger.info('Decoded json in %5.3fs', time.time() - startTime)

    if not isinstance(data, list) or isGeoJSON(data):
        data = [data]
    data = [entry['annotation'] if 'annotation' in entry else entry for entry in data]
    # Check some of the early elements to see if there are any girderIds
    # that need resolution.
    if 'uuid' in results:
        girderIds = [
            element for annotation in data
            for element in annotation.get('elements', [])[:100]
            if 'girderId' in element]
        if len(girderIds):
            if not resolveAnnotationGirderIds(
                    event, results, data, girderIds, referenceName, removeSingularFileItem):
                return
    for annotation in data:
        try:
            Annotation().createAnnotation(item, user, annotation)
        except Exception:
            logger.error('Could not create annotation object from data')
            if str(file['itemId']) == str(item['_id']):
                File().remove(file)
            raise
    if str(file['itemId']) == str(item['_id']):
        File().remove(file)
    if removeSingularFileItem:
        item = Item().load(file['itemId'], force=True)
        if item and len(list(Item().childFiles(item, limit=2))) == 1:
            Item().remove(item)


def process_annotations(
        event, referenceName='LargeImageAnnotationUpload', removeSingularFileItem=False):
    """Add annotations to an image on a ``data.process`` event"""
    if not itemFromEvent(event, referenceName):
        return
    processAnnotationsTask.delay(
        getattr(event, 'info', event), referenceName, removeSingularFileItem,
        girder_job_title='Process Annotations')
