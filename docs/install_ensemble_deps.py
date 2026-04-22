#!/usr/bin/env python3
"""
Script cài đặt dependencies cho Ensemble OCR Engine.
"""

import subprocess
import sys


def run_pip_install(packages: list[str], description: str) -> bool:
    """Cài đặt packages qua pip"""
    print(f"\n{'='*60}")
    print(f"Installing {description}")
    print(f"{'='*60}")
    
    cmd = [sys.executable, "-m", "pip", "install"] + packages
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True,
        )
        print(f"\n✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to install {description}")
        print(f"Error: {e}")
        return False


def main():
    print("="*60)
    print("Ensemble OCR Dependencies Installer")
    print("="*60)
    print()
    print("This will install:")
    print("  1. EasyOCR (includes PyTorch)")
    print("  2. KerasOCR")
    print("  3. TensorFlow")
    print()
    
    response = input("Continue? [Y/n]: ").strip().lower()
    if response and response not in ['y', 'yes']:
        print("Cancelled.")
        return 1
    
    results = []
    
    # Step 1: Install EasyOCR (will install PyTorch automatically)
    print("\n" + "="*60)
    print("Step 1/3: Installing EasyOCR")
    print("="*60)
    print("Note: This will also install PyTorch (CPU version)")
    print("      If you need GPU, install PyTorch GPU first:")
    print("      pip install torch --index-url https://download.pytorch.org/whl/cu118")
    print()
    
    results.append(run_pip_install(
        ["easyocr"],
        "EasyOCR"
    ))
    
    # Step 2: Install KerasOCR
    results.append(run_pip_install(
        ["keras-ocr"],
        "KerasOCR"
    ))
    
    # Step 3: Install TensorFlow
    print("\n" + "="*60)
    print("Step 3/3: Installing TensorFlow")
    print("="*60)
    print("Note: Installing CPU version")
    print("      For GPU support, use: pip install tensorflow[and-cuda]")
    print()
    
    results.append(run_pip_install(
        ["tensorflow"],
        "TensorFlow"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("Installation Summary")
    print("="*60)
    
    if all(results):
        print("✓ All dependencies installed successfully!")
        print()
        print("Next steps:")
        print("1. Run: python check_ensemble_setup.py")
        print("2. Start server: python -m uvicorn src.api.main:app --reload")
        print()
        print("For GPU support:")
        print("1. Uninstall CPU versions:")
        print("   pip uninstall torch torchvision torchaudio")
        print("2. Install GPU versions:")
        print("   pip install torch --index-url https://download.pytorch.org/whl/cu118")
        print("   pip install tensorflow[and-cuda]")
        return 0
    else:
        print("✗ Some installations failed")
        print()
        print("Try manual installation:")
        print("  pip install easyocr keras-ocr tensorflow")
        return 1


if __name__ == "__main__":
    sys.exit(main())
