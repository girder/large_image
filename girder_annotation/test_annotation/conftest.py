import pytest

from girder import events


def unbindGirderEventsByHandlerName(handlerName):
    for eventName in events._mapping:
        events.unbind(eventName, handlerName)


@pytest.fixture
def unbindLargeImage(db):
    yield True
    unbindGirderEventsByHandlerName('large_image')


@pytest.fixture
def unbindAnnotation(db):
    yield True
    unbindGirderEventsByHandlerName('large_image_annotation')
