import re
from datetime import datetime

def parse_txt_metadata(file_content, filename="survey_metadata.txt"):
    """
    Parses arbitrary sonar/survey TXT metadata files.
    Gracefully extracts standard hydrographic fields without assuming strict formats.
    """
    if isinstance(file_content, bytes):
        try:
            text = file_content.decode('utf-8')
        except UnicodeDecodeError:
            text = file_content.decode('latin-1', errors='ignore')
    else:
        text = str(file_content)

    metadata = {
        'filename': filename,
        'parsed_at': datetime.now().isoformat(),
        'fields': {},
        'track_points': []
    }

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Look for Key: Value or Key = Value or Key \t Value
        m = re.match(r'^([A-Za-z0-9_\s\-\/\.]+)\s*[:=]\s*(.+)$', line)
        if m:
            raw_key = m.group(1).strip()
            val = m.group(2).strip()
            norm_key = re.sub(r'[\s\-_]+', '_', raw_key).lower()
            metadata['fields'][norm_key] = val

            # Normalize common fields
            if norm_key in ['survey_id', 'mission_id', 'surveyid', 'id'] and 'survey_id' not in metadata:
                metadata['survey_id'] = val
            elif norm_key in ['survey_name', 'mission_name', 'name', 'title'] and 'survey_name' not in metadata:
                metadata['survey_name'] = val
            elif norm_key in ['timestamp', 'date', 'datetime', 'survey_date', 'utc_time'] and 'timestamp' not in metadata:
                metadata['timestamp'] = val
            elif norm_key in ['latitude', 'lat', 'start_lat', 'gps_lat'] and 'latitude' not in metadata:
                try:
                    metadata['latitude'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['longitude', 'lon', 'long', 'start_lon', 'gps_lon'] and 'longitude' not in metadata:
                try:
                    metadata['longitude'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['heading', 'heading_deg', 'azimuth'] and 'heading' not in metadata:
                try:
                    metadata['heading'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['depth', 'water_depth', 'bathymetry', 'depth_m'] and 'water_depth' not in metadata:
                try:
                    metadata['water_depth'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['altitude', 'sonar_altitude', 'alt_m'] and 'sonar_altitude' not in metadata:
                try:
                    metadata['sonar_altitude'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['range', 'sonar_range', 'swath_range', 'range_m'] and 'range' not in metadata:
                try:
                    metadata['range'] = float(re.findall(r'[-+]?\d*\.\d+|\d+', val)[0])
                except:
                    pass
            elif norm_key in ['vessel', 'platform', 'survey_platform', 'auv'] and 'platform' not in metadata:
                metadata['platform'] = val
            elif norm_key in ['crs', 'datum', 'projection', 'coordinate_system'] and 'crs' not in metadata:
                metadata['crs'] = val
            elif norm_key in ['pings', 'ping_count', 'total_pings'] and 'ping_count' not in metadata:
                try:
                    metadata['ping_count'] = int(re.findall(r'\d+', val)[0])
                except:
                    pass

        # Check for coordinate pairs in line (e.g. lat, lon track data)
        coord_match = re.findall(r'[-+]?\d{1,3}\.\d{4,8}', line)
        if len(coord_match) >= 2:
            try:
                lat, lon = float(coord_match[0]), float(coord_match[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    metadata['track_points'].append([lat, lon])
            except:
                pass

    if 'survey_id' not in metadata:
        clean_name = re.sub(r'[^A-Za-z0-9]', '', filename.split('.')[0]).upper()
        metadata['survey_id'] = f"TRG-TXT-{clean_name[:8] or 'SURVEY'}"

    return metadata
