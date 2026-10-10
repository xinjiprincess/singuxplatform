// Run inside the isolated test container after the filesystem fixture is Ready.
import { readdir, access } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const root = '/home/mcp/.npm/_npx';
let sdk;
if (process.env.MCP_SDK_CLIENT) sdk = process.env.MCP_SDK_CLIENT;
for (const entry of sdk ? [] : await readdir(root)) {
  const candidate = `${root}/${entry}/node_modules/@modelcontextprotocol/sdk/dist/esm/client/`;
  try {
    await access(`${candidate}index.js`);
    sdk = candidate;
    break;
  } catch { /* Skip incomplete npm cache entries. */ }
}
if (!sdk) throw new Error('Install the pinned filesystem MCP fixture first.');
const { Client } = await import(pathToFileURL(`${sdk}index.js`));
const { SSEClientTransport } = await import(pathToFileURL(`${sdk}sse.js`));
const { StdioClientTransport } = await import(pathToFileURL(`${sdk}stdio.js`));
const client = new Client({ name: 'singux-smoke', version: '1.0.0' });
const timeout = setTimeout(() => {
  console.error('MCP smoke test timed out');
  process.exit(1);
}, 30000);
try {
  const transport = process.argv.includes('--direct')
    ? new StdioClientTransport({ command: 'npx', args: ['-y', '@modelcontextprotocol/server-filesystem@2025.8.21', '/tmp'] })
    : new SSEClientTransport(new URL(
    'http://127.0.0.1:8080/mcp/sse/proxy/singux-local-smoke/sse',
  ));
  await client.connect(transport);
  const listed = await client.listTools();
  if (!listed.tools.some((tool) => tool.name === 'list_allowed_directories')) {
    throw new Error('Expected filesystem tool missing');
  }
  const result = await client.callTool({ name: 'list_allowed_directories', arguments: {} });
  if (result.isError || !result.content?.some((item) => item.text?.includes('/tmp'))) {
    throw new Error('Filesystem tool call did not return the isolated directory');
  }
  console.log(`MCP handshake, ${listed.tools.length} tools, and read-only tool call passed.`);
} finally {
  clearTimeout(timeout);
  await client.close();
}
