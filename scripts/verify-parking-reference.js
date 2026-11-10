/* Synthetic, fragment-only reported reference contract. */
'use strict';
const assert = require('node:assert/strict');
const C = require('../docs/assets/parking-charts.js');
const hash = value => '#reference=' + encodeURIComponent(JSON.stringify(value));
for (const watts of [0, 0.123, 100]) {
  const {rows, warning} = C.readReference(hash({name:'Example Cam',watts}));
  assert.equal(warning,'');
  assert.equal(rows.length,1);
  assert.equal(rows[0].power_w,watts);
  for (const key of ['current_ma','voltage_v','installed_channels','firmware','date','wake_seconds','source_url']) assert.equal(rows[0][key],undefined);
  for (const metric of Object.keys(C.metrics)) {
    const state = {...C.preset(metric),ids:[C.referenceID]};
    assert.equal(C.eligibleRows(rows,state).length,metric==='watts'?1:0);
    assert.equal(C.prepare(rows,state).plotted.length,metric==='watts'?1:0);
  }
  for (const group of ['buffered','unbuffered','radar']) assert.equal(C.eligibleRows(rows,{...C.preset('watts'),group,family:group}).length,0);
  assert.equal(C.eligibleRows(rows,{...C.preset('watts'),condition:'event-recording'}).length,0);
  const state=C.readState('?selection=1&id='+C.referenceID+'&metric=watts&highlight='+C.referenceID,rows);
  assert.equal(state.highlight,'Example Cam');
  assert(!C.query(state).includes('Example'));
  assert.equal(new URLSearchParams(C.query(state)).get('highlight'),C.referenceID);
}
const bad=[null,[],{}, {name:'Example Cam',watts:-1},{name:'Example Cam',watts:101},{name:'Example Cam',watts:'0.123'}, {name:'Example Cam',watts:null}, {name:'',watts:0}, {name:' x ',watts:0}, {name:'x'.repeat(81),watts:0}, {name:'x\n',watts:0}, {name:'Example Cam',watts:0,source_url:'https://example.com'}];
for(const value of bad) {assert.equal(C.readReference(hash(value)).rows.length,0);assert(C.readReference(hash(value)).warning);}
for(const value of ['#reference=%',' #reference={','#reference='+encodeURIComponent('{"name":"Example Cam","watts":1e999}'),hash({name:'Example Cam',watts:0})+'&reference={}', '#reference='+'x'.repeat(2048)]) assert(C.readReference(value.trim()).warning);
assert.deepEqual(C.readReference(''),{rows:[],warning:''});
console.log('PASS: bounded fragment schema, zero, metric/family/state eligibility, no invented fields, private highlight serialization, malformed input');
