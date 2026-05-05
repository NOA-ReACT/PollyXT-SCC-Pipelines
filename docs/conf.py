import pollyxt_pipelines

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
html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/NOA-ReACT/PollyXT-SCC-Pipelines",
    "source_branch": "master",
    "source_directory": "docs/",
}
pygments_style = "sphinx"
