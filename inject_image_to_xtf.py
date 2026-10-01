import cv2
import numpy as np
import struct

def main():
    # Load and prepare image
    img_path = '/Users/sbng/.gemini/antigravity-ide/brain/7799aa6f-6436-421a-897f-5267d81b0592/.user_uploaded/media_1789634045733.jpg'
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("Failed to load image")
        return
        
    img_resized = cv2.resize(img, (1024, 1000), interpolation=cv2.INTER_LINEAR)
    
    # Split into port (left 512) and stbd (right 512)
    # Port is reversed in XTF
    port_img = np.flip(img_resized[:, :512], axis=1)
    stbd_img = img_resized[:, 512:]
    
    in_xtf = 'tarang_synthetic_survey_001.xtf'
    out_xtf = 'tarang_synthetic_survey_001_modified.xtf'
    
    with open(in_xtf, 'rb') as f_in, open(out_xtf, 'wb') as f_out:
        # 1. Copy File Header (1024 bytes)
        file_header = f_in.read(1024)
        f_out.write(file_header)
        
        ping_idx = 0
        
        while True:
            packet_header = f_in.read(14)
            if len(packet_header) < 14:
                break
                
            magic, hdr_type, sub_chan, num_chans, res1, num_bytes = struct.unpack('<HBBHII', packet_header)
            
            rest_of_record = f_in.read(num_bytes - 14)
            record_data = bytearray(packet_header + rest_of_record)
            
            if magic == 0xFACE and hdr_type == 0 and num_bytes == 1408:
                if ping_idx < 1000:
                    # Inject port data at offset 320
                    record_data[320 : 320+512] = port_img[ping_idx].tobytes()
                    # Inject stbd data at offset 896
                    record_data[896 : 896+512] = stbd_img[ping_idx].tobytes()
                    ping_idx += 1
            
            f_out.write(record_data)
            
    print(f"Successfully injected image into {ping_idx} pings.")

if __name__ == '__main__':
    main()
