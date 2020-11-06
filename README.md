# PollyXT Pipelines

This project offers a library and a command-line tool for performing automated processing of PollyXT
files, mostly related to SCC. It can do:

- Convert PollyXT files to SCC format (including calibration files)
- Automatically fetch WRF profile files from a repository and convert them to SCC format
- **WIP**: Upload and download files from SCC

All the above actions support batch operations, for example convert an entire directory of measurements
at once.


## Installation

You can download one of the releases and install it with pip:

```
pip install --user ./pollyxt_pipelines_..._.whl
```


## Usage

TODO Write this section after the interface is finalized



## Development

The project uses [poetry](https://python-poetry.org/) as the package manager and
thus is required for working on the tool. After installing poetry, download the
required dependencies using:

```
poetry install
```