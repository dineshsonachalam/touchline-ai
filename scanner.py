"""Evidence-first whole-match candidate scanner. Never predicts a goal."""
import json, math
from pathlib import Path

DATA = Path(__file__).parent / 'public/data/match.json'

def distance(a,b): return math.dist(a,b)
def clearance(a,b,defenders):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    if den < 1: return 0
    gaps=[]
    for p in defenders[1:]:
        u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den
        if .1<u<.9: gaps.append(distance(p,(a[0]+u*dx,a[1]+u*dy)))
    return min(gaps,default=25)

def scan(frames, max_results=12):
    possible=[]
    # Samples are ~0.48 seconds apart; skip to ~3 second intervals.
    for k in range(10,len(frames)-18,6):
        f=frames[k]; ball=f['ball']
        if not all(isinstance(ball[i],(int,float)) and math.isfinite(ball[i]) for i in (0,1)):continue
        near=[]
        for team in ('home','away'):
            for idx,p in enumerate(f[team]):
                if idx:near.append((distance(ball,p),team,idx))
        near.sort()
        if len(near)<2 or near[0][0]>2.4 or near[1][0]-near[0][0]<.6:continue
        _,team,carrier=near[0]; own=f[team]; opp=f['away' if team=='home' else 'home']
        # Approximate attacking direction from goalkeeper's horizontal position.
        direction=1 if own[0][0]<52.5 else -1
        origin=own[carrier]; progress=origin[0] if direction==1 else 105-origin[0]
        if progress<48 or progress>95:continue
        goal=(105 if direction==1 else 0,34)
        options=[]
        for j,target in enumerate(own):
            if j in (0,carrier):continue
            pass_len=distance(origin,target)
            gain=(target[0]-origin[0])*direction
            if not 5<=pass_len<=38 or gain<6:continue
            gap=clearance(origin,target,opp)
            space=min(distance(target,d) for d in opp[1:])
            if gap<3.0 or space<3.0:continue
            dist_goal=distance(target,goal)
            if dist_goal>47:continue
            # Rank is a heuristic, not an expected-goals model.
            score=2.0*gain + 2.4*min(space,14) + 1.8*min(gap,12) - .55*pass_len - .4*dist_goal
            options.append({'to_index':j,'to_player':f'{team.upper()}_{j+1}','to':target,'distance_m':round(pass_len,1),'lane_clearance_m':round(gap,1),'receiver_space_m':round(space,1),'progress_m':round(gain,1),'score':round(score,2)})
        if not options:continue
        options.sort(key=lambda v:v['score'],reverse=True)
        best=options[0]
        # Look ahead ~4 seconds for a ball trajectory that differs from the alternative.
        future=frames[min(k+8,len(frames)-1)]['ball']
        actual_progress=(future[0]-ball[0])*direction
        if distance(future,best['to'])<5:continue # not obviously missed
        if actual_progress>best['progress_m']+5:continue
        possible.append({'id':f'frame-{k}','frame_index':k,'time':f['t'],'team':team.upper(),
          'carrier_index':carrier,'from_player':f'{team.upper()}_{carrier+1}', 'from':origin,
          'action':best,'other_options':options[1:3], 'score':best['score'],
          'actual_ball_after_4s':future, 'actual_progress_m':round(actual_progress,1),
          'attack_direction':direction})
    possible.sort(key=lambda x:x['score'],reverse=True)
    unique=[]
    for item in possible:
        if any(abs(item['time']-p['time'])<24 for p in unique):continue
        unique.append(item)
        if len(unique)>=max_results:break
    return unique

if __name__=='__main__':
    data=json.loads(DATA.read_text())
    items=scan(data['frames'])
    for x in items:print(round(x['time'],1),x['team'],x['from_player'],'->',x['action']['to_player'],x['score'])
