"""Download and verify the frozen numerical evidence for this repository."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
RELEASE_URL = ('https://github.com/galahad3723-blip/certified-network-optimisation/'
               'releases/download/v1.0.0/Certified_Network_Optimisation_Data.zip')
ARCHIVE_SHA256 = 'e558f2538b283e7283a78be81c3caeb133c58ca52930fec832830607cf42b99a'
PREFIX = 'Certified_Network_Optimisation_Data/'
OBSERVATIONS = ('results/', 'dis_extension/results/', 'dis_extension/transfer_results/')


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_archive(path):
    if digest_file(path) != ARCHIVE_SHA256:
        raise ValueError('Archive SHA256 differs from the published frozen snapshot.')
    with zipfile.ZipFile(path) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths.')
        manifest = bundle.read(PREFIX + 'SHA256SUMS.txt').decode('utf-8')
        expected_names = {PREFIX + 'SHA256SUMS.txt'}
        verified = 0
        for line in manifest.splitlines():
            expected, relative = line.split('  ', 1)
            relative_path = PurePosixPath(relative)
            if relative_path.is_absolute() or '..' in relative_path.parts:
                raise ValueError('Unsafe archive path.')
            name = PREFIX + relative
            if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                raise ValueError('File digest differs: ' + relative)
            expected_names.add(name)
            verified += 1
        if set(names) != expected_names:
            raise ValueError('The manifest does not cover all archive files.')
        return verified


def install_observations(path):
    planned = []
    with zipfile.ZipFile(path) as bundle:
        for name in bundle.namelist():
            relative = name.removeprefix(PREFIX)
            if not relative.startswith(OBSERVATIONS):
                continue
            target = ROOT.joinpath(*PurePosixPath(relative).parts)
            data = bundle.read(name)
            if target.exists():
                if not target.is_file() or target.read_bytes() != data:
                    raise FileExistsError('Existing observations differ; use a fresh checkout: ' + relative)
                continue
            planned.append((target, data))
        # Check every existing target before writing any new observation.
        for target, data in planned:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.download-tmp')
            with temporary.open('xb') as output:
                output.write(data)
            temporary.replace(target)
    return len(planned)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use an already downloaded release ZIP.')
    parser.add_argument('--verify-only', action='store_true', help='Verify without installing observations.')
    args = parser.parse_args()
    archive = args.archive
    if archive is None:
        cache = ROOT / '.data-cache'
        cache.mkdir(exist_ok=True)
        archive = cache / 'Certified_Network_Optimisation_Data.zip'
        if not archive.exists():
            temporary = archive.with_suffix('.zip.part')
            request = urllib.request.Request(RELEASE_URL, headers={'User-Agent':'certified-network-optimisation'})
            with urllib.request.urlopen(request, timeout=90) as source, temporary.open('xb') as output:
                shutil.copyfileobj(source, output)
            if digest_file(temporary) != ARCHIVE_SHA256:
                temporary.unlink()
                raise ValueError('Downloaded archive failed its SHA256 check.')
            temporary.replace(archive)
    verified = verify_archive(archive)
    added = 0 if args.verify_only else install_observations(archive)
    print(json.dumps({'verified_manifest_entries':verified,'installed_observation_files':added,
                      'archive_sha256':ARCHIVE_SHA256}, indent=2))


if __name__ == '__main__':
    main()
