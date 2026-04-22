#!/usr/bin/env python3
"""
Kiểm tra PyTorch trong venv hiện tại và hướng dẫn fix.
"""
import sys
import subprocess

def main():
    print("=" * 60)
    print("Kiểm tra PyTorch trong virtual environment")
    print("=" * 60)
    
    # Kiểm tra có đang ở venv không
    import os
    venv_active = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    print(f"\nPython executable: {sys.executable}")
    print(f"Virtual environment active: {venv_active}")
    
    if not venv_active:
        print("\n✗ KHÔNG đang ở virtual environment!")
        print("  → Cần activate .venv trước:")
        print("  → .venv\\Scripts\\activate")
        return 1
    
    print("\n✓ Đang ở virtual environment")
    
    # Kiểm tra PyTorch
    try:
        import torch
        version = torch.__version__
        has_cuda = torch.cuda.is_available()
        
        print(f"\nPyTorch version: {version}")
        print(f"CUDA available: {has_cuda}")
        
        if "+cpu" in version:
            print("\n✗ PyTorch CPU-only version detected!")
            print("\nCách fix:")
            print("1. Gỡ PyTorch CPU:")
            print("   pip uninstall -y torch torchvision torchaudio")
            print("\n2. Cài PyTorch CUDA 12.1:")
            print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
            print("\n3. Restart server")
            return 1
        
        if not has_cuda:
            print("\n✗ PyTorch không detect được CUDA!")
            print("  → Có thể driver NVIDIA chưa đúng")
            return 1
        
        print("\n✓ PyTorch CUDA OK!")
        print(f"  CUDA version: {torch.version.cuda}")
        print(f"  GPU count: {torch.cuda.device_count()}")
        if torch.cuda.device_count() > 0:
            print(f"  GPU 0: {torch.cuda.get_device_name(0)}")
        
        return 0
        
    except ImportError:
        print("\n✗ PyTorch chưa cài!")
        print("  → pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        return 1

if __name__ == "__main__":
    sys.exit(main())
