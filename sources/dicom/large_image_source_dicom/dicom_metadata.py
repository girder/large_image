def extract_dicom_metadata(dataset):
    # Extract any metadata we want to display from the dataset

    metadata = {}
    for field in TOP_LEVEL_METADATA_FIELDS:
        if field not in dataset:
            # This field is missing
            continue

        element = dataset[field]
        value = element.value

        if not value:
            # This field is blank
            continue

        if isinstance(value, list):
            value = ', '.join(value)

        metadata[element.name] = str(value)

    # The specimens are complex and many layers deep
    specimens = extract_specimen_metadata(dataset)
    if specimens:
        metadata['Specimens'] = specimens

    return metadata


# These are the top-level metadata fields we will look for
# (if available on the DICOM object)
TOP_LEVEL_METADATA_FIELDS = [
    'PatientID',
    'PatientName',
    'PatientSex',
    'PatientBirthDate',

    'AccessionNumber',
    'StudyID',
    'StudyDate',
    'StudyTime',

    'ClinicalTrialSponsorName',
    'ClinicalTrialProtocolID',
    'ClinicalTrialProtocolName',
    'ClinicalTrialSiteName',

    'Manufacturer',
    'ManufacturerModelName',
    'DeviceSerialNumber',
    'SoftwareVersions',

    'ReferringPhysicianName',
    'ModalitiesInStudy',
]


def extract_specimen_metadata(dataset):
    # Specimens are complex and many layers deep.
    # This function tries to extract what we need from the specimens.

    output = []
    for specimen in getattr(dataset, 'SpecimenDescriptionSequence', []):
        metadata = {}
        if 'SpecimenIdentifier' in specimen:
            metadata['Identifier'] = specimen.SpecimenIdentifier

        if 'SpecimenShortDescription' in specimen:
            metadata['Description'] = specimen.SpecimenShortDescription

        structures = ', '.join(
            x.CodeMeaning for x in getattr(specimen, 'PrimaryAnatomicStructureSequence', [])
        )
        if structures:
            metadata['Anatomical Structure'] = structures

        preps = []
        for prep in getattr(specimen, 'SpecimenPreparationSequence', []):
            steps = {}
            for step in getattr(prep, 'SpecimenPreparationStepContentItemSequence', []):
                # Only extract entries that have both a name and a value
                if (len(getattr(step, 'ConceptCodeSequence', [])) > 0 and
                        len(getattr(step, 'ConceptNameCodeSequence', [])) > 0):
                    name = step.ConceptNameCodeSequence[0].CodeMeaning
                    value = step.ConceptCodeSequence[0].CodeMeaning
                    if name in steps:
                        # There must be several values for this name.
                        # Turn it into a list instead.
                        if not isinstance(steps[name], list):
                            steps[name] = [steps[name]]
                        steps[name].append(value)
                    else:
                        steps[name] = value

            if steps:
                preps.append(steps)

        if preps:
            metadata['Specimen Preparation'] = preps

        if metadata:
            output.append(metadata)

    return output
