const {test} = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../static/js/booking/engine.js');
const group = {id: 'g', inputType: 'single_select', required: true, values: [{id: 'v', priceAdjustment: '20.10', durationAdjustmentMinutes: 30}]};
const category = {id: 'c', clientTypeIds: [], groups: [group], subcategories: []};
const selection = {clientTypeId: 'client', categoryId: 'c', subcategoryId: null, selectedOptions: {g: 'v'}, calculatedPrice: 50, calculatedDurationMinutes: 60};
test('price uses cents and supports negative adjustments', () => assert.equal(engine.calculateServicePrice({basePrice: '50', selectedOptions: [{priceAdjustment: '20.10'}, {priceAdjustment: '-5.05'}]}), 65.05));
test('duration sums selected adjustments', () => assert.equal(engine.calculateServiceDuration({baseDurationMinutes: 60, selectedOptions: [{durationAdjustmentMinutes: 30}, {durationAdjustmentMinutes: -10}]}), 80));
test('required options and category with no styles', () => {
  assert.equal(engine.isServiceConfigurationComplete(selection, category), true);
  assert.equal(engine.isServiceConfigurationComplete({...selection, selectedOptions: {}}, category), false);
});
test('category changes reset style and all options without mutating previous state', () => {
  const changed = engine.selectCategory(selection, 'other');
  assert.deepEqual(changed.selectedOptions, {});
  assert.equal(changed.subcategoryId, null);
  assert.deepEqual(selection.selectedOptions, {g: 'v'});
});
test('style changes keep inherited choices and remove invalid choices', () => {
  const changed = engine.selectSubcategory({...selection, selectedOptions: {g: 'v', old: 'a'}}, 's', {...category, subcategories: [{id: 's', groups: [group]}]});
  assert.deepEqual(changed.selectedOptions, {g: 'v'});
});
test('required boolean false and number zero are valid', () => {
  assert.equal(engine.validValue({inputType: 'boolean', required: true}, false), true);
  assert.equal(engine.validValue({inputType: 'number', required: true}, 0), true);
  assert.equal(engine.validValue({inputType: 'text', required: true}, '   '), false);
});
test('all multi select values contribute, unrelated text cannot affect price', () => {
  const c = {...category, groups: [{...group, inputType: 'multi_select'}]};
  assert.equal(engine.selectedAdjustments({...selection, selectedOptions: {g: ['v']}}, c).length, 1);
  assert.equal(engine.selectedAdjustments(selection, {...category, groups: [{...group, inputType: 'text'}]}).length, 0);
});
