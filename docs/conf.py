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
from sphinx.ext import apidoc
import os
import sys
sys.path.insert(0, os.path.abspath('../phi/'))
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../phi/'))
sys.path.insert(0, os.path.abspath('../../'))
cur_dir = os.path.abspath(os.path.dirname(__file__))
module = os.path.join(cur_dir, "..", "phi")
print('running apidoc... {}'.format(module))
apidoc.main([
    '--force',
    '--follow-links',
    '--separate',
    '--module-first',
    '--implicit-namespaces',
    # '--full',
    '-d 8',  # -d <MAXDEPTH>  Maximum depth for the generated table of contents file.
    '-o', cur_dir,
    module])
print(sys.path)
print(os.listdir())
print(os.listdir('..'))

# -- Project information -----------------------------------------------------

project = 'PhiFlow'
copyright = '2020, Philipp Holl'
author = 'Philipp Holl'

# The full version, including alpha/beta/rc tags
release = '1.0.2'


# -- General configuration ---------------------------------------------------

master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'recommonmark'
]
apidoc_module_dir = '../phi/'
apidoc_output_dir = ''
apidoc_excluded_paths = ['tests']
apidoc_separate_modules = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- APIDOC ----------------------------------------------
import subprocess
subprocess.call('rm -rf source; sphinx-apidoc -o source/ ../phi', shell=True)

# create _static directory
subprocess.call('mkdir -p _static', shell=True)

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
