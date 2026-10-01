import pyxtf
import ctypes

def main():
    filepath = 'tarang_synthetic_survey_001.xtf'
    (fh, p) = pyxtf.xtf_read(filepath)
    print("Header size:", ctypes.sizeof(fh))
    if pyxtf.XTFHeaderType.sonar in p:
        pings = p[pyxtf.XTFHeaderType.sonar]
        print("Num pings:", len(pings))
        if len(pings) > 0:
            ping = pings[0]
            print("Ping Header size:", ctypes.sizeof(ping))
            print("Num bytes this record:", ping.NumBytesThisRecord)
            for i, ch in enumerate(ping.data):
                print(f"Channel {i} length: {len(ch)}")
            print("Ch info size:", ctypes.sizeof(ping.ping_chan_headers[0]))
            
if __name__ == '__main__':
    main()
