/** 공식 Playwright MCP를 stdio로 호출하고 원문 응답을 즉시 체크포인트한다. */
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';

const args = Object.fromEntries(process.argv.slice(2).reduce((out, value, index, values) => {
  if (value.startsWith('--')) out.push([value.slice(2), values[index + 1]]);
  return out;
}, []));
if (!args['run-dir'] || !args['server-bin']) throw new Error('--run-dir와 --server-bin이 필요합니다');
const root = path.resolve(args['run-dir']);
const catalogue = JSON.parse(await fs.readFile(path.join(root, 'catalogue.json'), 'utf8'));
const digest = value => createHash('sha256').update(value).digest('hex');
const now = () => new Date().toISOString();
const exists = filename => fs.access(filename).then(() => true, () => false);
async function write(filename, value) {
  await fs.mkdir(path.dirname(filename), { recursive: true });
  const temp = `${filename}.${process.pid}.tmp`;
  await fs.writeFile(temp, JSON.stringify(value, null, 2));
  await fs.rename(temp, filename);
}
const server = spawn(process.execPath, [args['server-bin'], '--isolated', '--headless', '--snapshot-mode', 'none', '--output-dir', path.join(root, 'mcp-capture')], { stdio: ['pipe', 'pipe', 'pipe'] });
const pending = new Map();
let sequence = 0;
server.stderr.on('data', chunk => process.stderr.write(chunk));
readline.createInterface({ input: server.stdout }).on('line', line => {
  let message;
  try { message = JSON.parse(line); } catch { return; }
  const handler = pending.get(message.id);
  if (!handler) return;
  clearTimeout(handler.timer);
  pending.delete(message.id);
  if (message.error) handler.reject(new Error(JSON.stringify(message.error)));
  else handler.resolve(message.result);
});
server.on('exit', (code, signal) => {
  for (const handler of pending.values()) { clearTimeout(handler.timer); handler.reject(new Error(`MCP server exited ${code} signal=${signal}`)); }
  pending.clear();
});
async function rpc(method, params = {}) {
  const id = ++sequence;
  const result = new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`MCP timeout ${method}`)); }, 65000);
    pending.set(id, { resolve, reject, timer });
  });
  server.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
  return result;
}
const progress = { schema_version: 1, job_id: `tv-source-ui-${process.pid}`, pid: process.pid, started_at: now(), status: 'running', total: catalogue.items.length, requested_limit: args.limit ? Number(args.limit) : null, script_sha256: digest(await fs.readFile(new URL(import.meta.url))), completed_this_process: 0 };
try {
  await rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'quantbridge-source-checkpoint', version: '1' } });
  server.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' })}\n`);
  const available = await rpc('tools/list');
  const tool = available.tools.find(t => /browser_run_code(?:_unsafe)?$/.test(t.name));
  if (!tool) throw new Error('Playwright MCP의 코드 실행 도구가 없습니다');
  let count = 0;
  for (const item of catalogue.items) {
    if (count >= Number(args.limit || Infinity)) break;
    const receiptFile = path.join(root, 'source_receipts', `${item.id}.json`);
    let previous = await exists(receiptFile) ? JSON.parse(await fs.readFile(receiptFile, 'utf8')) : null;
    if (previous?.status === 'captured') {
      const bytes = await fs.readFile(path.join(root, previous.source_file));
      if (digest(bytes) !== previous.source_sha256) throw new Error(`보존 원문 SHA 불일치 ${item.id}`);
      continue;
    }
    const attempts = previous?.attempts || [];
    if (attempts.length >= 2) continue;
    progress.current_id = item.id;
    progress.last_normal_at = now();
    await write(path.join(root, 'source-browser-process.json'), progress);
    for (let attempt = attempts.length + 1; attempt <= 2; attempt++) {
      try {
        const code = `async(page)=>{
          await page.goto(${JSON.stringify(item.url)},{waitUntil:'domcontentloaded',timeout:25000});
          const control=page.getByText('Source code',{exact:true});
          await control.waitFor({state:'visible',timeout:8000});
          const responsePromise=page.waitForResponse(r=>r.url().includes('pine-facade/get/')&&r.status()===200,{timeout:15000});
          responsePromise.catch(()=>{});
          await control.click({timeout:8000});
          const response=await responsePromise;const body=await response.json();
          return {source:body.source,source_response_url:response.url(),script_access:body.scriptAccess,script_version:body.lastVersionMaj,page_title:await page.title(),observed_at:new Date().toISOString()};
        }`;
        const result = await rpc('tools/call', { name: tool.name, arguments: { code } });
        const text = result.content.filter(c => c.type === 'text').map(c => c.text).join('\n');
        if (result.isError) throw new Error(text.slice(0, 1200));
        const match = text.match(/### Result\n([\s\S]*?)(?:\n### |$)/);
        if (!match) throw new Error(`MCP 응답 구조 불일치: ${text.slice(0, 500)}`);
        const record = JSON.parse(match[1]);
        if (typeof record.source !== 'string' || !record.source.trim() || !['open', 'open_no_auth'].includes(record.script_access)) throw new Error('공개 Pine 원문이 없습니다');
        if (!decodeURIComponent(new URL(record.source_response_url).pathname).includes(item.script_id_part)) throw new Error('원문 응답의 publication ID 불일치');
        const raw = Buffer.from(record.source, 'utf8');
        const sourceFile = `sources/${item.id}.pine`;
        await fs.mkdir(path.join(root, 'sources'), { recursive: true });
        await fs.writeFile(path.join(root, sourceFile), raw);
        const { source, ...metadata } = record;
        attempts.push({ attempt, status: 'captured', observed_at: metadata.observed_at });
        await write(receiptFile, { ...metadata, id: item.id, url: item.url, status: 'captured', source_file: sourceFile, source_sha256: digest(raw), exact_response_bytes: true, provenance_kind: 'actual_source_code_ui_response', native_verified: false, attempts, mcp_job_id: progress.job_id });
        progress.completed_this_process++;
        console.log(JSON.stringify({ id: item.id, status: 'captured', attempt, at: now() }));
        break;
      } catch (error) {
        const reason = String(error);
        attempts.push({ attempt, status: 'capture_failed', error: reason.slice(0, 1500), observed_at: now() });
        await write(receiptFile, { id: item.id, url: item.url, status: 'capture_failed', attempts });
        console.log(JSON.stringify({ id: item.id, status: 'capture_failed', attempt, at: now() }));
        if (/captcha|verify you are human|MCP server exited|MCP timeout/i.test(reason)) throw error;
      }
    }
    count++;
  }
  progress.status = 'completed';
} catch (error) {
  progress.status = 'interrupted';
  progress.error = String(error);
  process.exitCode = 1;
} finally {
  progress.finished_at = now();
  await write(path.join(root, 'source-browser-process.json'), progress);
  server.stdin.end();
  server.kill('SIGTERM');
  console.log(JSON.stringify(progress));
}
