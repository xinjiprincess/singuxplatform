"""Assemble a schema-unchanged hotfix from the verified production executable JAR."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'com/xspaceagi/search/infra/elasticsearch/ElasticsearchServiceImpl.class'
MODULE = 'BOOT-INF/lib/app-platform-log-infra-1.0.0-SNAPSHOT.jar'
REMOVE = {'BOOT-INF/lib/elasticsearch-java-9.2.1.jar', 'BOOT-INF/lib/elasticsearch-rest5-client-9.2.1.jar'}
ADD = ['elasticsearch-java-8.18.0.jar', 'elasticsearch-rest-client-8.18.0.jar',
       'httpasyncclient-4.1.5.jar', 'httpcore-nio-4.4.16.jar']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compatible-jar', type=Path, required=True)
    args = parser.parse_args()
    baseline = ROOT / 'tmp/production-knowledge-baseline/app.jar'
    output = ROOT / 'outputs/knowledge-hotfix-20261007'
    runtime = output / 'runtime'
    libs = output / 'compile-libs'
    classes = output / 'classes'
    for folder in (runtime, libs, classes):
        folder.mkdir(parents=True, exist_ok=True)
    source = Path('D:/singuxplatform/nuwax-backend/app-platform-modules/app-platform-log/app-platform-log-infra/src/main/java/com/xspaceagi/search/infra/elasticsearch/ElasticsearchServiceImpl.java')
    lombok = Path.home() / '.m2/repository/org/projectlombok/lombok/1.18.36/lombok-1.18.36.jar'
    jdk = Path('C:/Program Files/Java/jdk-20/bin')
    with zipfile.ZipFile(baseline) as old, zipfile.ZipFile(args.compatible_jar) as compatible:
        replacements = {'BOOT-INF/lib/' + name: compatible.read('BOOT-INF/lib/' + name) for name in ADD}
        assert REMOVE <= set(old.namelist()), 'Unexpected production ES dependencies'
        for item in old.infolist():
            if item.filename.startswith('BOOT-INF/lib/') and item.filename.endswith('.jar') and item.filename not in REMOVE:
                (libs / Path(item.filename).name).write_bytes(old.read(item))
        for name, data in replacements.items():
            (libs / Path(name).name).write_bytes(data)
        subprocess.run([str(jdk / 'javac.exe'), '--release', '17', '-encoding', 'UTF-8',
                        '-cp', str(libs / '*') + ';' + str(lombok), '-processorpath', str(lombok),
                        '-d', str(classes), str(source)], check=True)
        generated = {p.relative_to(classes).as_posix() for p in classes.rglob('*.class')}
        assert generated == {SERVICE}, f'Unexpected compiled classes: {generated}'
        old_api = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', str(libs / '*'), SERVICE[:-6].replace('/', '.')])
        new_api = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', str(classes) + ';' + str(libs / '*'), SERVICE[:-6].replace('/', '.')])
        assert old_api == new_api, 'Public Elasticsearch service API changed'
        module_bytes = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(old.read(MODULE))) as module, zipfile.ZipFile(module_bytes, 'w') as patched:
            for item in module.infolist():
                patched.writestr(copy.copy(item), (classes / SERVICE).read_bytes() if item.filename == SERVICE else module.read(item))
        replacements[MODULE] = module_bytes.getvalue()
        index = [json.loads(line[2:]) for line in old.read('BOOT-INF/classpath.idx').decode().splitlines() if line.startswith('- ')]
        index = [name for name in index if name not in REMOVE]
        index.extend('BOOT-INF/lib/' + name for name in ADD)
        replacements['BOOT-INF/classpath.idx'] = ''.join('- ' + json.dumps(name) + '\n' for name in index).encode()
        layers = yaml.safe_load(old.read('BOOT-INF/layers.idx'))
        for layer in layers:
            for key, entries in layer.items():
                layer[key] = [name for name in (entries or []) if name not in REMOVE]
                if key == 'dependencies':
                    layer[key] = sorted(layer[key] + ['BOOT-INF/lib/' + name for name in ADD])
        replacements['BOOT-INF/layers.idx'] = ''.join(
            '- ' + json.dumps(key) + ':\n' + ''.join('  - ' + json.dumps(name) + '\n' for name in entries)
            for layer in layers for key, entries in layer.items()).encode()
        with zipfile.ZipFile(runtime / 'app.jar', 'w') as patched:
            for item in old.infolist():
                if item.filename not in REMOVE:
                    patched.writestr(copy.copy(item), replacements.pop(item.filename, None) or old.read(item))
            for name, data in replacements.items():
                # Spring Boot requires uncompressed nested JAR entries.
                patched.writestr(name, data, compress_type=zipfile.ZIP_STORED)
        with zipfile.ZipFile(runtime / 'app.jar') as patched:
            unchanged = [name for name in old.namelist() if name not in REMOVE | {MODULE, 'BOOT-INF/classpath.idx', 'BOOT-INF/layers.idx'}]
            assert all(old.read(name) == patched.read(name) for name in unchanged), 'Unrelated executable content changed'
            with zipfile.ZipFile(io.BytesIO(old.read(MODULE))) as a, zipfile.ZipFile(io.BytesIO(patched.read(MODULE))) as b:
                changed_classes = [name for name in a.namelist() if a.read(name) != b.read(name)]
                assert changed_classes == [SERVICE], changed_classes
        metadata = {
            'release': '1.1.10-20261007-knowledge-singletenant-r1',
            'image': 'singux/backend:1.1.10-20261007-knowledge-singletenant-r1',
            'schemaUnchanged': True, 'dataBackwardCompatible': True,
            'baselineManifest': 'sha256:aeccd376f79829d4d1ecd95083f08c9259af4bb2ca1ef4df8e8d8566b874bdaa',
            'baselineConfig': 'sha256:ab096327316a8d31a7cb1c9e3e764cd251213336de66a233b3d5b9720519eb47',
            'baselineJarSha256': digest(baseline.read_bytes()),
            'patchedJarSha256': digest((runtime / 'app.jar').read_bytes()),
            'sourceSha256': digest(source.read_bytes()),
            'changedClasses': changed_classes, 'removedLibraries': sorted(REMOVE),
            'addedLibraries': ['BOOT-INF/lib/' + name for name in ADD],
            'unchangedEntryCount': len(unchanged),
            'updatedIndexes': ['BOOT-INF/classpath.idx', 'BOOT-INF/layers.idx'],
            'scope': 'Elasticsearch compatibility and full-text delete only; no schema/login/tenant/domain-service changes'
        }
        (output / 'release.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        shutil.copyfile(ROOT / 'deploy/knowledge-hotfix.Dockerfile', runtime / 'Dockerfile')
        print(json.dumps(metadata, indent=2))

if __name__ == '__main__':
    main()
