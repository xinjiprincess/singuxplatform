/* eslint-disable no-console */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const TEXT_FILE_RE = /\.(ts|tsx|js|jsx)$/;
const IGNORE_PATH_RE =
  /(^docs\/)|(^tests\/)|(^src\/locales\/)|(^dist\/)|(^node_modules\/)/;
const CHINESE_STRING_RE = /(['"`])([^'"`]*[\u4e00-\u9fa5][^'"`]*)\1/g;
const LEGACY_SYSTEM_KEY_RE = /\bSystem\.[A-Za-z0-9_.]+\b/;
const DICT_KEY_RE = /dict\(\s*(['"`])([^'"`]+)\1/g;

const I18N_CONSTANTS_PATH = path.join(
  __dirname,
  '..',
  'src',
  'constants',
  'i18n.constants.ts',
);

// \u5408\u6cd5\u524d\u7f00\uff08Client\u3001Scope\uff09\u76f4\u63a5\u4ece\u8fd0\u884c\u65f6\u7684\u5355\u4e00\u5b9a\u4e49\u5904\u8bfb\u53d6\uff0c\u4e0d\u518d\u5728\u672c\u811a\u672c\u91cc\u53e6\u6284\u4e00\u4efd\u3002
// \u4e4b\u524d\u8fd9\u91cc\u624b\u5199\u7684 Scope \u5217\u8868\u6f0f\u4e86 Constants/Routes/Utils\uff0c\u5bfc\u81f4 PC.Constants.* \u8fd9\u7c7b
// \u5b8c\u5168\u5408\u6cd5\u7684 key \u88ab\u8bef\u62a5\u4e3a\u975e\u6cd5\uff1b\u53ea\u8981\u4e24\u5904\u662f\u590d\u5236\u5173\u7cfb\uff0c\u5c31\u4e00\u5b9a\u4f1a\u518d\u6b21\u6f02\u79fb\u3002
function readI18nKeyParts() {
  const source = fs.readFileSync(I18N_CONSTANTS_PATH, 'utf8');
  const readArray = (name) => {
    const block = source.match(
      new RegExp(`${name}\\s*=\\s*\\[([\\s\\S]*?)\\]`),
    );
    const values = block
      ? [...block[1].matchAll(/'([A-Za-z0-9]+)'/g)].map((match) => match[1])
      : [];
    if (!values.length) {
      // \u5b81\u53ef\u8ba9\u811a\u672c\u62a5\u9519\uff0c\u4e5f\u4e0d\u8981\u9000\u5316\u6210\u4e00\u6761\u8fc7\u5bbd\u7684\u89c4\u5219\u628a\u975e\u6cd5 key \u653e\u8fc7\u53bb
      throw new Error(
        `[i18n-check] Cannot read ${name} from ${I18N_CONSTANTS_PATH}. ` +
          'Fix this parser rather than loosening the key check.',
      );
    }
    return values;
  };

  return {
    clients: readArray('I18N_CLIENTS').join('|'),
    scopes: readArray('I18N_SCOPES').join('|'),
  };
}

const { clients: I18N_CLIENT_ALTERNATION, scopes: I18N_SCOPE_ALTERNATION } =
  readI18nKeyParts();
const I18N_KEY_RE = new RegExp(
  `^(${I18N_CLIENT_ALTERNATION})\\.(${I18N_SCOPE_ALTERNATION})\\.([A-Za-z0-9]+\\.)+[a-z][A-Za-z0-9]*$`,
);
const LEGACY_KEY_ALLOW_FILES = new Set([
  'src/services/i18nRuntime.ts',
  'scripts/check-hardcoded-i18n.js',
  'scripts/i18n-governance-report.js',
]);

function getDiffText() {
  const commands = [
    'git diff --unified=0 --no-color --diff-filter=ACMRTUXB',
    'git diff --cached --unified=0 --no-color --diff-filter=ACMRTUXB',
  ];
  const chunks = [];

  commands.forEach((cmd) => {
    try {
      const output = execSync(cmd, { encoding: 'utf8' }).trim();
      if (!output) return;
      chunks.push(output);
    } catch {
      // ignore git command failures
    }
  });

  return chunks.join('\n');
}

function scanAddedLines(diffText) {
  const lines = diffText.split('\n');
  const hardcodedFindings = [];
  const legacyKeyFindings = [];
  const invalidKeyFindings = [];
  let currentFile = '';
  let currentLine = 0;

  lines.forEach((line) => {
    if (line.startsWith('+++ b/')) {
      currentFile = line.replace('+++ b/', '').trim();
      return;
    }

    if (line.startsWith('@@')) {
      const match = line.match(/\+(\d+)(?:,(\d+))?/);
      currentLine = match ? Number(match[1]) : currentLine;
      return;
    }

    if (!currentFile || !TEXT_FILE_RE.test(currentFile)) return;
    if (IGNORE_PATH_RE.test(currentFile)) return;

    if (line.startsWith('+') && !line.startsWith('+++')) {
      const content = line.slice(1);
      CHINESE_STRING_RE.lastIndex = 0;
      if (CHINESE_STRING_RE.test(content)) {
        hardcodedFindings.push({
          file: currentFile,
          line: currentLine,
          content: content.trim(),
        });
      }

      LEGACY_SYSTEM_KEY_RE.lastIndex = 0;
      if (
        LEGACY_SYSTEM_KEY_RE.test(content) &&
        !LEGACY_KEY_ALLOW_FILES.has(currentFile)
      ) {
        legacyKeyFindings.push({
          file: currentFile,
          line: currentLine,
          content: content.trim(),
        });
      }

      DICT_KEY_RE.lastIndex = 0;
      let dictMatch = DICT_KEY_RE.exec(content);
      while (dictMatch) {
        const i18nKey = dictMatch[2];
        if (!I18N_KEY_RE.test(i18nKey)) {
          invalidKeyFindings.push({
            file: currentFile,
            line: currentLine,
            content: i18nKey,
          });
        }
        dictMatch = DICT_KEY_RE.exec(content);
      }

      currentLine += 1;
      return;
    }

    if (line.startsWith('-') && !line.startsWith('---')) {
      return;
    }

    CHINESE_STRING_RE.lastIndex = 0;
    currentLine += 1;
  });

  return { hardcodedFindings, legacyKeyFindings, invalidKeyFindings };
}

function main() {
  const diffText = getDiffText();
  if (!diffText) {
    console.log('[i18n-check] No changes to scan.');
    return;
  }

  const { hardcodedFindings, legacyKeyFindings, invalidKeyFindings } =
    scanAddedLines(diffText);

  if (
    !hardcodedFindings.length &&
    !legacyKeyFindings.length &&
    !invalidKeyFindings.length
  ) {
    console.log('[i18n-check] Added lines passed i18n governance checks.');
    return;
  }

  if (hardcodedFindings.length) {
    console.error('[i18n-check] Found hardcoded Chinese strings:');
    hardcodedFindings.forEach((item) => {
      console.error(`- ${item.file}:${item.line} ${item.content}`);
    });
  }

  if (legacyKeyFindings.length) {
    console.error('[i18n-check] Found legacy System.* keys in added lines:');
    legacyKeyFindings.forEach((item) => {
      console.error(`- ${item.file}:${item.line} ${item.content}`);
    });
  }

  if (invalidKeyFindings.length) {
    console.error(
      '[i18n-check] Found invalid dict keys (must be {Client}.{Scope}.{Domain}.{key}):',
    );
    invalidKeyFindings.forEach((item) => {
      console.error(`- ${item.file}:${item.line} ${item.content}`);
    });
  }

  process.exit(1);
}

main();
