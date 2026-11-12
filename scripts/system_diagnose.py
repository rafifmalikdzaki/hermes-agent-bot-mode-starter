#!/usr/bin/env python3
"""
system_diagnose.py
Hardware diagnostics, GPU/RAM health monitoring, and system optimization for IUABTW workstation.
Checks local RTX 3070, remote host reachability, Docker containers, agent memory, and applies safe optimizations.
"""

import sys
import os
import psutil
import shutil
import datetime
import subprocess
from pathlib import Path

def check_local_gpu():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "name": parts[0],
            "mem_used_mb": float(parts[1]),
            "mem_total_mb": float(parts[2]),
            "temp_c": float(parts[3]),
            "power_w": float(parts[4])
        }
    except Exception:
        return None

def check_remote_hosts():
    hosts = {
        "gpu-labkc-l40": ("gpu-labkc.ub.ac.id", 1004),
        "gpu-kc": ("gpu-labkc.ub.ac.id", 2001),
        "gpu-runpod": ("203.57.40.74", 10106)
    }
    results = {}
    import socket
    for hname, (addr, port) in hosts.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        try:
            s.connect((addr, port))
            results[hname] = "Online (Port open)"
            s.close()
        except Exception:
            results[hname] = "Offline or Proxy required"
    return results

def check_docker_containers():
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}} | {{.Image}} | {{.Status}}"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip().splitlines()
        return out
    except Exception:
        return []

def diagnose_system():
    # CPU & RAM
    load1, load5, load15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count(logical=True)
    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(str(Path.home()))
    
    gpu = check_local_gpu()
    docker = check_docker_containers()
    remotes = check_remote_hosts()

    return {
        "load": (load1, load5, load15),
        "cpu_count": cpu_count,
        "ram_used_gb": vmem.used / (1024**3),
        "ram_total_gb": vmem.total / (1024**3),
        "ram_percent": vmem.percent,
        "swap_used_gb": swap.used / (1024**3),
        "swap_total_gb": swap.total / (1024**3),
        "disk_free_gb": disk.free / (1024**3),
        "disk_total_gb": disk.total / (1024**3),
        "gpu": gpu,
        "docker": docker,
        "remotes": remotes
    }

def optimize_system():
    actions = []
    
    # 1. Clear stale update locks in ~/.hermes
    hermes_dir = Path.home() / ".hermes"
    for lock in hermes_dir.rglob("*.lock"):
        if "install.lock" in lock.name:
            try:
                lock.unlink()
                actions.append(f"Removed stale lock: {lock}")
            except Exception:
                pass

    # 2. Check for runaway log files > 50MB in ~/.hermes/logs and ~/.vibe/logs
    log_dirs = [hermes_dir / "logs", Path.home() / ".vibe" / "logs"]
    for ldir in log_dirs:
        if ldir.is_dir():
            for logfile in ldir.glob("*.log"):
                try:
                    size_mb = logfile.stat().st_size / (1024 * 1024)
                    if size_mb > 50:
                        # Truncate keeping last 5MB
                        lines = logfile.read_text(encoding="utf-8", errors="ignore").splitlines()
                        kept = "\n".join(lines[-5000:])
                        logfile.write_text(kept, encoding="utf-8")
                        actions.append(f"Trimmed oversized log {logfile.name} ({size_mb:.1f}MB -> ~5000 lines)")
                except Exception:
                    pass

    # 3. Trim Hermes daemon memory via Python garbage collector
    try:
        subprocess.run(
            ["systemctl", "--user", "kill", "-s", "USR1", "hermes-gateway.service"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )
        actions.append("Triggered Hermes daemon memory compaction & GC (SIGUSR1)")
    except Exception:
        pass

    return actions

def main():
    optimize = "--optimize" in sys.argv or "-o" in sys.argv
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    diag = diagnose_system()

    print(f"\n🖥️  IUABTW Workstation Diagnostics ({now_str})")
    print("═" * 75)
    print(f"• CPU Load (1m, 5m, 15m): {diag['load'][0]:.2f}, {diag['load'][1]:.2f}, {diag['load'][2]:.2f} (across {diag['cpu_count']} vCPUs)")
    print(f"• RAM Usage: {diag['ram_used_gb']:.1f} GB / {diag['ram_total_gb']:.1f} GB ({diag['ram_percent']}%) | Swap: {diag['swap_used_gb']:.1f} GB / {diag['swap_total_gb']:.1f} GB")
    print(f"• Disk Space: {diag['disk_free_gb']:.1f} GB free of {diag['disk_total_gb']:.1f} GB")

    if diag["gpu"]:
        g = diag["gpu"]
        print(f"• Local GPU: {g['name']}")
        print(f"  VRAM: {g['mem_used_mb']:.0f} MB / {g['mem_total_mb']:.0f} MB | Temp: {g['temp_c']}°C | Power: {g['power_w']:.1f}W")
    else:
        print("• Local GPU: None / Driver unqueried")

    if diag["docker"]:
        print(f"• Running Docker Containers ({len(diag['docker'])}):")
        for c in diag["docker"]:
            print(f"  🐳 {c}")

    print(f"• Remote Machine Clusters:")
    for rname, status in diag["remotes"].items():
        print(f"  🌐 {rname:15s}: {status}")

    print("═" * 75)

    if optimize:
        print("\n🧹 Executing Safe System Optimizations...")
        acts = optimize_system()
        if acts:
            for a in acts:
                print(f"  ✓ {a}")
        else:
            print("  ✓ System is already cleanly optimized; no stale locks or oversized logs found.")
        print()

if __name__ == "__main__":
    main()
