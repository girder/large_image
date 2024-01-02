#!/usr/bin/env python3

import urllib.request
from io import BytesIO

from dicomweb_client import DICOMwebClient
from pydicom import dcmread


def upload_example_data(server_url):

    # This is TCGA-AA-3697
    download_urls = [
        'https://data.kitware.com/api/v1/file/6594790e9c30d6f4e17c9d0d/download',
        'https://data.kitware.com/api/v1/file/6594790f9c30d6f4e17c9d10/download',
        'https://data.kitware.com/api/v1/file/6594790d9c30d6f4e17c9d0a/download',
    ]
    datasets = []
    for url in download_urls:
        resp = urllib.request.urlopen(url)
        data = resp.read()
        dataset = dcmread(BytesIO(data))
        datasets.append(dataset)

    client = DICOMwebClient(server_url)
    client.store_instances(datasets)


if __name__ == '__main__':
    url = 'http://localhost:8008/dcm4chee-arc/aets/DCM4CHEE/rs'
    upload_example_data(url)
