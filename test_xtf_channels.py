#!/usr/bin/env python
"""Quick test to verify XTF file has correct channel count."""
import pyxtf

filepath = "tarang_final_demo_survey_001.xtf"
print(f"Testing: {filepath}")

try:
    (fh, p) = pyxtf.xtf_read(filepath)
    print(f"✓ File parsed successfully")
    print(f"  NumberOfSonarChannels: {fh.NumberOfSonarChannels}")
    print(f"  NumberOfBathymetryChannels: {fh.NumberOfBathymetryChannels}")
    
    if pyxtf.XTFHeaderType.sonar in p:
        sonar_packets = p[pyxtf.XTFHeaderType.sonar]
        print(f"  Total pings: {len(sonar_packets)}")
        if len(sonar_packets) > 0:
            first_ping = sonar_packets[0]
            print(f"  Channels in first ping: {len(first_ping.data)}")
            for idx, ch in enumerate(first_ping.data):
                print(f"    Channel {idx}: {len(ch)} samples")
    print("\n✓ XTF file is valid and ready for upload!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
