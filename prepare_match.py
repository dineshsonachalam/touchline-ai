#!/usr/bin/env python3
"""Convert Metrica Sports Sample Game 1 tracking CSVs to Touchline AI JSON.

Uses only Python standard library. The patterns are computed heuristics, not LLM claims.
Sample data source: https://github.com/metrica-sports/sample-data
"""
import argparse,csv,json,math,statistics
from pathlib import Path


def read_tracking(path):
    """Read Metrica's three-row header and normalized (0..1) X/Y positions."""
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        try:
            next(reader)  # Team name row
            next(reader)  # Shirt number row
            labels = next(reader)  # Player11, blank, Player1, blank, ... Ball
        except StopIteration:
            raise ValueError(f'CSV has fewer than three header rows: {path}')

        player_cols = [(i, i + 1) for i, label in enumerate(labels)
                       if label.strip().lower().startswith('player')]
        ball_cols = next(((i, i + 1) for i, label in enumerate(labels)
                          if label.strip().lower() == 'ball'), None)
        if len(player_cols) < 11 or ball_cols is None:
            raise ValueError(f'Invalid Metrica header in {path}: '
                             f'{len(player_cols)} players, ball={ball_cols is not None}')

        def xy(row, columns):
            try:
                x, y = float(row[columns[0]]), float(row[columns[1]])
                if math.isfinite(x) and math.isfinite(y):
                    return [round(x * 105, 2), round(y * 68, 2)]
            except (ValueError, IndexError):
                pass
            return None

        frames = []
        # Only the first 11 columns are the starting players. Later columns
        # can represent substitutes; we retain 11 stable display slots.
        previous = [None] * 11
        previous_ball = [52.5, 34.0]
        for row in reader:
            try:
                t = float(row[2])  # 'Time [s]' is the THIRD column
                if not math.isfinite(t):
                    continue
            except (ValueError, IndexError):
                continue
            players = []
            for i, columns in enumerate(player_cols[:11]):
                position = xy(row, columns)
                if position is None:
                    position = previous[i] if previous[i] is not None else [52.5, 34.0]
                previous[i] = position
                players.append(position)
            ball = xy(row, ball_cols)
            if ball is None:
                ball = previous_ball
            previous_ball = ball
            frames.append({'t': round(t, 3), 'players': players, 'ball': ball})
    if not frames:
        raise ValueError(f'No tracking frames found in {path}')
    return frames


def detect(frames):
    """Find distinct high-line, flank concentration and central density windows.
    This is a deliberately simple, auditable heuristic based on tracked positions.
    It does not establish causality or goal probabilities.
    """
    candidates=[]
    for i in range(0,len(frames),20):
        f=frames[i];home=f['home'];away=f['away']
        if len(home)<11 or len(away)<11:continue
        # Attack direction isn't supplied reliably; we only report positional geometry.
        field=[p for p in away[1:] if p is not None]
        if not field:continue
        ys=[p[1] for p in field];xs=[p[0] for p in field]
        spread=statistics.pstdev(ys)
        meanx=statistics.mean(xs)
        highline=abs(meanx-52.5)/52.5
        wide=max(sum(y<22 for y in ys),sum(y>46 for y in ys))/len(ys)
        central=sum(22<y<46 and 37<x<68 for x,y in field)/len(field)
        candidates.append((f['t'],highline,wide,central,statistics.mean(ys),meanx))
    results=[]
    templates=[
      ('HIGH LINE','Opposition line pushed up','Opponent positioning is advanced toward one end.','highline',1),
      ('FLANK OVERLOAD','Opposition crowding a flank','Several opponents occupy the same wide channel.','overload',2),
      ('CENTRAL PRESS','Crowded central corridor','Opposition players are concentrated through the middle.','press',3),
    ]
    for title,sub,desc,typ,idx in templates:
        # Select strongest sustained ~30-second window, rather than a single frame.
        windows=[]
        for j in range(0,max(0,len(candidates)-6)):
            group=candidates[j:j+6]
            if group[-1][0]-group[0][0]>75:continue
            score=statistics.mean(row[idx] for row in group)
            windows.append((score,group[len(group)//2]))
        windows.sort(reverse=True,key=lambda v:v[0])
        pick=next((v for v in windows if all(abs(v[1][0]-r['time'])>180 for r in results)),None)
        if not pick:continue
        score,row=pick;t=row[0];mx=row[5];my=row[4]
        if typ=='highline':zone=[max(0,min(82,mx-7)),18,22,33];arrow=[[43,34],[min(100,mx+19),34]]
        elif typ=='overload':zone=[40,0 if my<34 else 44,34,24];arrow=[[40,34],[82,54 if my<34 else 12]]
        else:zone=[38,20,30,28];arrow=[[41,34],[78,55]]
        results.append({'time':round(t,1),'title':title,'subtitle':sub,'description':desc,'zone':zone,'arrow':arrow,'type':typ,'evidence':f'Positional heuristic, 30-second window · score {score:.2f} · verify visually'})
    return sorted(results,key=lambda r:r['time'])


def main():
    ap=argparse.ArgumentParser(description='Convert downloaded Metrica tracking CSVs to Touchline AI JSON')
    ap.add_argument('--home',required=True,help='Path to Sample_Game_1_RawTrackingData_Home_Team.csv')
    ap.add_argument('--away',required=True,help='Path to Sample_Game_1_RawTrackingData_Away_Team.csv')
    ap.add_argument('--output',default='public/data/match.json')
    ap.add_argument('--fps',type=float,default=2.0,help='Output sample rate (frames/second)')
    args=ap.parse_args()
    home=read_tracking(args.home);away=read_tracking(args.away)
    # Match by frame index; Metrica files are aligned frame-by-frame.
    n=min(len(home),len(away));step=max(1,round(25/args.fps))
    frames=[]
    for i in range(0,n,step):
        h,a=home[i],away[i]
        if abs(h['t']-a['t'])>.2:continue
        frames.append({'t':h['t'],'home':h['players'],'away':a['players'],'ball':h['ball']})
    if len(frames)<100:raise ValueError('Insufficient aligned tracking data')
    chapters=detect(frames)
    output={'kind':'tracking','duration':frames[-1]['t'],'frames':frames,'chapters':chapters,'source':'Metrica Sports sample-data; team identities anonymized','disclaimer':'Detection uses simple positional heuristics; what-if goal is illustrative'}
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,separators=(',',':')))
    print(f'Created {dest}: {len(frames)} frames, {len(chapters)} positional patterns, {dest.stat().st_size/1e6:.1f} MB')

if __name__=='__main__':main()
