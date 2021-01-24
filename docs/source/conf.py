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
sys.path.insert(0, os.path.abspath('../../'))

here = os.path.abspath(os.path.dirname(__file__))
pkg_base_dir = os.path.join(here, '..', '..')


# generate api

# cozmars_modules = ['robot', 'button', 'infrared', 'sonar', 'motor', 'lift', 'head', 'buzzer', 'screen', 'camera', 'microphone']
# with open(os.path.join(here, 'api', 'index.rst'), 'w') as f:
#     f.write('API\n=================\n\n.. automodule:: rcute_cozmars\n\n.. toctree::\n\n')
#     f.write('\n'.join([f'   {a}' for a in cozmars_modules]))

# for a in cozmars_modules:
#     with open(os.path.join(here, 'api', f'{a}.rst'), 'w') as f:
#         title = f'rcute_cozmars.{a}\n'
#         f.write(f'{title}{"="*len(title)}\n\n.. automodule:: {title}   :members:\n   :inherited-members:')

# get version
with open(os.path.join(pkg_base_dir, 'rcute_cozmars', 'version.py')) as f:
    ns = {}
    exec(f.read(), ns)
    version = ns['__version__']


# -- Project information -----------------------------------------------------

project = 'rcute-cozmars'
copyright = '2020, Huang Yan'
author = 'Huang Yan'

# The full version, including alpha/beta/rc tags
release = version
master_doc = 'index'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',]

pygments_style = 'sphinx'
autodoc_member_order = 'bysource'
autodoc_default_flags = ['members', "inherited-members"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'zh_CN'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']