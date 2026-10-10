const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const release = '1.1.10-20260924-r1';
const name = `singu-x-${release}-linux-amd64`;
const out = path.join(root, 'releases', name);
const backend = process.env.PACKAGE_BACKEND_DIR || 'D:/singuxplatform/nuwax-backend';
const run = (command, args, capture = false) => execFileSync(command, args, {
  cwd: root, stdio: capture ? ['ignore', 'pipe', 'inherit'] : 'inherit',
  encoding: capture ? 'utf8' : undefined, maxBuffer: 16 * 1024 * 1024,
});
const write = (relative, content) => {
  const target = path.join(out, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content.replace(/\r\n/g, '\n'), 'utf8');
};
const copyText = (source, target) => write(target, fs.readFileSync(source, 'utf8'));
const sha256 = async (file) => {
  const hash = crypto.createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
};

async function main() {
  if (fs.existsSync(out)) throw new Error(`Output already exists: ${out}`);
  const config = JSON.parse(run('docker', ['compose', '--env-file', '.env.compose', 'config', '--format', 'json'], true));
  const records = [];
  for (const [service, definition] of Object.entries(config.services)) {
    const metadata = JSON.parse(run('docker', ['image', 'inspect', definition.image], true))[0];
    if (metadata.Os !== 'linux' || metadata.Architecture !== 'amd64') {
      throw new Error(`Unsupported architecture: ${service}`);
    }
    const image = ['frontend', 'backend'].includes(service) ? `singux/${service}:${release}` : definition.image;
    if (image !== definition.image) run('docker', ['tag', metadata.Id, image]);
    definition.image = image;
    definition.platform = 'linux/amd64';
    definition.pull_policy = 'never';
    delete definition.build;
    delete definition.ports;
    records.push({ service, image, id: metadata.Id, platform: 'linux/amd64' });
  }
  config.name = 'singux';
  for (const volume of Object.values(config.volumes)) delete volume.name;
  for (const network of Object.values(config.networks || {})) delete network.name;
  const services = config.services;
  services.frontend.ports = ['${FRONTEND_PORT:-8080}:80'];
  services.mysql.volumes = ['mysql-data:/var/lib/mysql', './mysql:/docker-entrypoint-initdb.d:ro'];
  const secret = (key) => '${' + key + ':?Run sh deploy.sh to generate .env}';
  services.mysql.environment.MYSQL_ROOT_PASSWORD = secret('MYSQL_ROOT_PASSWORD');
  services.redis.environment.REDIS_PASSWORD = secret('REDIS_PASSWORD');
  services.minio.environment.MINIO_ROOT_USER = '${MINIO_ROOT_USER:-singux}';
  services.minio.environment.MINIO_ROOT_PASSWORD = secret('MINIO_ROOT_PASSWORD');
  services.milvus.environment.MINIO_ACCESS_KEY_ID = '${MINIO_ROOT_USER:-singux}';
  services.milvus.environment.MINIO_SECRET_ACCESS_KEY = secret('MINIO_ROOT_PASSWORD');
  const env = services.backend.environment;
  env.DB_PASSWORD = secret('MYSQL_ROOT_PASSWORD');
  env.DORIS_PASSWORD = secret('MYSQL_ROOT_PASSWORD');
  env.REDIS_PASSWORD = secret('REDIS_PASSWORD');
  env.JWT_SECRET_KEY = secret('JWT_SECRET_KEY');
  env.JAVA_OPTS = '${BACKEND_JAVA_OPTS:--Xms256m -Xmx2g}';
  for (const key of ['MCP_PROXY_URL', 'CODE_EXECUTE_URL', 'LOG_SERVICE_URL', 'BUILD_SERVER_URL', 'AI_AGENT_URL', 'DOCKER_PROXY_URL', 'DEV_SERVER_HOST', 'PROD_SERVER_HOST', 'MODEL_API_BASE_URL']) {
    env[key] = '${' + key + ':-' + (env[key] || '') + '}';
  }
  for (const key of ['ES_PASSWORD', 'ES_API_KEY', 'MILVUS_PASSWORD']) env[key] = '${' + key + ':-}';
  fs.mkdirSync(out, { recursive: true });
  write('compose.json', JSON.stringify(config, null, 2) + '\n');
  write('images.json', JSON.stringify({ release, created: new Date().toISOString(), images: records }, null, 2) + '\n');
  for (const file of ['deploy.sh', 'update.sh', 'UPDATE.md', '.env.example', 'README.md']) copyText(path.join(root, 'deploy/offline', file), file);
  copyText(path.join(root, 'deploy/mysql/00-create-databases.sql'), 'mysql/00-create-databases.sql');
  copyText(path.join(backend, 'sql/init.sql'), 'mysql/10-init.sql');
  copyText(path.join(root, 'deploy/migrations/20260924-login-account-label.sql'), 'migrations/login-account-label.sql');
  copyText(path.join(root, 'LICENSE'), 'licenses/frontend-LICENSE');
  copyText(path.join(backend, 'LICENSE'), 'licenses/backend-LICENSE');
  copyText(path.join(root, 'VERSION_CHANGES.md'), 'VERSION_CHANGES.md');
  console.log('Exporting eight runtime images to images.tar ...');
  run('docker', ['image', 'save', '-o', path.join(out, 'images.tar'), ...records.map((r) => r.image)]);
  console.log('Calculating file checksums ...');
  const files = fs.readdirSync(out, { recursive: true }).filter((f) => fs.statSync(path.join(out, f)).isFile()).sort();
  const checksums = [];
  for (const file of files) checksums.push(`${await sha256(path.join(out, file))}  ${file.replaceAll('\\', '/')}`);
  write('SHA256SUMS', checksums.join('\n') + '\n');
  console.log('Compressing server deployment bundle ...');
  const archive = out + '.tar.gz';
  run('tar', ['-czf', archive, '-C', path.dirname(out), name]);
  fs.writeFileSync(archive + '.sha256', `${await sha256(archive)}  ${path.basename(archive)}\n`);
  console.log(`Package ready: ${archive}`);
  console.log(`Bytes: ${fs.statSync(archive).size}`);
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
