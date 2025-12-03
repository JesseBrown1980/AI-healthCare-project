import sys
print("Importing torch...")
try:
    import torch
    print(f"Torch imported successfully. Version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
except Exception as e:
    print(f"Failed to import torch: {e}")
    sys.exit(1)
