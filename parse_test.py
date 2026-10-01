import pyxtf
(fh,p) = pyxtf.xtf_read('tarang_synthetic_survey_002.xtf')
pings = p.get(pyxtf.XTFHeaderType.sonar,[])
print('Total pings:', len(pings))
if pings:
    print('First ping - lat:', pings[0].SensorYcoordinate, 'lon:', pings[0].SensorXcoordinate)
    print('Last  ping - lat:', pings[-1].SensorYcoordinate, 'lon:', pings[-1].SensorXcoordinate)
