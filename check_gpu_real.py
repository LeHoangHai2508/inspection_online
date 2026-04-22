#!/usr/bin/env python3
"""
Kiểm tra GPU thực sự có available không trên máy.
"""
import sys

def check_nvidia_gpu():
    """Kiểm tra NVIDIA GPU bằng nvidia-smi"""
    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("✓ NVIDIA GPU detected:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"✗ NVIDIA GPU NOT detected: {e}")
        return False

def check_pytorch_cuda():
    """Kiểm tra PyTorch có CUDA support không"""
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        version = torch.__version__
        
        if has_cuda:
            print(f"✓ PyTorch {version} with CUDA support")
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU count: {torch.cuda.device_count()}")
            if torch.cuda.device_count() > 0:
                print(f"  GPU 0: {torch.cuda.get_device_name(0)}")
        else:
            print(f"✗ PyTorch {version} WITHOUT CUDA support")
            if "+cpu" in version:
                print("  → You installed CPU-only version!")
                print("  → Need to reinstall PyTorch with CUDA")
        
        return has_cuda
    except ImportError:
        print("✗ PyTorch NOT installed")
        return False

def check_tensorflow_gpu():
    """Kiểm tra TensorFlow có GPU support không"""
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        
        if gpus:
            print(f"✓ TensorFlow {tf.__version__} with GPU support")
            print(f"  GPU count: {len(gpus)}")
            for gpu in gpus:
                print(f"  - {gpu}")
        else:
            print(f"✗ TensorFlow {tf.__version__} WITHOUT GPU support")
        
        return len(gpus) > 0
    except ImportError:
        print("✗ TensorFlow NOT installed")
        return False
    except Exception as e:
        print(f"✗ TensorFlow error: {e}")
        return False

def main():
    print("=" * 60)
    print("Kiểm tra GPU trên máy")
    print("=" * 60)
    
    print("\n1. NVIDIA GPU Hardware:")
    print("-" * 60)
    has_nvidia = check_nvidia_gpu()
    
    print("\n2. PyTorch CUDA Support:")
    print("-" * 60)
    has_pytorch_cuda = check_pytorch_cuda()
    
    print("\n3. TensorFlow GPU Support:")
    print("-" * 60)
    has_tensorflow_gpu = check_tensorflow_gpu()
    
    print("\n" + "=" * 60)
    print("Kết luận:")
    print("=" * 60)
    
    if not has_nvidia:
        print("✗ Máy KHÔNG có NVIDIA GPU hoặc driver chưa cài")
        print("  → Không thể dùng GPU cho deep learning")
        print("  → Nên dùng gpu: false trong configs/ocr.yaml")
        return 1
    
    if not has_pytorch_cuda:
        print("✗ PyTorch đang dùng CPU-only version")
        print("  → Cần cài lại PyTorch với CUDA:")
        print("  → pip uninstall torch torchvision")
        print("  → pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        return 1
    
    if not has_tensorflow_gpu:
        print("✗ TensorFlow không detect được GPU")
        print("  → Có thể cần cài tensorflow-gpu hoặc cấu hình CUDA")
        return 1
    
    print("✓ GPU sẵn sàng cho EasyOCR + KerasOCR!")
    print("  → Có thể dùng gpu: true trong configs/ocr.yaml")
    return 0

if __name__ == "__main__":
    sys.exit(main())
