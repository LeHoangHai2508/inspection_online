#!/usr/bin/env python3
"""
Script test nhanh Ensemble OCR Engine.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.domain.enums import InspectionSide
from src.domain.models import TemplateUploadFile
from src.ocr.engine import AutoOCREngine


def test_ensemble_engine():
    """Test ensemble engine với mock data"""
    print("=" * 60)
    print("Test Ensemble OCR Engine")
    print("=" * 60)
    print()
    
    # Test với text file (mock)
    print("1. Testing with mock text file...")
    mock_content = b"""COMPOSITION
100% COTTON
MADE IN CHINA
WASH 30C
DO NOT BLEACH
DRY FLAT"""
    
    mock_file = TemplateUploadFile(
        filename="test.txt",
        content=mock_content,
        media_type="text/plain",
    )
    
    try:
        engine = AutoOCREngine()
        print(f"   Engine initialized: {engine.engine_name}")
        print(f"   Preferred engine: {engine._preferred_engine}")
        print()
        
        # Test side1
        print("2. Testing SIDE1...")
        result_side1 = engine.run(side=InspectionSide.SIDE1, file=mock_file)
        print(f"   Engine used: {result_side1.engine_name}")
        print(f"   Blocks found: {len(result_side1.blocks)}")
        print(f"   Raw text preview:")
        for line in result_side1.raw_text.split('\n')[:5]:
            print(f"     {line}")
        print()
        
        # Test side2
        print("3. Testing SIDE2...")
        result_side2 = engine.run(side=InspectionSide.SIDE2, file=mock_file)
        print(f"   Engine used: {result_side2.engine_name}")
        print(f"   Blocks found: {len(result_side2.blocks)}")
        print()
        
        print("=" * 60)
        print("✓ Basic test passed!")
        print()
        print("Note: This test used mock engine (text file).")
        print("To test real OCR:")
        print("1. Ensure EasyOCR + KerasOCR installed")
        print("2. Upload image via API/UI")
        print("3. Check logs for 'ensemble' engine usage")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def test_config_loading():
    """Test config loading"""
    print("\n" + "=" * 60)
    print("Test Config Loading")
    print("=" * 60)
    print()
    
    try:
        from src.utils.config_loader import load_yaml_config
        
        config = load_yaml_config("configs/ocr.yaml")
        
        print("Config loaded:")
        print(f"  engine: {config.get('engine')}")
        print(f"  easyocr_langs: {config.get('easyocr_langs')}")
        print(f"  verifier.enabled: {config.get('verifier', {}).get('enabled')}")
        print(f"  strict_real_ocr: {config.get('strict_real_ocr')}")
        print()
        
        # Validate config
        if config.get('engine') != 'ensemble':
            print("⚠ Warning: engine is not 'ensemble'")
            print(f"  Current: {config.get('engine')}")
            print("  Expected: ensemble")
            return 1
        
        if not config.get('easyocr_langs'):
            print("⚠ Warning: easyocr_langs is empty")
            return 1
        
        print("✓ Config validation passed!")
        return 0
        
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main test runner"""
    results = []
    
    # Test 1: Config
    results.append(test_config_loading())
    
    # Test 2: Engine
    results.append(test_ensemble_engine())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if all(r == 0 for r in results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
