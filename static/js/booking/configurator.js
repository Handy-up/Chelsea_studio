document.addEventListener('alpine:init', () => {
  Alpine.data('serviceConfigurator', () => ({
    catalogue: {clientTypes: [], categories: []}, loading: true, busy: false, error: '', review: false,
    previewMode: false, previewValidated: false,
    step: 1, configurationToken: '', selectedDate: '', selectedSlot: '', selectedSlotFormatted: '',
    files: {}, previews: {},
    /** @type {import('./types').BookingSelection} */
    bookingSelection: {clientTypeId: null, categoryId: null, subcategoryId: null, selectedOptions: {}, calculatedPrice: 0, calculatedDurationMinutes: 0},
    async init() {
      this.initial = JSON.parse(document.getElementById('configurator-initial').textContent);
      this.previewMode = this.$root.dataset.preview === 'true';
      this.step = this.previewMode ? 1 : this.initial.step;
      this.configurationToken = this.initial.token;
      this.selectedDate = this.initial.date;
      this.selectedSlot = this.initial.slot;
      await this.loadCatalogue();
    },
    async refreshCatalogue() { this.initial.selection = {...this.bookingSelection}; this.initial.fileReselect = Object.keys(this.files).length > 0; this.resetOptions(); this.invalidate(); this.step = 1; await this.loadCatalogue(); },
    async loadCatalogue() {
      this.loading = true; this.error = '';
      try {
        const response = await fetch(this.$root.dataset.catalogueUrl);
        if (!response.ok) throw new Error();
        this.catalogue = await response.json();
        if (this.initial.selection) {
          this.bookingSelection = {...this.bookingSelection, ...this.initial.selection};
          for (const group of this.groups) if (['photo', 'file'].includes(group.inputType)) delete this.bookingSelection.selectedOptions[group.id];
          if (this.initial.fileReselect) this.error = 'Vos autres choix sont conservés. Ajoutez à nouveau vos fichiers avant de continuer.';
        } else {
          if (this.catalogue.clientTypes.length === 1) this.bookingSelection.clientTypeId = this.catalogue.clientTypes[0].id;
          const category = this.catalogue.categories.find(c => c.id === this.initial.preselectedId);
          if (category) {
            if (category.clientTypeIds.length === 1 && this.catalogue.clientTypes.some(t => t.id === category.clientTypeIds[0])) this.bookingSelection.clientTypeId = category.clientTypeIds[0];
            this.bookingSelection.categoryId = category.id;
          }
        }
        this.recalculate();
      } catch (_) { this.error = 'Impossible de charger les coiffures. Vérifiez votre connexion puis réessayez.'; }
      finally { this.loading = false; }
    },
    get category() { return this.catalogue.categories.find(c => c.id === this.bookingSelection.categoryId); },
    get style() { return this.category?.subcategories.find(s => s.id === this.bookingSelection.subcategoryId); },
    get categories() { return this.catalogue.categories.filter(c => !c.clientTypeIds.length || c.clientTypeIds.includes(this.bookingSelection.clientTypeId)); },
    get groups() { return BookingEngine.groupsFor(this.category, this.bookingSelection.subcategoryId); },
    get complete() { return this.catalogue.clientTypes.some(t => t.id === this.bookingSelection.clientTypeId) && BookingEngine.isServiceConfigurationComplete(this.bookingSelection, this.category); },
    get selectedServiceId() { return this.bookingSelection.categoryId || ''; },
    get selectedServiceName() { return [this.category?.name, this.style?.name].filter(Boolean).join(' · '); },
    get selectedServiceDuration() { return this.bookingSelection.calculatedDurationMinutes; },
    get selectedServicePrice() { return this.category?.priceType === 'consultation_required' ? 'Sur devis' : (this.category?.priceType === 'starting_at' ? 'À partir de ' : '') + this.money(this.bookingSelection.calculatedPrice); },
    get summaryName() { return this.complete ? (this.style?.name || this.category?.name) : 'Un soin à votre image'; },
    get chosenGroups() { return this.groups.filter(g => { const v = this.bookingSelection.selectedOptions[g.id]; return v !== undefined && v !== null && v !== '' && (!Array.isArray(v) || v.length); }); },
    get remaining() {
      if (!this.bookingSelection.clientTypeId) return 'Choisissez le type de client.';
      if (!this.category) return 'Choisissez votre coiffure.';
      if (this.category.subcategories.length && !this.style) return 'Choisissez votre style.';
      const missing = this.groups.filter(g => !BookingEngine.validValue(g, this.bookingSelection.selectedOptions[g.id]));
      return missing.length ? 'Complétez les options requises.' : this.complete ? 'Votre soin est prêt à être confirmé.' : 'Cette combinaison ne peut pas être réservée.';
    },
    money(value) { return new Intl.NumberFormat('fr-FR', {style: 'currency', currency: this.previewMode ? (this.catalogue.currency || 'CAD') : 'EUR', currencyDisplay: 'narrowSymbol'}).format(Number(value)); },
    duration(value) { return value >= 60 ? `${Math.floor(value / 60)} h${value % 60 ? ' ' + String(value % 60).padStart(2, '0') : ''}` : `${value} min`; },
    adjustmentLabel(option) { return [Number(option.priceAdjustment) ? `${Number(option.priceAdjustment) > 0 ? '+' : ''}${this.money(option.priceAdjustment)}` : '', option.durationAdjustmentMinutes ? `${option.durationAdjustmentMinutes > 0 ? '+' : ''}${option.durationAdjustmentMinutes} min` : ''].filter(Boolean).join(' · '); },
    invalidate() { this.previewValidated = false; this.configurationToken = ''; this.selectedDate = ''; this.selectedSlot = ''; this.selectedSlotFormatted = ''; this.review = false; this.error = ''; },
    recalculate() {
      const selectedOptions = BookingEngine.selectedAdjustments(this.bookingSelection, this.category);
      this.bookingSelection.calculatedPrice = BookingEngine.calculateServicePrice({basePrice: this.category?.basePrice || 0, selectedOptions});
      this.bookingSelection.calculatedDurationMinutes = BookingEngine.calculateServiceDuration({baseDurationMinutes: this.category?.baseDurationMinutes || 0, selectedOptions});
    },
    selectClientType(id) { this.invalidate(); this.bookingSelection.clientTypeId = id; if (this.category && !this.categories.some(c => c.id === this.category.id)) this.resetCategory(); },
    resetOptions() { this.$root.querySelectorAll('input[type=file]').forEach(input => { input.value = ''; }); for (const url of Object.values(this.previews)) URL.revokeObjectURL(url); this.files = {}; this.previews = {}; this.bookingSelection.selectedOptions = {}; },
    resetCategory() { this.resetOptions(); this.bookingSelection = BookingEngine.selectCategory(this.bookingSelection, null); this.recalculate(); },
    resetSubcategory() { this.selectSubcategory(null); },
    selectCategory(id) { if (this.bookingSelection.categoryId === id) return; this.invalidate(); this.resetOptions(); this.bookingSelection = BookingEngine.selectCategory(this.bookingSelection, id); this.recalculate(); },
    selectSubcategory(id) {
      this.invalidate(); this.bookingSelection = BookingEngine.selectSubcategory(this.bookingSelection, id, this.category);
      for (const key of Object.keys(this.files)) if (!(key in this.bookingSelection.selectedOptions)) { delete this.files[key]; URL.revokeObjectURL(this.previews[key]); delete this.previews[key]; }
      this.recalculate();
    },
    selectOption(group, value) { this.invalidate(); this.bookingSelection.selectedOptions[group.id] = value; this.recalculate(); },
    toggleOption(group, id) { const current = this.bookingSelection.selectedOptions[group.id] || []; this.selectOption(group, current.includes(id) ? current.filter(v => v !== id) : [...current, id]); },
    colorFor(option) { const color = option.metadata?.color; return /^#[0-9a-f]{6}$/i.test(color || '') ? color : 'transparent'; },
    removeFile(group) {
      const input = document.getElementById('option-file-' + group.id);
      if (input) input.value = '';
      if (this.previews[group.id]) URL.revokeObjectURL(this.previews[group.id]);
      delete this.previews[group.id]; delete this.files[group.id];
      this.selectOption(group, null);
    },
    selectFile(group, event) {
      const file = event.target.files[0];
      if (this.previews[group.id]) URL.revokeObjectURL(this.previews[group.id]);
      delete this.previews[group.id]; delete this.files[group.id];
      this.selectOption(group, null);
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) { this.error = 'Chaque fichier doit faire au maximum 5 Mo.'; event.target.value = ''; return; }
      this.files[group.id] = file;
      this.selectOption(group, {name: file.name});
      if (group.inputType === 'photo') this.previews[group.id] = URL.createObjectURL(file);
    },
    optionLabel(group) {
      const value = this.bookingSelection.selectedOptions[group.id];
      if (value === undefined || value === null || value === '') return 'Non renseigné';
      if (group.inputType === 'boolean') return value ? 'Oui' : 'Non';
      if (['file', 'photo'].includes(group.inputType)) return value.name;
      if (group.inputType === 'single_select') return group.values.find(v => v.id === value)?.label || '';
      if (group.inputType === 'multi_select') return group.values.filter(v => value.includes(v.id)).map(v => v.label).join(', ') || 'Aucune';
      return value;
    },
    showReview() { if (this.complete) { this.review = true; this.$nextTick(() => this.$refs.reviewHeading.focus()); } },
    editService() { this.step = 1; this.review = false; this.configurationToken = ''; },
    async confirmService() {
      if (!this.complete || this.busy) return;
      if (this.previewMode) { this.previewValidated = true; this.$nextTick(() => this.$refs.previewNotice.focus()); return; }
      this.busy = true; this.error = '';
      try {
        const data = new FormData();
        data.append('selection', JSON.stringify({clientTypeId: this.bookingSelection.clientTypeId, categoryId: this.bookingSelection.categoryId, subcategoryId: this.bookingSelection.subcategoryId, selectedOptions: this.bookingSelection.selectedOptions}));
        for (const [id, file] of Object.entries(this.files)) data.append('option_file_' + id, file);
        const response = await fetch(this.$root.dataset.configureUrl, {method: 'POST', headers: {'X-CSRFToken': this.$root.querySelector('[name=csrfmiddlewaretoken]').value}, body: data});
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Votre sélection doit être vérifiée.');
        this.configurationToken = result.token;
        this.bookingSelection = {...this.bookingSelection, ...result.selection};
        await this.$nextTick();
        await htmx.ajax('GET', this.$root.dataset.calendarUrl, {target: '#calendar-container', swap: 'outerHTML', values: {configuration_token: this.configurationToken}});
        this.step = 2;
        this.$nextTick(() => this.$refs.dateHeading.focus());
      } catch (error) { this.error = error.message || 'Chargement impossible. Réessayez.'; }
      finally { this.busy = false; }
    },
    handleSubmit(event) { if (this.previewMode || this.step !== 4 || !this.configurationToken) { event.preventDefault(); this.step = 1; this.error = 'Confirmez d’abord votre soin et choisissez un créneau.'; } },
    destroy() { for (const url of Object.values(this.previews)) URL.revokeObjectURL(url); }
  }));
});
