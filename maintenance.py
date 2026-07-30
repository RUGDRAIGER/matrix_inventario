import os
import shutil
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HIGH_PERFORMANCE_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"


def _report(progress_cb, pct, msg):
    if progress_cb:
        progress_cb(pct, msg)


def _run_cmd(args, timeout=120):
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as ex:
        return False, str(ex)


def _dir_size(path):
    total = 0
    try:
        for root, _, files in os.walk(path):
            for name in files:
                fp = os.path.join(root, name)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _clean_tree(path, label=""):
    path = Path(path)
    if not path.exists():
        return 0, f"{label}: ruta no encontrada"
    freed_before = _dir_size(path)
    deleted = 0
    errors = 0
    try:
        for item in path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink(missing_ok=True)
                    deleted += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted += 1
            except OSError:
                errors += 1
    except OSError as ex:
        return 0, f"{label}: {ex}"
    freed = max(0, freed_before - _dir_size(path))
    detail = f"{label}: {deleted} elementos, {format_bytes(freed)} liberados"
    if errors:
        detail += f" ({errors} en uso)"
    return freed, detail


def _browser_profiles(browser):
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    base = (
        local / "Google" / "Chrome" / "User Data"
        if browser == "chrome"
        else local / "Microsoft" / "Edge" / "User Data"
    )
    if not base.exists():
        return []
    profiles = []
    if (base / "Default").exists():
        profiles.append(base / "Default")
    profiles.extend(p for p in base.glob("Profile *") if p.is_dir())
    return profiles


def _clean_browser(browser):
    subdirs = ("Cache", "Code Cache", "GPUCache", "Service Worker", "CacheStorage")
    cookie_names = ("Cookies", "Cookies-journal")
    total_freed = 0
    locked = False
    profiles = _browser_profiles(browser)
    label = "Chrome" if browser == "chrome" else "Edge"
    if not profiles:
        return 0, f"{label}: no instalado"
    for profile in profiles:
        for sub in subdirs:
            target = profile / sub
            if target.exists():
                freed, _ = _clean_tree(target, sub)
                total_freed += freed
        net = profile / "Network"
        if net.exists():
            for cf in cookie_names:
                cf_path = net / cf
                if not cf_path.exists():
                    continue
                try:
                    total_freed += cf_path.stat().st_size
                    cf_path.unlink(missing_ok=True)
                except OSError:
                    locked = True
    detail = f"{label}: cache y cookies limpiados ({format_bytes(total_freed)})"
    if locked:
        detail += " — cierre el navegador para cookies en uso"
    return total_freed, detail


def _clean_temp():
    paths = {os.environ.get(k) for k in ("TEMP", "TMP") if os.environ.get(k)}
    paths.add(r"C:\Windows\Temp")
    total_freed = 0
    parts = []
    for p in paths:
        freed, msg = _clean_tree(p, Path(p).name)
        total_freed += freed
        parts.append(msg)
    return total_freed, "TEMP/TMP — " + " | ".join(parts)


def _clean_prefetch():
    return _clean_tree(r"C:\Windows\Prefetch", "Prefetch")


def _empty_recycle_bin():
    ok, out = _run_cmd(
        ["powershell", "-NoProfile", "-Command",
         "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"]
    )
    return 0, "Papelera vaciada" if ok else f"Papelera: {out or 'requiere confirmacion'}"


def _flush_dns():
    ok, out = _run_cmd(["ipconfig", "/flushdns"])
    return 0, "Cache DNS vaciada" if ok else f"DNS: {out}"


def _set_high_performance():
    ok, _ = _run_cmd(["powercfg", "/setactive", HIGH_PERFORMANCE_GUID])
    if ok:
        return 0, "Plan de energia: Alto rendimiento"
    ok2, _ = _run_cmd(["powercfg", "/setactive", "SCHEME_MIN"])
    return 0, "Plan de energia optimizado" if ok2 else "No se pudo cambiar plan de energia"


def _clean_thumbnails():
    explorer = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Explorer"
    if not explorer.exists():
        return 0, "Miniaturas: ruta no encontrada"
    freed = 0
    count = 0
    for pattern in ("thumbcache_*.db", "iconcache_*.db"):
        for f in explorer.glob(pattern):
            try:
                freed += f.stat().st_size
                f.unlink(missing_ok=True)
                count += 1
            except OSError:
                pass
    return freed, f"Miniaturas: {count} archivos, {format_bytes(freed)}"


def _optimize_visual_effects():
    ok1, _ = _run_cmd([
        "powershell", "-NoProfile", "-Command",
        "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
        "-Name EnableTransparency -Value 0 -ErrorAction SilentlyContinue",
    ])
    ok2, _ = _run_cmd([
        "powershell", "-NoProfile", "-Command",
        "$p='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects';"
        "if(-not(Test-Path $p)){New-Item -Path $p -Force|Out-Null};"
        "Set-ItemProperty -Path $p -Name VisualFXSetting -Value 2 -ErrorAction SilentlyContinue",
    ])
    if ok1 or ok2:
        return 0, "Efectos visuales reducidos para mejor rendimiento"
    return 0, "No se pudieron ajustar efectos visuales"


def format_bytes(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _task_ok(detail):
    low = detail.lower()
    return not any(x in low for x in ("error", "no se pudo", "requiere confirmacion", "no accesible"))


def run_maintenance(options, progress_cb=None):
    steps = []
    if options.get("clean_temp"):
        steps.append(("Limpiar TEMP / TMP", _clean_temp))
    if options.get("clean_prefetch"):
        steps.append(("Limpiar Prefetch", _clean_prefetch))
    if options.get("clean_chrome"):
        steps.append(("Chrome cache y cookies", lambda: _clean_browser("chrome")))
    if options.get("clean_edge"):
        steps.append(("Edge cache y cookies", lambda: _clean_browser("edge")))
    if options.get("empty_recycle"):
        steps.append(("Vaciar papelera", _empty_recycle_bin))
    if options.get("flush_dns"):
        steps.append(("Vaciar cache DNS", _flush_dns))
    if options.get("high_performance"):
        steps.append(("Plan Alto rendimiento", _set_high_performance))
    if options.get("clean_thumbnails"):
        steps.append(("Cache de miniaturas", _clean_thumbnails))
    if options.get("optimize_visual"):
        steps.append(("Optimizar efectos visuales", _optimize_visual_effects))

    tasks = []
    total_freed = 0
    total = max(len(steps), 1)

    for i, (name, fn) in enumerate(steps):
        _report(progress_cb, int((i / total) * 100), f"Ejecutando: {name}...")
        try:
            freed, detail = fn()
            total_freed += freed or 0
            tasks.append({
                "name": name, "ok": _task_ok(detail),
                "detail": detail, "freed": freed or 0,
            })
        except Exception as ex:
            tasks.append({"name": name, "ok": False, "detail": str(ex), "freed": 0})

    _report(progress_cb, 100, "Mantenimiento completado")
    return {"tasks": tasks, "total_freed": total_freed}
