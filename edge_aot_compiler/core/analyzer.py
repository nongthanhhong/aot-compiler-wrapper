"""
analyzer.py — ONNX Model Topology Analyzer
===========================================

Parses an ONNX model graph to extract:
  - Input/output tensor names, shapes, and data types
  - Dynamic shape detection
  - Operator inventory (op types and counts)
  - Model metadata (IR version, opset, producer)

Serializes the results into a ``pre_compile_topology.json`` that
the C++ edge runtime can consume for memory pre-allocation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import onnx
from onnx import shape_inference


def _onnx_dtype_to_str(elem_type: int) -> str:
    """Map ONNX TensorProto.DataType enum to a readable string."""
    try:
        return onnx.TensorProto.DataType.Name(elem_type)
    except ValueError:
        return f"UNKNOWN({elem_type})"


def _parse_value_info(value_info: onnx.ValueInfoProto) -> Tuple[List[Any], str, bool]:
    """Parse shape and dtype from a ValueInfoProto."""
    tensor_type = value_info.type.tensor_type
    dtype = _onnx_dtype_to_str(tensor_type.elem_type)
    
    shape = []
    has_dynamic = False
    
    if tensor_type.HasField("shape"):
        for dim in tensor_type.shape.dim:
            if dim.HasField("dim_value"):
                shape.append(dim.dim_value)
            elif dim.HasField("dim_param"):
                shape.append(dim.dim_param)
                has_dynamic = True
            else:
                shape.append("unknown")
                has_dynamic = True
    else:
        has_dynamic = True

    return shape, dtype, has_dynamic


class ModelAnalyzer:
    """
    Loads an ONNX model and produces a topology report.

    Usage::

        analyzer = ModelAnalyzer(Path("model.onnx"))
        topology = analyzer.analyze()
        analyzer.save_topology(topology, Path("output/"))
    """

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path

    def analyze(self) -> Dict[str, Any]:
        """
        Parse the ONNX graph and return a structured topology dict.

        Returns:
            Dict with keys: ``inputs``, ``outputs``, ``operators``, ``metadata``, ``has_dynamic_shapes``.
        """
        # Load model and infer shapes
        model = onnx.load(str(self.model_path))
        try:
            model = shape_inference.infer_shapes(model)
        except Exception as e:
            # Continue even if shape inference fails partially
            print(f"  [yellow]⚠ Shape inference warning: {e}[/yellow]")

        graph = model.graph
        
        # 1. Inputs (exclude initializers/weights)
        initializer_names = {init.name for init in graph.initializer}
        inputs_data = []
        global_has_dynamic = False
        
        for input_info in graph.input:
            if input_info.name in initializer_names:
                continue
            shape, dtype, has_dyn = _parse_value_info(input_info)
            if has_dyn:
                global_has_dynamic = True
            inputs_data.append({
                "name": input_info.name,
                "shape": shape,
                "dtype": dtype,
                "has_dynamic_dimensions": has_dyn
            })

        # 2. Outputs
        outputs_data = []
        for output_info in graph.output:
            shape, dtype, _ = _parse_value_info(output_info)
            outputs_data.append({
                "name": output_info.name,
                "shape": shape,
                "dtype": dtype,
            })

        # 3. Operators
        operators: Dict[str, int] = {}
        for node in graph.node:
            op_type = node.op_type
            operators[op_type] = operators.get(op_type, 0) + 1

        # 4. Metadata
        opset_imports = {imp.domain or "ai.onnx": imp.version for imp in model.opset_import}
        metadata = {
            "ir_version": model.ir_version,
            "producer_name": model.producer_name,
            "producer_version": model.producer_version,
            "opset_imports": opset_imports,
        }

        return {
            "metadata": metadata,
            "has_dynamic_shapes": global_has_dynamic,
            "inputs": inputs_data,
            "outputs": outputs_data,
            "operators": operators,
        }

    def save_topology(self, topology: Dict[str, Any], output_dir: Path) -> Path:
        """
        Serialize the topology dict to ``pre_compile_topology.json``.

        Args:
            topology: The structured topology data.
            output_dir: Directory to write the JSON file into.

        Returns:
            Path to the written JSON file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "pre_compile_topology.json"
        with open(out_path, "w") as f:
            json.dump(topology, f, indent=2)
        return out_path

