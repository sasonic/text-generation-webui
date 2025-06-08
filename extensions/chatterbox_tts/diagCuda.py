import torch
print("--- PyTorch GPU Diagnostic ---")
is_available = torch.cuda.is_available()
print(f"Is CUDA available? -> {is_available}")
if is_available:
    print(f"CUDA Version (from PyTorch): {torch.version.cuda}")
    print(f"Number of GPUs found: {torch.cuda.device_count()}")
    print(f"Name of current GPU: {torch.cuda.get_device_name(0)}")
else:
    print("❌ FAILURE: PyTorch still cannot detect your GPU.")
print("--- End of Diagnostic ---")