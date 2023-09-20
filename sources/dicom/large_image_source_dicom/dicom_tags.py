# Cache these so we only look them up once per run
DICOM_TAGS = {}


def dicom_key_to_tag(key):
    if key not in DICOM_TAGS:
        import pydicom
        from pydicom.tag import Tag
        DICOM_TAGS[key] = Tag(pydicom.datadict.tag_for_keyword(key)).json_key

    return DICOM_TAGS[key]
