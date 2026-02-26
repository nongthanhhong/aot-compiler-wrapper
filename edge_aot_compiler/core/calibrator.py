"""
calibrator.py — Calibration Data Converter
===========================================

Converts calibration datasets (images, audio files, etc.) into raw
binary arrays (``.raw``) suitable for post-training quantization.

Also generates the ``input_list.txt`` manifest that vendor toolchains
(e.g., QNN) require to drive the quantization pass.
"""

from pathlib import Path
from typing import List

# External dependency — installed via `pip install numpy`
# import numpy as np


class CalibrationPreparer:
    """
    Reads a directory of calibration samples and produces:
      1. Converted ``.raw`` binary files
      2. An ``input_list.txt`` index file

    Usage::

        preparer = CalibrationPreparer(Path("calibration_data/"))
        raw_files = preparer.convert_to_raw(Path("output/raw/"))
        preparer.generate_input_list(raw_files, Path("output/"))
    """

    def __init__(self, calibration_dir: Path) -> None:
        self.calibration_dir = calibration_dir

    def convert_to_raw(self, output_dir: Path) -> List[Path]:
        """
        Convert each sample in ``calibration_dir`` to a ``.raw`` binary array.

        Args:
            output_dir: Where to write the ``.raw`` files.

        Returns:
            List of paths to the generated ``.raw`` files.
        """
        # TODO: Phase 2 — implement NumPy-based conversion
        raise NotImplementedError("Phase 2: raw conversion not yet implemented")

    def generate_input_list(self, raw_files: List[Path], output_dir: Path) -> Path:
        """
        Write an ``input_list.txt`` containing one ``.raw`` path per line.

        Args:
            raw_files: List of ``.raw`` file paths.
            output_dir: Where to write ``input_list.txt``.

        Returns:
            Path to the generated ``input_list.txt``.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        list_path = output_dir / "input_list.txt"
        with open(list_path, "w") as f:
            for raw_file in raw_files:
                f.write(f"{raw_file}\n")
        return list_path
