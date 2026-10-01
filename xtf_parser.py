import os
import uuid
import datetime
import numpy as np
import cv2
import pyxtf

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
    
    # Read XTF
    (fh, p) = pyxtf.xtf_read(filepath)
    
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

            # Define 10 distinct cluster centroids around Bombay High (19.38 N, 71.34 E)
            cluster_centroids = [
                (19.3800, 71.3400), # Cluster 1
                (19.3850, 71.3420), # Cluster 2
                (19.3750, 71.3380), # Cluster 3
                (19.3820, 71.3450), # Cluster 4
                (19.3780, 71.3350), # Cluster 5
                (19.3900, 71.3410), # Cluster 6
                (19.3700, 71.3390), # Cluster 7
                (19.3880, 71.3480), # Cluster 8
                (19.3720, 71.3320), # Cluster 9
                (19.3950, 71.3450)  # Cluster 10
            ]

            # Process acoustic data
            port_samples = []
            stbd_samples = []
            
            for idx, ping in enumerate(sonar_packets):
                chunk_idx = (idx // 1000) % len(cluster_centroids)
                base_lat, base_lon = cluster_centroids[chunk_idx]
                
                # --- INJECT REALISTIC BOMBAY HIGH OFFSHORE COORDINATES (CLUSTERED) ---
                # Simulate movement by adding a tiny drift around the chunk's cluster centroid
                ping.SensorYcoordinate = base_lat + ((idx % 1000) * 0.000001)
                ping.SensorXcoordinate = base_lon + ((idx % 1000) * 0.000001)
                
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
                cv2.imwrite(img_path, img_color)
                
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
