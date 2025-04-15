import os

import pytest


@pytest.mark.notebook
@pytest.mark.parametrize(('notebook', 'execute'), [
    ('docs/notebooks/large_image_examples.ipynb', False),
    ('docs/notebooks/zarr_sink_example.ipynb', False),
    ('docs/notebooks/frame_viewer_example.ipynb', False),
])
def test_notebook_exec(notebook, execute, tmp_path):
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor

    testDir = os.path.dirname(os.path.realpath(__file__))
    notebookpath = os.path.join(testDir, '..', notebook)
    with open(notebookpath) as f:
        nb = nbformat.read(f, as_version=4)
        if execute:
            ep = ExecutePreprocessor(
                timeout=600, kernel_name='python3',
                resources={'metadata': {'path': tmp_path}})
            try:
                result = ep.preprocess(nb)
                assert result is not None, f'Got empty notebook for {notebook}'
            except Exception as exp:
                msg = f'Failed executing {notebook}: {exp}'
                raise AssertionError(msg)
