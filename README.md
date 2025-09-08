# PollyXT Pipelines

PollyXT-Pipelines is a tool and a library for processing PollyXT files, mainly related to the integration
with [Single Calculus Chain (SCC)](https://www.earlinet.org/index.php?id=281). It currently supports
the following features:

- Conversion of PollyXT files to SCC format
- Create Sounding files from WRF profiles
- Batch upload to SCC for processing
- Batch download of products, both for new files and by date range

To get started, check the [**demo**](https://asciinema.org/a/380595) and read the [**documentation**](https://noa-react.github.io/PollyXT-SCC-Pipelines/)!

## Installation

This project requires Python 3.8 or newer. It works on both Windows and Linux. It is available through `pip`:

```sh
# Replace with the filename you downloaded
pip install pollyxt-pipelines
```

If you are using Anaconda on Windows, run the above command in Anaconda Prompt **in a fresh environment**.

## Usage

The tool is usable through the command line. Commands are structured as follows:

```
pollyxt_pipelines COMMAND_NAME arg1 arg2 arg3...
```

Different command are used to carry out each task and they accept different arguments. You can view the help for each command with `pollyxt_pipelines COMMAND_NAME --help`. For more details check the [documentation](https://noa-react.github.io/PollyXT-SCC-Pipelines/).

## Development

The project uses [uv](https://docs.astral.sh/uv/) as the package manager and
thus is required for working on the tool. After installing uv, download the
required dependencies using:

```
uv sync
```

You can also install optional dependencies for development or documentation:

```
# Install development dependencies (linting, testing)
uv sync --extra dev

# Install documentation dependencies
uv sync --extra docs

# Install all optional dependencies
uv sync --all-extras
```

To run the application during development:

```
uv run pollyxt_pipelines --help
```

## License

The project is available under the GNU Lesser General Public License v3.0. Please publish any changes you make,
or better yet, contribute them to this repository so everyone can benefit. However, you can use this project
as a library without publishing your source code.

The license is available in the `COPYING` and `COPYING.LESSER` files.

## Authors & Contributors

- Anna Gialitaki <togialitaki@noa.gr>: Original PollyXT to SCC code
- Thanasis Georgiou <ageorgiou@noa.gr>: Command line tool
- Iannis Binietoglou <i.binietoglou@impworks.gr>: [scc-access](https://repositories.imaa.cnr.it/public/scc_access) tool, which was the basis for the upload/download features. `scc-access` is available under the MIT license.
- Andi Klamt <klamt@tropos.de>
