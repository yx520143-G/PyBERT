"""Compare rendered history against saved originals; no engine/helper/COM calls."""
import hashlib
import json
import shutil
import socket
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

root=Path.cwd(); evidence=root/'docs/webui/issue4/evidence'; out=evidence/'com-history-p2'; ui=root/'output/playwright/com-history-p2'
target=out/'report-v1.json'; assert not target.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def cli(name):
    text=(ui/name).read_text(encoding='utf-8');value=json.loads(text.split('### Result',1)[1].split('### Ran',1)[0].strip());return json.loads(value) if isinstance(value,str) and value.startswith('{') else value
checks=[]
def check(name,good):checks.append(dict(check=name,passed=bool(good)))
snapshot=read(evidence/'chrome-20261024/final-idle.json');tasks={t['task_id']:t for t in snapshot['state']['com_tasks']}
def verify(row):
    task=tasks[row['id']]; directory=evidence/'chrome-20261024'/row['id']
    path=directory/('com.json' if task['state']=='succeeded' else 'com-input.json')
    if path.exists():
        original=read(path)
        expected=dict(com_id=original['com_id'],parameter_source=original['parameter_source']['kind'],parameters_sha256=original['parameter_source']['parameters_sha256'],**{k:original[k] for k in ['versions','adapter_sha','source_hashes','helper','parameter_schema']})
        check(row['id']+' actual recorded identity/versions/source hashes',row['identity']==expected)
        check(row['id']+' full actual parameters',row['parameters']==original['parameter_source']['parameters'])
    else:
        check(row['id']+' absent source explicitly unavailable',isinstance(row['identity'],str) and '未生成' in row['identity'] and isinstance(row['parameters'],str) and '未记录' in row['parameters'])
    check(row['id']+' own historical task logs',row['logs']==('\n'.join(task['logs']) if task['logs'] else '该任务无保存日志。'))
    if row.get('error') is not None:check(row['id']+' original traceback',row['error']==task['traceback'])
for name in ['03-out-of-order-and-poll.txt','17-audited-out-of-order.txt']:
    result=cli(name)
    for row in result['values']:verify(row)
    check(name+' completion order reversed',result['completed'][:2]==['c922f333-2a39-4fe3-abd0-5793c9bba535','e6e6867a-a976-4e47-a7bd-ee53767a2f9e'])
    stable=result['stable'];check(name+' preserved open DOM/scroll across poll',all(stable[k] for k in ['open','same_row','same_identity','same_logs']) and stable['identity_scroll_top']==40)
for name in ['08-cancel-and-retry.txt','18-audited-cancel-and-retry.txt']:
    result=cli(name)
    for row in result['cancelled']:
        verify(row);check(row['id']+' no cancelled value publication','cancelled' in row['summary'] and 'dB' not in row['summary'])
    verify(result['recovered'])
    check(name+' explicit read failure with retry only',result['injected_failure']['identity_count']==0 and '来源记录读取失败' in result['injected_failure']['message'] and result['GET_count']==2)
switched=cli('13-after-core-switch.txt')
check('later normalization current task and core switch keep COM history independent',switched['current_task'].startswith('normalize ') and switched['selected_run']=='c3cadfdc-13e8-4ed9-bee3-b3b11462cd96')
for row in switched['values']:verify(row);check(row['id']+' remains expanded after selected core change',row['open']=='')
environment=cli('15-environment.txt');check('actual Chrome1280x720 scale1','Chrome/' in environment['ua'] and [environment['width'],environment['height'],environment['dpr']]==[1280,720,1])
audit=read(ui/'19-server-audit-v2.json')
check('request audit: no calculation submits/workers/main/COM',audit['active_task_id'] is None and audit['main_simulations']==audit['COM_calls']==audit['workers']==0 and all(r['method']=='GET' or r['method']=='POST' and r['path']=='/api/normalize' for r in audit['requests']))
gets=[r['path'] for r in audit['requests'] if r['path'].startswith('/api/com/')]
check('only five terminal metadata GETs, no repeat from state polling',len(gets)==len(set(gets))==5)
freeze=read(out/'before-review-v1.json')
for path,expected in freeze['source_hashes'].items():
    if path!='tools/serve_web_com_history_review.py':check(path+' Chrome frozen source unchanged',sha(root/path)==expected)
correction=read(out/'harness-correction-v2.json');check('corrected read-only audit harness pinned',sha(root/'tools/serve_web_com_history_review.py')==correction['helper_sha256'])
parent=read(evidence/'delivery-index-v1.json');check('all270 parent artifact bytes preserved before README revision',len(parent['files'])==270 and all(sha(root/row['path'])==row['sha256'] for row in parent['files']))
raw=read(evidence/'delivery-source-and-cost-v1.json')['raw_files'];check('all52 original raw bytes preserved',len(raw)==52 and all(sha(root/row['path'])==row['sha256'] for row in raw))
suite=ET.parse(evidence/'com-history-p2-tests-v1.xml').getroot().find('testsuite');check('seven actual-artifact API contracts pass',suite.get('tests')=='7' and suite.get('failures')==suite.get('errors')==suite.get('skipped')=='0')
ports={}
for port in [8767,8768,8769]:
    with socket.socket() as connection:connection.settimeout(1);ports[str(port)]=connection.connect_ex(('127.0.0.1',port))!=0
check('all own review/production ports closed',all(ports.values()))
copy=out/'ui';copy.mkdir(exist_ok=False)
for path in ui.iterdir():
    if path.is_file():shutil.copyfile(path,copy/path.name)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
report=dict(implementation_cut=head,parent_head='f15b27e8291cdf55d6f5c5aea78621a62a5ee2c8',source_hashes={p:sha(root/p) for p in freeze['source_hashes']},checks=checks,passed=all(c['passed'] for c in checks),screenshots_pixels_inspected=['04-success-identity.png','05-success-old-logs.png','06-failed-source-missing.png','09-cancelled-saved-input.png','10-early-cancel-no-source.png','14-linked-com-after-core-switch.png','19-audited-history.png'],read_only_request_audit=audit,initial_harness_failure=correction,source_applicability='only COM GET saved-record payload and resources.js history display changed; numeric producer/task orchestration untouched, prior raw/COM evidence reused; seven new read-only API contracts plus actual saved-data Chrome checks',no_main_simulation_or_COM_rerun=True,ports_closed=ports,default_COM='BLOCKED_BUDGET / NOT_EXECUTED',CI='no CI checks/statuses claimed')
target.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(report=str(target),sha256=sha(target),checks=len(checks),passed=report['passed'],failed=[r['check'] for r in checks if not r['passed']])))
if not report['passed']:raise SystemExit(1)
