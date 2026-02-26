"""
packager.py — Transparent Deployment Packager
===============================================

Combines compilation artifacts into a single, auditable deployment bundle:

  ``deploy_bundle.zip``
  ├── manifest.json        — Source of truth for the edge device
  ├── model.serialized     — Optimized NPU binary payload
  └── audit_log.txt        — Full compilation audit trail
"""

import json
import zipfile
from pathlib import Path
from typing import Any, Dict


class DeploymentPackager:
    """
    Creates the final ``deploy_bundle.zip`` for Android deployment.

    Usage::

        packager = DeploymentPackager(output_dir=Path("build/"))
        packager.create_manifest(topology, compile_result)
        packager.package_bundle()
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def create_manifest(
        self,
        topology: Dict[str, Any],
        compile_result: Dict[str, Any],
    ) -> Path:
        """
        Merge topology and compilation metadata into ``manifest.json``.

        Args:
            topology: Pre-compilation topology data.
            compile_result: Post-compilation metadata (paths, timing, etc.).

        Returns:
            Path to the written ``manifest.json``.
        """
        manifest = {
            "version": "1.0",
            "topology": topology,
            "compilation": compile_result,
        }
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        return manifest_path

    def package_bundle(
        self,
        manifest_path: Path,
        model_binary_path: Path,
        audit_log_path: Path,
    ) -> Path:
        """
        Compress all deployment artifacts into ``deploy_bundle.zip``.

        Args:
            manifest_path: Path to ``manifest.json``.
            model_binary_path: Path to the compiled model binary.
            audit_log_path: Path to ``audit_log.txt``.

        Returns:
            Path to the generated ``deploy_bundle.zip``.
        """
        # TODO: Phase 4 — implement full packaging logic
        bundle_path = self.output_dir / "deploy_bundle.zip"
        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, "manifest.json")
            zf.write(model_binary_path, model_binary_path.name)
            zf.write(audit_log_path, "audit_log.txt")
        return bundle_path
