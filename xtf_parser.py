import os
import shutil
import tempfile
import uuid
import datetime
import logging
import numpy as np
import cv2
import pyxtf
from pyxtf import XTFFileHeader

logger = logging.getLogger("tarang.evidence")


def _patch_xtf_channel_counts(src_path: str) -> str:
    """
    pyxtf raises NotImplementedError when the XTF file header reports more than
    6 total channels (sonar + bathy + snippet + forward + echo + interferometry).
    Many real-world side-scan sonars (e.g. dual-frequency or combined SSS/MBES
    units) set snippet or echo strength channel counts that push the total above 6
    even though only 2 sonar channels carry actual data.

    This function reads the 1024-byte file header, checks channel_count(), and
    if it exceeds 6, zeros the non-sonar count fields (bytes 70-75 of the XTF
    file header struct) in a temporary copy of the file.  The original is never
    modified.  Returns the path that should be passed to pyxtf.xtf_read().

    Offsets in XTFFileHeader (confirmed against pyxtf 1.x ctypes definition):
      NumberOfSonarChannels        +62  (uint16)
      NumberOfBathymetryChannels   +64  (uint16)
      NumberOfSnippetChannels      +66  (uint16)
      NumberOfForwardLookArrays    +68  (uint16)
      NumberOfEchoStrengthChannels +70  (uint16)
      NumberOfInterferometryChannels +72 (uint16)
    """
    import ctypes

    with open(src_path, "rb") as f:
        fh = XTFFileHeader.create_from_buffer(f)
        total = fh.channel_count()

    if total <= 6:
        return src_path   # file is already compliant

    logger.warning(
        "XTF header reports %d total channels (>6 limit). "
        "Zeroing non-sonar channel counts in a temporary working copy: %s",
        total, os.path.basename(src_path)
    )

    # Re-read header into a patched ctypes struct
    with open(src_path, "rb") as f:
        patched_fh = XTFFileHeader.create_from_buffer(f)
    patched_fh.NumberOfBathymetryChannels     = 0
    patched_fh.NumberOfSnippetChannels        = 0
    patched_fh.NumberOfForwardLookArrays      = 0
    patched_fh.NumberOfEchoStrengthChannels   = 0
    patched_fh.NumberOfInterferometryChannels = 0
    if patched_fh.NumberOfSonarChannels > 6:
        patched_fh.NumberOfSonarChannels = 2

    patched_bytes = bytes(patched_fh)

    # Write temp file: patched header + original body
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xtf", prefix="tarang_patched_")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp:
            tmp.write(patched_bytes)
            with open(src_path, "rb") as orig:
                orig.seek(len(patched_bytes))
                shutil.copyfileobj(orig, tmp)
    except Exception as exc:
        logger.error("XTF channel-count patch failed: %s", exc)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return src_path   # fall back to original; pyxtf may still raise

    return tmp_path


def normalize_samples(samples):
    # Convert arbitrary acoustic intensities to 8-bit grayscale
    # Simple linear normalization with clipping to enhance contrast
    arr = np.array(samples, dtype=np.float32)
    # Clip extreme values (e.g., 99th percentile) to avoid washing out the image
    p99 = np.percentile(arr, 99) if len(arr) > 0 else 255
    if p99 > 0:
        arr = np.clip(arr, 0, p99)
        arr = (arr / p99) * 255
    return arr.astype(np.uint8)

def parse_xtf(filepath, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Pre-patch the XTF header so pyxtf does not reject files where non-sonar
    # channel count fields (bathy, snippet, echo, etc.) push total above 6.
    work_path = _patch_xtf_channel_counts(filepath)
    _is_temp   = work_path != filepath

    try:
        (fh, p) = pyxtf.xtf_read(work_path)
    except Exception:
        if _is_temp:
            try:
                os.unlink(work_path)
            except Exception:
                pass
        raise
    finally:
        # Clean up temp file after pyxtf has finished reading it
        if _is_temp:
            try:
                os.unlink(work_path)
            except Exception:
                pass
    
    # Extract rich metadata
    metadata = {
        "Survey ID": uuid.uuid4().hex[:8],
        "Input Type": "xtf",
        "Synthetic": False,
        "File Name": os.path.basename(filepath),
        "Total Pings": 0,
        "Channel Count": 0,
        "Channels": []
    }
    
    if hasattr(fh, 'NoteString') and fh.NoteString:
        try:
            ns = fh.NoteString.decode('utf-8', errors='ignore').strip()
            if ns: metadata["Note"] = ns
            if b'SYNTHETIC' in fh.NoteString.upper():
                metadata["Synthetic"] = True
        except: pass
        
    for field in ['SonarName', 'RecordingProgramName', 'RecordingProgramVersion', 'SystemType', 'NavUnits', 'ProjectionType']:
        if hasattr(fh, field):
            val = getattr(fh, field)
            try:
                # If it's a pyxtf ctypes array, convert to bytes first
                if hasattr(val, '_type_') and hasattr(val, '_length_'):
                    val = bytes(val)
                if isinstance(val, bytes):
                    val = val.decode('utf-8', errors='ignore').strip('\x00').strip()
            except: pass
            
            # Don't add ctypes object string representations if conversion failed
            if val and not str(val).startswith('<pyxtf'):
                metadata[field] = val
            
    for field in ['NavOffsetX', 'NavOffsetY', 'NavOffsetZ', 'NavOffsetYaw', 'MRUOffsetX', 'MRUOffsetY', 'MRUOffsetZ', 'MRUOffsetPitch', 'MRUOffsetRoll', 'MRUOffsetYaw']:
        if hasattr(fh, field):
            val = getattr(fh, field)
            if val != 0.0:
                metadata[field] = round(val, 3)

    ping_data = []
    
    if pyxtf.XTFHeaderType.sonar in p:
        sonar_packets = p[pyxtf.XTFHeaderType.sonar]
        metadata["Total Pings"] = len(sonar_packets)
        
        if len(sonar_packets) > 0:
            first_ping = sonar_packets[0]
            metadata["Channel Count"] = len(first_ping.data)
            for idx, ch in enumerate(first_ping.data):
                side = "PORT" if idx == 0 else "STARBOARD"
                metadata["Channels"].append(side)
            if len(first_ping.data) > 0:
                metadata["Samples per Ping"] = len(first_ping.data[0])
            
            # Times
            metadata["Start Time"] = str(first_ping.get_time())
            metadata["End Time"] = str(sonar_packets[-1].get_time())
            
            # Track bounds
            min_lat, max_lat = 90, -90
            min_lon, max_lon = 180, -180
            altitudes, depths, speeds = [], [], []

            # Process acoustic data
            port_samples = []
            stbd_samples = []
            
            for idx, ping in enumerate(sonar_packets):
                # Use actual coordinates if available
                pass                
                if ping.SensorYcoordinate:
                    min_lat, max_lat = min(min_lat, ping.SensorYcoordinate), max(max_lat, ping.SensorYcoordinate)
                if ping.SensorXcoordinate:
                    min_lon, max_lon = min(min_lon, ping.SensorXcoordinate), max(max_lon, ping.SensorXcoordinate)
                if getattr(ping, 'SensorAltitude', 0) > 0:
                    altitudes.append(ping.SensorAltitude)
                if getattr(ping, 'SensorDepth', 0) > 0:
                    depths.append(ping.SensorDepth)
                if getattr(ping, 'SensorSpeed', 0) > 0:
                    speeds.append(ping.SensorSpeed)
                    
                ping_info = {
                    "ping_number": ping.PingNumber,
                    "timestamp": str(ping.get_time()),
                    "latitude": ping.SensorYcoordinate,
                    "longitude": ping.SensorXcoordinate,
                    "heading_degrees": ping.SensorHeading,
                    "speed_mps": ping.SensorSpeed,
                    "depth": getattr(ping, 'SensorDepth', 0),
                    "altitude": getattr(ping, 'SensorAltitude', 0),
                    "channels": []
                }
                
                if len(ping.data) > 0:
                    port_arr = normalize_samples(ping.data[0])
                    port_samples.append(port_arr)
                    ping_info["channels"].append({"side": "PORT", "number_of_samples": len(port_arr)})
                
                if len(ping.data) > 1:
                    stbd_arr = normalize_samples(ping.data[1])
                    stbd_samples.append(stbd_arr)
                    ping_info["channels"].append({"side": "STARBOARD", "number_of_samples": len(stbd_arr)})
                    
                ping_data.append(ping_info)
            
            if min_lat < 90: metadata["Min Latitude"] = round(min_lat, 6)
            if max_lat > -90: metadata["Max Latitude"] = round(max_lat, 6)
            if min_lon < 180: metadata["Min Longitude"] = round(min_lon, 6)
            if max_lon > -180: metadata["Max Longitude"] = round(max_lon, 6)
            if altitudes: metadata["Avg Altitude"] = f"{round(sum(altitudes)/len(altitudes), 2)} m"
            if depths: metadata["Avg Depth"] = f"{round(sum(depths)/len(depths), 2)} m"
            if speeds: metadata["Avg Speed"] = f"{round(sum(speeds)/len(speeds), 2)} kts"
            
            metadata["Channels"] = ", ".join(metadata["Channels"])

            # Reconstruct Images
            images = []
            
            # We will generate one image per 1000 pings (chunking)
            chunk_size = 1000
            for i in range(0, len(port_samples), chunk_size):
                port_chunk = port_samples[i:i+chunk_size]
                stbd_chunk = stbd_samples[i:i+chunk_size]
                
                if not port_chunk and not stbd_chunk:
                    continue
                    
                # Combine port and stbd side-by-side
                # Port channel is usually flipped so nadir (0) is in the middle
                combined_rows = []
                for p_row, s_row in zip(port_chunk, stbd_chunk):
                    p_flipped = np.flip(p_row)
                    combined = np.concatenate([p_flipped, s_row])
                    combined_rows.append(combined)
                
                if not combined_rows:
                    continue
                    
                img_array = np.vstack(combined_rows)
                
                # The injected image already has the correct aspect ratio, no need to stretch
                stretch_factor = 1
                new_height = img_array.shape[0] * stretch_factor
                if stretch_factor != 1:
                    img_array = cv2.resize(img_array, (img_array.shape[1], new_height), interpolation=cv2.INTER_LINEAR)
                
                # Convert to BGR so it matches standard cv2.imread output for YOLO without artificial colors
                img_color = cv2.cvtColor(img_array, cv2.COLORMAP_BONE) if False else cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
                
                img_filename = f"xtf_{metadata['Survey ID']}_{i}.jpg"
                img_path = os.path.join(output_dir, img_filename)
                if not cv2.imwrite(img_path, img_color):
                    logger.error("XTF sonar raster generation failed: path=%s", img_path)
                    raise OSError(f'Unable to write reconstructed sonar image: {img_filename}')

                # Storage is intentionally handled once by app.py after the
                # full survey ID, image ID, sequence, and content hash are
                # known. Uploading here created a second anonymous object and
                # left the database unable to associate it with detections.
                logger.info("XTF sonar raster generated: path=%s ping_start=%s", img_path, i)
                
                images.append({
                    "id": f"img_{i}",
                    "path": img_path,
                    "filename": img_filename,
                    "ping_start": i,
                    "ping_end": i + len(port_chunk) - 1
                })
                
            return {
                "metadata": metadata,
                "pings": ping_data,
                "images": images
            }
            
    return None
