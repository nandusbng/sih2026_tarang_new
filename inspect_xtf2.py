import pyxtf
import ctypes

def main():
    filepath = 'tarang_synthetic_survey_001.xtf'
    (fh, p) = pyxtf.xtf_read(filepath)
    if pyxtf.XTFHeaderType.sonar in p:
        pings = p[pyxtf.XTFHeaderType.sonar]
        ping = pings[0]
        print(dir(ping))
        if hasattr(ping, 'ping_chan_headers'):
            for ch in ping.ping_chan_headers:
                print("Chan Header:", dir(ch))
            
if __name__ == '__main__':
    main()
