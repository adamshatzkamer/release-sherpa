const {test} = require('node:test');
const assert = require('node:assert/strict');
const {chooseCopilot, parseResponse, allowedFile} = require('./core');
test('never selects a different provider', () => {
  assert.throws(() => chooseCopilot([{vendor: 'other', id: 'model', name: 'model'}]));
  assert.equal(chooseCopilot([{vendor: 'copilot', id: 'model', name: 'model'}]).vendor, 'copilot');
});
test('rejects incomplete approvals', () => {
  assert.throws(() => parseResponse('{"verdict":"approved"}'));
});
test('rejects credential files and traversal even when tracked', () => {
  for (const file of ['.env', 'nested/.env.production', '../source.js', '/source.js', 'key.pem']) {
    assert.equal(allowedFile(file, new Set([file])), false);
  }
  assert.equal(allowedFile('source.js', new Set(['source.js'])), true);
});
test('limits requested files', () => {
  assert.throws(() => parseResponse(JSON.stringify({read_files: Array(9).fill('source.js')})));
});
