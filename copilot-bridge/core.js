'use strict';
const path = require('node:path');
const crypto = require('node:crypto');

function chooseCopilot(models, preferred) {
  const eligible = models.filter(m => m.vendor === 'copilot' && m.id !== 'auto');
  const selected = eligible.find(m => m.id === preferred)
    || eligible.find(m => /sonnet|gpt-5|gpt-4\.1/i.test(m.name + ' ' + m.id) && !/mini|nano/i.test(m.name))
    || eligible[0];
  if (!selected) throw new Error('No Copilot-provider model is available. No Codex fallback was attempted.');
  return selected;
}

function parseResponse(text) {
  const cleaned = text.trim().replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '');
  const value = JSON.parse(cleaned);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid review response');
  if (Array.isArray(value.read_files)) {
    if (value.read_files.length > 8 || !value.read_files.every(p => typeof p === 'string')) throw new Error('Invalid file request');
    return value;
  }
  if (!['approved', 'blocked', 'changes_requested'].includes(value.verdict)
      || typeof value.merge_ready !== 'boolean' || typeof value.deploy_ready !== 'boolean'
      || !Array.isArray(value.blockers) || !value.blockers.every(b => typeof b === 'string')
      || typeof value.summary !== 'string' || !value.summary.trim()
      || typeof value.review_markdown !== 'string' || !value.review_markdown.trim()) {
    throw new Error('Incomplete Copilot review; no approval result will be written');
  }
  return value;
}

function allowedFile(name, tracked) {
  if (!tracked.has(name) || path.isAbsolute(name) || name.split('/').includes('..')) return false;
  return !/(^|\/)(\.env(?:\.|$)|\.git(?:\/|$)|id_rsa|id_ed25519)|\.(pem|p12|key)$/i.test(name);
}

function digest(text) { return crypto.createHash('sha256').update(text).digest('hex'); }
module.exports = {chooseCopilot, parseResponse, allowedFile, digest};
