#!/usr/bin/env python3

import urllib.request
from io import BytesIO

from dicomweb_client import DICOMwebClient
from pydicom import dcmread


def upload_example_data(server_url):

    download_urls = [
        # 'https://data.kitware.com/api/v1/file/65933ddb9c30d6f4e17c9ca1/download',
        # 'https://data.kitware.com/api/v1/file/65933dd09c30d6f4e17c9c9e/download',

        # This is the lowest resolution
        'https://data.kitware.com/api/v1/file/65933ddd9c30d6f4e17c9ca4/download',
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
