import os

with open('xtf_parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_metadata_logic = """
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
                if isinstance(val, bytes): val = val.decode('utf-8', errors='ignore').strip()
            except: pass
            if val: metadata[field] = val
            
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
                if ping.SensorYcoordinate:
                    min_lat, max_lat = min(min_lat, ping.SensorYcoordinate), max(max_lat, ping.SensorYcoordinate)
                if ping.SensorXcoordinate:
                    min_lon, max_lon = min(min_lon, ping.SensorXcoordinate), max(max_lon, ping.SensorXcoordinate)
                if ping.SensorAltitude and ping.SensorAltitude > 0:
                    altitudes.append(ping.SensorAltitude)
                if ping.SensorDepth and ping.SensorDepth > 0:
                    depths.append(ping.SensorDepth)
                if ping.SensorSpeed and ping.SensorSpeed > 0:
                    speeds.append(ping.SensorSpeed)
                    
                ping_info = {
"""

# Replace the block from metadata = { to the start of ping_info = {
import re
pattern = re.compile(r'    metadata = \{.*?(?=                ping_info = \{)', re.DOTALL)
content = pattern.sub(new_metadata_logic, content)

# Also add the summary metadata after the for loop
summary_logic = """
            if min_lat < 90: metadata["Min Latitude"] = round(min_lat, 6)
            if max_lat > -90: metadata["Max Latitude"] = round(max_lat, 6)
            if min_lon < 180: metadata["Min Longitude"] = round(min_lon, 6)
            if max_lon > -180: metadata["Max Longitude"] = round(max_lon, 6)
            if altitudes: metadata["Avg Altitude"] = f"{round(sum(altitudes)/len(altitudes), 2)} m"
            if depths: metadata["Avg Depth"] = f"{round(sum(depths)/len(depths), 2)} m"
            if speeds: metadata["Avg Speed"] = f"{round(sum(speeds)/len(speeds), 2)} kts"
            
            metadata["Channels"] = ", ".join(metadata["Channels"])

            # Reconstruct Images
"""
content = content.replace("            # Reconstruct Images\n", summary_logic)

with open('xtf_parser.py', 'w', encoding='utf-8') as f:
    f.write(content)
