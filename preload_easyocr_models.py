#!/usr/bin/env python3
"""
Pre-download EasyOCR models để tránh lỗi concurrent download.
Chạy script này TRƯỚC KHI start server.
"""
import sys

def main():
    print("=" * 60)
    print("Pre-downloading EasyOCR models")
    print("=" * 60)
    
    try:
        import easyocr
        
        # Download models cho latin_basic profile
        print("\nDownloading models for latin_basic profile (en, vi)...")
        reader = easyocr.Reader(['en', 'vi'], gpu=False, verbose=True)
        print("✓ Models downloaded successfully!")
        
        # Test OCR
        print("\nTesting OCR...")
        import numpy as np
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        result = reader.readtext(test_image)
        print("✓ OCR test passed!")
        
        print("\n" + "=" * 60)
        print("SUCCESS! You can now start the server:")
        print("python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
