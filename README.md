# Transparent AOT Compiler Wrapper

An enterprise-grade Python orchestrator that wraps vendor-specific AOT compiler toolchains into a **transparent, auditable** deployment pipeline for edge AI inference.

## The Problem

Vendor tools (Qualcomm QNN, MediaTek NeuroPilot, etc.) are black boxes — feed them an ONNX model, get a proprietary binary. If the NPU rejects an operation or quantization destroys accuracy, you have no idea why.

## The Solution

This wrapper automates the vendor toolchain while acting as an **auditor at every step**. It runs as interactive software — checking SDK dependencies, guiding you through configuration, and producing a transparent deployment bundle.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the interactive wrapper
python -m edge_aot_compiler

# Or use CLI flags for scripted workflows
python -m edge_aot_compiler --model model.onnx --target qnn_lpai --calibration_dir ./cal_data/
```

On first run, the wrapper will detect the missing QAIRT SDK and offer to download it automatically.

## Directory Structure

```
edge_aot_compiler/
├── cli.py                  # Interactive TUI + CLI flags entry point
├── core/                   # Domain 1: Vendor-agnostic logic
│   ├── sdk_manager.py      # Phase 0: QAIRT SDK download / extract / validate
│   ├── compiler_base.py    # Abstract Strategy Pattern interface
│   ├── analyzer.py         # ONNX topology → pre_compile_topology.json
│   ├── calibrator.py       # Images/audio → .raw + input_list.txt
│   └── packager.py         # manifest.json + deploy_bundle.zip
├── plugins/                # Domain 2: Vendor-specific implementations
│   ├── qualcomm_lpai.py    # Qualcomm QNN / Hexagon LPAI
│   └── mediatek_apu.py     # MediaTek NeuroPilot (placeholder)
└── edge_runtime/           # Domain 3: Android C++ (NDK / JNI)
    ├── MyEngine.h
    └── MyEngine.cpp
```

## Output: Deployment Bundle

| File | Purpose |
|------|---------|
| `manifest.json` | Source-of-truth for the edge device (shapes, types, buffer sizes) |
| `model.serialized` | Optimized NPU binary payload |
| `audit_log.txt` | Full compilation audit trail with fallback warnings |

## Roadmap

- [x] **Phase 0** — SDK provisioning (auto-download QAIRT)
- [x] **Phase 1** — Interactive TUI + CLI skeleton
- [ ] **Phase 2** — ONNX analysis & calibration
- [ ] **Phase 3** — Qualcomm QNN plugin
- [ ] **Phase 4** — Transparent packager
- [ ] **Phase 5** — Android C++ runtime
