"""Opt-in acceptance inside HA local; creates/removes one temporary test session.

Run explicitly via docker exec after local/worker readiness. Never run in HA real.
Uses an isolated basic user with prediction permission; removes only its own records.
"""
def main():
    import json,time,secrets,hashlib,concurrent.futures,os
    from urllib.request import Request,urlopen
    from urllib.error import HTTPError
    import web_server as w
    from rainmapper_core.mushroom_prediction_map import CONTRACT_ID,API_PATH
    from rainmapper_core.mushroom_map_weather import map_today

    base='http://127.0.0.1:8099'
    device='map-check-'+secrets.token_hex(8); token=secrets.token_urlsafe(32)
    username='map-check-'+secrets.token_hex(8)
    def test_user_record(remove=False):
     # Preserve every existing raw record, including fields unknown to this test.
     raw=json.loads(w.USERS_JSON_PATH.read_text())
     raw['users']=[u for u in raw['users'] if u.get('username')!=username]
     if not remove: raw['users'].append({'username':username,'password':w.hash_password(secrets.token_urlsafe(32)),
       'role':'basic','enabled':True,'max_devices':1,'can_use_prediction_map':True})
     w.USERS_JSON_PATH.write_text(json.dumps(raw,indent=2)+'\n')
    test_user_record()
    devices=w.read_devices(); assert device not in devices
    devices[device]={'username':username,'device_id':device,'enabled':'true','token_hash':w.token_hash(token),'user_agent':'prediction-map-local-acceptance'}
    w.write_devices(devices)
    start_date=os.environ.get('RAINMAPPER_MAP_CHECK_DATE',map_today().isoformat())
    report={'contract':CONTRACT_ID,'start_date':start_date,'checks':{},'queries':[]}
    def http(path,body=None,auth=True):
     headers={'Content-Type':'application/json'}
     if auth: headers.update({'Authorization':'Bearer '+token,'X-Rainmapper-Device':device})
     req=Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
     try:
      with urlopen(req,timeout=10) as r: raw=r.read();return r.status,json.loads(raw),len(raw)
     except HTTPError as e:
      raw=e.read();return e.code,json.loads(raw),len(raw)
    def payload(mode,point=None):
     return {'contract':CONTRACT_ID,'request_id':'check_'+secrets.token_hex(8),'point':point or {'lat':42.29077,'lon':1.53842},'start_date':start_date,'horizon_days':7,'history_days':60,'execution':mode,'calendar_timezone':'Europe/Madrid'}
    def submit(mode,point=None):
     p=payload(mode,point); start=time.monotonic(); status,accepted,n=http(API_PATH+'/queries',p);assert status==202,(status,accepted)
     return p,accepted,start
    def finish(p,accepted,start):
     deadline=time.monotonic()+110; polls=0; state_bytes=0
     while time.monotonic()<deadline:
      code,result,size=http(API_PATH+'/queries/'+accepted['query_id']); polls+=1
      if code==200:
       assert result['calendar_timezone']==p['calendar_timezone']
       report['queries'].append({'mode':p['execution'],'point':p['point'],'elapsed_ms':round((time.monotonic()-start)*1000,2),'compute_ms':result['execution']['compute_ms'],'polls':polls,'state_bytes':state_bytes,'result_bytes':size,'calculated_species':sum(any(v is not None for v in r['probabilities']) for r in result['species'])})
       return result
      assert code==202,(code,result)
      state_bytes+=size;time.sleep(.2)
     raise AssertionError('timeout')
    def query(mode,point=None):return finish(*submit(mode,point))
    def canonical(result):
     # These fields are measurement-only; scientific payload must match exactly.
     if isinstance(result,dict):return {k:canonical(v) for k,v in result.items() if k not in ('request_id','execution','lookup_ms','cache_hit','elapsed_ms')}
     if isinstance(result,list):return [canonical(v) for v in result]
     return result
    def differences(a,b,path=''):
     if type(a)!=type(b):return [path]
     if isinstance(a,dict):
      if a.keys()!=b.keys():return [path+':keys']
      return sum((differences(a[k],b[k],path+'/'+k) for k in a),[])
     if isinstance(a,list):
      if len(a)!=len(b):return [path+':length']
      return sum((differences(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
     return [] if a==b else [path]
    try:
     deadline=time.monotonic()+30
     while time.monotonic()<deadline:
      code,caps,_=http(API_PATH+'/capabilities')
      if code==200 and all(caps['executors'].values()):break
      time.sleep(.5)
     assert code==200 and caps['executors']=={'local':True,'worker':True},(code,caps)
     report['checks']['ready']=caps
     assert caps['admin_only'] is False
     report['checks']['basic_user_allowed']=True
     assert http(API_PATH+'/capabilities',auth=False)[0]==401
     report['checks']['unauthorized']=401
     invalid=payload('local');invalid['point']['lat']=999
     assert http(API_PATH+'/queries',invalid)[0]==400
     report['checks']['invalid_coordinate']=400
     results={m:query(m) for m in ('local','worker')}
     report['differences']=differences(canonical(results['local']),canonical(results['worker']))
     assert not report['differences'],report['differences']
     # An available model may abstain; null probabilities remain valid.
     assert report['queries'][0]['calculated_species']>0
     report['checks']['initial_parity']=True
     for mode in ('local','worker'):
      r=query(mode);assert canonical(r)==canonical(results[mode]);report['checks'][mode+'_warm_parity']=True
     # Both executors active at once, one request each.
     requests=[submit(m,{'lat':42.02466,'lon':1.77189}) for m in ('local','worker')]
     paired=[finish(*x) for x in requests];assert canonical(paired[0])==canonical(paired[1])
     report['checks']['concurrent_parity']=True
     for mode in ('local','worker'):
      p,a,t=submit(mode)
      code,r,_=http(API_PATH+'/queries/'+a['query_id']+'/cancel',{})
      assert code==200 and r['state'] in ('cancelled','complete')
      if r['state']=='cancelled': assert http(API_PATH+'/queries/'+a['query_id'])[0]==409
      report['checks'][mode+'_cancel']=r['state']
     report['scientific_provenance']=results['local']['provenance']
     report['species']=results['local']['species']
     report['ok']=True
    finally:
     current=w.read_devices();current.pop(device,None);w.write_devices(current)
     report['temporary_test_device_removed']=device not in w.read_devices()
     test_user_record(remove=True)
     print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == "__main__":
    main()
