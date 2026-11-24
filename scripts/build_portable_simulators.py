"""Build the installable static app from the existing simulator templates/engines.

Run after changing either simulator. --check fails when committed output is stale.
No server, AI API, CDN, new hosting service, or student data is required at runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'app/static/simulators'


def build():
    env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape(['html']))
    result = {}
    for filename, template, kind, title in [
        ('index.html', 'portable_simulator_home.html', 'home', 'Golf Simulators'),
        ('flight.html', 'ball_flight_simulator.html', 'flight', 'Ball Flight'),
        ('d-plane.html', 'd_plane_lab.html', 'd-plane', 'D-Plane'),
    ]:
        html = env.get_template(template).render(simulator_base='portable_simulator_base.html', portable=True, simulator=kind, page_title=title)
        html = '\n'.join(line.rstrip() for line in html.splitlines()) + '\n'
        for original in re.findall(r'/static/(?:js|css)/[\w.]+(?:\?[^"\s]+)?', html):
            path = original.split('?')[0]
            asset = 'assets/' + path.rsplit('/', 1)[1]
            result[asset] = (ROOT / 'app' / path.lstrip('/')).read_bytes()
            html = html.replace(original, './' + asset)
        result[filename] = html.encode()
    result['app.css'] = (ROOT / 'app/static/css/portable_simulators.css').read_bytes()
    result['app.js'] = (ROOT / 'app/static/js/portable_simulators.js').read_bytes()
    for size in (180, 192, 512):
        result[f'icon-{size}.png'] = (ROOT / f'app/static/img/simulator-icon-{size}.png').read_bytes()
    result['icon.svg'] = (ROOT / 'app/static/img/simulator-icon.svg').read_bytes()
    result['manifest.webmanifest'] = (json.dumps({
        'id': './', 'name': 'WSBCO Golf Simulators', 'short_name': 'Golf Simulators',
        'description': 'Ball flight and D-plane teaching tools for the range.',
        'start_url': './index.html', 'scope': './', 'display': 'standalone',
        'background_color': '#f1f5f2', 'theme_color': '#153f35', 'lang': 'en',
        'icons': [{'src': f'./icon-{size}.png', 'sizes': f'{size}x{size}', 'type': 'image/png', 'purpose': 'any maskable'} for size in (192, 512)],
        'shortcuts': [{'name': 'Ball Flight', 'url': './flight.html'}, {'name': 'D-Plane', 'url': './d-plane.html'}],
    }, indent=2) + '\n').encode()
    digest = hashlib.sha256()
    for name, data in sorted(result.items()):
        digest.update(name.encode()); digest.update(data)
    worker = (ROOT / 'scripts/simulator_service_worker.js').read_text()
    worker = worker.replace("__VERSION__", digest.hexdigest()[:16]).replace('__FILES__', json.dumps(sorted(result)))
    result['sw.js'] = worker.encode()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = build()
    if args.check:
        actual = {str(p.relative_to(OUT)): p.read_bytes() for p in OUT.rglob('*') if p.is_file()}
        if actual != files:
            raise SystemExit('Portable simulator output is stale. Run python scripts/build_portable_simulators.py')
        print('Portable simulator output is current.')
    else:
        # Only generated app files live here; remove stale generated assets.
        OUT.mkdir(parents=True, exist_ok=True)
        for path in OUT.rglob('*'):
            if path.is_file() and str(path.relative_to(OUT)) not in files:
                path.unlink()
        for name, data in files.items():
            path = OUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(f'Built {len(files)} files, {sum(map(len, files.values())):,} bytes.')
