from large_image_source_dicom.dicom_metadata import extract_dicom_metadata
from large_image_source_dicom.dicom_tags import dicom_key_to_tag


def get_dicomweb_metadata(client, study_uid, series_uid):
    # Many series-level metadata items are available if we explicitly
    # request for them in the `search_for_series()` calls.
    # However, some things are not available in the series-level
    # metadata - in particular, the specimen information is only
    # on the instance-level metadata.
    # It seems that, for the most part, all WSI DICOM instances in a
    # series have virtually identical metadata (except one or two things,
    # such as the suffix on the serial number, and sometimes one of the
    # items in the specimen metadata).
    # We will do as the SLIM viewer does: grab a single volume instance
    # and use that for the metadata.
    volume_metadata = get_first_wsi_volume_metadata(client, study_uid, series_uid)
    if not volume_metadata:
        # No metadata
        return None

    from pydicom import Dataset
    dataset = Dataset.from_json(volume_metadata)
    return extract_dicom_metadata(dataset)


def get_first_wsi_volume_metadata(client, study_uid, series_uid):
    # Find the first WSI Volume and return the DICOMweb metadata
    from wsidicom.uid import WSI_SOP_CLASS_UID

    image_type_tag = dicom_key_to_tag('ImageType')
    instance_uid_tag = dicom_key_to_tag('SOPInstanceUID')

    # We can't include the SOPClassUID as a search filter because Imaging Data Commons
    # produces an error if we do. Perform the filtering manually instead.
    class_uid_tag = dicom_key_to_tag('SOPClassUID')

    fields = [
        image_type_tag,
        instance_uid_tag,
        class_uid_tag,
    ]
    wsi_instances = client.search_for_instances(
        study_uid, series_uid, fields=fields)

    volume_instance = None
    for instance in wsi_instances:
        class_type = instance.get(class_uid_tag, {}).get('Value')
        if not class_type or class_type[0] != WSI_SOP_CLASS_UID:
            # Only look at WSI classes
            continue

        image_type = instance.get(image_type_tag, {}).get('Value')
        # It would be nice if we could have a search filter for this, but
        # I didn't see one...
        if image_type and len(image_type) > 2 and image_type[2] == 'VOLUME':
            volume_instance = instance
            break

    if not volume_instance:
        # No volumes were found...
        return None

    instance_uid = volume_instance[instance_uid_tag]['Value'][0]

    return client.retrieve_instance_metadata(study_uid, series_uid, instance_uid)
