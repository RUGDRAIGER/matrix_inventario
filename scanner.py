import json
import subprocess
import socket


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
            timeout=90,
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


def _get_wmi(namespace=r"root\cimv2"):
    try:
        import wmi
        return wmi.WMI(namespace=namespace)
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
            model = (disk.Model or "").upper()
            media = (disk.MediaType or "").upper()
            if "NVME" in model or "M.2" in model:
                dtype = "NVMe/M.2"
            elif "SSD" in model or "SOLID" in media:
                dtype = "SSD"
            else:
                dtype = "HDD"
            drives.append(f"{dtype} {size_gb} GB")
        if drives:
            data["disco_detalle"] = " | ".join(drives)
    except Exception:
        pass

    try:
        for os_info in wmi_conn.Win32_OperatingSystem():
            data["windows_version"] = _safe(
                f"{os_info.Caption} ({os_info.Version} Build {os_info.BuildNumber})"
            )
            break
    except Exception:
        pass

    return data


def _scan_network():
    """IP y MAC de la tarjeta física activa del PC (no router/virtual)."""
    script = r"""
    $adapter = $null
    $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Where-Object { $_.NextHop -ne '0.0.0.0' } |
        Sort-Object RouteMetric, InterfaceMetric |
        Select-Object -First 1
    if ($route) {
        $adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue
    }
    if (-not $adapter -or $adapter.Virtual -or $adapter.Status -ne 'Up') {
        $adapter = Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Status -eq 'Up' -and
                $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VPN|TAP|TUN|Loopback|Bluetooth'
            } |
            Sort-Object InterfaceMetric |
            Select-Object -First 1
    }
    if (-not $adapter) { exit 1 }
    $ipObj = Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        } |
        Sort-Object PrefixLength -Descending |
        Select-Object -First 1
    if (-not $ipObj) { exit 1 }
    [PSCustomObject]@{
        IP  = $ipObj.IPAddress
        MAC = ($adapter.MacAddress -replace '-', ':')
        Adapter = $adapter.InterfaceDescription
    } | ConvertTo-Json -Compress
    """
    raw = _run_powershell(script)
    if raw:
        try:
            data = json.loads(raw)
            ip = data.get("IP", "N/A")
            mac = data.get("MAC", "N/A")
            if ip and mac:
                return ip, mac
        except Exception:
            pass

    ip = "N/A"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    mac = "N/A"
    ps_mac = _run_powershell(
        "(Get-NetAdapter -Physical | Where-Object {$_.Status -eq 'Up' -and $_.Virtual -eq $false} | "
        "Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty MacAddress)"
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


def _monitor_key(marca, modelo, serie):
    return f"{marca}|{modelo}|{serie}".lower()


def _scan_monitors_wmi_root():
    monitors = []
    wmi_root = _get_wmi(namespace=r"root\wmi")
    if not wmi_root:
        return monitors
    try:
        for mon in wmi_root.WmiMonitorID():
            marca = _safe(_decode_wmi_string(mon.ManufacturerName))
            modelo = _safe(
                _decode_wmi_string(mon.UserFriendlyName)
                or _decode_wmi_string(mon.ProductCodeID)
            )
            serie = _safe(_decode_wmi_string(mon.SerialNumberID))
            monitors.append({"tipo": "MONITOR", "marca": marca, "modelo": modelo, "serie": serie})
    except Exception:
        pass
    return monitors


def _scan_monitors_powershell():
    script = r"""
    function Decode-WmiString($arr) {
        if (-not $arr) { return '' }
        -join ($arr | Where-Object { $_ -gt 0 } | ForEach-Object { [char]$_ })
    }
    $results = @()
    try {
        Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorID -ErrorAction Stop | ForEach-Object {
            $results += [PSCustomObject]@{
                Marca  = (Decode-WmiString $_.ManufacturerName)
                Modelo = (Decode-WmiString $_.UserFriendlyName)
                Serie  = (Decode-WmiString $_.SerialNumberID)
            }
        }
    } catch {}
    if ($results.Count -eq 0) {
        Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
            Where-Object { $_.PNPClass -eq 'Monitor' -and $_.Status -eq 'OK' } |
            ForEach-Object {
                $results += [PSCustomObject]@{
                    Marca  = $_.Manufacturer
                    Modelo = $_.Name
                    Serie  = ($_.DeviceID -split '\\')[-1]
                }
            }
    }
    if ($results.Count -eq 0) {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
public static class DisplayHelper {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct DISPLAY_DEVICE {
        public int cb; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string DeviceString;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string DeviceID;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string DeviceKey;
        public uint StateFlags;
    }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplayDevices(string lpDevice, uint iDevNum, ref DISPLAY_DEVICE lpDisplayDevice, uint dwFlags);
    public static List<string[]> GetMonitors() {
        var list = new List<string[]>();
        DISPLAY_DEVICE d = new DISPLAY_DEVICE(); d.cb = Marshal.SizeOf(d);
        for (uint i = 0; EnumDisplayDevices(null, i, ref d, 0); i++) {
            if ((d.StateFlags & 0x00000001) != 0) {
                list.Add(new string[]{ d.DeviceString ?? "", d.DeviceID ?? "" });
            }
            d.cb = Marshal.SizeOf(d);
        }
        return list;
    }
}
"@
        [DisplayHelper]::GetMonitors() | ForEach-Object {
            $results += [PSCustomObject]@{
                Marca  = 'N/A'
                Modelo = $_[0]
                Serie  = ($_[1] -split '\\')[-1]
            }
        }
    }
    $results | ConvertTo-Json -Compress
    """
    raw = _run_powershell(script)
    monitors = []
    if not raw:
        return monitors
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            monitors.append({
                "tipo": "MONITOR",
                "marca": _safe(item.get("Marca", item.get("marca", ""))),
                "modelo": _safe(item.get("Modelo", item.get("modelo", ""))),
                "serie": _safe(item.get("Serie", item.get("serie", ""))),
            })
    except Exception:
        pass
    return monitors


def _scan_monitors_wmi(wmi_conn):
    seen = set()
    monitors = []

    for source in (_scan_monitors_wmi_root(), _scan_monitors_powershell()):
        for mon in source:
            key = _monitor_key(mon["marca"], mon["modelo"], mon["serie"])
            if key in seen and key != "n/a|n/a|n/a":
                continue
            seen.add(key)
            monitors.append(mon)

    if not monitors and wmi_conn:
        try:
            for mon in wmi_conn.Win32_DesktopMonitor():
                m = {
                    "tipo": "MONITOR",
                    "marca": _safe(mon.MonitorManufacturer),
                    "modelo": _safe(mon.Name),
                    "serie": _safe(mon.PNPDeviceID.split("\\")[-1] if mon.PNPDeviceID else ""),
                }
                key = _monitor_key(m["marca"], m["modelo"], m["serie"])
                if key not in seen:
                    seen.add(key)
                    monitors.append(m)
        except Exception:
            pass

    return monitors


def _scan_webcams(wmi_conn):
    webcams = []
    if not wmi_conn:
        return webcams
    seen = set()
    try:
        for dev in wmi_conn.Win32_PnPEntity():
            name = (dev.Name or "").lower()
            cls = (dev.PNPClass or "").lower()
            if ("camera" in name or "webcam" in name) or cls in ("camera", "image"):
                key = (dev.DeviceID or dev.Name or "").lower()
                if key in seen:
                    continue
                seen.add(key)
                webcams.append({
                    "tipo": "WEBCAM",
                    "marca": _safe(dev.Manufacturer),
                    "modelo": _safe(dev.Name),
                    "serie": _safe(dev.DeviceID.split("\\")[-1] if dev.DeviceID else ""),
                })
    except Exception:
        pass
    return webcams


def _label_group(items, base_name, tipo):
    if not items:
        return [{
            "tipo": tipo, "etiqueta": f"{base_name} 1",
            "marca": "N/A", "modelo": "N/A", "serie": "N/A",
        }]
    for i, item in enumerate(items, 1):
        item["tipo"] = tipo
        item["etiqueta"] = f"{base_name} {i}"
    return items


def _normalize_accesorios(monitors, webcams):
    accesorios = []
    accesorios.extend(_label_group(monitors, "Monitor", "MONITOR"))
    accesorios.extend(_label_group(webcams, "Webcam", "WEBCAM"))
    return accesorios


def scan_hardware(progress_callback=None):
    _report(progress_callback, 0, "Iniciando escaneo...")
    _report(progress_callback, 5, "Conectando WMI...")
    wmi_conn = _get_wmi()

    _report(progress_callback, 15, "Leyendo datos del sistema...")
    pc_data = _scan_pc_wmi(wmi_conn)

    _report(progress_callback, 45, "Consultando red del PC (IP/MAC)...")
    ip, mac = _scan_network()
    pc_data["ip_address"] = ip
    pc_data["mac_address"] = mac

    _report(progress_callback, 60, "Detectando Microsoft Office...")
    pc_data["office_version"] = _scan_office()

    _report(progress_callback, 72, "Escaneando monitores...")
    monitors = _scan_monitors_wmi(wmi_conn)

    _report(progress_callback, 88, "Escaneando webcams...")
    webcams = _scan_webcams(wmi_conn)

    accesorios = _normalize_accesorios(monitors, webcams)
    _report(progress_callback, 100, "Escaneo completado")
    return {"pc": pc_data, "accesorios": accesorios}


def scan_hardware_json(progress_callback=None):
    return json.dumps(scan_hardware(progress_callback), ensure_ascii=False, indent=2)
