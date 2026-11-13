#!/usr/bin/env python3
"""Builds prices/moves-<game>.json: each card's price 1, 7 and 30 days ago, from the daily price lists already saved in this
repo's history (prices/<game>.json is committed every day). The app's Set charts use it for biggest risers and fallers.

  { updated, days: { "1": "YYYY-MM-DD", "7": ..., "30": ... }, p: { productId: [price 1 day ago, 7 days ago, 30 days ago] } }

Only cards worth 50 cents or more today are kept, and only when one of the old prices differs. A window with no saved
list that far back is left out (the 30-day one uses the oldest list there is once it's at least two weeks old)."""
import datetime, json, os, subprocess, sys, time

GAMES = ['pokemon', 'pokemon-jp', 'onepiece']
WINDOWS = [1, 7, 30]
MIN_PRICE = 0.5
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'prices')


def git(*args):
    r = subprocess.run(['git', *args], capture_output=True, text=True, cwd=os.path.join(OUT, '..'))
    return r.stdout.strip() if r.returncode == 0 else ''


def commits(path):
    """[(date, sha)] newest first, for every commit that changed this file."""
    out = []
    for line in git('log', '--format=%H %cI', '--', path).splitlines():
        sha, when = line.split(' ', 1)
        out.append((datetime.datetime.fromisoformat(when.replace('Z', '+00:00')), sha))
    return out


def old_list(sha, path):
    raw = git('show', f'{sha}:{path}')
    try:
        return json.loads(raw).get('p') or {}
    except Exception:
        return None


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    for game in GAMES:
        path = f'prices/{game}.json'
        try:
            cur = json.load(open(os.path.join(OUT, f'{game}.json')))['p']
        except Exception as e:
            print(f'{game}: no current list ({e})', file=sys.stderr); continue
        hist = commits(path)
        if not hist:
            print(f'{game}: no history', file=sys.stderr); continue
        # today's list may already be committed (run after the daily commit) or not yet (run before it)
        newest_day = hist[0][0].date()
        days, olds = {}, []
        for w in WINDOWS:
            target = now - datetime.timedelta(days=w)
            pick = next(((d, s) for d, s in hist if d <= target + datetime.timedelta(hours=6)), None)
            if pick is None and w == 30 and hist and (now - hist[-1][0]).days >= 14:
                pick = hist[-1]
            if pick is None:
                olds.append(None); continue
            lst = old_list(pick[1], path)
            if lst is None:
                olds.append(None); continue
            days[str(w)] = pick[0].date().isoformat()
            olds.append(lst)
        p = {}
        for pid, e in cur.items():
            now_price = e[0]
            if now_price is None or now_price < MIN_PRICE:
                continue
            row, differs = [], False
            for lst in olds:
                v = lst.get(pid) if lst else None
                v = v[0] if v else None
                row.append(v)
                if v is not None and abs(v - now_price) >= 0.01:
                    differs = True
            if differs:
                p[pid] = row
        data = {'updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'days': days, 'p': p}
        with open(os.path.join(OUT, f'moves-{game}.json'), 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        print(f'{game}: {len(p)} cards moved · windows {days} · newest saved list {newest_day}')


if __name__ == '__main__':
    main()
