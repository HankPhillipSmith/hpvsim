# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import subprocess
import sys
import sphinx_rtd_theme
from datetime import datetime
import hpvsim as hpv

# Set environment
os.environ['SPHINX_BUILD'] = 'True' # This is used so cv.options.set('jupyter') doesn't reset the Matplotlib renderer
os.environ['HPVSIM_WARNINGS'] = 'error' # Don't let warnings pass in the tutorials
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1' # Suppress harmless warning in documentation build
on_rtd = os.environ.get('READTHEDOCS') == 'True'

if sys.platform in ["linux", "darwin"]:
    subprocess.check_output(["make", "generate-api"], cwd=os.path.dirname(os.path.abspath(__file__)))
else:
    subprocess.check_output(["make.bat", "generate-api"], cwd=os.path.dirname(os.path.abspath(__file__)))

# Rename "hpvsim package" to "API reference"
filename = 'modules.rst' # This must match the Makefile
with open(filename) as f: # Read existing file
    lines = f.readlines()
lines[0] = "API reference\n" # Blast away the existing heading and replace with this
lines[1] = "=============\n" # Ensure the heading is the right length
with open(filename, "w") as f: # Write new file
    f.writelines(lines)


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.mathjax',
    'sphinx.ext.githubpages',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',  # Add a link to the Python source code for classes, functions etc.
    'nbsphinx',
    'IPython.sphinxext.ipython_console_highlighting',  # Temporary fix for https://github.com/spatialaudio/nbsphinx/issues/687
    'sphinx_search.extension', # search across multiple docsets in domain
    'myst_parser', # source files written in MD or RST
]

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

autodoc_default_options = {
    'member-order': 'bysource',
    'members': None
}

autodoc_mock_imports = []


napoleon_google_docstring = True

# Configure autosummary
autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (ie. params) to class summaries
html_show_sourcelink = False  # Remove 'view source code' from top of page (for html, not python)
autodoc_member_order = 'bysource' # Keep original ordering
add_module_names = False  # NB, does not work
autodoc_inherit_docstrings = False # Stops sublcasses from including docs from parent classes

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = 'HPVsim'
copyright = f'2022 - {datetime.today().year}, Bill & Melinda Gates Foundation. All rights reserved.\nThese docs were built for {project} version {hpv.__version__}\n'
author = 'Institute for Disease Modeling'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The versions
version = hpv.__version__
release = hpv.__version__


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# suppress warnings for multiple possible Python references in the namespace
# suppress_warnings = ['ref.python']
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# RST epilog is added to the end of every topic. Useful for replace
# directives to use across the docset.
rst_epilog = "\n.. include:: /variables.txt"

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


html_logo = "images/IDM_white.png"
html_favicon = "images/favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

html_static_path = ['_static']

html_css_files = ['theme_overrides.css']

html_js_files = ['show_block_by_os.js'] 

html_context = {
    'rtd_url': 'https://docs.idmod.org/projects/hpvsim/en/latest',
    'theme_vcs_pageview_mode': 'edit'
}
# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#
if not on_rtd:
    html_extra_path = ['robots.txt']

# If not None, a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
# The empty string is equivalent to '%b %d, %Y'.
#
html_last_updated_fmt = '%Y-%b-%d'


# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
html_use_opensearch = 'docs.idmod.org/projects/hpvsim/en/latest'

# -- RTD Sphinx search for searching across the entire domain, default child -------------

if os.environ.get('READTHEDOCS') == 'True':

    search_project_parent = "institute-for-disease-modeling-idm"
    search_project = os.environ["READTHEDOCS_PROJECT"]
    search_version = os.environ["READTHEDOCS_VERSION"]

    rtd_sphinx_search_default_filter = f"subprojects:{search_project}/{search_version}"

    rtd_sphinx_search_filters = {
        "Search this project": f"project:{search_project}/{search_version}",
        "Search all IDM docs": f"subprojects:{search_project_parent}/{search_version}",
    }

# Output file base name for HTML help builder.
htmlhelp_basename = 'HPVsim'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    'preamble': '%XeLaTeX packages'
                '\\usepackage{xltxtra}'
                '\\usepackage{fontspec} %%Font package'
                '\\usepackage{xunicode}'
                '%%Select fonts'
                '\\setmainfont[Mapping=tex-text]{nimbusserif}'
                '\\setsansfont[Mapping=tex-text]{nimbussans}'
                '\\setmonofont{nimbusmono}',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'hpvsim-docs.tex', 'HPVsim',
     'Institute for Disease Modeling', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#
# latex_logo = None

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'hpvsim-docs', 'HPVsim',
     [author], 1)
]

# If true, show URL addresses after external links.
#
man_show_urls = True

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'hpvsim-docs', 'HVPsim',
     author, 'Institute for Disease Modeling', 'How to use HPVsim to simulate HPV transmission.',
     'Miscellaneous'),
]

# Example configuration for intersphinx: refer to the Python standard library.
# intersphinx_mapping = {'https://docs.python.org/': None}

intersphinx_mapping = {'python': ('https://docs.python.org/3', None),
                       'fpsim': ('https://docs.idmod.org/projects/fpsim/en/latest', None),
                       'sciris': ('https://sciris.readthedocs.io/en/latest/', None)
                       }

# Configure nbsphinx
nbsphinx_kernel_name = "python"
nbsphinx_timeout = 180 # Time in seconds; use -1 for no timeout
nbsphinx_execute_arguments = [
    "--InlineBackend.figure_formats={'svg', 'pdf'}",
    "--InlineBackend.rc=figure.dpi=96",
]

# Modify this to not rerun the Jupyter notebook cells -- usually set by build_docs
nb_ex_default = ['auto', 'never'][0]
nb_ex = os.getenv('NBSPHINX_EXECUTE')
if not nb_ex: nb_ex = nb_ex_default
print(f'\n\nBuilding Jupyter notebooks with build option: {nb_ex}\n\n')
nbsphinx_execute = nb_ex
