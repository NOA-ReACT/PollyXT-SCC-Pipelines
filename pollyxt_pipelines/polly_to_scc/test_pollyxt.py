import numpy as np

from pollyxt_pipelines.polly_to_scc import pollyxt


def test_make_nan_during_calibration():
    """
    Tests that calibration times are actually set to NaN
    """

    # Depol angle with two calibration periods
    depol_cal_angle = np.array([0.0, 1.0, 0.0, 2.0, 5.0])

    # Original raw_signal array
    t1 = np.array(
        [
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
            [0, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
        ],
        dtype=np.float32,
    )
    t2 = np.array(
        [
            [0, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
            [0, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        ],
        dtype=np.float32,
    )

    raw_signal = np.stack([t1, t2, t2, t1, t2])

    # Correct result
    correct_raw_signal = np.copy(raw_signal)
    correct_raw_signal[1, :, :] = np.nan
    correct_raw_signal[3, :, :] = np.nan
    correct_raw_signal[4, :, :] = np.nan

    pollyxt.make_nan_during_calibration(depol_cal_angle, raw_signal)

    assert np.all(np.isnan(raw_signal) == np.isnan(correct_raw_signal))
    assert np.all(
        (raw_signal == correct_raw_signal)
        | (np.isnan(raw_signal) == np.isnan(correct_raw_signal))
    )
