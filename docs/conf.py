# Configuration file for the Sphinx documentation builder.

import inspect
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
    "sphinx.ext.linkcode",
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
    "show_toc_level": 2,
    "navbar_persistent": ["search-button"],
    "footer_end": [],
    "search_bar_text": "Search",
    "article_header_start": [],
    "primary_sidebar_end": [],
}

html_sidebars = {
    "**": [],
}

add_module_names = True
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


# -- linkcode (GitHub source links) ------------------------------------------

_GITHUB_URL = "https://github.com/remrama/liwca/blob/main"


def linkcode_resolve(domain: str, info: dict) -> str | None:
    """Map a documented Python object to its GitHub source URL."""
    if domain != "py" or not info["module"]:
        return None

    mod = sys.modules.get(info["module"])
    if mod is None:
        return None

    obj = mod
    for part in info["fullname"].split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None

    obj = inspect.unwrap(obj)

    try:
        source_file = inspect.getsourcefile(obj)
    except TypeError:
        return None
    if source_file is None:
        return None

    # Resolve to a path relative to the package root (src/).
    source_file = os.path.relpath(source_file, start=os.path.join(os.path.dirname(__file__), ".."))
    source_file = source_file.replace("\\", "/")

    try:
        lines, start = inspect.getsourcelines(obj)
        end = start + len(lines) - 1
        return f"{_GITHUB_URL}/{source_file}#L{start}-L{end}"
    except OSError:
        return f"{_GITHUB_URL}/{source_file}"
