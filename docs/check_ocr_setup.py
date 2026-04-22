#!/usr/bin/env python3
"""
Script kiểm tra OCR setup
Chạy: python check_ocr_setup.py
"""

import sys


def check_pytesseract():
    """Kiểm tra pytesseract"""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ pytesseract: OK (Tesseract {version})")
        return True
    except ImportError:
        print("❌ pytesseract: NOT INSTALLED")
        print("   Fix: pip install pytesseract")
        return False
    except Exception as e:
        print(f"❌ pytesseract: ERROR - {e}")
        return False


def check_pil():
    """Kiểm tra PIL/Pillow"""
    try:
        from PIL import Image
        print("✅ PIL/Pillow: OK")
        return True
    except ImportError:
        print("❌ PIL/Pillow: NOT INSTALLED")
        print("   Fix: pip install pillow")
        return False


def check_cv2():
    """Kiểm tra OpenCV"""
    try:
        import cv2
        print(f"✅ OpenCV: OK (version {cv2.__version__})")
        return True
    except ImportError:
        print("❌ OpenCV: NOT INSTALLED")
        print("   Fix: pip install opencv-python")
        return False


def check_tesseract_langs():
    """Kiểm tra Tesseract language packs"""
    try:
        import subprocess
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        langs = []
        for line in result.stdout.splitlines():
            item = line.strip()
            if not item or ":" in item:
                continue
            if item in {"osd", "equ"}:
                continue
            langs.append(item)
        
        required = ["eng", "ara", "chi_sim", "chi_tra", "jpn", "kor", "tha", "vie", "rus"]
        missing = [lang for lang in required if lang not in langs]
        
        if missing:
            print(f"⚠️  Tesseract languages: MISSING {missing}")
            print(f"   Installed: {', '.join(langs[:10])}...")
            print("   Fix: Install missing language packs")
            return False
        else:
            print(f"✅ Tesseract languages: OK ({len(langs)} installed)")
            return True
            
    except Exception as e:
        print(f"❌ Tesseract languages: ERROR - {e}")
        return False


def check_parser_code():
    """Kiểm tra parser có code Arabic"""
    try:
        with open("src/ocr/parser.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        has_arabic_helper = "_is_arabic_token" in content
        has_merge_helper = "_merge_items_preserve_script_direction" in content
        uses_merge = "merged_text = _merge_items_preserve_script_direction(items)" in content
        
        if has_arabic_helper and has_merge_helper and uses_merge:
            print("✅ Parser: Arabic helpers OK")
            return True
        else:
            print("❌ Parser: Arabic helpers MISSING")
            if not has_arabic_helper:
                print("   Missing: _is_arabic_token()")
            if not has_merge_helper:
                print("   Missing: _merge_items_preserve_script_direction()")
            if not uses_merge:
                print("   Missing: usage of _merge_items_preserve_script_direction()")
            return False
    except Exception as e:
        print(f"❌ Parser: ERROR - {e}")
        return False


def check_engine_code():
    """Kiểm tra engine có PSM 11 và không threshold"""
    try:
        with open("src/ocr/engine.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        has_psm_11 = 'psm = "6" if side == InspectionSide.SIDE1 else "11"' in content
        no_threshold = "# _, image = cv2.threshold(" in content
        has_logging = 'print(f"[OCR] backend=pytesseract' in content
        
        if has_psm_11:
            print("✅ Engine: PSM 11 for side2 OK")
        else:
            print("❌ Engine: PSM 11 MISSING (still using PSM 4?)")
        
        if no_threshold:
            print("✅ Engine: Threshold disabled for side2 OK")
        else:
            print("⚠️  Engine: Threshold still enabled for side2")
        
        if has_logging:
            print("✅ Engine: Logging added OK")
        else:
            print("⚠️  Engine: Logging not added")
        
        return has_psm_11 and no_threshold
    except Exception as e:
        print(f"❌ Engine: ERROR - {e}")
        return False


def check_config():
    """Kiểm tra config có đủ ngôn ngữ"""
    try:
        with open("configs/ocr.yaml", "r", encoding="utf-8") as f:
            content = f.read()
        
        has_side1_ara = "side1:" in content and "ara" in content
        has_side1_chi = "side1:" in content and "chi_sim" in content
        has_side2_chi = "side2:" in content and "chi_sim" in content and "chi_tra" in content
        
        if has_side1_ara and has_side1_chi and has_side2_chi:
            print("✅ Config: Languages OK")
            return True
        else:
            print("❌ Config: Languages MISSING")
            if not has_side1_ara:
                print("   Missing: ara in side1")
            if not has_side1_chi:
                print("   Missing: chi_sim in side1")
            if not has_side2_chi:
                print("   Missing: chi_sim+chi_tra in side2")
            return False
    except Exception as e:
        print(f"❌ Config: ERROR - {e}")
        return False


def main():
    print("=" * 60)
    print("OCR Setup Check")
    print("=" * 60)
    print()
    
    results = []
    
    print("1. Dependencies:")
    results.append(check_pytesseract())
    results.append(check_pil())
    results.append(check_cv2())
    print()
    
    print("2. Tesseract:")
    results.append(check_tesseract_langs())
    print()
    
    print("3. Code:")
    results.append(check_parser_code())
    results.append(check_engine_code())
    results.append(check_config())
    print()
    
    print("=" * 60)
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Next steps:")
        print("1. Restart server:")
        print("   python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000")
        print("2. Upload template and check terminal for [OCR] logs")
        print("3. Verify preview shows correct Arabic and Chinese")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Fix the issues above, then run this script again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
