from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
print(f"project_root={root}")
print(f"python={sys.executable}")
print(f"python_version={sys.version.split()[0]}")

for rel in ["1_AI_Engine", "scripts", "4_Local_Workspace", "4_Local_Workspace/models", "4_Local_Workspace/dataset"]:
    p = root / rel
    print(f"{rel}: {'OK' if p.exists() else 'MISSING'}")

try:
    import torch
    print(f"torch={torch.__version__}")
    print(f"cuda_available={torch.cuda.is_available()}")
    print(f"torch_cuda={torch.version.cuda}")
    if torch.cuda.is_available():
        print(f"cuda_device={torch.cuda.get_device_name(0)}")
except Exception as exc:
    print(f"torch=ERROR: {exc}")

for name in ["PIL", "numpy", "cv2"]:
    try:
        mod = __import__(name)
        print(f"{name}=OK")
    except Exception as exc:
        print(f"{name}=ERROR: {exc}")


models_dir = root / "4_Local_Workspace" / "models"
if models_dir.exists():
    for model_path in sorted(models_dir.glob("*.pt")):
        try:
            head = model_path.read_bytes()[:80]
            if head.startswith(b"version https://git-lfs.github.com/spec"):
                print(f"model_file={model_path.name}: GIT_LFS_POINTER_NOT_REAL_MODEL")
            else:
                print(f"model_file={model_path.name}: {model_path.stat().st_size} bytes")
        except Exception as exc:
            print(f"model_file={model_path.name}: ERROR {exc}")
