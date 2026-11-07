/**
 * TagForge - Precision Editorial Workstation & Labeling Engine
 * Modern, Responsive, Feature-rich Data Annotation Tool
 */

(() => {
  'use strict';

  // --- DEFAULT LABEL PRESETS ---
  const PRESET_TAXONOMIES = {
    mentalHealth4: [
      { id: '1', key: '1', name: 'Normal', desc: 'Objektif / Doa / Solusi Praktis', color: 'secondary' },
      { id: '2', key: '2', name: 'Stress', desc: 'Beban Berat / Pusing / Revisi / Dosen Killer', color: 'amber' },
      { id: '3', key: '3', name: 'Cemas', desc: 'Khawatir Berlebihan / Panik / Overthinking', color: 'primary' },
      { id: '4', key: '4', name: 'Depresi', desc: 'Putus Asa / Trauma Berat / RSJ / Psikiater', color: 'error' }
    ],
    sentiment5: [
      { id: '1', key: '1', name: 'Positif', desc: 'Sentimen Baik & Pujian', color: 'secondary' },
      { id: '2', key: '2', name: 'Negatif', desc: 'Kritik / Komplain', color: 'error' },
      { id: '3', key: '3', name: 'Netral', desc: 'Objektif Biasa', color: 'outline' },
      { id: '4', key: '4', name: 'Keluhan Layanan', desc: 'Isu Staf / Pengiriman', color: 'tertiary' },
      { id: '5', key: '5', name: 'Pertanyaan / FAQ', desc: 'Inquiry Konsumen', color: 'primary' }
    ],
    sentiment3: [
      { id: '1', key: '1', name: 'Positif', desc: 'Pujian / Kepuasan', color: 'secondary' },
      { id: '2', key: '2', name: 'Negatif', desc: 'Kritik / Keluhan', color: 'error' },
      { id: '3', key: '3', name: 'Netral', desc: 'Objektif / Informasi', color: 'outline' }
    ],
    binary: [
      { id: '1', key: '1', name: 'Relevan', desc: 'Sesuai topik penelitian', color: 'secondary' },
      { id: '2', key: '2', name: 'Tidak Relevan', desc: 'Spam / Out of topic', color: 'error' }
    ]
  };

  // Color theme definitions mapped to Material 3 tokens
  const COLOR_MAP = {
    secondary: {
      key: 'secondary',
      label: 'Mint Emerald',
      colorBg: 'bg-secondary-container/20',
      colorText: 'text-secondary',
      dotBg: 'bg-secondary',
      badgeBg: 'bg-secondary',
      badgeText: 'text-on-secondary',
      kbdBg: 'bg-secondary',
      kbdText: 'text-on-secondary',
      ringColor: 'ring-secondary'
    },
    error: {
      key: 'error',
      label: 'Coral Red',
      colorBg: 'bg-error-container/30',
      colorText: 'text-error',
      dotBg: 'bg-error',
      badgeBg: 'bg-error',
      badgeText: 'text-on-error',
      kbdBg: 'bg-error',
      kbdText: 'text-on-error',
      ringColor: 'ring-error'
    },
    primary: {
      key: 'primary',
      label: 'Sky Blue',
      colorBg: 'bg-primary-container/30',
      colorText: 'text-primary',
      dotBg: 'bg-primary',
      badgeBg: 'bg-primary',
      badgeText: 'text-on-primary',
      kbdBg: 'bg-primary',
      kbdText: 'text-on-primary',
      ringColor: 'ring-primary'
    },
    tertiary: {
      key: 'tertiary',
      label: 'Lavender Violet',
      colorBg: 'bg-tertiary-container/30',
      colorText: 'text-tertiary',
      dotBg: 'bg-tertiary',
      badgeBg: 'bg-tertiary',
      badgeText: 'text-on-tertiary',
      kbdBg: 'bg-tertiary',
      kbdText: 'text-on-tertiary',
      ringColor: 'ring-tertiary'
    },
    amber: {
      key: 'amber',
      label: 'Warm Amber',
      colorBg: 'bg-amber-500/20',
      colorText: 'text-amber-300',
      dotBg: 'bg-amber-400',
      badgeBg: 'bg-amber-400',
      badgeText: 'text-stone-900',
      kbdBg: 'bg-amber-400',
      kbdText: 'text-stone-900',
      ringColor: 'ring-amber-400'
    },
    outline: {
      key: 'outline',
      label: 'Silver Slate',
      colorBg: 'bg-surface-variant',
      colorText: 'text-on-surface',
      dotBg: 'bg-outline',
      badgeBg: 'bg-outline',
      badgeText: 'text-surface-dim',
      kbdBg: 'bg-on-surface',
      kbdText: 'text-surface',
      ringColor: 'ring-outline'
    }
  };

  // --- APPLICATION STATE ---
  const state = {
    // Dataset
    rawCsv: '',
    fileName: '',
    headers: [],
    rows: [], // Array of row objects { _index, [col]: val, _label, _skipped, _labeledAt }
    currentIndex: 0,
    
    // Column Mappings
    mapping: {
      textColumn: '',
      idColumn: '',
      labelColumn: 'actual_sentiment',
      metadataColumns: []
    },

    // Label Schema (Default 4 Kategori: Normal, Stress, Cemas, Depresi)
    labels: JSON.parse(JSON.stringify(PRESET_TAXONOMIES.mentalHealth4)),

    // Navigation and Filtering
    filterMode: 'all', // 'all', 'unlabeled', 'labeled', 'skipped'
    searchQuery: '',
    queuePage: 1,
    queuePageSize: 20,

    // Statistics & Timers
    sessionStartTime: Date.now(),
    itemStartTime: Date.now(),
    elapsedSeconds: 0,
    labeledCount: 0,
    fontSizeDelta: 0 // 0 = standard, 1 = lg, 2 = xl, -1 = sm
  };

  // --- LOCALSTORAGE KEYS ---
  const STORAGE_KEYS = {
    SETTINGS: 'tagforge_saved_settings_v1',
    ANNOTATIONS_PREFIX: 'tagforge_annotations_data_'
  };

  // --- INITIALIZATION ---
  document.addEventListener('DOMContentLoaded', () => {
    initApp();
  });

  function initApp() {
    loadSettingsFromStorage();
    setupEventListeners();
    setupHotkeys();
    startSessionTimer();
    renderLabelButtons();
    updateAppScreenState();
  }

  // --- STORAGE HELPERS ---
  function loadSettingsFromStorage() {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.labels && Array.isArray(parsed.labels) && parsed.labels.length > 0) {
          state.labels = parsed.labels;
        }
        if (parsed.mapping) {
          state.mapping = Object.assign(state.mapping, parsed.mapping);
        }
      }
    } catch (e) {
      console.warn('Gagal memuat pengaturan tersimpan:', e);
    }
  }

  function saveSettingsToStorage() {
    try {
      const payload = {
        labels: state.labels,
        mapping: state.mapping,
        updatedAt: new Date().toISOString()
      };
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(payload));
      updateAutoSaveStatus('Pengaturan Tersimpan');
    } catch (e) {
      console.warn('Gagal menyimpan pengaturan:', e);
    }
  }

  function saveAnnotationsToStorage() {
    if (!state.fileName || state.rows.length === 0) return;
    try {
      const key = STORAGE_KEYS.ANNOTATIONS_PREFIX + encodeURIComponent(state.fileName);
      const annotationsMap = {};
      state.rows.forEach(r => {
        if (r._label || r._skipped) {
          annotationsMap[r._index] = {
            label: r._label,
            skipped: r._skipped,
            labeledAt: r._labeledAt
          };
        }
      });
      localStorage.setItem(key, JSON.stringify(annotationsMap));
      updateAutoSaveStatus('Auto-save: OK');
    } catch (e) {
      console.warn('Gagal menyimpan anotasi:', e);
    }
  }

  function restoreAnnotationsFromStorage() {
    if (!state.fileName) return;
    try {
      const key = STORAGE_KEYS.ANNOTATIONS_PREFIX + encodeURIComponent(state.fileName);
      const saved = localStorage.getItem(key);
      if (saved) {
        const annotationsMap = JSON.parse(saved);
        state.rows.forEach(r => {
          if (annotationsMap[r._index]) {
            r._label = annotationsMap[r._index].label || '';
            r._skipped = !!annotationsMap[r._index].skipped;
            r._labeledAt = annotationsMap[r._index].labeledAt;
          }
        });
        updateStats();
      }
    } catch (e) {
      console.warn('Gagal memulihkan anotasi tersimpan:', e);
    }
  }

  function updateAutoSaveStatus(text = 'Auto-save: OK') {
    const statusEl = document.getElementById('autosave-indicator');
    if (statusEl) {
      statusEl.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span> ${text}`;
    }
  }

  // --- SCREEN SWITCHER (LANDING VS WORKSPACE) ---
  function updateAppScreenState() {
    const landingScreen = document.getElementById('upload-landing-screen');
    const workspaceScreen = document.getElementById('workspace-screen');
    const navChangeCsvBtn = document.getElementById('nav-btn-change-csv');

    if (state.rows.length === 0) {
      if (landingScreen) {
        landingScreen.classList.remove('hidden');
        landingScreen.classList.add('flex');
      }
      if (workspaceScreen) {
        workspaceScreen.classList.add('hidden');
        workspaceScreen.classList.remove('flex');
      }
      if (navChangeCsvBtn) {
        navChangeCsvBtn.classList.add('hidden');
        navChangeCsvBtn.classList.remove('inline-flex');
      }
    } else {
      if (landingScreen) {
        landingScreen.classList.add('hidden');
        landingScreen.classList.remove('flex');
      }
      if (workspaceScreen) {
        workspaceScreen.classList.remove('hidden');
        workspaceScreen.classList.add('flex');
      }
      if (navChangeCsvBtn) {
        navChangeCsvBtn.classList.remove('hidden');
        navChangeCsvBtn.classList.add('inline-flex');
      }
    }
  }

  async function loadWorkspaceCsv() {
    try {
      const response = await fetch('./dataset_mental_health_cleaned.csv');
      if (response.ok) {
        const text = await response.text();
        loadCsvData(text, 'dataset_mental_health_cleaned.csv');
        return;
      }
    } catch (err) {
      console.log('Fetch lokal terhalang protokol file:// browser.');
    }

    // Jika berjalan via file:// dan fetch diblokir browser, picu file input
    showToast('Protokol browser membatasi baca otomatis. Silakan pilih file "dataset_mental_health_cleaned.csv" lewat dialog file.', false);
    document.getElementById('landing-csv-file-input')?.click();
  }

  function parseCsvString(csvString) {
    if (window.Papa && typeof window.Papa.parse === 'function') {
      const parsed = Papa.parse(csvString, {
        header: true,
        skipEmptyLines: true,
        dynamicTyping: false
      });
      return {
        headers: parsed.meta.fields || [],
        data: parsed.data || []
      };
    }

    // Fallback RFC4180 parser
    return fallbackCsvParser(csvString);
  }

  function fallbackCsvParser(text) {
    const lines = [];
    let row = [''];
    let inQuotes = false;

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      const nextChar = text[i + 1];

      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          row[row.length - 1] += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        row.push('');
      } else if ((char === '\r' || char === '\n') && !inQuotes) {
        if (char === '\r' && nextChar === '\n') i++;
        lines.push(row);
        row = [''];
      } else {
        row[row.length - 1] += char;
      }
    }
    if (row.length > 1 || row[0] !== '') lines.push(row);

    if (lines.length === 0) return { headers: [], data: [] };

    const headers = lines[0].map(h => h.trim());
    const data = [];

    for (let i = 1; i < lines.length; i++) {
      const currentLine = lines[i];
      if (currentLine.length < headers.length && currentLine.every(c => c === '')) continue;
      const obj = {};
      headers.forEach((h, idx) => {
        obj[h] = currentLine[idx] !== undefined ? currentLine[idx] : '';
      });
      data.push(obj);
    }

    return { headers, data };
  }

  function loadCsvData(csvText, filename = 'dataset.csv') {
    state.rawCsv = csvText;
    state.fileName = filename;

    const parsed = parseCsvString(csvText);
    state.headers = parsed.headers;

    // Detect mapping intelligently
    autoDetectColumnMapping(parsed.headers);

    // Transform rows
    state.rows = parsed.data.map((rowObj, index) => {
      const existingLabel = rowObj[state.mapping.labelColumn] || '';
      return {
        ...rowObj,
        _index: index,
        _label: existingLabel ? String(existingLabel).trim() : '',
        _skipped: false,
        _labeledAt: existingLabel ? Date.now() : null
      };
    });

    // Restore cached annotations for this file if available
    restoreAnnotationsFromStorage();

    // Reset current index to first unlabeled row
    const firstUnlabeled = state.rows.findIndex(r => !r._label && !r._skipped);
    state.currentIndex = firstUnlabeled >= 0 ? firstUnlabeled : 0;

    // Render components
    renderMappingDropdowns();
    renderLabelButtons();
    renderCurrentRecord();
    updateStats();
    renderQueueTable();
    updateAppScreenState();
    openModal('modal-mapping');
    showToast(`Dataset "${filename}" berhasil dimuat (${state.rows.length} baris).`, true);
  }

  function autoDetectColumnMapping(headers) {
    if (!headers || headers.length === 0) return;

    // Auto text column
    const textCandidates = ['comment_text', 'text', 'clean_text', 'content', 'tweet', 'review', 'pesan', 'kalimat', 'body'];
    const matchedText = textCandidates.find(c => headers.includes(c));
    state.mapping.textColumn = matchedText || headers.find(h => h.toLowerCase().includes('text')) || headers[0];

    // Auto ID column
    const idCandidates = ['comment_id', 'id', 'post_id', 'no', 'index', 'tweet_id'];
    const matchedId = idCandidates.find(c => headers.includes(c));
    state.mapping.idColumn = matchedId || headers.find(h => h.toLowerCase().includes('id')) || headers[0];

    // Auto Label column
    const labelCandidates = ['actual_sentiment', 'sentiment', 'label', 'kategori', 'category', 'class', 'annotation'];
    const matchedLabel = labelCandidates.find(c => headers.includes(c));
    state.mapping.labelColumn = matchedLabel || 'actual_sentiment';

    // Auto Metadata columns
    const metaCandidates = ['author', 'platform', 'post_title', 'parent_text', 'like_count', 'reply_count', 'created_at', 'search_keyword'];
    state.mapping.metadataColumns = headers.filter(h => metaCandidates.includes(h));

    // Save mapping setting
    saveSettingsToStorage();
  }

  // --- RECORD RENDERING ---
  function renderCurrentRecord() {
    if (state.rows.length === 0) {
      renderEmptyState();
      return;
    }

    const row = state.rows[state.currentIndex];
    if (!row) return;

    // Counter and Index
    const totalCount = state.rows.length;
    const itemIndex = state.currentIndex + 1;
    
    document.getElementById('counter-badge').textContent = `Data #${itemIndex} dari ${totalCount}`;
    const mobileCounter = document.getElementById('mobile-counter-badge');
    if (mobileCounter) mobileCounter.textContent = `#${itemIndex} / ${totalCount}`;
    
    // Status Pill
    const statusPill = document.getElementById('sample-status-pill');
    if (row._label) {
      const activeColor = getLabelColorDef(row._label);
      statusPill.textContent = `TERLABELI: ${row._label.toUpperCase()}`;
      statusPill.className = `inline-flex items-center px-space-md py-space-2xs rounded-full ${activeColor.colorBg} ${activeColor.colorText} font-label-sm text-label-sm uppercase tracking-wider font-semibold ring-1 ${activeColor.ringColor}`;
    } else if (row._skipped) {
      statusPill.textContent = 'DILEWATI';
      statusPill.className = 'inline-flex items-center px-space-md py-space-2xs rounded-full bg-amber-500/20 text-amber-300 font-label-sm text-label-sm uppercase tracking-wider font-medium';
    } else {
      statusPill.textContent = 'BELUM DILABELI';
      statusPill.className = 'inline-flex items-center px-space-md py-space-2xs rounded-full bg-surface-container-highest text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider';
    }

    // Record ID
    const idVal = row[state.mapping.idColumn] || `#${itemIndex}`;
    const idEl = document.getElementById('record-id-display');
    if (idEl) idEl.textContent = `ID: ${idVal}`;

    // Corpus Text
    const textVal = row[state.mapping.textColumn] || '(Teks kolom kosong atau kolom belum dipilih)';
    const textEl = document.getElementById('corpus-text-body');
    if (textEl) {
      textEl.textContent = `“${textVal}”`;
      applyTextSize(textEl);
    }

    // Text metrics (characters and words)
    const charCount = textVal.length;
    const wordCount = textVal.trim().split(/\s+/).filter(Boolean).length;
    const charEl = document.getElementById('char-count-display');
    const wordEl = document.getElementById('word-count-display');
    if (charEl) charEl.textContent = `${charCount} Karakter`;
    if (wordEl) wordEl.textContent = `${wordCount} Kata`;

    // Metadata & Context Chips
    renderMetadataAccordion(row);

    // Active Selection Badge in Card
    renderActiveTagBadge(row._label);

    // Update Label Buttons Highlight
    highlightActiveLabelButton(row._label);

    // Reset item timer
    state.itemStartTime = Date.now();
  }

  function renderMetadataAccordion(row) {
    const metaContainer = document.getElementById('metadata-chips-container');
    if (!metaContainer) return;

    metaContainer.innerHTML = '';

    const cols = state.mapping.metadataColumns || [];
    if (cols.length === 0) {
      metaContainer.innerHTML = `<span class="text-outline text-[12px] italic">Tidak ada metadata tambahan yang dimapping.</span>`;
      return;
    }

    cols.forEach(col => {
      const val = row[col];
      if (val !== undefined && val !== null && String(val).trim() !== '') {
        const chip = document.createElement('div');
        chip.className = 'inline-flex items-center gap-1.5 px-space-sm py-space-2xs rounded-md bg-surface-container-high border border-outline/20 text-on-surface-variant text-[12px]';
        
        let icon = 'tag';
        if (col.includes('author') || col.includes('user')) icon = 'person';
        if (col.includes('platform')) icon = 'hub';
        if (col.includes('title')) icon = 'title';
        if (col.includes('parent')) icon = 'reply';
        if (col.includes('date') || col.includes('created')) icon = 'schedule';
        if (col.includes('like')) icon = 'thumb_up';

        chip.innerHTML = `
          <span class="material-symbols-outlined text-[13px] text-primary">${icon}</span>
          <span class="text-outline font-medium">${col}:</span>
          <span class="text-on-surface font-semibold max-w-[200px] truncate" title="${escapeHtml(String(val))}">${escapeHtml(String(val))}</span>
        `;
        metaContainer.appendChild(chip);
      }
    });

    // If there is parent_text or post_title, show extended quote box
    const contextBox = document.getElementById('context-quote-box');
    const parentText = row['parent_text'] || row['post_title'];
    if (contextBox) {
      if (parentText && String(parentText).trim() !== '' && parentText !== row[state.mapping.textColumn]) {
        contextBox.classList.remove('hidden');
        contextBox.innerHTML = `
          <div class="flex items-start gap-2 p-3 rounded-lg bg-surface-container-lowest/80 border border-outline/20 text-body-sm text-on-surface-variant">
            <span class="material-symbols-outlined text-tertiary text-[18px] shrink-0 mt-0.5">forum</span>
            <div class="flex flex-col gap-1 min-w-0">
              <span class="font-label-sm text-[11px] font-bold text-tertiary uppercase tracking-wider">Konteks / Post Utama</span>
              <p class="text-body-sm text-on-surface line-clamp-3 italic">"${escapeHtml(String(parentText))}"</p>
            </div>
          </div>
        `;
      } else {
        contextBox.classList.add('hidden');
        contextBox.innerHTML = '';
      }
    }
  }

  function renderActiveTagBadge(currentLabel) {
    const noTagPrompt = document.getElementById('no-tag-prompt');
    const selectedBadge = document.getElementById('selected-badge');
    const selectedBadgeLabel = document.getElementById('selected-badge-label');

    if (!selectedBadge || !noTagPrompt || !selectedBadgeLabel) return;

    if (currentLabel) {
      const colorDef = getLabelColorDef(currentLabel);
      noTagPrompt.classList.add('hidden');
      selectedBadge.classList.remove('hidden');
      selectedBadge.className = `flex items-center gap-space-xs px-space-md py-space-2xs rounded-lg font-label-sm text-label-sm ${colorDef.colorBg} ${colorDef.colorText} ring-1 ${colorDef.ringColor} shadow-sm`;
      selectedBadgeLabel.textContent = currentLabel;
    } else {
      selectedBadge.classList.add('hidden');
      noTagPrompt.classList.remove('hidden');
    }
  }

  function highlightActiveLabelButton(currentLabel) {
    const buttons = document.querySelectorAll('.label-choice');
    buttons.forEach(btn => {
      const name = btn.getAttribute('data-label-name');
      if (name && currentLabel && name.toLowerCase() === currentLabel.toLowerCase()) {
        btn.classList.add('is-active', 'ring-2', 'ring-primary');
      } else {
        btn.classList.remove('is-active', 'ring-2', 'ring-primary');
      }
    });
  }

  function renderEmptyState() {
    const textEl = document.getElementById('corpus-text-body');
    if (textEl) {
      textEl.innerHTML = `<span class="text-outline italic">Tidak ada dataset aktif. Silakan unggah file CSV atau klik tombol di bawah untuk memuat data.</span>`;
    }
  }

  // --- LABEL BUTTONS GRID RENDERING ---
  function renderLabelButtons() {
    const grid = document.getElementById('label-buttons-grid');
    if (!grid) return;

    grid.innerHTML = '';

    state.labels.forEach((lbl, idx) => {
      const colorDef = COLOR_MAP[lbl.color] || COLOR_MAP.primary;
      const keyDisplay = lbl.key || String(idx + 1);

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'label-choice group relative flex flex-col items-start p-space-md rounded-xl bg-surface-container-low hover:bg-surface-container transition-all text-left shadow-sm border border-transparent hover:border-outline/30';
      btn.setAttribute('data-label-name', lbl.name);
      btn.setAttribute('data-label-key', keyDisplay);

      btn.innerHTML = `
        <div class="flex items-center justify-between w-full mb-space-xs">
          <kbd class="font-kbd-badge text-kbd-badge px-space-xs py-space-2xs rounded bg-surface-container-highest ${colorDef.colorText} group-hover:${colorDef.kbdBg} group-hover:${colorDef.kbdText} transition-colors">${keyDisplay}</kbd>
          <span class="w-2.5 h-2.5 rounded-full ${colorDef.dotBg}"></span>
        </div>
        <span class="font-headline-sm text-headline-sm text-on-surface group-hover:${colorDef.colorText} transition-colors font-semibold truncate w-full">${escapeHtml(lbl.name)}</span>
        <span class="font-label-sm text-label-sm text-on-surface-variant mt-space-2xs line-clamp-1">${escapeHtml(lbl.desc || 'Label Anotasi')}</span>
      `;

      btn.addEventListener('click', () => {
        applyLabel(lbl.name);
      });

      grid.appendChild(btn);
    });

    // Button to open inline Add Label
    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.id = 'btn-open-new-label';
    addBtn.className = 'group relative flex flex-col items-center justify-center p-space-md rounded-xl bg-surface-container-lowest hover:bg-surface-container-low text-on-surface-variant hover:text-primary transition-all text-center shadow-sm border border-dashed border-outline/30';
    addBtn.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-surface-container-high group-hover:bg-primary-container flex items-center justify-center mb-space-xs text-primary transition-colors">
        <span class="material-symbols-outlined text-[18px]">add</span>
      </div>
      <span class="font-label-sm text-label-sm font-semibold">Tambah Label</span>
      <span class="font-code-sm text-code-sm text-outline mt-space-2xs">Kustom Baru</span>
    `;
    addBtn.addEventListener('click', toggleQuickAddPanel);
    grid.appendChild(addBtn);

    // Update label counter header
    const shortcutGuide = document.getElementById('shortcut-guide-text');
    if (shortcutGuide) {
      shortcutGuide.textContent = `PILIH LABEL (Pintasan Keyboard 1 - ${Math.min(state.labels.length, 9)})`;
    }
  }

  function getLabelColorDef(labelName) {
    const found = state.labels.find(l => l.name.toLowerCase() === (labelName || '').toLowerCase());
    if (found && COLOR_MAP[found.color]) {
      return COLOR_MAP[found.color];
    }
    return COLOR_MAP.primary;
  }

  // --- LABEL APPLICATION LOGIC ---
  function applyLabel(labelName) {
    if (state.rows.length === 0) return;

    const row = state.rows[state.currentIndex];
    if (!row) return;

    // Toggle off if clicking the already chosen label
    if (row._label === labelName) {
      row._label = '';
      row._skipped = false;
      showToast(`Label "${labelName}" dibatalkan.`);
    } else {
      row._label = labelName;
      row._skipped = false;
      row._labeledAt = Date.now();
      showToast(`Label "${labelName}" dipilih.`);
    }

    renderCurrentRecord();
    updateStats();
    saveAnnotationsToStorage();
  }

  function removeCurrentLabel() {
    if (state.rows.length === 0) return;
    const row = state.rows[state.currentIndex];
    if (!row) return;

    row._label = '';
    renderCurrentRecord();
    updateStats();
    saveAnnotationsToStorage();
    showToast('Label dihapus.');
  }

  function submitAndNext() {
    if (state.rows.length === 0) return;

    const row = state.rows[state.currentIndex];
    if (!row._label) {
      showToast('Pilih label terlebih dahulu atau tekan Lewati [S]', false);
      return;
    }

    showToast(`Data #${state.currentIndex + 1} disimpan sebagai "${row._label}". Melanjutkan...`);

    // Advance to next row
    navigateToNext();
  }

  function skipCurrent() {
    if (state.rows.length === 0) return;

    const row = state.rows[state.currentIndex];
    row._skipped = true;
    showToast(`Data #${state.currentIndex + 1} dilewati.`);

    saveAnnotationsToStorage();
    navigateToNext();
  }

  function navigateToNext() {
    if (state.currentIndex < state.rows.length - 1) {
      state.currentIndex++;
      renderCurrentRecord();
      updateQueueActiveRow();
    } else {
      showToast('🎉 Selamat! Anda telah mencapai akhir dataset.');
    }
  }

  function navigateToPrev() {
    if (state.currentIndex > 0) {
      state.currentIndex--;
      renderCurrentRecord();
      updateQueueActiveRow();
      showToast(`Kembali ke Data #${state.currentIndex + 1}.`);
    } else {
      showToast('Ini adalah data pertama.');
    }
  }

  function jumpToRow(targetIndex) {
    if (targetIndex >= 0 && targetIndex < state.rows.length) {
      state.currentIndex = targetIndex;
      renderCurrentRecord();
      updateQueueActiveRow();
      closeAllModals();
      showToast(`Beralih ke Data #${targetIndex + 1}.`);
    }
  }

  // --- STATS & METRICS ---
  function updateStats() {
    const total = state.rows.length;
    if (total === 0) return;

    const labeled = state.rows.filter(r => !!r._label).length;
    const skipped = state.rows.filter(r => r._skipped).length;
    const percentage = ((labeled / total) * 100).toFixed(1);

    // Desktop header stats
    const progressText = document.getElementById('progress-counter-text');
    if (progressText) progressText.textContent = `${labeled} / ${total}`;

    const progressFill = document.getElementById('progress-bar-fill');
    if (progressFill) progressFill.style.width = `${percentage}%`;

    const percentText = document.getElementById('progress-percent-text');
    if (percentText) percentText.textContent = `${percentage}%`;

    // Speed calculation
    const elapsedMinutes = Math.max((Date.now() - state.sessionStartTime) / 60000, 0.1);
    const speed = Math.round(labeled / elapsedMinutes);
    const speedEl = document.getElementById('annotator-speed-display');
    if (speedEl) speedEl.textContent = `${speed} / mnt`;

    // Queue tab count badges
    const allTab = document.getElementById('tab-queue-all-count');
    const unlabeledTab = document.getElementById('tab-queue-unlabeled-count');
    const labeledTab = document.getElementById('tab-queue-labeled-count');
    const skippedTab = document.getElementById('tab-queue-skipped-count');

    if (allTab) allTab.textContent = total;
    if (unlabeledTab) unlabeledTab.textContent = total - labeled - skipped;
    if (labeledTab) labeledTab.textContent = labeled;
    if (skippedTab) skippedTab.textContent = skipped;

    // Render distribution bars in export modal
    renderDistributionStats(labeled, total);
  }

  function renderDistributionStats(labeled, total) {
    const distContainer = document.getElementById('label-distribution-container');
    if (!distContainer) return;

    distContainer.innerHTML = '';

    const labelCounts = {};
    state.labels.forEach(l => { labelCounts[l.name] = 0; });

    state.rows.forEach(r => {
      if (r._label && labelCounts[r._label] !== undefined) {
        labelCounts[r._label]++;
      }
    });

    state.labels.forEach(lbl => {
      const count = labelCounts[lbl.name] || 0;
      const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
      const colorDef = COLOR_MAP[lbl.color] || COLOR_MAP.primary;

      const item = document.createElement('div');
      item.className = 'flex flex-col gap-1';
      item.innerHTML = `
        <div class="flex items-center justify-between text-body-sm">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full ${colorDef.dotBg}"></span>
            <span class="font-medium text-on-surface">${escapeHtml(lbl.name)}</span>
          </div>
          <span class="font-code-sm text-outline">${count} (${pct}%)</span>
        </div>
        <div class="w-full h-2 rounded-full bg-surface-container-highest overflow-hidden">
          <div class="h-full ${colorDef.badgeBg} transition-all duration-300" style="width: ${pct}%"></div>
        </div>
      `;
      distContainer.appendChild(item);
    });
  }

  function startSessionTimer() {
    const timerEl = document.getElementById('session-timer');
    const mobileTimer = document.getElementById('label-timer');

    setInterval(() => {
      state.elapsedSeconds++;
      const mins = String(Math.floor(state.elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(state.elapsedSeconds % 60).padStart(2, '0');
      const formatted = `${mins}:${secs}s`;

      if (timerEl) timerEl.textContent = formatted;
      if (mobileTimer) mobileTimer.textContent = formatted;
    }, 1000);
  }

  // --- COLUMN MAPPING UI ---
  function renderMappingDropdowns() {
    const textSelect = document.getElementById('mapping-text-col');
    const idSelect = document.getElementById('mapping-id-col');
    const labelSelect = document.getElementById('mapping-label-col');
    const metaCheckboxes = document.getElementById('mapping-meta-checkboxes');

    if (!textSelect || !idSelect || !labelSelect || !metaCheckboxes) return;

    // Clear options
    textSelect.innerHTML = '';
    idSelect.innerHTML = '<option value="">-- Buat Nomor Baris Otomatis (1, 2, 3...) --</option>';
    labelSelect.innerHTML = '';
    metaCheckboxes.innerHTML = '';

    state.headers.forEach(h => {
      // Text Col
      const textOpt = document.createElement('option');
      textOpt.value = h;
      textOpt.textContent = h;
      if (h === state.mapping.textColumn) textOpt.selected = true;
      textSelect.appendChild(textOpt);

      // ID Col
      const idOpt = document.createElement('option');
      idOpt.value = h;
      idOpt.textContent = h;
      if (h === state.mapping.idColumn) idOpt.selected = true;
      idSelect.appendChild(idOpt);

      // Label Col
      const lblOpt = document.createElement('option');
      lblOpt.value = h;
      lblOpt.textContent = h;
      if (h === state.mapping.labelColumn) lblOpt.selected = true;
      labelSelect.appendChild(lblOpt);

      // Metadata Checkbox
      const checkWrap = document.createElement('label');
      checkWrap.className = 'flex items-center gap-2 p-2 rounded-lg bg-surface-container-lowest hover:bg-surface-container text-body-sm text-on-surface cursor-pointer transition-colors';
      const isChecked = state.mapping.metadataColumns.includes(h);
      checkWrap.innerHTML = `
        <input type="checkbox" value="${escapeHtml(h)}" class="meta-col-cb accent-primary rounded w-4 h-4" ${isChecked ? 'checked' : ''}>
        <span class="truncate">${escapeHtml(h)}</span>
      `;
      metaCheckboxes.appendChild(checkWrap);
    });

    // Option to add new label column name
    const newLblOpt = document.createElement('option');
    newLblOpt.value = '__custom_new__';
    newLblOpt.textContent = '+ Ketik Nama Kolom Baru...';
    labelSelect.appendChild(newLblOpt);

    updateMappingPreview();
  }

  function updateMappingPreview() {
    const previewBox = document.getElementById('mapping-live-preview');
    if (!previewBox || state.rows.length === 0) return;

    const sampleRow = state.rows[0];
    const textCol = document.getElementById('mapping-text-col')?.value || state.mapping.textColumn;
    const idCol = document.getElementById('mapping-id-col')?.value || state.mapping.idColumn;
    
    previewBox.innerHTML = `
      <div class="p-3 rounded-lg bg-surface-container-lowest border border-outline/20 flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-[11px] text-outline font-code-sm">
          <span>ID: ${escapeHtml(String(sampleRow[idCol] || '#1'))}</span>
          <span class="text-primary font-bold">Pratinjau Baris #1</span>
        </div>
        <p class="text-body-sm text-on-surface line-clamp-3">“${escapeHtml(String(sampleRow[textCol] || ''))}”</p>
      </div>
    `;
  }

  function applyMappingChanges() {
    const textSelect = document.getElementById('mapping-text-col');
    const idSelect = document.getElementById('mapping-id-col');
    const labelSelect = document.getElementById('mapping-label-col');
    const customLabelInput = document.getElementById('mapping-custom-label-input');

    if (textSelect) state.mapping.textColumn = textSelect.value;
    if (idSelect) state.mapping.idColumn = idSelect.value;

    if (labelSelect) {
      if (labelSelect.value === '__custom_new__' && customLabelInput && customLabelInput.value.trim()) {
        const customName = customLabelInput.value.trim();
        state.mapping.labelColumn = customName;
        if (!state.headers.includes(customName)) {
          state.headers.push(customName);
        }
      } else {
        state.mapping.labelColumn = labelSelect.value;
      }
    }

    // Selected meta columns
    const checkboxes = document.querySelectorAll('.meta-col-cb:checked');
    state.mapping.metadataColumns = Array.from(checkboxes).map(cb => cb.value);

    saveSettingsToStorage();
    renderCurrentRecord();
    renderQueueTable();
    closeAllModals();
    showToast('Pemetaan kolom CSV berhasil diperbarui!', true);
  }

  // --- LABEL TAXONOMY MANAGER ---
  function renderTaxonomyList() {
    const listContainer = document.getElementById('taxonomy-manager-list');
    if (!listContainer) return;

    listContainer.innerHTML = '';

    state.labels.forEach((lbl, idx) => {
      const colorDef = COLOR_MAP[lbl.color] || COLOR_MAP.primary;
      const row = document.createElement('div');
      row.className = 'flex items-center justify-between p-3 rounded-xl bg-surface-container-lowest border border-outline/20 hover:border-outline/50 transition-all';
      row.innerHTML = `
        <div class="flex items-center gap-3 min-w-0">
          <kbd class="font-kbd-badge text-kbd-badge px-2 py-1 rounded ${colorDef.kbdBg} ${colorDef.kbdText} font-bold">${lbl.key || idx + 1}</kbd>
          <div class="flex flex-col min-w-0">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full ${colorDef.dotBg}"></span>
              <span class="font-headline-sm text-sm text-on-surface font-semibold truncate">${escapeHtml(lbl.name)}</span>
            </div>
            <span class="text-[12px] text-outline truncate">${escapeHtml(lbl.desc || '-')}</span>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <button type="button" class="btn-delete-label w-8 h-8 rounded-lg text-outline hover:text-error hover:bg-surface-container flex items-center justify-center transition-colors" data-label-name="${escapeHtml(lbl.name)}" title="Hapus Label">
            <span class="material-symbols-outlined text-[18px]">delete</span>
          </button>
        </div>
      `;

      row.querySelector('.btn-delete-label').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteLabel(lbl.name);
      });

      listContainer.appendChild(row);
    });
  }

  function addNewLabel(name, desc, color) {
    if (!name || !name.trim()) return;

    const trimmed = name.trim();
    if (state.labels.some(l => l.name.toLowerCase() === trimmed.toLowerCase())) {
      showToast(`Label "${trimmed}" sudah ada!`, false);
      return;
    }

    const nextKey = String(Math.min(state.labels.length + 1, 9));
    state.labels.push({
      id: String(Date.now()),
      key: nextKey,
      name: trimmed,
      desc: desc ? desc.trim() : 'Label Anotasi Kustom',
      color: color || 'secondary'
    });

    saveSettingsToStorage();
    renderLabelButtons();
    renderTaxonomyList();
    renderCurrentRecord();
    showToast(`Label baru "${trimmed}" ditambahkan.`, true);
  }

  function deleteLabel(name) {
    if (state.labels.length <= 1) {
      showToast('Minimal harus ada 1 label.', false);
      return;
    }

    state.labels = state.labels.filter(l => l.name.toLowerCase() !== name.toLowerCase());
    // Re-index hotkeys
    state.labels.forEach((l, idx) => {
      l.key = String(idx + 1);
    });

    saveSettingsToStorage();
    renderLabelButtons();
    renderTaxonomyList();
    renderCurrentRecord();
    showToast(`Label "${name}" dihapus.`);
  }

  function loadPresetTaxonomy(presetKey) {
    if (PRESET_TAXONOMIES[presetKey]) {
      state.labels = JSON.parse(JSON.stringify(PRESET_TAXONOMIES[presetKey]));
      saveSettingsToStorage();
      renderLabelButtons();
      renderTaxonomyList();
      renderCurrentRecord();
      showToast(`Preset label "${presetKey}" berhasil diterapkan!`, true);
    }
  }

  // --- QUEUE / BATCH TABLE ---
  function renderQueueTable() {
    const tableBody = document.getElementById('queue-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';

    // Filter rows
    let filtered = state.rows.filter(r => {
      if (state.filterMode === 'unlabeled') return !r._label && !r._skipped;
      if (state.filterMode === 'labeled') return !!r._label;
      if (state.filterMode === 'skipped') return r._skipped;
      return true;
    });

    // Search query filter
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(r => {
        const text = String(r[state.mapping.textColumn] || '').toLowerCase();
        const id = String(r[state.mapping.idColumn] || '').toLowerCase();
        const lbl = String(r._label || '').toLowerCase();
        return text.includes(q) || id.includes(q) || lbl.includes(q);
      });
    }

    const totalFiltered = filtered.length;
    const startIndex = (state.queuePage - 1) * state.queuePageSize;
    const pageRows = filtered.slice(startIndex, startIndex + state.queuePageSize);

    // Update pagination labels
    const pageInfo = document.getElementById('queue-page-info');
    if (pageInfo) {
      const totalPages = Math.max(Math.ceil(totalFiltered / state.queuePageSize), 1);
      pageInfo.textContent = `Halaman ${state.queuePage} dari ${totalPages} (${totalFiltered} item)`;
    }

    if (pageRows.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="py-8 text-center text-outline italic">
            Tidak ada data yang cocok dengan kriteria filter saat ini.
          </td>
        </tr>
      `;
      return;
    }

    pageRows.forEach(r => {
      const tr = document.createElement('tr');
      const isCurrent = r._index === state.currentIndex;
      tr.className = `border-b border-outline/10 hover:bg-surface-container transition-colors cursor-pointer ${isCurrent ? 'bg-primary-container/15' : ''}`;
      
      const idVal = r[state.mapping.idColumn] || `#${r._index + 1}`;
      const textVal = r[state.mapping.textColumn] || '';
      
      let labelPill = '<span class="text-outline text-[12px] italic">Belum Ada</span>';
      if (r._label) {
        const colorDef = getLabelColorDef(r._label);
        labelPill = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${colorDef.colorBg} ${colorDef.colorText}">${escapeHtml(r._label)}</span>`;
      } else if (r._skipped) {
        labelPill = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/20 text-amber-300">Dilewati</span>';
      }

      tr.innerHTML = `
        <td class="p-3 font-code-sm text-outline text-[12px]">#${r._index + 1}</td>
        <td class="p-3 font-code-sm text-primary text-[12px] font-semibold">${escapeHtml(String(idVal))}</td>
        <td class="p-3 text-body-sm text-on-surface max-w-md truncate" title="${escapeHtml(textVal)}">${escapeHtml(textVal)}</td>
        <td class="p-3">${labelPill}</td>
        <td class="p-3 text-right">
          <button type="button" class="px-3 py-1 rounded-lg bg-surface-container-high hover:bg-primary hover:text-on-primary text-on-surface text-[12px] font-semibold transition-colors">
            Anotasi
          </button>
        </td>
      `;

      tr.addEventListener('click', () => {
        jumpToRow(r._index);
      });

      tableBody.appendChild(tr);
    });
  }

  function updateQueueActiveRow() {
    renderQueueTable();
  }

  // --- EXPORT ENGINE ---
  function exportCsv(onlyLabeled = false) {
    if (state.rows.length === 0) {
      showToast('Tidak ada data untuk diekspor.', false);
      return;
    }

    const rowsToExport = onlyLabeled ? state.rows.filter(r => !!r._label) : state.rows;
    if (rowsToExport.length === 0) {
      showToast('Belum ada baris yang dilabeli.', false);
      return;
    }

    // Determine output headers
    const exportHeaders = [...state.headers];
    const targetLabelCol = state.mapping.labelColumn || 'actual_sentiment';
    if (!exportHeaders.includes(targetLabelCol)) {
      exportHeaders.push(targetLabelCol);
    }

    // Generate CSV lines
    const csvRows = [];
    csvRows.push(exportHeaders.map(escapeCsvCell).join(','));

    rowsToExport.forEach(r => {
      const rowCells = exportHeaders.map(col => {
        if (col === targetLabelCol) {
          return escapeCsvCell(r._label || r[col] || '');
        }
        return escapeCsvCell(r[col] !== undefined ? r[col] : '');
      });
      csvRows.push(rowCells.join(','));
    });

    const csvContent = '\uFEFF' + csvRows.join('\r\n'); // Include UTF-8 BOM
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const filename = `labeled_${state.fileName.replace(/\.csv$/i, '')}_${new Date().toISOString().slice(0, 10)}.csv`;
    downloadBlob(blob, filename);
    showToast(`Berhasil mengekspor ${rowsToExport.length} baris ke ${filename}!`, true);
  }

  function exportJson() {
    if (state.rows.length === 0) return;

    const exportData = state.rows.map(r => {
      const cleanObj = {};
      state.headers.forEach(h => { cleanObj[h] = r[h]; });
      cleanObj[state.mapping.labelColumn] = r._label || '';
      cleanObj['_skipped'] = r._skipped;
      cleanObj['_labeledAt'] = r._labeledAt;
      return cleanObj;
    });

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const filename = `labeled_${state.fileName.replace(/\.csv$/i, '')}_${new Date().toISOString().slice(0, 10)}.json`;
    downloadBlob(blob, filename);
    showToast(`Berhasil mengekspor JSON (${exportData.length} item).`, true);
  }

  function exportConfig() {
    const config = {
      version: '1.0',
      appName: 'TagForge',
      exportDate: new Date().toISOString(),
      mapping: state.mapping,
      labels: state.labels
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    downloadBlob(blob, 'tagforge_labeling_config.json');
    showToast('Konfigurasi berhasil diunduh.', true);
  }

  function importConfig(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const config = JSON.parse(e.target.result);
        if (config.labels && Array.isArray(config.labels)) {
          state.labels = config.labels;
        }
        if (config.mapping) {
          state.mapping = Object.assign(state.mapping, config.mapping);
        }
        saveSettingsToStorage();
        renderLabelButtons();
        renderTaxonomyList();
        renderMappingDropdowns();
        renderCurrentRecord();
        showToast('Konfigurasi berhasil diimpor!', true);
      } catch (err) {
        showToast('File konfigurasi JSON tidak valid.', false);
      }
    };
    reader.readAsText(file);
  }

  function escapeCsvCell(cellValue) {
    if (cellValue === null || cellValue === undefined) return '""';
    const str = String(cellValue);
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return `"${str}"`;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // --- UI TOGGLES, MODALS & EVENT LISTENERS ---
  function setupEventListeners() {
    // Navigation Action Buttons
    document.getElementById('btn-prev')?.addEventListener('click', navigateToPrev);
    document.getElementById('btn-skip')?.addEventListener('click', skipCurrent);
    document.getElementById('btn-submit-next')?.addEventListener('click', submitAndNext);
    document.getElementById('btn-remove-tag')?.addEventListener('click', removeCurrentLabel);

    // Quick Add Panel inline
    document.getElementById('btn-cancel-new-label')?.addEventListener('click', toggleQuickAddPanel);
    document.getElementById('btn-save-new-label')?.addEventListener('click', handleQuickAddSave);
    document.getElementById('input-new-label-name')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleQuickAddSave();
      } else if (e.key === 'Escape') {
        toggleQuickAddPanel();
      }
    });

    // Modal Nav Triggers
    document.getElementById('nav-btn-mapping')?.addEventListener('click', () => {
      openModal('modal-mapping');
    });
    document.getElementById('nav-btn-taxonomy')?.addEventListener('click', () => {
      renderTaxonomyList();
      openModal('modal-taxonomy');
    });
    document.getElementById('nav-btn-queue')?.addEventListener('click', () => {
      if (state.rows.length === 0) {
        showToast('Harap masukkan file CSV terlebih dahulu.', false);
        return;
      }
      renderQueueTable();
      openModal('modal-queue');
    });
    document.getElementById('nav-btn-export')?.addEventListener('click', () => {
      if (state.rows.length === 0) {
        showToast('Harap masukkan file CSV terlebih dahulu.', false);
        return;
      }
      updateStats();
      openModal('modal-export');
    });
    document.getElementById('nav-btn-change-csv')?.addEventListener('click', () => {
      document.getElementById('landing-csv-file-input')?.click();
    });

    // Landing Screen Upload Event Handlers
    const landingFileInput = document.getElementById('landing-csv-file-input');
    const landingBrowseBtn = document.getElementById('btn-browse-landing-csv');
    const landingDropZone = document.getElementById('landing-drop-zone');
    const btnLoadLocalCsv = document.getElementById('btn-load-local-project-csv');

    landingBrowseBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      landingFileInput?.click();
    });
    landingFileInput?.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) handleUploadedCsvFile(file);
    });

    if (landingDropZone) {
      ['dragenter', 'dragover'].forEach(name => {
        landingDropZone.addEventListener(name, (e) => {
          e.preventDefault();
          landingDropZone.classList.add('border-primary', 'bg-surface-container-high');
        });
      });
      ['dragleave', 'drop'].forEach(name => {
        landingDropZone.addEventListener(name, (e) => {
          e.preventDefault();
          landingDropZone.classList.remove('border-primary', 'bg-surface-container-high');
        });
      });
      landingDropZone.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file && (file.name.endsWith('.csv') || file.type.includes('csv') || file.type.includes('text'))) {
          handleUploadedCsvFile(file);
        } else {
          showToast('Harap unggah file berformat .csv', false);
        }
      });
    }

    btnLoadLocalCsv?.addEventListener('click', () => {
      loadWorkspaceCsv();
    });

    // Close Modals buttons
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.addEventListener('click', closeAllModals);
    });

    // Close on backdrop click
    document.querySelectorAll('.app-modal').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAllModals();
      });
    });

    // Mapping Modal Actions
    document.getElementById('btn-save-mapping')?.addEventListener('click', applyMappingChanges);
    document.getElementById('mapping-text-col')?.addEventListener('change', updateMappingPreview);
    document.getElementById('mapping-id-col')?.addEventListener('change', updateMappingPreview);
    document.getElementById('mapping-label-col')?.addEventListener('change', (e) => {
      const customWrap = document.getElementById('custom-label-input-wrap');
      if (customWrap) {
        if (e.target.value === '__custom_new__') customWrap.classList.remove('hidden');
        else customWrap.classList.add('hidden');
      }
    });

    // File Upload Handler inside Modal (Drag & Drop + Input)
    const fileInput = document.getElementById('csv-file-input');
    fileInput?.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) handleUploadedCsvFile(file);
    });

    const dropZone = document.getElementById('csv-drop-zone');
    if (dropZone) {
      ['dragenter', 'dragover'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
          e.preventDefault();
          dropZone.classList.add('border-primary', 'bg-surface-container');
        });
      });
      ['dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
          e.preventDefault();
          dropZone.classList.remove('border-primary', 'bg-surface-container');
        });
      });
      dropZone.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file && (file.name.endsWith('.csv') || file.type.includes('csv') || file.type.includes('text'))) {
          handleUploadedCsvFile(file);
        } else {
          showToast('Harap unggah file berformat .csv', false);
        }
      });
    }

    // Taxonomy Presets Buttons
    document.querySelectorAll('.btn-preset-tax').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        if (preset) loadPresetTaxonomy(preset);
      });
    });

    // Add Label in Taxonomy Manager
    document.getElementById('btn-add-tax-label')?.addEventListener('click', () => {
      const nameInput = document.getElementById('input-tax-name');
      const descInput = document.getElementById('input-tax-desc');
      const colorSelect = document.getElementById('select-tax-color');
      if (nameInput && nameInput.value.trim()) {
        addNewLabel(nameInput.value, descInput ? descInput.value : '', colorSelect ? colorSelect.value : 'secondary');
        nameInput.value = '';
        if (descInput) descInput.value = '';
      }
    });

    // Queue Filters
    document.querySelectorAll('.queue-filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.queue-filter-tab').forEach(t => t.classList.remove('bg-primary', 'text-on-primary'));
        tab.classList.add('bg-primary', 'text-on-primary');
        state.filterMode = tab.getAttribute('data-filter') || 'all';
        state.queuePage = 1;
        renderQueueTable();
      });
    });

    // Queue Search
    document.getElementById('queue-search-input')?.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.trim();
      state.queuePage = 1;
      renderQueueTable();
    });

    // Queue Pagination buttons
    document.getElementById('queue-prev-page')?.addEventListener('click', () => {
      if (state.queuePage > 1) {
        state.queuePage--;
        renderQueueTable();
      }
    });
    document.getElementById('queue-next-page')?.addEventListener('click', () => {
      const filtered = state.rows.filter(r => {
        if (state.filterMode === 'unlabeled') return !r._label && !r._skipped;
        if (state.filterMode === 'labeled') return !!r._label;
        if (state.filterMode === 'skipped') return r._skipped;
        return true;
      });
      const totalPages = Math.ceil(filtered.length / state.queuePageSize);
      if (state.queuePage < totalPages) {
        state.queuePage++;
        renderQueueTable();
      }
    });

    // Export Action Buttons
    document.getElementById('btn-export-full-csv')?.addEventListener('click', () => exportCsv(false));
    document.getElementById('btn-export-labeled-csv')?.addEventListener('click', () => exportCsv(true));
    document.getElementById('btn-export-json')?.addEventListener('click', exportJson);
    document.getElementById('btn-export-config')?.addEventListener('click', exportConfig);

    const importConfigFile = document.getElementById('input-import-config');
    importConfigFile?.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) importConfig(file);
    });

    // Font size toggles
    document.getElementById('btn-text-size-down')?.addEventListener('click', () => {
      state.fontSizeDelta = Math.max(state.fontSizeDelta - 1, -1);
      renderCurrentRecord();
    });
    document.getElementById('btn-text-size-up')?.addEventListener('click', () => {
      state.fontSizeDelta = Math.min(state.fontSizeDelta + 1, 2);
      renderCurrentRecord();
    });

    // Jump Input
    const jumpInput = document.getElementById('input-jump-row');
    document.getElementById('btn-jump-row')?.addEventListener('click', () => {
      if (jumpInput && jumpInput.value) {
        const target = parseInt(jumpInput.value, 10) - 1;
        jumpToRow(target);
      }
    });
    jumpInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const target = parseInt(jumpInput.value, 10) - 1;
        jumpToRow(target);
      }
    });

    // Copy Corpus Text
    document.getElementById('btn-copy-corpus')?.addEventListener('click', () => {
      const text = state.rows[state.currentIndex]?.[state.mapping.textColumn] || '';
      navigator.clipboard.writeText(text).then(() => {
        showToast('Teks berhasil disalin ke clipboard!');
      });
    });
  }

  function handleUploadedCsvFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result;
      if (typeof content === 'string') {
        loadCsvData(content, file.name);
        closeAllModals();
        openModal('modal-mapping');
      }
    };
    reader.readAsText(file);
  }

  function toggleQuickAddPanel() {
    const panel = document.getElementById('quick-add-panel');
    const input = document.getElementById('input-new-label-name');
    if (!panel) return;

    panel.classList.toggle('hidden');
    panel.classList.toggle('flex');
    if (!panel.classList.contains('hidden') && input) {
      input.focus();
    }
  }

  function handleQuickAddSave() {
    const input = document.getElementById('input-new-label-name');
    if (input && input.value.trim()) {
      addNewLabel(input.value.trim(), 'Label Kustom', 'secondary');
      input.value = '';
      toggleQuickAddPanel();
    }
  }

  function applyTextSize(textEl) {
    textEl.classList.remove('text-[14px]', 'text-[16px]', 'text-[18px]', 'text-[22px]', 'leading-relaxed', 'leading-loose');
    if (state.fontSizeDelta === -1) {
      textEl.classList.add('text-[14px]', 'leading-normal');
    } else if (state.fontSizeDelta === 1) {
      textEl.classList.add('text-[20px]', 'leading-relaxed');
    } else if (state.fontSizeDelta === 2) {
      textEl.classList.add('text-[24px]', 'leading-loose');
    } else {
      textEl.classList.add('text-[18px]', 'leading-relaxed');
    }
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  }

  function closeAllModals() {
    document.querySelectorAll('.app-modal').forEach(m => {
      m.classList.add('hidden');
      m.classList.remove('flex');
    });
  }

  // --- HOTKEY SYSTEM ---
  function setupHotkeys() {
    window.addEventListener('keydown', (e) => {
      // Don't trigger hotkeys if user is actively typing in an input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        return;
      }

      // Check for numeric keys 1-9 for label selection
      if (['1', '2', '3', '4', '5', '6', '7', '8', '9'].includes(e.key)) {
        const foundLabel = state.labels.find(l => l.key === e.key);
        if (foundLabel) {
          applyLabel(foundLabel.name);
        }
        return;
      }

      const keyUpper = e.key.toUpperCase();
      if (keyUpper === 'A' || e.key === 'ArrowLeft') {
        e.preventDefault();
        navigateToPrev();
      } else if (keyUpper === 'S' || e.key === 'ArrowRight') {
        e.preventDefault();
        skipCurrent();
      } else if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        submitAndNext();
      } else if (e.key === 'Backspace' || e.key === 'Delete') {
        removeCurrentLabel();
      } else if (keyUpper === 'M') {
        e.preventDefault();
        openModal('modal-mapping');
      } else if (keyUpper === 'L') {
        e.preventDefault();
        renderTaxonomyList();
        openModal('modal-taxonomy');
      } else if (keyUpper === 'Q') {
        e.preventDefault();
        renderQueueTable();
        openModal('modal-queue');
      } else if (e.key === 'Escape') {
        closeAllModals();
      }
    });
  }

  // --- TOAST NOTIFICATION ---
  let toastTimeout = null;
  function showToast(message, isSuccess = true) {
    const toast = document.getElementById('toast-notification');
    const toastMsg = document.getElementById('toast-message');
    const toastIcon = document.getElementById('toast-icon');

    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    if (toastIcon) {
      toastIcon.textContent = isSuccess ? 'check_circle' : 'info';
      toastIcon.className = `material-symbols-outlined text-[20px] ${isSuccess ? 'text-secondary' : 'text-amber-400'}`;
    }

    toast.classList.remove('translate-y-16', 'opacity-0', 'pointer-events-none');
    
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toast.classList.add('translate-y-16', 'opacity-0', 'pointer-events-none');
    }, 2200);
  }

  // Helper escape HTML
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

})();
