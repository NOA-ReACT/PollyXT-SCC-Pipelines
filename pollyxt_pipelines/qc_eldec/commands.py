"""
Commands for performing the QC check on ELDEC products
"""

from cleo import Command

from pollyxt_pipelines import config, locations
from pollyxt_pipelines.qc_eldec import qc_eldec_file


class QCEldec(Command):
    """Perform calibration QC check on ELDEC files

    qc-eldec
        {input : Path to ELDEC file}
        {location : Which location does this calibration file come from.}
        {plot? : Optionally, a path to store the plot}
    """

    help = """
    This command performs quality checks on ELDEC files produced by calibration uploads. Specifically:

    * is relative error of the gain factor below threshold?
    * is relative standard deviation of ratio profiles below threshold?
    * is there an overlap between uncertainty range of gain factor and standard deviation of time series * factor ?

    Every time this command is executed, the history of calibration results are stored in a file (per-location), which is used for the last criteria. To delete this file, use the `qc-eldec-clear-history` command.

    The history files are stored at the config directory. For Linux, that should be `~/.config/pollyxt_pipelines/` and for Windows `%APPDATA%/PollyXT_Pipelines/`.

    Original code by Ina Mattis (@imattis on GitLab): https://gitlab.com/imattis/qc_eldec_file
    """

    def handle(self):
        # Get arguments
        input_file = self.argument("input")
        plot_path = self.argument("plot")

        location_name = self.argument("location")
        location = locations.LOCATIONS[location_name]
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Execute check
        eldec = qc_eldec_file.ELDECfile(input_file, location, plot_path=plot_path)
        if eldec.calibration_ok():
            self.line("Calibration OK!")
            return 0

        self.line("Calibration does not pass checked.")
        return 1


class QCEldecDeleteHistory(Command):
    """Delete history of qc-eldec command

    qc-eldec-delete-history
    """

    def handle(self):
        timeseries_dir = config.config_paths()[-1] / "qc_eldec"
        for file in timeseries_dir.glob("*.nc"):
            self.line(f"Deleting {file}")
            file.unlink()
