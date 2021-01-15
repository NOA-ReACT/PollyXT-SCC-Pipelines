import pollyxt_pipelines
from sphinx_typlog_theme import (
    add_badge_roles,
    add_github_roles,
)

project = "PollyXT-Pipelines"
copyright = "2020, NOA - ReACT"
author = "Thanasis Georgiou, Anna Gialitaki"

primary_domain = "py"
default_role = "py:obj"

extensions = [
    "sphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]
napoleon_use_param = True

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_static_path = ["_static"]
html_theme = "sphinx_typlog_theme"
html_theme_options = {
    # 'color': '#389e0d',
    "github_user": "NOA-ReACT",
    "github_repo": "PollyXT-SCC-Pipelines",
    "logo_name": "PollyXT-Pipelines",
    "description": "PollyXT and SCC intergration",
}
html_sidebars = {
    "**": [
        "logo.html",
        "github.html",
        "globaltoc.html",
        "searchbox.html",
    ]
}
pygments_style = "sphinx"


def setup(app):
    add_badge_roles(app)
    add_github_roles(app, "NOA-ReACT/PollyXT-SCC-Pipelines")
