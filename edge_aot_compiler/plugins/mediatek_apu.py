"""
mediatek_apu.py — MediaTek NeuroPilot APU Compiler Plugin (Future)
===================================================================

Placeholder implementation of ``VendorCompiler`` for the MediaTek APU
via the NeuroPilot SDK.  All methods raise ``NotImplementedError``.

This file exists to prove the Strategy Pattern's extensibility —
adding a new vendor requires only implementing this interface.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from edge_aot_compiler.core.compiler_base import VendorCompiler


class MediaTekAPUCompiler(VendorCompiler):
    """
    Vendor plugin for MediaTek NeuroPilot target (APU).

    .. warning:: This is a placeholder. Implementation is planned for
       a future release once MediaTek SDK access is available.
    """

    def __init__(
        self,
        model_path: Path,
        output_dir: Path,
        calibration_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(model_path, output_dir, calibration_dir)

    def generate_configs(self) -> Dict[str, Any]:
        raise NotImplementedError("MediaTek NeuroPilot support is not yet implemented")

    def compile(self) -> Path:
        raise NotImplementedError("MediaTek NeuroPilot support is not yet implemented")

    def intercept_logs(self) -> str:
        raise NotImplementedError("MediaTek NeuroPilot support is not yet implemented")
