import os
from tempfile import TemporaryDirectory

import pytest


@pytest.mark.notebook()
@pytest.mark.parametrize('notebook', ['docs/large_image_examples.ipynb'])
def test_notebook_exec(notebook):
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor

    testDir = os.path.dirname(os.path.realpath(__file__))
    notebookpath = os.path.join(testDir, '..', notebook)
    with TemporaryDirectory() as tempDir:
        with open(notebookpath) as f:
            nb = nbformat.read(f, as_version=4)
            ep = ExecutePreprocessor(
                timeout=600, kernel_name='python3',
                resources={'metadata': {'path': tempDir}})
            try:
                result = ep.preprocess(nb)
                assert result is not None, f'Got empty notebook for {notebook}'
            except Exception as exp:
                msg = f'Failed executing {notebook}: {exp}'
                raise AssertionError(msg)
