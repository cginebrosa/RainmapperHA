from pathlib import Path
import sys,shutil,json,tempfile
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path.cwd()/'local-apps/wunderground/code'))
from station_research import Research,handler,ThreadingHTTPServer
root=Path(tempfile.mkdtemp(prefix='station-research-browser-'))
source=Path('local-apps/wunderground/data')
for name in ('candidates.json','stations.json','baseline-summary.json','existing-availability-30.json','grid.json','search-points.json'):
 shutil.copy2(source/name,root/name)
(root/'viewer').symlink_to((source/'viewer').resolve(),target_is_directory=True)
def fetch(endpoint,params):
 if endpoint.endswith('near'):return {'location':{'stationId':['IBROWSER1','IOLIOL3'],'latitude':[41.7,41.9],'longitude':[1.2,1.22],'stationName':['Prueba aislada','Oliola'],'qcStatus':[1,1]}}
 end=datetime.now(ZoneInfo('Europe/Madrid')).date()-timedelta(days=1)
 return {'observations':[{'obsTimeLocal':str(end-timedelta(days=i))+' 23:59:00','metric':{'elev':425.8,'precipTotal':0.0}} for i in range(30)]}
r=Research(root,fetch=fetch)
print(root,flush=True)
ThreadingHTTPServer(('127.0.0.1',8124),handler(r)).serve_forever()
