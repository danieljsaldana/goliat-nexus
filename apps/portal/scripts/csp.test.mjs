import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {inlineScriptHashes} from './csp.mjs';

const hash=text=>`'sha256-${createHash('sha256').update(text).digest('base64')}'`;

test('CSP hashes preserve inline script text across HTML tag variants',()=>{
 const source='console.log("á &amp; < >");\n';
 for(const markup of [
  `<SCRIPT>${source}</SCRIPT>`,
  `<script data-label=">">${source}</script \t>`,
  `<ScRiPt>${source}</sCrIpT\n>`,
 ])assert.deepEqual(inlineScriptHashes(markup),[hash(source)]);
});

test('CSP does not authorize commented scripts, external fallbacks or inert templates',()=>{
 const markup='<!-- <script>commented()</script> -->'+
  '<script SRC="/app.js">externalFallback()</script>'+
  '<script src>emptySource()</script>'+
  '<template><script>inert()</script></template>'+
  '<script>inline()</script><script>inline()</script>';
 assert.deepEqual(inlineScriptHashes(markup),[hash('inline()')]);
});

test('CSP follows browser normalization of line endings',()=>{
 assert.deepEqual(inlineScriptHashes('<script>first();\r\nsecond();\rlast();</script>'),[hash('first();\nsecond();\nlast();')]);
});
