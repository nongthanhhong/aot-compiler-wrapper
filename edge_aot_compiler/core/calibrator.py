"""
calibrator.py — Calibration Data Converter
===========================================

Converts calibration datasets (images, audio files, etc.) into raw
binary arrays (``.raw``) suitable for post-training quantization.

Also generates the ``input_list.txt`` manifest that vendor toolchains
(e.g., QNN) require to drive the quantization pass.
"""

from pathlib import Path
from typing import Callable, List, Tuple, Optional, Any

import numpy as np

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import soundfile as sf
    import librosa
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class CalibrationPreparer:
    """
    Reads a directory of calibration samples and produces:
      1. Converted ``.raw`` binary files
      2. An ``input_list.txt`` index file

    Usage::

        preparer = CalibrationPreparer(Path("calibration_data/"))
        raw_files = preparer.convert_to_raw(Path("output/raw/"), ["batch_size", 80, 3000], "FLOAT")
        preparer.generate_input_list(raw_files, Path("output/"))
    """

    def __init__(self, calibration_dir: Path) -> None:
        self.calibration_dir = calibration_dir

    def convert_to_raw(
        self,
        output_dir: Path,
        input_shape: List[Any],
        dtype: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Path]:
        """
        Convert each sample in ``calibration_dir`` to a ``.raw`` binary array.

        Args:
            output_dir: Where to write the ``.raw`` files.
            input_shape: The expected shape from topology (e.g., ["batch", 80, 3000]).
            dtype: The expected ONNX dtype string (e.g. "FLOAT").

        Returns:
            List of paths to the generated ``.raw`` files.
        """
        if not self.calibration_dir.exists():
            print(f"  [yellow]⚠ Calibration directory not found: {self.calibration_dir}[/yellow]")
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        raw_files = []
        np_dtype = np.float32 if dtype == "FLOAT" else np.float16

        # Sort files to ensure stable ordering
        supported_ext = {".npy", ".wav", ".flac", ".jpg", ".jpeg", ".png", ".bmp"}
        files = sorted(
            [f for f in self.calibration_dir.iterdir()
             if f.is_file() and f.suffix.lower() in supported_ext]
        )
        total = len(files)
        
        for idx, file_path in enumerate(files):
            out_path = output_dir / f"sample_{idx:03d}.raw"
            ext = file_path.suffix.lower()

            try:
                if ext in [".npy"]:
                    arr = np.load(file_path).astype(np_dtype)
                    # We assume user provides exactly the correct shape if using .npy
                
                elif ext in [".wav", ".flac"]:
                    if not HAS_AUDIO:
                        raise ImportError("Install `soundfile` and `librosa` for audio support.")
                    # Generic ASR preprocessing heuristic:
                    # If model expects 3D `[batch, 80, seq_len]`, generate Mel Spectrogram
                    audio_data, sr = sf.read(file_path)
                    
                    # Convert to mono if needed
                    if len(audio_data.shape) > 1:
                        audio_data = audio_data.mean(axis=1)
                        
                    # Resample to 16k if that's standard for ASR models
                    if sr != 16000:
                        audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=16000)
                    
                    # Usually input_shape[1] is feature_size (like 80 for Mel)
                    n_mels = 80
                    if len(input_shape) >= 2 and isinstance(input_shape[1], int):
                        n_mels = input_shape[1]
                        
                    # Compute Log-Mel Spectrogram
                    mel_spec = librosa.feature.melspectrogram(y=audio_data, sr=16000, n_mels=n_mels)
                    mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
                    
                    # Pad or truncate to expected sequence length if fixed
                    seq_len = input_shape[-1]
                    if isinstance(seq_len, int):
                        if mel_spec.shape[1] < seq_len:
                            pad_width = seq_len - mel_spec.shape[1]
                            mel_spec = np.pad(mel_spec, ((0, 0), (0, pad_width)), mode='constant')
                        else:
                            mel_spec = mel_spec[:, :seq_len]
                            
                    # Expand dims for batch
                    arr = np.expand_dims(mel_spec, axis=0).astype(np_dtype)

                elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                    if not HAS_PIL:
                        raise ImportError("Install `Pillow` for image support.")
                    img = Image.open(file_path).convert("RGB")
                    
                    # Basic resize heuristic: look for ints in input_shape [batch, C, H, W]
                    spatial_dims = [d for d in input_shape if isinstance(d, int) and d > 3]
                    if len(spatial_dims) >= 2:
                        # Assuming H, W are the last two dims
                        img = img.resize((spatial_dims[-1], spatial_dims[-2]))
                        
                    arr = np.array(img, dtype=np_dtype) / 255.0
                    
                    # CHW if model expects channel first
                    if arr.shape[-1] == 3 and (len(input_shape) >= 2 and input_shape[1] in [1, 3]):
                        arr = arr.transpose(2, 0, 1)
                    
                    arr = np.expand_dims(arr, axis=0) # Add batch dim

                else:
                    # Unsupported extension
                    continue
                
                # Write raw binary
                arr.tofile(out_path)
                raw_files.append(out_path)

                if progress_callback:
                    progress_callback(idx + 1, total, file_path.name)
                
            except Exception as e:
                print(f"  [red]✗ Error processing {file_path.name}: {e}[/red]")
                if progress_callback:
                    progress_callback(idx + 1, total, file_path.name)
        return raw_files

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
                f.write(f"{raw_file.absolute()}\n")
        return list_path
