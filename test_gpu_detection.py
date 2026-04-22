#!/usr/bin/env python3
"""
Script test GPU auto-detection.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def test_pytorch_gpu():
    """Test PyTorch CUDA"""
    print("=" * 60)
    print("PyTorch CUDA Detection")
    print("=" * 60)
    
    try:
        import torch
        
        cuda_available = torch.cuda.is_available()
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {cuda_available}")
        
        if cuda_available:
            print(f"CUDA version: {torch.version.cuda}")
            print(f"Device count: {torch.cuda.device_count()}")
            print(f"Current device: {torch.cuda.current_device()}")
            print(f"Device name: {torch.cuda.get_device_name(0)}")
        else:
            print("No CUDA device found (CPU only)")
        
        return cuda_available
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_tensorflow_gpu():
    """Test TensorFlow GPU"""
    print("\n" + "=" * 60)
    print("TensorFlow GPU Detection")
    print("=" * 60)
    
    try:
        import tensorflow as tf
        
        gpus = tf.config.list_physical_devices('GPU')
        print(f"TensorFlow version: {tf.__version__}")
        print(f"GPU devices: {len(gpus)}")
        
        if gpus:
            for gpu in gpus:
                print(f"  - {gpu.name}")
        else:
            print("No GPU device found (CPU only)")
        
        return len(gpus) > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_auto_detect():
    """Test auto-detect function"""
    print("\n" + "=" * 60)
    print("Auto-detect GPU Function")
    print("=" * 60)
    
    try:
        from src.ocr.engine import _detect_gpu_available
        
        has_gpu = _detect_gpu_available()
        
        print(f"\nResult: GPU={'Available' if has_gpu else 'Not Available'}")
        
        return has_gpu
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resolve_gpu_setting():
    """Test resolve GPU setting"""
    print("\n" + "=" * 60)
    print("Resolve GPU Setting")
    print("=" * 60)
    
    try:
        from src.ocr.engine import _resolve_gpu_setting
        
        test_cases = [
            ("auto", "Auto-detect"),
            ("true", "Force GPU"),
            ("false", "Force CPU"),
            (True, "Boolean True"),
            (False, "Boolean False"),
            ("yes", "String yes"),
            ("no", "String no"),
        ]
        
        for value, description in test_cases:
            result = _resolve_gpu_setting(value)
            print(f"{description:20} ({value!r:10}) → {result}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("\n" + "=" * 60)
    print("GPU Detection Test Suite")
    print("=" * 60)
    print()
    
    pytorch_gpu = test_pytorch_gpu()
    tensorflow_gpu = test_tensorflow_gpu()
    auto_detect = test_auto_detect()
    resolve_test = test_resolve_gpu_setting()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    print(f"PyTorch CUDA:     {'✓' if pytorch_gpu else '✗'}")
    print(f"TensorFlow GPU:   {'✓' if tensorflow_gpu else '✗'}")
    print(f"Auto-detect:      {'✓' if auto_detect else '✗'}")
    print(f"Resolve function: {'✓' if resolve_test else '✗'}")
    print()
    
    if pytorch_gpu and tensorflow_gpu:
        print("✓ GPU fully available! Ensemble engine will use GPU.")
        print()
        print("Config recommendation:")
        print("  gpu: auto  # Will use GPU automatically")
    elif pytorch_gpu or tensorflow_gpu:
        print("⚠ Partial GPU support:")
        if pytorch_gpu:
            print("  - PyTorch has CUDA (EasyOCR can use GPU)")
        if tensorflow_gpu:
            print("  - TensorFlow has GPU (KerasOCR can use GPU)")
        print()
        print("Ensemble engine will use CPU (requires both).")
        print()
        print("Config recommendation:")
        print("  gpu: auto  # Will use CPU automatically")
    else:
        print("✗ No GPU available. Ensemble engine will use CPU.")
        print()
        print("Config recommendation:")
        print("  gpu: auto  # Will use CPU automatically")
        print()
        print("To enable GPU:")
        print("1. Install PyTorch with CUDA:")
        print("   pip install torch --index-url https://download.pytorch.org/whl/cu118")
        print("2. Install TensorFlow with GPU:")
        print("   pip install tensorflow[and-cuda]")
    
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
