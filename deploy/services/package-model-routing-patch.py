"""Compile and test the direct/proxy routing fix against the MCP-patched baseline."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path('D:/singuxplatform/nuwax-backend')
BASE = ROOT / 'outputs/mcp-logging-20261010/runtime/app.jar'
BASE_SHA = '14c19d06bae8ed464c62aceb5f6cd8bc1c49d9501eeb0fd24f49e7957ad7a581'
MODULE = 'BOOT-INF/lib/app-platform-agent-core-infra-0.0.1-SNAPSHOT.jar'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sha(BASE.read_bytes()) == BASE_SHA
    out = ROOT / 'outputs/model-routing-20261010'
    classes = out / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    runtime = out / 'runtime'
    runtime.mkdir(exist_ok=True)
    module = BACKEND / 'app-platform-modules/app-platform-agent/app-platform-agent-core-infra'
    relative = 'com/xspaceagi/agent/core/infra/component/model/'
    source = module / ('src/main/java/' + relative + 'ModelClientFactory.java')
    test = module / ('src/test/java/' + relative + 'WorkflowModelProxyRegression.java')
    libs = ROOT / 'outputs/mcp-logging-20261010/compile-libs'
    jdk = Path('C:/Program Files/Java/jdk-20/bin')
    cp = str(classes) + ';' + str(libs / '*')
    subprocess.run([str(jdk / 'javac.exe'), '--release', '17', '-encoding', 'UTF-8',
                    '-cp', cp, '-processorpath', str(libs / 'lombok-1.18.36.jar'),
                    '-d', str(classes), str(source), str(test)], check=True)
    subprocess.run([str(jdk / 'java.exe'), '-cp', cp,
                    'com.xspaceagi.agent.core.infra.component.model.WorkflowModelProxyRegression'], check=True, timeout=90)
    patches = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('ModelClientFactory*.class')}
    assert patches
    data = io.BytesIO()
    with zipfile.ZipFile(BASE) as base, zipfile.ZipFile(io.BytesIO(base.read(MODULE))) as old, zipfile.ZipFile(data, 'w') as new:
        assert set(patches).issubset(old.namelist())
        for item in old.infolist():
            new.writestr(copy.copy(item), patches.get(item.filename, old.read(item)))
    replacement = data.getvalue()
    (out / Path(MODULE).name).write_bytes(replacement)
    with zipfile.ZipFile(BASE) as old, zipfile.ZipFile(runtime / 'app.jar', 'w') as new:
        for item in old.infolist():
            new.writestr(copy.copy(item), replacement if item.filename == MODULE else old.read(item))
    with zipfile.ZipFile(BASE) as old, zipfile.ZipFile(runtime / 'app.jar') as new:
        assert old.namelist() == new.namelist()
        assert all(old.read(name) == new.read(name) for name in old.namelist() if name != MODULE)
    report = {'image': 'singux/backend:1.1.10-20261010-model-routing-r1',
              'baselineJarSha256': BASE_SHA, 'patchedJarSha256': sha((runtime / 'app.jar').read_bytes()),
              'schemaUnchanged': True, 'modules': {MODULE: sha(replacement)},
              'changedModules': [MODULE], 'regressionPassed': True,
              'sourceSha256': sha(source.read_bytes()), 'testSha256': sha(test.read_bytes())}
    (out / 'release.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
