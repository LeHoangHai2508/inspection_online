@echo off
REM Script cài PyTorch với CUDA vào virtual environment

echo ============================================================
echo Cài PyTorch với CUDA support vào .venv
echo ============================================================

echo.
echo Bước 1: Activate virtual environment
call .venv\Scripts\activate.bat

echo.
echo Bước 2: Gỡ PyTorch CPU-only
pip uninstall -y torch torchvision torchaudio

echo.
echo Bước 3: Cài PyTorch với CUDA 12.1 (cho CUDA 12.5 driver)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo Bước 4: Kiểm tra cài đặt
python check_gpu_real.py

echo.
echo ============================================================
echo Hoàn tất! Nếu thấy "PyTorch with CUDA support" thì OK
echo ============================================================
pause
