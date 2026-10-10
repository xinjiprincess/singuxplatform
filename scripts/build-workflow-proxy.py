"""Patch only the model client factory on the verified MCP production baseline."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'outputs/service-recovery-mcp-20261009'
OUT = ROOT / 'outputs/workflow-proxy-20261009'
SOURCE = Path('D:/singuxplatform/nuwax-backend/app-platform-modules/app-platform-agent/app-platform-agent-core-infra/src')
PREFIX = 'com/xspaceagi/agent/core/infra/component/model/'
IMAGE = 'singux/backend:1.1.10-20261009-workflow-proxy-r1'
BASE_SHA = '4afe7428cc11450df8dd39ff028c46659cad3ae364d9cfa0b5cb1e7972b3b7ac'

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    jdk = Path('C:/Program Files/Java/jdk-20/bin')
    libs = BASE / 'compile-libs'
    classes = OUT / 'classes'; classes.mkdir(parents=True, exist_ok=True)
    runtime = OUT / 'runtime'; runtime.mkdir(parents=True, exist_ok=True)
    lombok = Path.home() / '.m2/repository/org/projectlombok/lombok/1.18.36/lombok-1.18.36.jar'
    sources = [SOURCE / 'main/java' / PREFIX / (name + '.java') for name in ('ModelClientFactory', 'ModelEndpoint')]
    test = SOURCE / 'test/java' / PREFIX / 'WorkflowModelProxyRegression.java'
    cp = str(classes) + ';' + str(libs / '*') + ';' + str(lombok)
    subprocess.run([str(jdk / 'javac.exe'), '--release', '17', '-encoding', 'UTF-8', '-cp', cp,
        '-processorpath', str(lombok), '-d', str(classes), *map(str, sources), str(test)], check=True)
    subprocess.run([str(jdk / 'java.exe'), '-cp', cp, PREFIX.replace('/', '.') + 'WorkflowModelProxyRegression'], check=True)
    name = PREFIX.replace('/', '.') + 'ModelClientFactory'
    before = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', str(libs / '*'), name])
    after = subprocess.check_output([str(jdk / 'javap.exe'), '-public', '-classpath', cp, name])
    assert before == after, 'Public API mismatch'
    baseline = (BASE / 'runtime/app.jar').read_bytes()
    assert sha(baseline) == BASE_SHA, 'Baseline JAR changed'
    with zipfile.ZipFile(io.BytesIO(baseline)) as old:
        names = [n for n in old.namelist() if n.startswith('BOOT-INF/lib/app-platform-agent-core-infra-') and n.endswith('.jar')]
        assert len(names) == 1
        module = names[0]
        generated = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('*.class')
            if p.name.startswith('ModelClientFactory') or p.name == 'ModelEndpoint.class'}
        buffer = io.BytesIO(); changed = []
        with zipfile.ZipFile(io.BytesIO(old.read(module))) as nested, zipfile.ZipFile(buffer, 'w') as patched:
            for item in nested.infolist():
                if item.filename in generated:
                    patched.writestr(copy.copy(item), generated.pop(item.filename)); changed.append(item.filename)
                else: patched.writestr(copy.copy(item), nested.read(item))
            for entry, data in generated.items(): patched.writestr(entry, data); changed.append(entry)
        with zipfile.ZipFile(runtime / 'app.jar', 'w') as patched:
            for item in old.infolist(): patched.writestr(copy.copy(item), buffer.getvalue() if item.filename == module else old.read(item))
        with zipfile.ZipFile(runtime / 'app.jar') as patched:
            assert old.namelist() == patched.namelist()
            assert all(old.read(n) == patched.read(n) for n in old.namelist() if n != module)
        report = {'image': IMAGE, 'baselineJarSha256': BASE_SHA, 'patchedJarSha256': sha((runtime / 'app.jar').read_bytes()),
            'schemaUnchanged': True, 'changedModule': module, 'changedClasses': changed,
            'unchangedExecutableEntries': len(old.namelist()) - 1,
            'sourceSha256': {str(p): sha(p.read_bytes()) for p in sources},
            'test': 'Local fake HTTP proxy: sync, stream, no AgentContext, token, invalid URL'}
    (OUT / 'release.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (runtime / 'Dockerfile').write_text('FROM singux/backend:1.1.10-20261009-service-recovery-mcp-r1\nCOPY --chown=app:app app.jar /app/app.jar\n', encoding='ascii')
    subprocess.run(['docker', 'build', '--pull=false', '-t', IMAGE, str(runtime)], check=True)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
