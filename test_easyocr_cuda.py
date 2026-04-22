#!/usr/bin/env python3
"""
Test EasyOCR CUDA detection
"""
import sys

def main():
    print("=" * 60)
    print("Test EasyOCR CUDA Detection")
    print("=" * 60)
    
    # 1. Check PyTorch CUDA
    print("\n1. PyTorch CUDA:")
    print("-" * 60)
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU count: {torch.cuda.device_count()}")
            print(f"GPU 0: {torch.cuda.get_device_name(0)}")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    # 2. Test EasyOCR initialization
    print("\n2. EasyOCR Initialization:")
    print("-" * 60)
    try:
        import easyocr
        
        # Test với GPU=True
        print("Initializing EasyOCR with GPU=True...")
        reader = easyocr.Reader(['en'], gpu=True, verbose=False)
        print("✓ EasyOCR initialized with GPU=True")
        
        # Check internal GPU setting
        if hasattr(reader, 'detector'):
            if hasattr(reader.detector, 'device'):
                print(f"  Detector device: {reader.detector.device}")
        
        if hasattr(reader, 'recognizer'):
            if hasattr(reader.recognizer, 'device'):
                print(f"  Recognizer device: {reader.recognizer.device}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
