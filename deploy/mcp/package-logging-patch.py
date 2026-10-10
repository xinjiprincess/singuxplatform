"""Compile only MCP logging classes against the exact production JAR dependency set."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path('D:/singuxplatform/nuwax-backend')
BASE = ROOT / 'outputs/workflow-proxy-20261009/runtime/app.jar'
BASE_SHA = 'aeda06730b81da6feb4d03d16ff0d8888a1f3a00789f3f83ebe75988ba4bd6db'
BASE_IMAGE = 'singux/backend:1.1.10-20261009-workflow-proxy-r1'
TAG = 'singux/backend:1.1.10-20261010-mcp-logs-r1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sha(BASE.read_bytes()) == BASE_SHA, 'Unrecognized production baseline'
    out = ROOT / 'outputs/mcp-logging-20261010'
    libs = out / 'compile-libs'; libs.mkdir(parents=True, exist_ok=True)
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    runtime = out / 'runtime'; runtime.mkdir(exist_ok=True)
    module = BACKEND / 'app-platform-modules/app-platform-mcp'
    application = module / 'app-platform-mcp-application/src/main/java/com/xspaceagi/mcp/application/service'
    sources = [application / (name + '.java') for name in
               ('McpLogSanitizer', 'McpDeployTaskServiceImpl', 'SSEMcpUpdateTaskServiceImpl')]
    sources += [module / 'app-platform-mcp-ui/src/main/java/com/xspaceagi/mcp/ui/api/service/McpApiServiceImpl.java']
    with zipfile.ZipFile(BASE) as base:
        for entry in base.infolist():
            if entry.filename.startswith('BOOT-INF/lib/') and entry.filename.endswith('.jar'):
                (libs / Path(entry.filename).name).write_bytes(base.read(entry))
    lombok = Path.home() / '.m2/repository/org/projectlombok/lombok/1.18.36/lombok-1.18.36.jar'
    args = ['--release', '17', '-encoding', 'UTF-8', '-cp', str(libs / '*') + ';' + str(lombok),
            '-processorpath', str(lombok), '-d', str(classes)] + list(map(str, sources))
    subprocess.run(['C:/Program Files/Java/jdk-20/bin/javac.exe'] + args, check=True)
    replacements = {}
    changed = []
    for module_name, prefix in (
            ('app-platform-mcp-application-0.0.1-SNAPSHOT.jar', 'com/xspaceagi/mcp/application/service/'),
            ('app-platform-mcp-ui-0.0.1-SNAPSHOT.jar', 'com/xspaceagi/mcp/ui/api/service/')):
        data = io.BytesIO()
        patch = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('*.class')
                 if p.relative_to(classes).as_posix().startswith(prefix)}
        with zipfile.ZipFile(libs / module_name) as old, zipfile.ZipFile(data, 'w') as new:
            for item in old.infolist():
                new.writestr(copy.copy(item), patch.pop(item.filename, old.read(item)))
            for name, content in patch.items():
                new.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)
        replacements['BOOT-INF/lib/' + module_name] = data.getvalue()
        (out / module_name).write_bytes(data.getvalue())
    with zipfile.ZipFile(BASE) as old, zipfile.ZipFile(runtime / 'app.jar', 'w') as new:
        for item in old.infolist():
            new.writestr(copy.copy(item), replacements.get(item.filename, old.read(item)))
            if item.filename in replacements: changed.append(item.filename)
    with zipfile.ZipFile(BASE) as old, zipfile.ZipFile(runtime / 'app.jar') as new:
        assert old.namelist() == new.namelist()
        assert all(old.read(name) == new.read(name) for name in old.namelist() if name not in replacements)
    (runtime / 'Dockerfile').write_text('FROM ' + BASE_IMAGE + '\nCOPY --chown=app:app app.jar /app/app.jar\n')
    report = {'image': TAG, 'baselineJarSha256': BASE_SHA,
              'patchedJarSha256': sha((runtime / 'app.jar').read_bytes()), 'schemaUnchanged': True,
              'changedModules': changed,
              'modules': {name: sha(data) for name, data in replacements.items()},
              'sources': {str(path): sha(path.read_bytes()) for path in sources}}
    (out / 'release.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
