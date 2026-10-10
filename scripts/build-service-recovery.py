"""Compile a bounded single-tenant recovery image from the previous verified hotfix."""
import copy
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND = Path('D:/singuxplatform/nuwax-backend')
BASE = ROOT / 'outputs/knowledge-hotfix-20261007'
OUT = ROOT / 'outputs/service-recovery-20261008'
IMAGE = 'singux/backend:1.1.10-20261008-service-recovery-r1'
PATCHES = {
    'app-platform-log-infra': ('app-platform-modules/app-platform-log/app-platform-log-infra', 'com/xspaceagi/search/infra/elasticsearch/ElasticsearchServiceImpl'),
    'app-platform-knowledge-core-domain': ('app-platform-modules/app-platform-knowledge/app-platform-knowledge-core-domain', 'com/xspaceagi/knowledge/domain/service/impl/KnowledgeDocumentDomainService'),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    global OUT, IMAGE
    parser = argparse.ArgumentParser()
    parser.add_argument('--with-mcp', action='store_true')
    args = parser.parse_args()
    if args.with_mcp:
        OUT = ROOT / 'outputs/service-recovery-mcp-20261009'
        IMAGE = 'singux/backend:1.1.10-20261009-service-recovery-mcp-r1'
        PATCHES['app-platform-mcp-application'] = (
            'app-platform-modules/app-platform-mcp/app-platform-mcp-application',
            'com/xspaceagi/mcp/application/service/McpDeployTaskServiceImpl')
    runtime, libs, classes = (OUT / name for name in ('runtime', 'compile-libs', 'classes'))
    for directory in (runtime, libs, classes):
        directory.mkdir(parents=True, exist_ok=True)
    baseline = BASE / 'runtime/app.jar'
    metadata = json.loads((BASE / 'release.json').read_text())
    assert sha(baseline.read_bytes()) == metadata['patchedJarSha256'], 'Previous hotfix checksum mismatch'
    jdk = Path('C:/Program Files/Java/jdk-20/bin')
    lombok = Path.home() / '.m2/repository/org/projectlombok/lombok/1.18.36/lombok-1.18.36.jar'
    with zipfile.ZipFile(baseline) as old:
        for name in old.namelist():
            if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                (libs / Path(name).name).write_bytes(old.read(name))
        sources = [BACKEND / folder / 'src/main/java' / (prefix + '.java') for folder, prefix in PATCHES.values()]
        subprocess.run([str(jdk / 'javac.exe'), '--release', '17', '-encoding', 'UTF-8', '-cp', str(libs / '*') + ';' + str(lombok),
                        '-processorpath', str(lombok), '-d', str(classes), *map(str, sources)], check=True)
        replacements, changed = {}, []
        for module, (_, prefix) in PATCHES.items():
            names = [name for name in old.namelist() if name.startswith('BOOT-INF/lib/' + module + '-') and name.endswith('.jar')]
            assert len(names) == 1, names
            module_name = names[0]
            class_name = prefix.replace('/', '.')
            before = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', str(libs / '*'), class_name])
            after = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', str(classes) + ';' + str(libs / '*'), class_name])
            assert before == after, 'Public API changed: ' + class_name
            generated = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('*.class')
                         if p.relative_to(classes).as_posix() == prefix + '.class' or p.relative_to(classes).as_posix().startswith(prefix + '$')}
            buffer = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(old.read(module_name))) as module_zip, zipfile.ZipFile(buffer, 'w') as patched:
                for item in module_zip.infolist():
                    if item.filename in generated:
                        patched.writestr(copy.copy(item), generated.pop(item.filename))
                        changed.append(module_name + '!/' + item.filename)
                    elif not (item.filename.startswith(prefix + '$') and item.filename.endswith('.class')):
                        patched.writestr(copy.copy(item), module_zip.read(item))
                for name, data in generated.items():
                    patched.writestr(name, data)
                    changed.append(module_name + '!/' + name)
            replacements[module_name] = buffer.getvalue()
        with zipfile.ZipFile(runtime / 'app.jar', 'w') as patched:
            for item in old.infolist():
                patched.writestr(copy.copy(item), replacements.get(item.filename, old.read(item)))
        with zipfile.ZipFile(runtime / 'app.jar') as patched:
            assert old.namelist() == patched.namelist()
            assert all(old.read(name) == patched.read(name) for name in old.namelist() if name not in replacements)
        (runtime / 'Dockerfile').write_text(
            'FROM singux/backend:1.1.10-20261007-knowledge-singletenant-r1\n'
            'COPY --chown=app:app app.jar /app/app.jar\n'
            f'LABEL org.opencontainers.image.version="{IMAGE.split(":", 1)[1]}"\n', encoding='ascii')
        report = {'image': IMAGE, 'schemaUnchanged': True, 'productionApproved': False,
                  'baselineJarSha256': sha(baseline.read_bytes()), 'patchedJarSha256': sha((runtime / 'app.jar').read_bytes()),
                  'changedClasses': changed, 'unchangedExecutableEntries': len(old.namelist()) - len(replacements),
                  'sourceSha256': {str(p): sha(p.read_bytes()) for p in sources},
                  'pending': ['Approved working Q&A model configuration',
                              'Computer runner image and complete sandbox integration', 'Image proxy 403 request tracing']}
        (OUT / 'release.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        subprocess.run(['docker', 'build', '--pull=false', '-t', IMAGE, str(runtime)], check=True)
        print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
