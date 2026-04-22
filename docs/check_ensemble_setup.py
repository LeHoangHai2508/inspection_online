#!/usr/bin/env python3
"""
Script kiểm tra cài đặt EasyOCR + KerasOCR cho ensemble engine.
"""

import sys


def check_easyocr():
    """Kiểm tra EasyOCR"""
    try:
        import easyocr
        print("✓ EasyOCR installed")
        return True
    except ImportError:
        print("✗ EasyOCR NOT installed")
        print("  Install: pip install easyocr")
        return False


def check_keras_ocr():
    """Kiểm tra KerasOCR"""
    try:
        import keras_ocr
        print("✓ KerasOCR installed")
        return True
    except ImportError:
        print("✗ KerasOCR NOT installed")
        print("  Install: pip install keras-ocr")
        return False


def check_tensorflow():
    """Kiểm tra TensorFlow"""
    try:
        import tensorflow as tf
        
        # TensorFlow 2.16+ không có __version__ trực tiếp
        try:
            version = tf.__version__
        except AttributeError:
            version = tf.version.VERSION
        
        print(f"✓ TensorFlow {version} installed")
        
        # Kiểm tra GPU
        try:
            gpus = tf.config.list_physical_devices('GPU')
            if gpus:
                print(f"  GPU available: {len(gpus)} device(s)")
                for gpu in gpus:
                    print(f"    - {gpu.name}")
            else:
                print("  GPU: Not available (CPU only)")
        except Exception:
            print("  GPU: Cannot detect")
        
        return True
    except ImportError:
        print("✗ TensorFlow NOT installed")
        print("  Install: pip install tensorflow")
        return False


def check_pytorch():
    """Kiểm tra PyTorch (cho EasyOCR)"""
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__} installed")
        
        # Kiểm tra CUDA
        if torch.cuda.is_available():
            print(f"  CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("  CUDA: Not available (CPU only)")
        
        return True
    except ImportError:
        print("✗ PyTorch NOT installed")
        print("  EasyOCR will install PyTorch automatically")
        return False


def check_opencv():
    """Kiểm tra OpenCV"""
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__} installed")
        return True
    except ImportError:
        print("✗ OpenCV NOT installed")
        print("  Install: pip install opencv-python")
        return False


def check_pillow():
    """Kiểm tra Pillow"""
    try:
        from PIL import Image
        import PIL
        print(f"✓ Pillow {PIL.__version__} installed")
        return True
    except ImportError:
        print("✗ Pillow NOT installed")
        print("  Install: pip install pillow")
        return False


def main():
    print("=" * 60)
    print("Kiểm tra cài đặt Ensemble OCR Engine")
    print("=" * 60)
    print()
    
    checks = [
        ("Core dependencies", [
            check_opencv,
            check_pillow,
        ]),
        ("EasyOCR stack", [
            check_pytorch,
            check_easyocr,
        ]),
        ("KerasOCR stack", [
            check_tensorflow,
            check_keras_ocr,
        ]),
    ]
    
    all_passed = True
    
    for section_name, section_checks in checks:
        print(f"\n{section_name}:")
        print("-" * 60)
        for check_fn in section_checks:
            if not check_fn():
                all_passed = False
        print()
    
    print("=" * 60)
    if all_passed:
        print("✓ All checks passed! Ensemble engine ready to use.")
        print()
        print("Next steps:")
        print("1. Ensure configs/ocr.yaml has engine: ensemble")
        print("2. Start the server: python -m uvicorn src.api.main:app --reload")
        print("3. Upload templates and test OCR")
        return 0
    else:
        print("✗ Some checks failed. Install missing dependencies.")
        print()
        print("Quick install:")
        print("  pip install easyocr keras-ocr tensorflow opencv-python pillow")
        return 1


if __name__ == "__main__":
    sys.exit(main())
