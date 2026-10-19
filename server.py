#!/usr/bin/env python3
"""Touchline AI: full-match scan, measured evidence, Azure tactical assessment."""
import json, os, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import certifi, httpx
from openai import OpenAI
from scanner import scan

ROOT=Path(__file__).parent
CACHE=None
LOCK=threading.Lock()

def azure_client():
    endpoint=os.environ.get('AZURE_OPENAI_ENDPOINT','').strip().rstrip('/')
    key=os.environ.get('AZURE_OPENAI_API_KEY','').strip()
    if not endpoint or not key:raise RuntimeError('Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY (same as working app.py).')
    if not endpoint.endswith('/openai/v1'):
        endpoint += '/v1' if endpoint.endswith('/openai') else '/openai/v1'
    return OpenAI(base_url=endpoint+'/',api_key=key,http_client=httpx.Client(verify=certifi.where(),timeout=50),max_retries=1)

def get_candidates():
    global CACHE
    with LOCK:
        if CACHE is None:
            data=json.loads((ROOT/'public/data/match.json').read_text())
            CACHE=[item for item in scan(data['frames'],100) if item['team']=='HOME'][:12]
    return CACHE

def evaluate(items):
    deployment=os.environ.get('AZURE_OPENAI_DEPLOYMENT','gpt-5-mini')
    evidence=[{'id':x['id'],'time':round(x['time'],1),'team':x['team'],'ball_carrier':x['from_player'],
      'proposed_receiver':x['action']['to_player'],'forward_gain_m':x['action']['progress_m'],
      'passing_lane_clearance_m':x['action']['lane_clearance_m'],
      'receiver_defender_distance_m':x['action']['receiver_space_m'],
      'actual_ball_progress_next_4s_m':x['actual_progress_m']} for x in items]
    system=('You are a football tactical analyst. Review measured candidate moments from synthetic football-realistic tracking data. '
      'All candidates are for HOME (fictional Argentina against fictional Spain). Pick exactly three distinct candidate IDs ranked by the strongest plausible attacking opportunity. '
      'Use only evidence supplied. Never claim a goal was scored, that the alternative would succeed, or that actual play was definitely a mistake. '
      'Return ONLY JSON: {"top_three":[{"id":"...","headline":"short title","reason":"one sentence explaining the measured tactical tradeoff"},...]}. '
      'Every ID must come from the input; avoid invented numbers.')
    # GPT-5-mini may spend the entire completion budget on reasoning,
    # leaving message.content empty. Request JSON explicitly and allow enough tokens.
    with azure_client() as client:
        response=client.chat.completions.create(
            model=deployment,
            messages=[{'role':'system','content':system},
                      {'role':'user','content':json.dumps(evidence)}],
            response_format={'type':'json_object'},
            max_completion_tokens=6000,
        )
    choice=response.choices[0]
    content=(choice.message.content or '').strip()
    if not content:
        raise RuntimeError(
            f'Azure returned an empty answer (finish_reason={choice.finish_reason}). '
            'The model may have exhausted its completion-token budget.'
        )
    if content.startswith('```'):
        content=re.sub(r'^```(?:json)?\s*|\s*```$', '', content).strip()
    try:
        parsed=json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'Azure returned malformed JSON: {content[:350]}') from exc
    if not isinstance(parsed,dict) or not isinstance(parsed.get('top_three'),list):
        raise RuntimeError(f'Azure response is missing top_three: {content[:350]}')
    valid={x['id']:x for x in items}; selected=[]
    for choice in parsed.get('top_three',[]):
        if not isinstance(choice,dict):continue
        id_=choice.get('id')
        if id_ not in valid or id_ in [x['id'] for x in selected]:continue
        x=valid[id_]
        selected.append({**x,'headline':str(choice.get('headline') or 'Potential attacking option')[:75],
          'reason':str(choice.get('reason') or 'A forward passing option was available.')[:240]})
        if len(selected)==3:break
    if len(selected)!=3:raise RuntimeError('Azure did not select three valid moments. Retry the scan.')
    return selected

class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,payload):
        raw=json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/health':return self.send_json(200,{'ok':True,'deployment':os.environ.get('AZURE_OPENAI_DEPLOYMENT','gpt-5-mini')})
        self.send_json(404,{'error':'Not found'})
    def do_POST(self):
        if self.path!='/api/scan':return self.send_json(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>1000:raise ValueError('Request too large')
            if size:self.rfile.read(size)
            items=get_candidates()
            if len(items)<3:return self.send_json(422,{'error':'Insufficient reliable candidate moments in this match.'})
            selected=evaluate(items)
            self.send_json(200,{'status':'READY','opportunities':selected,'scanned_frames':len(json.loads((ROOT/'public/data/match.json').read_text())['frames']),
              'note':'Synthetic football match; ranked potential attacking options, not verified missed goals or simulated outcomes.'})
        except Exception as exc:
            print(f'ERROR /api/scan: {type(exc).__name__}: {exc}', flush=True)
            self.send_json(502,{'error':str(exc)})

if __name__=='__main__':
    port=int(os.environ.get('PORT','8000'))
    print(f'Touchline AI listening on 0.0.0.0:{port}')
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
