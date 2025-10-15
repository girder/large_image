# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

docs_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(docs_dir, '..', '..')))

# -- Project information -----------------------------------------------------

project = 'large_image'
copyright = 'Kitware, Inc.'
author = 'Kitware, Inc.'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.ifconfig',
    'sphinx.ext.mathjax',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinxcontrib.jquery',
    'sphinxcontrib.mermaid',
    'IPython.sphinxext.ipython_console_highlighting',
    'nbsphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build/**.ipynb', '**.ipynb_checkpoints', 'format_table.rst']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

pygments_style = 'sphinx'


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']
html_css_files = ['custom.css']
html_favicon = 'static/K.png'
html_permalinks = True
html_permalinks_icon = '&#128279'

autoclass_content = 'both'

mermaid_version = '10.6.0'
mermaid_init_js = 'mermaid.initialize({startOnLoad:true});'

nbsphinx_requirejs_path = ''
