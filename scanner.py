import json
import subprocess
import socket
import uuid


def _safe(value, default="N/A"):
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _report(progress_cb, pct, msg):
    if progress_cb:
        progress_cb(pct, msg)


def _run_powershell(script):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _decode_wmi_string(raw):
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    try:
        chars = [chr(c) for c in raw if c > 0]
        return "".join(chars).strip()
    except Exception:
        return str(raw)


def _get_wmi():
    try:
        import wmi
        return wmi.WMI()
    except Exception:
        return None


def _scan_pc_wmi(wmi_conn):
    data = {
        "marca": "N/A", "modelo": "N/A", "serie": "N/A",
        "windows_version": "N/A", "procesador": "N/A", "ram_gb": 0,
        "disco_detalle": "N/A", "office_version": "N/A",
        "ip_address": "N/A", "mac_address": "N/A",
    }
    if not wmi_conn:
        return data

    try:
        for cs in wmi_conn.Win32_ComputerSystem():
            data["marca"] = _safe(cs.Manufacturer)
            data["modelo"] = _safe(cs.Model)
            total_ram = int(cs.TotalPhysicalMemory or 0) / (1024 ** 3)
            data["ram_gb"] = round(total_ram, 1)
    except Exception:
        pass

    try:
        for bios in wmi_conn.Win32_BIOS():
            data["serie"] = _safe(bios.SerialNumber)
            break
    except Exception:
        pass

    try:
        procs = [cpu.Name.strip() for cpu in wmi_conn.Win32_Processor()]
        if procs:
            data["procesador"] = " | ".join(procs)
    except Exception:
        pass

    try:
        drives = []
        for disk in wmi_conn.Win32_DiskDrive():
            size_gb = round(int(disk.Size or 0) / (1024 ** 3), 1)
            media = (disk.MediaType or "").upper()
            model = (disk.Model or "").upper()
            if "NVME" in model or "M.2" in model or "M2" in model:
                dtype = "NVMe/M.2"
            elif "SSD" in model or "SOLID" in media:
                dtype = "SSD"
            elif "HDD" in model or "FIXED" in media:
                dtype = "HDD"
            else:
                iface = (disk.InterfaceType or "").upper()
                dtype = "NVMe/M.2" if "NVME" in iface else ("SSD" if "SSD" in model else "HDD")
            drives.append(f"{dtype} {size_gb} GB")
        if drives:
            data["disco_detalle"] = " | ".join(drives)
    except Exception:
        pass

    try:
        for os_info in wmi_conn.Win32_OperatingSystem():
            caption = os_info.Caption or ""
            version = os_info.Version or ""
            build = os_info.BuildNumber or ""
            data["windows_version"] = _safe(f"{caption} ({version} Build {build})")
            break
    except Exception:
        pass

    return data


def _scan_network():
    ip, mac = "N/A", "N/A"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    try:
        mac_raw = uuid.getnode()
        mac = ":".join(f"{(mac_raw >> ele) & 0xff:02x}" for ele in range(40, -1, -8))
    except Exception:
        pass
    ps_ip = _run_powershell(
        "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown'} | Select-Object -First 1 -ExpandProperty IPAddress)"
    )
    if ps_ip:
        ip = ps_ip
    ps_mac = _run_powershell(
        "(Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1 -ExpandProperty MacAddress)"
    )
    if ps_mac:
        mac = ps_mac.replace("-", ":")
    return ip, mac


def _scan_office():
    script = r"""
    $paths = @(
        'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration',
        'HKLM:\SOFTWARE\Microsoft\Office\16.0\Common\InstallRoot'
    )
    foreach ($p in $paths) {
        if (Test-Path $p) {
            $v = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue
            if ($v.ProductReleaseIds) { $v.ProductReleaseIds; exit }
        }
    }
    Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like '*Microsoft Office*' -or $_.DisplayName -like '*Microsoft 365*' } |
        Select-Object -First 1 -ExpandProperty DisplayName
    """
    result = _run_powershell(script)
    return _safe(result) if result else "N/A"


def _scan_monitors_wmi(wmi_conn):
    monitors = []
    if not wmi_conn:
        return monitors
    try:
        for mon in wmi_conn.WmiMonitorID():
            monitors.append({
                "tipo": "MONITOR",
                "marca": _safe(_decode_wmi_string(mon.ManufacturerName)),
                "modelo": _safe(_decode_wmi_string(mon.UserFriendlyName) or _decode_wmi_string(mon.ProductCodeID)),
                "serie": _safe(_decode_wmi_string(mon.SerialNumberID)),
            })
    except Exception:
        pass
    if not monitors:
        try:
            for mon in wmi_conn.Win32_DesktopMonitor():
                monitors.append({
                    "tipo": "MONITOR",
                    "marca": _safe(mon.MonitorManufacturer),
                    "modelo": _safe(mon.Name),
                    "serie": _safe(mon.PNPDeviceID.split("\\")[-1] if mon.PNPDeviceID else ""),
                })
        except Exception:
            pass
    return monitors


def _scan_webcams(wmi_conn):
    webcams = []
    if not wmi_conn:
        return webcams
    try:
        for dev in wmi_conn.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            cls = (dev.PNPClass or "").lower()
            if ("camera" in name or "webcam" in name) or cls in ("camera", "image"):
                webcams.append({
                    "tipo": "WEBCAM",
                    "marca": _safe(dev.Manufacturer),
                    "modelo": _safe(dev.Name),
                    "serie": _safe(dev.DeviceID.split("\\")[-1] if dev.DeviceID else ""),
                })
    except Exception:
        pass
    return webcams


def _scan_parlantes(wmi_conn):
    parlantes = []
    if not wmi_conn:
        return parlantes
    try:
        for dev in wmi_conn.Win32_SoundDevice():
            parlantes.append({
                "tipo": "PARLANTE",
                "marca": _safe(dev.Manufacturer),
                "modelo": _safe(dev.Name or dev.ProductName),
                "serie": _safe(dev.DeviceID.split("\\")[-1] if dev.DeviceID else ""),
            })
    except Exception:
        pass
    if not parlantes:
        try:
            for dev in wmi_conn.Win32_PnPEntity():
                cls = (dev.PNPClass or "").lower()
                name = (dev.Name or "").lower()
                if cls == "media" or any(k in name for k in ("audio", "speaker", "sound")):
                    parlantes.append({
                        "tipo": "PARLANTE",
                        "marca": _safe(dev.Manufacturer),
                        "modelo": _safe(dev.Name),
                        "serie": _safe(dev.DeviceID.split("\\")[-1] if dev.DeviceID else ""),
                    })
        except Exception:
            pass
    return parlantes[:5]


def _label_group(items, base_name):
    if not items:
        return [{
            "tipo": base_name.upper() if base_name == "Monitor" else 
                    ("WEBCAM" if base_name == "Webcam" else "PARLANTE"),
            "etiqueta": f"{base_name} 1",
            "marca": "N/A", "modelo": "N/A", "serie": "N/A",
        }]
    tipo_map = {"Monitor": "MONITOR", "Webcam": "WEBCAM", "Parlante": "PARLANTE"}
    tipo = tipo_map.get(base_name, base_name.upper())
    for i, item in enumerate(items, 1):
        item["tipo"] = tipo
        item["etiqueta"] = f"{base_name} {i}"
    return items


def _normalize_accesorios(monitors, webcams, parlantes):
    accesorios = []
    accesorios.extend(_label_group(monitors, "Monitor"))
    accesorios.extend(_label_group(webcams, "Webcam"))
    accesorios.extend(_label_group(parlantes, "Parlante"))
    return accesorios


def scan_hardware(progress_callback=None):
    _report(progress_callback, 0, "Iniciando escaneo...")

    _report(progress_callback, 5, "Conectando WMI...")
    wmi_conn = _get_wmi()

    _report(progress_callback, 15, "Leyendo datos del sistema...")
    pc_data = _scan_pc_wmi(wmi_conn)

    _report(progress_callback, 45, "Consultando red (IP/MAC)...")
    ip, mac = _scan_network()
    pc_data["ip_address"] = ip
    pc_data["mac_address"] = mac

    _report(progress_callback, 60, "Detectando Microsoft Office...")
    pc_data["office_version"] = _scan_office()

    _report(progress_callback, 72, "Escaneando monitores...")
    monitors = _scan_monitors_wmi(wmi_conn)

    _report(progress_callback, 84, "Escaneando webcams...")
    webcams = _scan_webcams(wmi_conn)

    _report(progress_callback, 94, "Escaneando dispositivos de audio...")
    parlantes = _scan_parlantes(wmi_conn)

    accesorios = _normalize_accesorios(monitors, webcams, parlantes)
    _report(progress_callback, 100, "Escaneo completado")

    return {"pc": pc_data, "accesorios": accesorios}


def scan_hardware_json(progress_callback=None):
    return json.dumps(scan_hardware(progress_callback), ensure_ascii=False, indent=2)
