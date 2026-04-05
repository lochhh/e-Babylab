# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from datetime import date

project = "e-Babylab"
author = "Chang Huan Lo"
copyright = f"2022–{date.today().year}, {author}"
release = "v2.0.0"
github_url = f"https://github.com/lochhh/{project}"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "myst_parser",
    "nbsphinx",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

# Configure the myst parser to enable cool markdown features
# See https://sphinx-design.readthedocs.io
myst_enable_extensions = [
    "amsmath",
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
# Automatically add anchors to markdown headings
myst_heading_anchors = 4

# Configure auto-generation of API docs
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "inherited-members": "BaseModel",  # exclude Pydantic BaseModel methods
    "show-inheritance": True,
    "undoc-members": True,
}
# sphinx-autodoc-typehints settings
always_use_bars_union = True

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "logo": {
        "text": f"{project} {release}"
        # "image_light": "images/logo-light.png",
        # "image_dark": "images/logo-dark.png",
    },
    "icon_links": [
        {
            # Label for this link
            "name": "GitHub",
            # URL where the link will redirect
            "url": github_url,
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fa-brands fa-github",
            # The type of image to be used (see below for details)
            "type": "fontawesome",
        }
    ],
    "show_toc_level": 3,  # Show the first 3 levels of the local TOC
}
html_static_path = ["_static"]
