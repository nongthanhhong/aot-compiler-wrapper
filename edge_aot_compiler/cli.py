"""
cli.py — The Interactive Entry Point
======================================

Transparent AOT Compiler Wrapper — interactive TUI experience.

Two modes:
  1. **Interactive** (default): Guided prompts with SDK check first
  2. **CLI flags**: ``python -m edge_aot_compiler --model ... --target ...``

The wrapper always checks for the QAIRT SDK before proceeding.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
from rich.tree import Tree

from edge_aot_compiler.core.compiler_base import VendorCompiler
from edge_aot_compiler.core.sdk_manager import SDKManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "0.1.0"

BANNER = r"""
 _____ ____   ____ _____    _    ___ 
| ____|  _ \ / ___| ____|  / \  |_ _|
|  _| | | | | |  _|  _|   / _ \  | | 
| |___| |_| | |_| | |___ / ___ \ | | 
|_____|____/ \____|_____/_/   \_\___|
                                      
 Transparent AOT Compiler Wrapper
"""

# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------

VENDOR_REGISTRY: dict[str, type[VendorCompiler]] = {}


def _register_plugins() -> None:
    """Lazily register all available vendor plugins."""
    from edge_aot_compiler.plugins.qualcomm_htp import QualcommHTPCompiler
    from edge_aot_compiler.plugins.mediatek_apu import MediaTekAPUCompiler

    VENDOR_REGISTRY["qnn_htp"] = QualcommHTPCompiler
    VENDOR_REGISTRY["mediatek_apu"] = MediaTekAPUCompiler


# ---------------------------------------------------------------------------
# Argument Parser (for non-interactive mode)
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for non-interactive mode."""
    parser = argparse.ArgumentParser(
        prog="edge_aot_compiler",
        description="Transparent AOT Compiler Wrapper — compile ML models for edge NPUs",
    )
    parser.add_argument(
        "--model", type=Path, default=None,
        help="Path to the source ONNX model file",
    )
    parser.add_argument(
        "--target", type=str, default=None,
        choices=["qnn_htp", "mediatek_apu"],
        help="Target hardware vendor / backend",
    )
    parser.add_argument(
        "--calibration_dir", type=Path, default=None,
        help="Directory containing calibration data (images/audio)",
    )
    parser.add_argument(
        "--output_dir", type=Path, default=None,
        help="Directory for compilation artifacts (default: build/)",
    )
    return parser


# ---------------------------------------------------------------------------
# Interactive Prompts
# ---------------------------------------------------------------------------

def _prompt_model(console: Console) -> Path:
    """Ask the user for the ONNX model path with validation."""
    while True:
        raw = Prompt.ask(
            "\n  [bold cyan]📂 Model path[/bold cyan] [dim](ONNX file)[/dim]"
        )
        model_path = Path(raw).expanduser().resolve()
        if model_path.is_file() and model_path.suffix.lower() == ".onnx":
            console.print(f"  [green]✓[/green] {model_path}")
            return model_path
        elif model_path.is_file():
            console.print(f"  [yellow]⚠  File exists but is not .onnx: {model_path}[/yellow]")
            use_anywady = Confirm.ask("  [dim]Use this file anyway?[/dim]", default=False)
            if use_anyway:
                return model_path
        else:
            console.print(f"  [red]✗ File not found: {model_path}[/red]")


def _prompt_target(console: Console) -> str:
    """Ask the user to select a target backend."""
    _register_plugins()
    targets = list(VENDOR_REGISTRY.keys())

    console.print("\n  [bold cyan]🎯 Available targets:[/bold cyan]")
    for i, t in enumerate(targets, 1):
        console.print(f"     [bold]{i}.[/bold] {t}")

    while True:
        choice = Prompt.ask(
            "\n  [bold cyan]Select target[/bold cyan]",
            choices=[str(i + 1) for i in range(len(targets))] + targets,
            default="1",
        )
        # Allow numeric or name selection
        if choice.isdigit() and 1 <= int(choice) <= len(targets):
            selected = targets[int(choice) - 1]
        elif choice in targets:
            selected = choice
        else:
            console.print("  [red]Invalid selection[/red]")
            continue

        console.print(f"  [green]✓[/green] Target: {selected}")
        return selected


def _prompt_calibration_dir(console: Console) -> Path | None:
    """Optionally ask for calibration data directory."""
    use_cal = Confirm.ask(
        "\n  [bold cyan]📐 Provide calibration data?[/bold cyan] [dim](for quantization)[/dim]",
        default=False,
    )
    if not use_cal:
        console.print("  [dim]Skipping calibration — will use default precision[/dim]")
        return None

    while True:
        raw = Prompt.ask("  [bold cyan]Calibration directory[/bold cyan]")
        cal_dir = Path(raw).expanduser().resolve()
        if cal_dir.is_dir():
            console.print(f"  [green]✓[/green] {cal_dir}")
            return cal_dir
        console.print(f"  [red]✗ Directory not found: {cal_dir}[/red]")


def _prompt_output_dir(console: Console) -> Path:
    """Ask for output directory with a sensible default."""
    raw = Prompt.ask(
        "\n  [bold cyan]📁 Output directory[/bold cyan]",
        default="build",
    )
    out_dir = Path(raw).expanduser().resolve()
    console.print(f"  [green]✓[/green] {out_dir}")
    return out_dir


# ---------------------------------------------------------------------------
# Pipeline Display
# ---------------------------------------------------------------------------

def _show_pipeline_summary(
    console: Console,
    model_path: Path,
    target: str,
    calibration_dir: Path | None,
    output_dir: Path,
) -> None:
    """Print a summary panel before starting the pipeline."""
    cal_str = str(calibration_dir) if calibration_dir else "[dim]none[/dim]"
    console.print()
    console.print(Panel.fit(
        f"  [bold]Model[/bold]       : {model_path}\n"
        f"  [bold]Target[/bold]      : {target}\n"
        f"  [bold]Calibration[/bold] : {cal_str}\n"
        f"  [bold]Output[/bold]      : {output_dir}",
        title="[bold cyan]Pipeline Configuration[/bold cyan]",
        border_style="bright_blue",
    ))


from rich.table import Table

def _run_pipeline(
    console: Console,
    compiler: VendorCompiler,
    sdk: SDKManager,
) -> None:
    """Execute the compilation pipeline with live progress."""
    from edge_aot_compiler.core.analyzer import ModelAnalyzer

    console.print()
    
    # --- Phase 2: Analyze ONNX topology ---
    with console.status("[bold green]📋 Phase 2 — The Auditor (Analyzing ONNX topology)...[/bold green]"):
        analyzer = ModelAnalyzer(compiler.model_path)
        topology = analyzer.analyze()
        out_json = analyzer.save_topology(topology, compiler.output_dir)
        
    console.print(f"  [green]✓[/green] [bold]Phase 2 — The Auditor (Topology Analyzed)[/bold]")
    console.print(f"    Saved to: [dim]{out_json}[/dim]\n")

    # Print summary table
    table = Table(title="[bold cyan]Model Topology Summary[/bold cyan]", border_style="bright_blue")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Inputs", str(len(topology["inputs"])))
    table.add_row("Outputs", str(len(topology["outputs"])))
    total_ops = sum(topology["operators"].values())
    unique_ops = len(topology["operators"])
    table.add_row("Operators", f"{total_ops} total ({unique_ops} unique types)")
    
    console.print("    ", table, "\n")

    if topology.get("has_dynamic_shapes"):
        console.print(
            "  [bold yellow]⚠️  Dynamic Shapes Detected[/bold yellow]\n"
            "    Your model contains dynamic input dimensions (e.g. batch size).\n"
            "    Vendor SDKs (like QNN) require fixed shapes for edge deployment.\n"
            "    [dim](Phase 3 will prompt for fixed dimensions.)[/dim]\n"
        )
    
    # Print the rest of the pending pipeline
    tree = Tree("[bold dimmer]Pending Pipeline Phases[/bold dimmer]")
    tree.add("[dimmer]📐 Phase 2 — The Auditor (Calibration)[/dimmer]")
    tree.add("[dimmer]⚙️  Phase 3 — Vendor Plugin (The Strategy Implementation)[/dimmer]")
    tree.add("[dimmer]📦 Phase 4 — The Transparent Packager[/dimmer]")
    tree.add("[dimmer]📱 Phase 5 — The Native Edge Runtime (Android C++ Integration)[/dimmer]")
    console.print(tree)
    
    console.print(
        "\n  [yellow]⚠️  Phases 2-5 execution not yet implemented — skeleton only[/yellow]"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Entrypoint: interactive TUI or CLI flags.

    Flow:
      1. Welcome banner
      2. Phase 0 — SDK check / download
      3. Gather parameters (interactive prompts or CLI flags)
      4. Run pipeline
    """
    console = Console()
    parser = build_parser()
    args = parser.parse_args()

    # Detect mode: interactive if no --model was provided
    interactive = args.model is None

    # ── Welcome Banner ─────────────────────────────────────────────────
    console.print(
        Panel.fit(
            f"[bold bright_cyan]{BANNER}[/bold bright_cyan]\n"
            f"  [dim]v{VERSION}[/dim]",
            border_style="bright_blue",
        )
    )

    # ── Phase 0: SDK Check ─────────────────────────────────────────────
    console.print(Rule("[bold bright_blue] Phase 0 — SDK Setup [/bold bright_blue]"))

    project_root = Path(__file__).resolve().parent.parent
    sdk = SDKManager(project_root=project_root)

    if not sdk.ensure_sdk():
        sys.exit(1)

    # ── Gather Parameters ──────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold bright_blue] Configuration [/bold bright_blue]"))

    if interactive:
        model_path = _prompt_model(console)
        target = _prompt_target(console)
        calibration_dir = _prompt_calibration_dir(console)
        output_dir = _prompt_output_dir(console)
    else:
        # CLI-flag mode — validate required args
        if not args.model or not args.target:
            console.print(
                "[bold red]Error:[/] --model and --target are required "
                "in non-interactive mode."
            )
            parser.print_help()
            sys.exit(1)
        model_path = args.model.resolve()
        target = args.target
        calibration_dir = args.calibration_dir.resolve() if args.calibration_dir else None
        output_dir = (args.output_dir or Path("build")).resolve()
        _register_plugins()

    # ── Confirm ────────────────────────────────────────────────────────
    _show_pipeline_summary(console, model_path, target, calibration_dir, output_dir)

    if interactive:
        if not Confirm.ask("\n  [bold]Proceed with compilation?[/bold]", default=True):
            console.print("  [dim]Aborted by user.[/dim]")
            sys.exit(0)

    # ── Instantiate & Run ──────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold bright_blue] Pipeline Execution [/bold bright_blue]"))

    compiler_cls = VENDOR_REGISTRY.get(target)
    if compiler_cls is None:
        console.print(f"[bold red]Error:[/] Unknown target '{target}'")
        sys.exit(1)

    compiler = compiler_cls(
        model_path=model_path,
        output_dir=output_dir,
        calibration_dir=calibration_dir,
    )
    compiler.ensure_output_dir()

    _run_pipeline(console, compiler, sdk)

    console.print(
        "\n  [bold green]Done.[/bold green] [dim]Ready for Phase 1+ implementation.[/dim]\n"
    )


if __name__ == "__main__":
    main()
