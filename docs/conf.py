# Configuration file for the Sphinx documentation builder.

import time

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
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "bizstyle"
# html_static_path = ["_static"]
html_title = liwca.__name__
html_show_sphinx = False
html_show_copyright = False

html_use_index = False
html_permalinks = True

html_copy_source = False
html_show_sourcelink = False

add_function_parentheses = False

# -- Extension configuration -------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"

autosummary_generate = True

napoleon_google_docstring = False
napoleon_numpy_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "sklearn": ("https://scikit-learn.org/stable/", None),
}
