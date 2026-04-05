# Configuration file for the Sphinx documentation builder.

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_ext"))

import liwca

project = liwca.__name__
release = liwca.__version__
version = liwca.__version__
author = liwca.__author__.split("<")[0].strip()
curr = time.strftime("%Y")
copyright = f"2024-{curr}, {author}"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "dictcatalogue",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = liwca.__name__
html_show_sphinx = False
html_show_copyright = False

html_use_index = False
html_permalinks = True

html_copy_source = False
html_show_sourcelink = False

html_theme_options = {
    "github_url": "https://github.com/remrama/liwca",
    "show_prev_next": True,
    "navigation_with_keys": True,
    "show_nav_level": 2,
    "navbar_persistent": ["search-button"],
    "footer_end": [],
    "search_bar_text": "Search",
    "article_header_start": [],
    "primary_sidebar_end": [],
}

html_sidebars = {
    "**": [],
}

add_module_names = False
add_function_parentheses = False

# -- Extension configuration -------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"

autosummary_generate = True

napoleon_google_docstring = False
napoleon_numpy_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "pandera": ("https://pandera.readthedocs.io/en/stable/", None),
    "pooch": ("https://www.fatiando.org/pooch/latest/", None),
    "sklearn": ("https://scikit-learn.org/stable/", None),
}
