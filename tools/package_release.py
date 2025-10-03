#!/usr/bin/env python3
import sys
import shutil
import hashlib
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
OUTPUT = ROOT / 'release'

try:
    sys.path.insert(0, str(ROOT))
    from plookingII.config.constants import APP_VERSION
except Exception:
    APP_VERSION = '0.0.0'


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], check: bool = True) -> int:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description='Package and (optionally) upload PlookingII release artifacts')
    parser.add_argument('--build', action='store_true', help='Run tools/build.py --package before packaging')
    parser.add_argument('--upload', action='store_true', help='Upload artifacts to GitHub Release (auto-create if missing)')
    parser.add_argument('--notes-file', default=str(ROOT / f'RELEASE_NOTES_v{APP_VERSION}.md'), help='Release notes file path')
    parser.add_argument('--dry-run', action='store_true', help='Do not perform network actions; print commands only')
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Optional build step
    if args.build:
        print('> Building app (tools/build.py --package) ...')
        _run([sys.executable, str(ROOT / 'tools' / 'build.py'), '--package'])

    artifacts = []
    app_dir = DIST / 'PlookingII.app'
    cli_dir = DIST / 'PlookingII'

    if app_dir.exists():
        zip_path = OUTPUT / f'PlookingII-{APP_VERSION}-macOS-app.zip'
        shutil.make_archive(str(zip_path).replace('.zip', ''), 'zip', str(app_dir))
        artifacts.append(zip_path)

    if cli_dir.exists():
        zip_path = OUTPUT / f'PlookingII-{APP_VERSION}-macOS-cli.zip'
        shutil.make_archive(str(zip_path).replace('.zip', ''), 'zip', str(cli_dir))
        artifacts.append(zip_path)

    # sha256
    for art in artifacts:
        sha_path = art.with_suffix(art.suffix + '.sha256')
        sha_path.write_text(f'{sha256sum(art)}  {art.name}\n', encoding='utf-8')
        print(f'Wrote {sha_path.name}: {sha_path.read_text().strip()}')

    if not artifacts:
        print('No artifacts found under dist/. Run tools/build.py --package first.')
        sys.exit(1)

    print('\nArtifacts:')
    for art in artifacts:
        print(' -', art)

    # Optional upload
    if args.upload:
        print('\n> Uploading artifacts to GitHub Release...')
        # Check gh availability
        try:
            _run(['gh', '--version'], check=True)
        except Exception:
            print('ERROR: GitHub CLI (gh) not found. Install from https://cli.github.com/')
            sys.exit(2)

        tag = f'v{APP_VERSION}'

        # Create release if missing
        rc = _run(['gh', 'release', 'view', tag], check=False)
        if rc != 0:
            print(f'> Creating release {tag} ...')
            notes_file = Path(args.notes_file)
            create_cmd = ['gh', 'release', 'create', tag, '--title', f'PlookingII {tag}']
            if notes_file.exists():
                create_cmd += ['--notes-file', str(notes_file)]
            else:
                create_cmd += ['--notes', f'Release {tag}']
            if args.dry_run:
                print('DRY RUN:', ' '.join(create_cmd))
            else:
                _run(create_cmd, check=True)

        # Upload artifacts
        upload_cmd = ['gh', 'release', 'upload', tag, '--clobber'] + [str(p) for p in artifacts]
        if args.dry_run:
            print('DRY RUN:', ' '.join(upload_cmd))
        else:
            _run(upload_cmd, check=True)


if __name__ == '__main__':
    main()
