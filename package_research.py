"""Package sources and evidence while excluding previous studies and QA caches."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent


def main():
    output=ROOT/'deliverables'
    output.mkdir(exist_ok=True)
    files=[]
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        relative=path.relative_to(ROOT)
        if relative.parts[0] in {'baseline','deliverables','tmp','rendered','qa'}:
            continue
        if '__pycache__' in relative.parts or path.suffix=='.pyc' or relative.name=='theory_validation_log.json':
            continue
        if relative.name in {'SHA256SUMS.txt','render_equations.cjs','package.json'}:
            continue
        files.append(path)
    files.sort()
    lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in files]
    manuscripts=[output/name for name in ['Certified_NUM_Research.md','DIS_Study.md']
                 if (output/name).exists()]
    for manuscript in manuscripts:
        lines.append(hashlib.sha256(manuscript.read_bytes()).hexdigest()+'  manuscript/'+manuscript.name)
    manifest=ROOT/'SHA256SUMS.txt'
    manifest.write_text('\n'.join(lines)+'\n')
    files.append(manifest)
    archive=output/'Certified_NUM_Code_and_Data.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for p in files:
            bundle.write(p,Path('Certified_NUM_Research')/p.relative_to(ROOT))
        for manuscript in manuscripts:
            bundle.write(manuscript,Path('Certified_NUM_Research')/'manuscript'/manuscript.name)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
    print(json.dumps({'archive':str(archive),'files':len(files)+len(manuscripts),'bytes':archive.stat().st_size,
                      'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':
    main()
