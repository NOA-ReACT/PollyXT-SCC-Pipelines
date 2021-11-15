"""
Commands for performing the QC check on ELDEC products
"""

from pathlib import Path

from cleo import Command

from pollyxt_pipelines.qc_eldec import qc_eldec_file


class QCEldec(Command):
    """Perform calibration QC check on ELDEC files

    qc-eldec
        {input : Path to ELDEC file}
        {timeseries : Path to the timeseries of previous calibrations. If it does not exist, it will be created.}
        {plot? : Optionally, a path to store the plot}
    """

    def handle(self):
        # Get arguments
        input_file = self.argument("input")
        timeseries_path = Path(self.argument("timeseries"))
        plot_path = self.argument("plot")

        # Execute check
        eldec = qc_eldec_file.ELDECfile(input_file, timeseries_path, plot_path=plot_path)
        if eldec.calibration_ok():
            self.line("Calibration OK!")
            return 0

        self.line("Calibration does not pass checked.")
        return 1