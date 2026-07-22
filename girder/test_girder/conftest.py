import os
import subprocess

import pytest

pytestmark = pytest.mark.girder


@pytest.fixture
def unavailableWorker(db, monkeypatch):
    """
    Make sure that Girder Worker can't be reached and times out quickly.
    """
    # Use an invalid broker to make sure we don't connect to girder_worker so
    # this will be incomplete.  We don't want to use amqp as it will retry a
    # very long time.  The mongodb backend is deprecated and throws many
    # warnings, but works for this test condition.
    monkeypatch.setenv('GIRDER_WORKER_BROKER', 'mongodb://0.0.0.0')
    monkeypatch.setenv('GIRDER_WORKER_BACKEND', 'mongodb://0.0.0.0')
    return True


@pytest.fixture(scope='session')
def girderWorkerProcess():
    oldbroker = os.environ.get('GIRDER_WORKER_BROKER')
    oldbackend = os.environ.get('GIRDER_WORKER_BACKEND')
    broker = 'amqp://guest@127.0.0.1'
    backend = 'rpc://guest@127.0.0.1'
    os.environ['GIRDER_WORKER_BROKER'] = broker
    os.environ['GIRDER_WORKER_BACKEND'] = backend
    env = os.environ.copy()
    env['C_FORCE_ROOT'] = 'true'
    proc = subprocess.Popen([
        'celery', '-A', 'girder_worker.app', '--broker', broker,
        '--result-backend', backend, 'worker', '--concurrency=1'],
        close_fds=True, env=env)
    yield True
    proc.terminate()
    proc.wait()
    if oldbroker is not None:
        os.environ['GIRDER_WORKER_BROKER'] = oldbroker
    else:
        os.environ.pop('GIRDER_WORKER_BROKER')
    if oldbackend is not None:
        os.environ['GIRDER_WORKER_BACKEND'] = oldbackend
    else:
        os.environ.pop('GIRDER_WORKER_BACKEND')


@pytest.fixture
def girderWorker(db, girderWorkerProcess, monkeypatch):
    """
    Run an instance of Girder worker, connected to rabbitmq.  The rabbitmq
    service must be running.
    """
    monkeypatch.setenv('GIRDER_WORKER_BROKER', 'amqp://guest@127.0.0.1')
    monkeypatch.setenv('GIRDER_WORKER_BACKEND', 'rpc://guest@127.0.0.1')
    return True


def unbindGirderEventsByHandlerName(handlerName):
    from girder import events

    for eventName in events._mapping:
        events.unbind(eventName, handlerName)


@pytest.fixture
def unbindLargeImage(db):
    yield True
    unbindGirderEventsByHandlerName('large_image')
