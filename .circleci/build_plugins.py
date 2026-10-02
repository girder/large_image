#!/usr/bin/env python

import argparse
import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path


def build_plugins(
    plugins_dir: Path, max_workers: int = 8, rebuild: bool = False,
    extra: list[str] | None = None, dry_run: bool = False,
) -> None:
    build_dirs = []
    if extra:
        build_dirs += extra
    for line in subprocess.run(
        ['git', 'ls-tree', '-r', 'HEAD', '--name-only'], capture_output=True,
        text=True, check=True,
    ).stdout.splitlines():
        line = line.strip()
        if line.endswith('/package.json'):
            web_client_dir = Path(line).parent
            if web_client_dir.exists() and (web_client_dir / 'package.json').exists() and (
                    rebuild or (web_client_dir / 'package-lock.json').exists()):
                build_dirs.append(web_client_dir)
    if dry_run:
        print('Would process:')
        for dir in sorted([str(d) for d in build_dirs]):
            print(f'  {dir}')
        return
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(max_workers, len(build_dirs)),
    ) as executor:
        futures = {
            executor.submit(
                subprocess.run,
                ('npm ci' if not rebuild else
                 'rm -rf package-lock.json node_modules && npm install') +
                ' && SKIP_SOURCE_MAPS=true npm run build',
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                cwd=dir,
            ): dir for dir in build_dirs
        }
        for future in concurrent.futures.as_completed(futures):
            dir = futures[future]
            try:
                future.result()
                print(f'Build completed for {dir}')
            except subprocess.CalledProcessError as e:
                print(f'Build failed for {dir}: {e}', file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build web clients for girder plugins.')
    parser.add_argument(
        'plugins_dir', type=Path, help='Directory containing plugin directories.')
    parser.add_argument(
        '--workers', type=int, default=8, help='Number of worker threads (default: 8).')
    parser.add_argument(
        '--rebuild', action='store_true', default=False,
        help='Rebuild package-lock.json files and reinstall.')
    parser.add_argument(
        '--dry-run', '-n', action='store_true', default=False,
        help='Report what would be built.')
    parser.add_argument(
        '--extra', action='append',
        help='Additional directories to build; for example, use "." and '
        '"girder/web".')
    args = parser.parse_args()
    if str(os.environ.get('SKIP_BUILD_PLUGINS')).lower() not in {'1', 'true'}:
        build_plugins(args.plugins_dir, args.workers, args.rebuild, args.extra, args.dry_run)
