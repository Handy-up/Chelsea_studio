(function (root) {
  'use strict';
  const present = value => value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0) && (typeof value !== 'string' || value.trim() !== '');
  const calculateServicePrice = ({basePrice, selectedOptions = []}) =>
    (Math.round(Number(basePrice) * 100) + selectedOptions.reduce((sum, option) => sum + Math.round(Number(option.priceAdjustment) * 100), 0)) / 100;
  const calculateServiceDuration = ({baseDurationMinutes, selectedOptions = []}) =>
    Number(baseDurationMinutes) + selectedOptions.reduce((sum, option) => sum + Number(option.durationAdjustmentMinutes), 0);
  function groupsFor(category, subcategoryId) {
    return category?.subcategories.find(style => style.id === subcategoryId)?.groups || category?.groups || [];
  }
  function validValue(group, value) {
    if (!present(value)) return !group.required;
    if (group.inputType === 'boolean') return typeof value === 'boolean';
    if (group.inputType === 'single_select') return group.values.some(option => option.id === value);
    if (group.inputType === 'multi_select') return Array.isArray(value) && new Set(value).size === value.length && value.every(id => group.values.some(option => option.id === id));
    if (group.inputType === 'number') return typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 1000000;
    if (['photo', 'file'].includes(group.inputType)) return typeof value?.name === 'string' && !!value.name;
    return typeof value === 'string' && value.length <= 2000;
  }
  function isServiceConfigurationComplete(selection, category) {
    return !!selection.clientTypeId && !!category && (!category.clientTypeIds.length || category.clientTypeIds.includes(selection.clientTypeId)) &&
      (!category.subcategories.length || category.subcategories.some(style => style.id === selection.subcategoryId)) &&
      groupsFor(category, selection.subcategoryId).every(group => validValue(group, selection.selectedOptions[group.id])) &&
      selection.calculatedPrice >= 0 && selection.calculatedDurationMinutes > 0 && selection.calculatedDurationMinutes <= 1440;
  }
  function pruneOptions(options, groups) {
    return Object.fromEntries(Object.entries(options).filter(([key, value]) => groups.some(group => group.id === key && validValue({...group, required: false}, value))));
  }
  function selectCategory(selection, categoryId) {
    return {...selection, categoryId, subcategoryId: null, selectedOptions: {}};
  }
  function selectSubcategory(selection, subcategoryId, category) {
    return {...selection, subcategoryId, selectedOptions: pruneOptions(selection.selectedOptions, groupsFor(category, subcategoryId))};
  }
  function selectedAdjustments(selection, category) {
    const style = category?.subcategories.find(s => s.id === selection.subcategoryId);
    const adjustments = style ? [style] : [];
    for (const group of groupsFor(category, selection.subcategoryId)) {
      const value = selection.selectedOptions[group.id];
      for (const option of group.values) {
        if (group.inputType === 'boolean' ? typeof value === 'boolean' && option.value === String(value) :
            group.inputType === 'multi_select' ? Array.isArray(value) && value.includes(option.id) :
            group.inputType === 'single_select' && value === option.id) adjustments.push(option);
      }
    }
    return adjustments;
  }
  const api = {calculateServicePrice, calculateServiceDuration, isServiceConfigurationComplete, groupsFor, selectCategory, selectSubcategory, selectedAdjustments, validValue};
  if (typeof module !== 'undefined') module.exports = api;
  else root.BookingEngine = api;
})(typeof window === 'undefined' ? globalThis : window);
