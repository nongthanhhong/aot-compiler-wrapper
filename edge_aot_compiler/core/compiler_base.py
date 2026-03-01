"""
compiler_base.py — The Strategy Pattern Interface
==================================================

Defines the abstract VendorCompiler base class that all vendor-specific
plugins must implement. This ensures a consistent contract across all
supported hardware targets.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class VendorCompiler(ABC):
    """
    Abstract base class for vendor-specific AOT compiler plugins.

    Every hardware vendor plugin (Qualcomm, MediaTek, etc.) must subclass
    this and implement all abstract methods. The CLI orchestrator interacts
    only with this interface — never with vendor-specific details directly.

    Attributes:
        model_path (Path): Path to the source ONNX model file.
        output_dir (Path): Directory where compilation artifacts are written.
        calibration_dir (Optional[Path]): Directory containing calibration data.
    """

    def __init__(
        self,
        model_path: Path,
        output_dir: Path,
        calibration_dir: Optional[Path] = None,
    ) -> None:
        self.model_path = model_path
        self.output_dir = output_dir
        self.calibration_dir = calibration_dir

    # ------------------------------------------------------------------
    # Abstract Methods — Must be implemented by every vendor plugin
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_configs(self) -> Dict[str, Any]:
        """
        Generate vendor-specific configuration files required by the
        toolchain (e.g., htp_backend_extensions.json for QNN, config files for NeuroPilot).

        Returns:
            Dict mapping config file names to their generated paths.
        """
        ...

    @abstractmethod
    def compile(self) -> Path:
        """
        Execute the full compilation pipeline:
          1. Quantize / convert the ONNX model
          2. Generate intermediate libraries
          3. Produce the final optimized binary

        Returns:
            Path to the final compiled binary artifact (e.g., model.serialized).
        """
        ...

    @abstractmethod
    def intercept_logs(self) -> str:
        """
        Parse and return the compilation audit log, highlighting any
        hardware fallbacks, unsupported operations, or quantization warnings.

        Returns:
            The full audit log as a string.
        """
        ...

    # ------------------------------------------------------------------
    # Concrete helper (shared across all vendors)
    # ------------------------------------------------------------------

    def ensure_output_dir(self) -> None:
        """Create the output directory tree if it doesn't already exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
