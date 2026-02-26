"""
sdk_manager.py — QAIRT SDK Lifecycle Manager
==============================================

Manages the Qualcomm AI Runtime (QAIRT) SDK:
  - Detect if already downloaded & extracted
  - Download from Qualcomm's distribution endpoint
  - Extract and validate key binaries
  - Provide SDK paths for subprocess calls in the plugin layer

The wrapper calls ``ensure_sdk()`` at startup — before asking for
any model or compilation arguments.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import urllib.request

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QAIRT_VERSION = "2.43.0.260128"
QAIRT_DOWNLOAD_URL = (
    "https://softwarecenter.qualcomm.com/api/download/software/sdks/"
    "Qualcomm_AI_Runtime_Community/All/"
    f"{QAIRT_VERSION}/v{QAIRT_VERSION}.zip"
)

# Key binaries we expect inside the SDK (relative to SDK root)
EXPECTED_BINARIES = [
    "bin/x86_64-linux-clang/qnn-onnx-converter",
    "bin/x86_64-linux-clang/qnn-model-lib-generator",
    "bin/x86_64-linux-clang/qnn-context-binary-generator",
]

console = Console()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SDKManager:
    """
    Manages the QAIRT SDK installation lifecycle.

    Args:
        project_root: Path to the project root (where ``qairt/`` lives).
        version: QAIRT version string.
    """

    def __init__(
        self,
        project_root: Path,
        version: str = QAIRT_VERSION,
    ) -> None:
        self.project_root = project_root
        self.version = version
        self.sdk_dir = project_root / "qairt"
        self.sdk_version_dir = self.sdk_dir / version

    @property
    def sdk_root(self) -> Path:
        """Full path to the versioned SDK root."""
        return self.sdk_version_dir

    @property
    def is_installed(self) -> bool:
        """Check if the SDK directory exists and contains expected structure."""
        return self.sdk_version_dir.is_dir()

    def get_bin_path(self, tool_name: str) -> Optional[Path]:
        """
        Resolve the full path to a QNN CLI tool binary.

        Args:
            tool_name: e.g. ``qnn-onnx-converter``

        Returns:
            Absolute path to the binary, or None if not found.
        """
        if not self.is_installed:
            return None
        # Search common bin locations
        for bin_subdir in ["bin/x86_64-linux-clang", "bin"]:
            candidate = self.sdk_version_dir / bin_subdir / tool_name
            if candidate.exists():
                return candidate
        return None

    def validate(self) -> dict[str, bool]:
        """
        Check which expected binaries are present.

        Returns:
            Dict mapping binary relative path → exists (bool).
        """
        results = {}
        for rel_path in EXPECTED_BINARIES:
            full_path = self.sdk_version_dir / rel_path
            results[rel_path] = full_path.exists()
        return results

    # ------------------------------------------------------------------
    # Core lifecycle
    # ------------------------------------------------------------------

    def ensure_sdk(self) -> bool:
        """
        Top-level entry point called at wrapper startup.

        1. Check if SDK is already installed.
        2. If not, prompt the user and download/extract it.

        Returns:
            True if SDK is ready, False if user declined or download failed.
        """
        console.print()

        if self.is_installed:
            console.print(
                f"  [bold green]✅ QAIRT SDK found[/bold green]  "
                f"[dim]v{self.version}[/dim]  →  [dim]{self.sdk_version_dir}[/dim]"
            )
            return True

        # SDK not found — prompt user
        console.print(
            f"  [bold yellow]⚠  QAIRT SDK not found[/bold yellow]  "
            f"[dim](expected at {self.sdk_version_dir})[/dim]"
        )
        console.print(
            f"  [dim]Download URL: {QAIRT_DOWNLOAD_URL}[/dim]\n"
        )

        proceed = Confirm.ask(
            "  [bold]Download QAIRT SDK now?[/bold]",
            default=True,
        )
        if not proceed:
            console.print("  [red]SDK required. Exiting.[/red]")
            return False

        return self._download_and_extract()

    def _download_and_extract(self) -> bool:
        """Download the SDK zip and extract it."""
        self.sdk_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.sdk_dir / f"v{self.version}.zip"

        try:
            # --- Download with progress ---
            self._download(zip_path)

            # --- Extract ---
            self._extract(zip_path)

            # --- Cleanup zip ---
            console.print("  [dim]Cleaning up zip archive...[/dim]")
            zip_path.unlink(missing_ok=True)

            # --- Validate ---
            if self.is_installed:
                console.print(
                    f"\n  [bold green]✅ QAIRT SDK installed successfully[/bold green]  "
                    f"[dim]v{self.version}[/dim]"
                )
                return True
            else:
                console.print(
                    "  [bold red]❌ Extraction completed but SDK directory not found.[/bold red]\n"
                    "  [dim]The zip may have a different internal structure. "
                    "Check the qairt/ directory manually.[/dim]"
                )
                return False

        except Exception as e:
            console.print(f"\n  [bold red]❌ SDK setup failed:[/bold red] {e}")
            # Clean up partial download
            zip_path.unlink(missing_ok=True)
            return False

    def _download(self, destination: Path) -> None:
        """Download the SDK zip with a rich progress bar."""
        console.print(f"\n  [bold cyan]Downloading QAIRT SDK v{self.version}...[/bold cyan]\n")

        # Start the download to get content length
        req = urllib.request.Request(QAIRT_DOWNLOAD_URL)
        response = urllib.request.urlopen(req)
        total_size = int(response.headers.get("Content-Length", 0))

        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(bar_width=40),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("  Downloading", total=total_size)

            with open(destination, "wb") as f:
                while True:
                    chunk = response.read(1024 * 256)  # 256 KB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))

        console.print("  [green]Download complete.[/green]")

    def _extract(self, zip_path: Path) -> None:
        """Extract the SDK zip into the qairt/ directory."""
        console.print(f"\n  [bold cyan]Extracting SDK...[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.0f}%",
            console=console,
        ) as progress:
            with zipfile.ZipFile(zip_path, "r") as zf:
                members = zf.namelist()
                task = progress.add_task("  Extracting", total=len(members))
                for member in members:
                    zf.extract(member, self.sdk_dir)
                    progress.update(task, advance=1)

        console.print("  [green]Extraction complete.[/green]")

    # ------------------------------------------------------------------
    # Environment setup (for subprocess calls)
    # ------------------------------------------------------------------

    def get_env(self) -> dict[str, str]:
        """
        Return a dict of environment variables to inject when calling
        QNN tools via subprocess.

        Sets ``QNN_SDK_ROOT`` and prepends tool bin dirs to ``PATH``.
        """
        env = os.environ.copy()
        env["QNN_SDK_ROOT"] = str(self.sdk_version_dir)

        # Prepend bin directories to PATH
        bin_dirs = [
            str(self.sdk_version_dir / "bin" / "x86_64-linux-clang"),
            str(self.sdk_version_dir / "bin"),
        ]
        env["PATH"] = os.pathsep.join(bin_dirs) + os.pathsep + env.get("PATH", "")

        return env
