import pyxtf

filepath = 'tarang_synthetic_survey_001.xtf'
try:
    (fh, p) = pyxtf.xtf_read(filepath)
    print("Header:", fh)
    
    # Get all packet types
    types = set(list(p.keys()))
    print("Packet types:", types)
    
    if pyxtf.XTFHeaderType.sonar in p:
        sonar_packets = p[pyxtf.XTFHeaderType.sonar]
        print(f"Number of sonar ping packets: {len(sonar_packets)}")
        if len(sonar_packets) > 0:
            ping = sonar_packets[0]
            print(f"Ping 0: Channels: {len(ping.data)}")
            for idx, ch in enumerate(ping.data):
                print(f"Channel {idx}: length {len(ch)}")
except Exception as e:
    print(f"Error parsing: {e}")
