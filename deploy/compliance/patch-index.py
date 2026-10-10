"""Patch only the production baseline HTML shell; leave business bundles unchanged."""
from pathlib import Path
import sys


def patch(source, footer):
    if 'singux-site-filing' in source:
        raise ValueError('Filing footer already present; review instead of duplicate')
    if source.count('</head>') != 1 or source.count('</body>') != 1:
        raise ValueError('Unexpected HTML shell')
    return source.replace('</head>', '<link rel="stylesheet" href="/singux-filing-20261009.css"></head>').replace('</body>', footer + '</body>')


if __name__ == '__main__':
    target = Path(sys.argv[1])
    target.write_text(patch(target.read_text(encoding='utf-8'), Path(sys.argv[2]).read_text(encoding='utf-8')), encoding='utf-8')
