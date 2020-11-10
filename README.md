# PollyXT Pipelines

This project offers a library and a command-line tool for performing automated processing of PollyXT
files, mostly related to SCC. It can do:

- Convert PollyXT files to SCC format (including calibration files)
- Automatically fetch WRF profile files from a repository and convert them to SCC format
- Upload and download files from SCC

All the above actions support batch operations, for example convert an entire directory of measurements
at once.


## Installation

This project requires Python 3.6 or newer. It works on both Windows and Linux. You can download one of the [releases](https://react-gitlab.space.noa.gr/ReACT/pangea-datacenter/PollyXT-Pipelines/-/releases) and install it with pip:

```sh
# Replace with the filename you downloaded
pip install --user ./pollyxt_pipelines_..._.whl
```

If you are using Anaconda on Windows, run the above command in Anaconda Prompt.

## Usage

The tool is usable through the command line. Commands are structured as follows:

```
pollyxt_pipelines COMMAND_NAME arg1 arg2 arg3...
```

Different command are used to carry out each task and they accept different arguments. You can view the help for each command with `pollyxt_pipelines COMMAND_NAME --help`.

### Convert PollyXT files to SCC format

You can convert PollyXT files to the SCC format using the `pollyxt_pipelines create-scc` command:

```sh
pollyxt_pipelines create-scc input location output-path

# For example, convert `2020_10_01_Thu_NOA_00_00_31.nc` from Antikythera and
# store output in the `scc` directory
pollyxt_pipelines create-scc 2020_10_01_Thu_NOA_00_00_31.nc Antikythera ./scc

# Do the same but create 2-hour files
pollyxt_pipelines create-scc 2020_10_01_Thu_NOA_00_00_31.nc Antikythera ./scc --interval=120
```

The arguments are:
* `input`: Which file to uplaod
* `location`: Where did this measurement take place. Use `Antikythera` or `Finokalia`.
* `output-path`: Where to store the output files
* `--interval`: Optionally, set how long the output files should be, in minutes. Default value is hourly files (60)
* `--no-radiosonde`: Do not create radiosonde files (see below)
* `--no-calibration`: Do not create calibration files

For each file, a corresponding sounding file (`rs_XXXXXXXXX.nc`) is created. To disable this, you can use the `--no-radiosonde` option. The radiosonde files are created using WRF profile files. You **must** tell the program where to find the profile files using:

```
pollyxt_pipelines config wrf.path /path/to/wrf/files
```

If you want to convert multiple files, simply use `create-scc-batch` which works with directories instead of files. For example:

```sh
# Convert the whole `Polly_Files` directory and write output in `SCC_Files`
pollyxt_pipelines create-scc-batch Polly_Files Finokalia SCC_Files
```


### Upload to SCC and download products

Connection to SCC requires your credentials. You can set them using:

```sh
# Login to the first page (popup)
pollyxt_pipelines config http.username scc_user
pollyxt_pipelines config http.password PASSWORD

# Second login at webpage
pollyxt_pipelines config auth.username YOUR_USERNAME
pollyxt_pipelines config auth.password PASSWORD
```

After setting your credentials, you can upload files using the `scc-upload` command:

```sh
# Upload everything inside the `SCC_Data` directory and
# create a download list in `uploads.csv`.
pollyxt_pipelines scc-upload SCC_Data uploads.csv
```

The `uploads.csv` file now contains the IDs of all uploaded files. To download the processing products, you can use `scc-download`:

```sh
# Download all processing products from the previous files to `SCC_Products`
pollyxt_pipelines scc-download SCC_products uploads.csv
```

If a product is not ready, the file will be skipped. You can re-run the command later to check if the product is available.

## Development

The project uses [poetry](https://python-poetry.org/) as the package manager and
thus is required for working on the tool. After installing poetry, download the
required dependencies using:

```
poetry install
```


## Authors & Contributors
- Anna Gialitaki <togialitaki@noa.gr>: Original PollyXT to SCC code
- Thanasis Georgiou <ageorgiou@noa.gr>: Command line tool
- Iannis Binietoglou <i.binietoglou@impworks.gr>: [scc-access](https://repositories.imaa.cnr.it/public/scc_access) tool, which was the basis for the upload/download features