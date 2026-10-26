// Frontend JavaScript Application Logic for PDF Question-Paper RAG Web UI

async function loadPartials() {
  const elements = document.querySelectorAll('[data-partial]');
  for (const el of elements) {
    const file = el.getAttribute('data-partial');
    if (!file) continue;
    try {
      const res = await fetch(file);
      if (res.ok) {
        const html = await res.text();
        const temp = document.createElement('div');
        temp.innerHTML = html.trim();
        if (temp.firstElementChild) {
          el.replaceWith(temp.firstElementChild);
        } else {
          el.innerHTML = html;
        }
      }
    } catch (e) {
      console.warn("Could not load partial file:", file, e);
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  // Load HTML component partials first
  await loadPartials();

  const searchInput = document.getElementById('searchInput');
  const schoolFilter = document.getElementById('schoolFilter');
  const classFilter = document.getElementById('classFilter');
  const subjectFilter = document.getElementById('subjectFilter');
  const typeFilter = document.getElementById('typeFilter');
  const pageSizeSelect = document.getElementById('pageSizeSelect');
  const searchBtn = document.getElementById('searchBtn');
  const randomBtn = document.getElementById('randomBtn');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const resultsGrid = document.getElementById('resultsGrid');
  const resultsCountHeader = document.getElementById('resultsCountHeader');
  const paginationInfo = document.getElementById('paginationInfo');
  const copyPromptBtn = document.getElementById('copyPromptBtn');
  const samplePills = document.querySelectorAll('.sample-pill');
  const pipelineLoaderCard = document.getElementById('pipelineLoaderCard');

  // Pagination elements
  const paginationBar = document.getElementById('paginationBar');
  const firstPageBtn = document.getElementById('firstPageBtn');
  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const lastPageBtn = document.getElementById('lastPageBtn');
  const pageIndicator = document.getElementById('pageIndicator');

  let currentRagPrompt = "";
  let currentPage = 1;
  let totalPages = 1;
  let isRandomMode = true;

  // Fetch Dataset Summary Stats
  fetchStats();

  // Initial Default Load with Random Questions
  performSearch();

  // Event Listeners
  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      isRandomMode = false;
      currentPage = 1;
      performSearch();
    });
  }

  if (randomBtn) {
    randomBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (clearSearchBtn) clearSearchBtn.style.display = 'none';
      isRandomMode = true;
      currentPage = 1;
      performSearch();
    });
  }

  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      isRandomMode = false;
      currentPage = 1;
      performSearch();
    }
  });

  searchInput.addEventListener('input', () => {
    clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    isRandomMode = true;
    currentPage = 1;
    performSearch();
  });

  if (schoolFilter) {
    schoolFilter.addEventListener('change', () => {
      currentPage = 1;
      performSearch();
    });
  }

  classFilter.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
  });

  subjectFilter.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
  });

  typeFilter.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
  });

  pageSizeSelect.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
  });

  samplePills.forEach(pill => {
    pill.addEventListener('click', () => {
      searchInput.value = pill.getAttribute('data-query');
      clearSearchBtn.style.display = 'block';
      isRandomMode = false;
      currentPage = 1;
      performSearch();
    });
  });

  const scrollToTop = () => {
    if (resultsGrid) resultsGrid.scrollTop = 0;
    const searchSection = document.getElementById('searchTabSection');
    if (searchSection) searchSection.scrollTop = 0;
    const canvas = document.querySelector('.main-content-canvas');
    if (canvas) canvas.scrollTop = 0;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Pagination Listeners
  firstPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage = 1;
      scrollToTop();
      performSearch();
    }
  });

  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      scrollToTop();
      performSearch();
    }
  });

  nextPageBtn.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage++;
      scrollToTop();
      performSearch();
    }
  });

  lastPageBtn.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage = totalPages;
      scrollToTop();
      performSearch();
    }
  });

  copyPromptBtn.addEventListener('click', () => {
    if (!currentRagPrompt) return;
    navigator.clipboard.writeText(currentRagPrompt).then(() => {
      copyPromptBtn.innerText = "✓ Formatted RAG Prompt Context Copied!";
      setTimeout(() => {
        copyPromptBtn.innerText = "📋 Copy Formatted RAG Prompt Context";
      }, 2500);
    });
  });

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        document.getElementById('statPapers').innerText = data.total_papers || 0;
        document.getElementById('statQuestions').innerText = data.total_questions || 0;
        document.getElementById('statImages').innerText = data.total_images || 0;

        if (data.papers && data.papers.length > 0) {
          populateFilterDropdowns(data.papers);
        }
      }
    } catch (err) {
      console.warn("Could not fetch stats:", err);
    }
  }

  function populateFilterDropdowns(papers) {
    const currentClass = classFilter.value;
    const currentSubject = subjectFilter.value;

    const classesSet = new Set(['6', '7', '8', '9', '10', '11', '12']);
    const subjectsMap = {
      'mental_ability': 'Mental Ability / Reasoning',
      'mathematics': 'Mathematics',
      'science': 'Science',
      'physics': 'Physics',
      'chemistry': 'Chemistry',
      'biology': 'Biology',
      'social_science': 'Social Science',
      'english': 'English'
    };

    papers.forEach(p => {
      if (p.class) classesSet.add(String(p.class));
      if (p.subject) {
        const sKey = String(p.subject).toLowerCase();
        if (!subjectsMap[sKey]) {
          subjectsMap[sKey] = sKey.charAt(0).toUpperCase() + sKey.slice(1).replace(/_/g, ' ');
        }
      }
    });

    const sortedClasses = Array.from(classesSet).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));

    classFilter.innerHTML = '<option value="all">All Classes</option>';
    sortedClasses.forEach(cls => {
      const opt = document.createElement('option');
      opt.value = cls;
      opt.textContent = `Class ${cls}`;
      classFilter.appendChild(opt);
    });
    if (classesSet.has(currentClass)) {
      classFilter.value = currentClass;
    } else {
      classFilter.value = "all";
    }

    subjectFilter.innerHTML = '<option value="all">All Subjects</option>';
    Object.keys(subjectsMap).sort().forEach(subjKey => {
      const opt = document.createElement('option');
      opt.value = subjKey;
      opt.textContent = subjectsMap[subjKey];
      subjectFilter.appendChild(opt);
    });
    if (currentSubject && (subjectsMap[currentSubject] || currentSubject === 'all')) {
      subjectFilter.value = currentSubject;
    } else {
      subjectFilter.value = "all";
    }
  }

  function resetLoaderSteps() {
    for (let i = 1; i <= 4; i++) {
      const step = document.getElementById(`step${i}`);
      const status = document.getElementById(`step${i}Status`);
      step.className = "timeline-step";
      status.innerText = "Waiting...";
    }
  }

  function updateStep(stepNum, state, statusText) {
    const step = document.getElementById(`step${stepNum}`);
    const status = document.getElementById(`step${stepNum}Status`);
    step.className = `timeline-step ${state}`;
    status.innerText = statusText;
  }

  async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
      isRandomMode = true;
    }

    searchBtn.disabled = true;
    searchBtn.innerHTML = "<span>Executing Pipeline...</span>";

    pipelineLoaderCard.style.display = "block";
    resetLoaderSteps();

    // Step 1: Vectorizing / Querying Mode
    updateStep(1, "active", isRandomMode ? "Fetching Random Questions..." : "Vectorizing Query...");
    await delay(120);
    updateStep(1, "completed", "Done ✓");

    // Step 2: Querying VectorStore DB
    updateStep(2, "active", "Querying VectorStore DB...");

    try {
      const page_size = parseInt(pageSizeSelect.value, 10) || 10;
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          page: currentPage,
          page_size: page_size,
          class_filter: classFilter ? classFilter.value : 'all',
          subject_filter: subjectFilter ? subjectFilter.value : 'all',
          type_filter: typeFilter ? typeFilter.value : 'all',
          school_filter: schoolFilter ? schoolFilter.value : 'all',
          random_sample: isRandomMode && !query
        })
      });

      if (!res.ok) throw new Error("Search request failed");

      const data = await res.json();
      updateStep(2, "completed", "Done ✓");

      // Step 3: Resolving Diagram PNGs
      updateStep(3, "active", "Resolving images...");
      await delay(100);
      updateStep(3, "completed", "Done ✓");

      // Step 4: Formatting LaTeX & Options Grid
      updateStep(4, "active", "Typesetting LaTeX...");
      
      currentRagPrompt = data.rag_prompt_context || "";
      currentPage = data.page || 1;
      totalPages = data.total_pages || 1;

      renderResults(data);
      scrollToTop();

      updateStep(4, "completed", "Done ✓");
      await delay(200);
      pipelineLoaderCard.style.display = "none";

      // Trigger MathJax LaTeX Typesetting after the async library is ready.
      await typesetMath(resultsGrid);
    } catch (err) {
      console.error(err);
      updateStep(2, "active", "Failed ✕");
      resultsGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚠️</div>
          <h3>Search request failed. Ensure API server is running on port 8000.</h3>
        </div>
      `;
    } finally {
      searchBtn.disabled = false;
      searchBtn.innerHTML = "<span>Execute RAG Pipeline</span>";
    }
  }

  function formatQuestionTypeBadge(qType, requiresImage) {
    if (!qType) return '';
    const typeMap = {
      'single_choice_mcq': 'Multiple Choice',
      'assertion_reason': 'Assertion & Reason',
      'true_false': 'True / False',
      'fill_in_the_blank': 'Fill in Blank',
      'match_the_following': 'Match Following',
      'multiple_choice_multi': 'Multiple Select',
      'short_answer': 'Short Answer',
      'long_answer': 'Long Answer',
      'case_study_passage': 'Case Study',
      'diagram_based': 'Diagram Based',
      'numeric_answer': 'Calculation'
    };
    const label = typeMap[qType] || qType.replace('_', ' ').toUpperCase();
    const imgTag = requiresImage ? ' <span title="Diagram Figure Required">🖼️</span>' : '';
    return `<span class="badge badge-type">${label}${imgTag}</span>`;
  }

  
  // Data Cleaning & Formatting Engine
  function cleanStemText(text) {
    if (!text) return '';
    let cleaned = String(text);
    // Strip page boundary tags
    cleaned = cleaned.replace(/<!?--?\s*PAGE\s*\d+\s*(?:START|END)?\s*--?>/gi, '');
    cleaned = cleaned.replace(/<-?\s*PAGE\s*\d+\s*(?:START|END)?\s*-?>/gi, '');
    cleaned = cleaned.replace(/PAGE\s*\d+\s*(?:START|END)/gi, '');
    // Strip raw image placeholder strings if present
    cleaned = cleaned.replace(/\[IMAGE_PLACEHOLDER_\d+\]/gi, '');
    // A bad extraction must never render unreadable private-font boxes. The
    // backend selects the English page and converts known math glyphs first.
    cleaned = cleaned.replace(/[\ufffc\ufffd\ue000-\uf8ff]/g, '');
    cleaned = cleaned.replace(/[\u0b00-\u0d7f]/g, '');
    // Strip leading punctuation dots or hyphens
    cleaned = cleaned.replace(/^[\s\.\:\-\–\—]+/, '');
    return cleaned.replace(/\s{2,}/g, ' ').trim();
  }

  function cleanOptionText(optText, optLabel) {
    if (!optText) return '';
    let cleaned = String(optText).trim();
    cleaned = cleaned.replace(/\s+\d+\/\d+\/\d+\s*#\s*\d+\s*\|\s*P\s*a\s*g\s*e(?:\s+P\.?\s*T\.?\s*O\.?)?\s*$/i, '');
    if (optLabel) {
      const escapedLabel = String(optLabel).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const prefixPattern = new RegExp(`^\\s*(?:\\(${escapedLabel}\\)|${escapedLabel}[\\.\\)\\:]|#\\d+)\\s*`, 'i');
      cleaned = cleaned.replace(prefixPattern, '');
    }
    cleaned = cleaned.replace(/^[\s\:\-\–\—]+/, '');
    return cleaned.trim();
  }

  function renderMarkdownToHtml(md) {
    if (!md) return '';
    if (window.marked && typeof window.marked.parse === 'function') {
      try { return window.marked.parse(md); } catch (e) { return md; }
    }
    return md;
  }

  async function typesetMath(container) {
    if (!window.MathJax || !window.MathJax.typesetPromise) return;

    try {
      if (window.MathJax.startup && window.MathJax.startup.promise) {
        await window.MathJax.startup.promise;
      }
      await window.MathJax.typesetPromise(container ? [container] : undefined);
    } catch (err) {
      console.warn('MathJax could not typeset the rendered content:', err);
    }
  }

  function renderResults(data) {
    const results = data.results || [];
    const total = data.total_results || 0;
    const page = data.page || 1;
    const pages = data.total_pages || 1;
    const isRand = data.is_random;

    const titlePrefix = isRand ? "Random Sample" : "Search Results";
    resultsCountHeader.innerText = `${titlePrefix} (${total} questions)`;
    paginationInfo.innerText = `Page ${page} of ${pages}`;
    pageIndicator.innerText = `Page ${page} of ${pages}`;

    copyPromptBtn.style.display = results.length > 0 ? "inline-block" : "none";

    // Update Pagination Buttons
    if (pages > 1) {
      paginationBar.style.display = "flex";
      firstPageBtn.disabled = (page <= 1);
      prevPageBtn.disabled = (page <= 1);
      nextPageBtn.disabled = (page >= pages);
      lastPageBtn.disabled = (page >= pages);
    } else {
      paginationBar.style.display = "none";
    }

    if (results.length === 0) {
      resultsGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📂</div>
          <h3>No matching questions found</h3>
          <p>Try adjusting your search query or resetting class/subject dropdowns</p>
        </div>
      `;
      return;
    }

    resultsGrid.innerHTML = "";

    results.forEach(item => {
      const card = document.createElement('div');
      card.className = "question-card";

      const simPct = (item.similarity * 100).toFixed(1);

      const simBadgeHtml = isRand
        ? `<span class="card-sim" style="background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald);">Question Chunk</span>`
        : `<span class="card-sim">${simPct}% Similarity</span>`;

      // Render Options Grid if options exist
      let optionsHtml = "";
      if (item.options && item.options.length > 0) {
        const seenOptionLabels = new Set();
        const displayOptions = item.options.filter(opt => {
          const label = String(opt?.label || '').trim().toUpperCase();
          if (!label || seenOptionLabels.has(label)) return false;
          seenOptionLabels.add(label);
          return true;
        }).slice(0, 4);
        const optionCards = displayOptions.map(opt => `
          <div class="option-card">
            <span class="option-label">${opt.label}</span>
            <span class="option-text">${renderMarkdownToHtml(cleanOptionText(opt.latex_text || opt.text, opt.label))}</span>
          </div>
        `).join("");

        optionsHtml = `
          <div class="options-container">
            <div class="options-title">MCQ Choice Options</div>
            <div class="options-grid">
              ${optionCards}
            </div>
          </div>
        `;
      }

      // Render Subparts Grid if subparts exist
      let subpartsHtml = "";
      if (item.subparts && item.subparts.length > 0) {
        const cleanStemLower = (item.stem_text || "").trim().toLowerCase();
        const validSubparts = item.subparts.filter(sub => {
          if (!sub) return false;
          const sLower = sub.trim().toLowerCase();
          if (sLower === cleanStemLower || (cleanStemLower.length > 20 && cleanStemLower.includes(sLower))) {
            return false;
          }
          return true;
        });

        if (validSubparts.length > 0) {
          const subpartItems = validSubparts.map(sub => {
            const s = sub.trim();
            if (s === "OR" || s === "OR\n" || s === "[OR]" || s === "OR:") {
              return `
                <div class="or-divider">
                  <span class="or-badge">OR</span>
                </div>
              `;
            }
            return `
              <div class="subpart-card">${renderMarkdownToHtml(s)}</div>
            `;
          }).join("");

          subpartsHtml = `
            <div class="subparts-container">
              ${subpartItems}
            </div>
          `;
        }
      }

      // Render Diagram Figure Lightbox if diagrams exist
      let diagramHtml = "";
      let validUrls = (item.image_urls || []).map(u => {
        if (!u) return "";
        let str = String(u).trim();
        if (str.startsWith("{") && str.includes("filename")) {
          const match = str.match(/['"]filename['"]\s*:\s*['"]([^'"]+)['"]/);
          if (match) {
            return `/static/parsed/${item.class}/${item.subject}/${item.year}/${item.paper_id}/images/${match[1]}`;
          }
        }
        return str.replace(/['"\}]/g, "");
      }).filter(Boolean);

      if (validUrls.length === 0 && item.linked_images && item.linked_images.length > 0) {
        validUrls = item.linked_images.map(img => {
          const fn = typeof img === 'object' ? (img.filename || img.relative_path) : String(img);
          const cleanFn = fn ? fn.replace(/^.*[\\\/]/, '').replace(/['"} ]/g, '') : '';
          if (!cleanFn) return '';
          return `/static/parsed/${item.class}/${item.subject}/${item.year}/${item.paper_id}/images/${cleanFn}`;
        }).filter(Boolean);
      }

      if (validUrls.length > 0) {
        const imgTags = validUrls.map(url => `
          <div class="diagram-img-wrapper" onclick="window.openImageLightbox('${url}')">
            <img src="${url}" alt="Linked Diagram Figure" class="diagram-img" loading="lazy" onerror="window.handleImageError(this, '${url}')" />
            <div class="diagram-zoom-hint">🔍 Click to Expand</div>
          </div>
        `).join("");

        diagramHtml = `
          <div class="diagram-container">
            <div class="diagram-header">
              <span class="material-symbols-outlined text-[18px]">image</span>
              <span>Linked Diagram Figures (${validUrls.length})</span>
            </div>
            <div class="diagram-images-grid">
              ${imgTags}
            </div>
          </div>
        `;
      }

      const qTypeBadge = formatQuestionTypeBadge(item.question_type, item.requires_image);

      card.innerHTML = `
        <div class="card-header">
          <div class="card-badges">
            <span class="badge badge-class">Class ${item.class}</span>
            <span class="badge badge-subject">${item.subject}</span>
            <span class="badge badge-year">${item.year}</span>
            <span class="badge badge-qnum">${item.question_number}</span>
            ${qTypeBadge}
          </div>
          ${simBadgeHtml}
        </div>

        <div class="question-stem">${renderMarkdownToHtml(cleanStemText(item.latex_stem || item.stem_text, item.options && item.options.length > 0))}</div>

        ${optionsHtml}
        ${subpartsHtml}
        ${diagramHtml}

        <div class="card-footer-actions" style="margin-top: 16px;">
          <button class="btn-explain-ai" data-target="exp-${item.chunk_id}">
            Solution & Step-by-Step Explanation
          </button>
        </div>
        <div class="explanation-box" id="exp-${item.chunk_id}" style="display:none; margin-top:14px; padding:16px; background:rgba(15,23,42,0.75); border:1px solid rgba(99,102,241,0.4); border-radius:8px; font-size:14px; line-height:1.6; color:var(--text-primary);"></div>
      `;

      // Attach raw data properties directly to the button element
      const explainBtn = card.querySelector('.btn-explain-ai');
      if (explainBtn) {
        explainBtn._chunkId = item.chunk_id;
        explainBtn._questionText = item.stem_text;
        explainBtn._options = item.options || [];
        explainBtn._subparts = item.subparts || [];
        explainBtn._classLevel = item.class;
        explainBtn._subject = item.subject;
      }

      resultsGrid.appendChild(card);
    });

    // Add click listeners for AI Explain buttons
    document.querySelectorAll('.btn-explain-ai').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const targetId = btn.getAttribute('data-target');
        const expBox = document.getElementById(targetId);
        if (!expBox) return;

        if (expBox.style.display === 'block') {
          expBox.style.display = 'none';
          return;
        }

        btn.disabled = true;
        btn.textContent = '⏳ Generating AI Explanation...';
        expBox.style.display = 'block';
        expBox.innerHTML = '<div style="color:var(--accent-cyan); font-weight:600;">Computing solution...</div>';

        try {
          const res = await fetch('/api/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              chunk_id: btn._chunkId || '',
              question_text: btn._questionText || btn.getAttribute('data-stem') || '',
              options: btn._options || [],
              subparts: btn._subparts || [],
              class_level: btn._classLevel || '',
              subject: btn._subject || ''
            })
          });
          const data = await res.json();
          const sourceLabel = data.cache_hit ? 'Saved Solution' : `AI Solution & Concept Explanation (${data.model_used})`;
          expBox.innerHTML = `<div style="font-weight:700; color:var(--accent-cyan); margin-bottom:8px;">${sourceLabel}:</div>${escapeHtml(data.explanation || data.latex_explanation)}`;
          await typesetMath(expBox);
        } catch (err) {
          expBox.innerHTML = `<div style="color:#f87171;">⚠️ Failed to fetch AI explanation: ${err.message}</div>`;
        } finally {
          btn.disabled = false;
          btn.textContent = '💡 Toggle AI Solution & Explanation';
        }
      });
    });
  }

  // Tab Navigation Listeners
  const tabSearchBtn = document.getElementById('tabSearchBtn');
  const tabDraftsBtn = document.getElementById('tabDraftsBtn');
  const tabDedupBtn = document.getElementById('tabDedupBtn');
  const searchTabSection = document.getElementById('searchTabSection');
  const draftsTabSection = document.getElementById('draftsTabSection');
  const dedupTabSection = document.getElementById('dedupTabSection');
  const draftsBadge = document.getElementById('draftsBadge');
  const dedupBadge = document.getElementById('dedupBadge');
  const draftsQueueGrid = document.getElementById('draftsQueueGrid');
  const dedupQueueGrid = document.getElementById('dedupQueueGrid');
  const tabUploadBtn = document.getElementById('tabUploadBtn');
  const tabPatternBtn = document.getElementById('tabPatternBtn');
  const uploadTabSection = document.getElementById('uploadTabSection');
  const patternTabSection = document.getElementById('patternTabSection');
  const filtersAside = document.querySelector('.filters-aside');
  const pdfFileInput = document.getElementById('pdfFileInput');
  const pdfFileLabel = document.getElementById('pdfFileLabel');
  const processPdfBtn = document.getElementById('processPdfBtn');
  const uploadStatusCard = document.getElementById('uploadStatusCard');
  const uploadStatusText = document.getElementById('uploadStatusText');
  const contextReviewPanel = document.getElementById('contextReviewPanel');
  const reviewPaperTitle = document.getElementById('reviewPaperTitle');
  const aiRefineBtn = document.getElementById('aiRefineBtn');
  const embedFinalBtn = document.getElementById('embedFinalBtn');
  const contextQuestionsList = document.getElementById('contextQuestionsList');

  let currentUploadedPaperId = null;

  if (tabSearchBtn && tabDraftsBtn && tabDedupBtn) {
    const showSidebarFilter = (show) => {
      if (filtersAside) filtersAside.style.display = show ? 'block' : 'none';
    };

    tabSearchBtn.addEventListener('click', () => {
      tabSearchBtn.classList.add('active');
      tabDraftsBtn.classList.remove('active');
      tabDedupBtn.classList.remove('active');
      if (tabUploadBtn) tabUploadBtn.classList.remove('active');
      searchTabSection.style.display = 'block';
      draftsTabSection.style.display = 'none';
      if (dedupTabSection) dedupTabSection.style.display = 'none';
      if (uploadTabSection) uploadTabSection.style.display = 'none';
      if (patternTabSection) patternTabSection.style.display = 'none';
      showSidebarFilter(true);
      performSearch();
    });

    tabDraftsBtn.addEventListener('click', () => {
      tabDraftsBtn.classList.add('active');
      tabSearchBtn.classList.remove('active');
      tabDedupBtn.classList.remove('active');
      if (tabUploadBtn) tabUploadBtn.classList.remove('active');
      searchTabSection.style.display = 'none';
      draftsTabSection.style.display = 'block';
      if (dedupTabSection) dedupTabSection.style.display = 'none';
      if (uploadTabSection) uploadTabSection.style.display = 'none';
      if (patternTabSection) patternTabSection.style.display = 'none';
      showSidebarFilter(true);
      fetchDraftsQueue();
    });

    tabDedupBtn.addEventListener('click', () => {
      tabDedupBtn.classList.add('active');
      tabSearchBtn.classList.remove('active');
      tabDraftsBtn.classList.remove('active');
      if (tabUploadBtn) tabUploadBtn.classList.remove('active');
      searchTabSection.style.display = 'none';
      draftsTabSection.style.display = 'none';
      if (dedupTabSection) dedupTabSection.style.display = 'block';
      if (uploadTabSection) uploadTabSection.style.display = 'none';
      if (patternTabSection) patternTabSection.style.display = 'none';
      showSidebarFilter(true);
      fetchDedupQueue();
    });

    if (tabUploadBtn) {
      tabUploadBtn.addEventListener('click', () => {
        tabUploadBtn.classList.add('active');
        tabSearchBtn.classList.remove('active');
        tabDraftsBtn.classList.remove('active');
        tabDedupBtn.classList.remove('active');
        searchTabSection.style.display = 'none';
        draftsTabSection.style.display = 'none';
        if (dedupTabSection) dedupTabSection.style.display = 'none';
        if (uploadTabSection) uploadTabSection.style.display = 'flex';
        if (patternTabSection) patternTabSection.style.display = 'none';
        showSidebarFilter(false);
      });
    }

    if (tabPatternBtn) {
      tabPatternBtn.addEventListener('click', () => {
        tabPatternBtn.classList.add('active');
        tabSearchBtn.classList.remove('active');
        tabDraftsBtn.classList.remove('active');
        tabDedupBtn.classList.remove('active');
        if (tabUploadBtn) tabUploadBtn.classList.remove('active');
        searchTabSection.style.display = 'none';
        draftsTabSection.style.display = 'none';
        if (dedupTabSection) dedupTabSection.style.display = 'none';
        if (uploadTabSection) uploadTabSection.style.display = 'none';
        if (patternTabSection) patternTabSection.style.display = 'flex';
        showSidebarFilter(false);
        fetchSchoolsList();
      });
    }
  }

  // --- School & Pattern Lab Management ---
  let activePatternId = null;
  let availableSchools = [];

  const patternSchoolSelect = document.getElementById('patternSchoolSelect');
  const refreshSchoolsBtn = document.getElementById('refreshSchoolsBtn');
  const patternNameInput = document.getElementById('patternNameInput');
  const patternClassInput = document.getElementById('patternClassInput');
  const patternSubjectInput = document.getElementById('patternSubjectInput');
  const schoolDbStatusText = document.getElementById('schoolDbStatusText');
  const schoolDbQuestionCount = document.getElementById('schoolDbQuestionCount');
  const schoolDbPaperCount = document.getElementById('schoolDbPaperCount');
  const generateSectionTitle = document.getElementById('generateSectionTitle');
  const generateBtnText = document.getElementById('generateBtnText');
  const analyzePatternBtn = document.getElementById('analyzePatternBtn');
  const generatePatternPaperBtn = document.getElementById('generatePatternPaperBtn');
  const patternAnalysisResult = document.getElementById('patternAnalysisResult');
  const generatedPatternPaperResult = document.getElementById('generatedPatternPaperResult');
  const uploadSchoolInput = document.getElementById('uploadSchoolInput');
  const uploadDbHint = document.getElementById('uploadDbHint');
  const schoolListSuggestions = document.getElementById('schoolListSuggestions');

  function slugifySchool(name) {
    if (!name) return 'general';
    return name.trim().toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_-]+/g, '_').replace(/^_+|_+$/g, '') || 'general';
  }

  // Reactive DB hint on upload form
  if (uploadSchoolInput && uploadDbHint) {
    uploadSchoolInput.addEventListener('input', () => {
      const slug = slugifySchool(uploadSchoolInput.value);
      uploadDbHint.textContent = `${slug}.db`;
    });
  }

  async function fetchSchoolsList(selectSchoolSlug = null) {
    try {
      const res = await fetch('/api/schools');
      if (!res.ok) return;
      const data = await res.json();
      availableSchools = data.schools || [];

      // Update Pattern Lab school dropdown
      if (patternSchoolSelect) {
        const prevValue = selectSchoolSlug || patternSchoolSelect.value;
        patternSchoolSelect.innerHTML = '';

        if (availableSchools.length === 0) {
          patternSchoolSelect.innerHTML = '<option value="navodaya">Navodaya Vidyalaya (navodaya.db)</option>';
        } else {
          availableSchools.forEach(school => {
            const opt = document.createElement('option');
            opt.value = school.id;
            const qCount = school.question_count || 0;
            const pCount = school.paper_count || 0;
            opt.textContent = `${school.name} (${qCount} questions · ${school.db_file})`;
            patternSchoolSelect.appendChild(opt);
          });
        }

        if (prevValue && Array.from(patternSchoolSelect.options).some(o => o.value === prevValue)) {
          patternSchoolSelect.value = prevValue;
        } else if (Array.from(patternSchoolSelect.options).some(o => o.value === 'navodaya')) {
          patternSchoolSelect.value = 'navodaya';
        }

        updateSchoolUiState();
      }

      // Update sidebar school filter
      if (schoolFilter) {
        const prevFilterVal = schoolFilter.value;
        schoolFilter.innerHTML = '<option value="all">All Schools & Master DB</option>';
        availableSchools.forEach(school => {
          const opt = document.createElement('option');
          opt.value = school.id || school.slug;
          opt.textContent = `${school.name} (${school.question_count || 0} Qs)`;
          schoolFilter.appendChild(opt);
        });
        if (prevFilterVal && Array.from(schoolFilter.options).some(o => o.value === prevFilterVal)) {
          schoolFilter.value = prevFilterVal;
        }
      }

      // Update upload datalist suggestions
      if (schoolListSuggestions) {
        schoolListSuggestions.innerHTML = '';
        availableSchools.forEach(school => {
          const opt = document.createElement('option');
          opt.value = school.name;
          opt.textContent = `${school.name} (${school.db_file})`;
          schoolListSuggestions.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('Could not fetch schools list:', err);
    }
  }

  function updateSchoolUiState() {
    if (!patternSchoolSelect) return;
    const selectedId = patternSchoolSelect.value;
    const school = availableSchools.find(s => s.id === selectedId) || {
      id: selectedId,
      name: patternSchoolSelect.selectedOptions[0]?.text.split(' (')[0] || 'Navodaya Vidyalaya',
      db_file: `${slugifySchool(selectedId)}.db`,
      question_count: 0,
      paper_count: 0
    };

    if (patternNameInput) {
      patternNameInput.value = `${school.name} Exam Pattern`;
    }
    if (generateSectionTitle) {
      generateSectionTitle.textContent = `Generate Original Paper (${school.name} Style)`;
    }
    if (generateBtnText) {
      generateBtnText.textContent = `Generate Paper in ${school.name} Pattern`;
    }
    if (schoolDbStatusText) {
      schoolDbStatusText.innerHTML = `Active School DB: <strong class="text-indigo-300 font-mono">${escapeHtml(school.db_file || school.id + '.db')}</strong>`;
    }
    if (schoolDbQuestionCount) {
      schoolDbQuestionCount.textContent = `${school.question_count || 0} questions indexed`;
    }
    if (schoolDbPaperCount) {
      schoolDbPaperCount.textContent = `${school.paper_count || 0} papers uploaded`;
    }

    if (analyzePatternBtn) {
      if ((school.question_count || 0) === 0) {
        analyzePatternBtn.title = 'No questions indexed yet. Upload a PDF paper for this school first.';
      } else {
        analyzePatternBtn.title = 'Ready for pattern analysis';
      }
    }
  }

  if (patternSchoolSelect) {
    patternSchoolSelect.addEventListener('change', updateSchoolUiState);
  }

  if (refreshSchoolsBtn) {
    refreshSchoolsBtn.addEventListener('click', () => {
      refreshSchoolsBtn.classList.add('animate-spin');
      fetchSchoolsList().finally(() => {
        setTimeout(() => refreshSchoolsBtn.classList.remove('animate-spin'), 600);
      });
    });
  }

  // Initial load of school directory
  fetchSchoolsList();

  if (analyzePatternBtn) {
    analyzePatternBtn.addEventListener('click', async () => {
      analyzePatternBtn.disabled = true;
      patternAnalysisResult.innerHTML = '<div class="text-indigo-300 flex items-center gap-2"><span class="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></span><span>Querying school database & analyzing exam blueprints...</span></div>';
      try {
        const selectedSchool = patternSchoolSelect ? patternSchoolSelect.value : null;
        const response = await fetch('/api/patterns/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pattern_name: document.getElementById('patternNameInput').value.trim(),
            class_level: document.getElementById('patternClassInput').value.trim(),
            subject: document.getElementById('patternSubjectInput').value.trim(),
            school: selectedSchool
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Pattern analysis failed');
        activePatternId = data.pattern_id;
        generatePatternPaperBtn.disabled = false;

        const typesBadge = Object.entries(data.blueprint.question_type_distribution || {})
          .map(([t, count]) => `<span class="bg-indigo-950/70 border border-indigo-700/50 text-indigo-300 px-2 py-0.5 rounded text-[10px] font-mono">${escapeHtml(t)}: ${count}</span>`)
          .join(' ');

        const diffBadge = Object.entries(data.blueprint.difficulty_distribution || {})
          .map(([d, count]) => `<span class="bg-slate-800 border border-slate-700 text-slate-300 px-2 py-0.5 rounded text-[10px] font-mono">${escapeHtml(d)}: ${count}</span>`)
          .join(' ');

        patternAnalysisResult.innerHTML = `
          <div class="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-lg flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="text-emerald-400 font-bold flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[16px]">verified</span>
                <span>Blueprint Saved: ${escapeHtml(data.pattern_name)}</span>
              </span>
              <span class="text-slate-400 text-[11px] font-mono">DB: ${escapeHtml(data.school || selectedSchool)}.db</span>
            </div>
            <div class="text-slate-300 text-xs">
              <strong>Sample Questions Analyzed:</strong> ${data.blueprint.sample_count} questions from ${escapeHtml(data.school || 'selected school')}
            </div>
            <div class="flex flex-wrap items-center gap-1.5 mt-1">
              <span class="text-slate-400 text-[11px]">Format Distribution:</span>
              ${typesBadge || '<span class="text-slate-500">Standard mix</span>'}
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-slate-400 text-[11px]">Difficulty Profile:</span>
              ${diffBadge || '<span class="text-slate-500">Balanced</span>'}
            </div>
          </div>
        `;
      } catch (error) {
        patternAnalysisResult.innerHTML = `<div class="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-400 flex items-center gap-2"><span class="material-symbols-outlined text-base">error</span><span>${escapeHtml(error.message)}</span></div>`;
      } finally {
        analyzePatternBtn.disabled = false;
      }
    });
  }

  // --- Dynamic Subject & Topic Suggestions in Step 2 ---
  const patternGenSubjectSelect = document.getElementById('patternGenSubjectSelect');
  const patternTopicSuggestions = document.getElementById('patternTopicSuggestions');
  const subjectTopicsMap = {
    mental_ability: [
      { val: "Odd One Out & Similarity", label: "Figure Discrimination (Odd Man Out)" },
      { val: "Figure Matching", label: "Exact Figure Match" },
      { val: "Pattern Completion", label: "Missing Segment Pattern" },
      { val: "Figure Series Completion", label: "Sequential Series" },
      { val: "Analogy & Spatial Relations", label: "Figure Analogy (A:B :: C:D)" },
      { val: "Geometrical Figure Completion", label: "Triangle / Square / Circle Completion" },
      { val: "Mirror Imaging", label: "Lateral Inversion & Reflections" },
      { val: "Space Visualization & Paper Folding", label: "Punched Hole & Paper Unfolding" },
      { val: "Embedded Figures", label: "Hidden Figure Detection" }
    ],
    mathematics: [
      { val: "Quadratic Equations & Roots", label: "Algebra: ax² + bx + c = 0" },
      { val: "Arithmetic Progressions (AP)", label: "AP: nth term & Sum" },
      { val: "Triangles & Similarity (with Figure)", label: "Geometry: Thales BPT & Ratios" },
      { val: "Circles & Tangents (with Figure)", label: "Geometry: Tangents & Pythagoras" },
      { val: "Introduction to Trigonometry", label: "Trig: Identities & Angles" },
      { val: "Heights and Distances", label: "Applications of Trigonometry" },
      { val: "Coordinate Geometry & Section Formula", label: "Distance & Section formula" },
      { val: "Sets & Venn Diagrams (with Figure)", label: "Set Operations & Word Problems" },
      { val: "Surface Areas & Volumes", label: "3D Solids & Melting Shapes" },
      { val: "Probability & Statistics", label: "Cards, Dice, Mean, Median" },
      { val: "Real Numbers & Polynomials", label: "HCF, LCM, Irrational Proofs" }
    ],
    physics: [
      { val: "Electricity & Ohm's Law (Numericals)", label: "Current, Resistance & Joule Heat" },
      { val: "Light - Reflection & Refraction", label: "Mirror & Lens Formula Numericals" },
      { val: "Magnetic Effects of Electric Current", label: "Fleming's Rules & Solenoid" },
      { val: "Human Eye & Dispersion", label: "Prism & Atmospheric Refraction" }
    ],
    science: [
      { val: "Electricity & Circuits", label: "Physics: Ohm's Law" },
      { val: "Light - Optics", label: "Physics: Reflection & Refraction" },
      { val: "Chemical Reactions & Balancing", label: "Chemistry: Balancing & Types" },
      { val: "Acids, Bases & Salts", label: "Chemistry: pH & Reactions" },
      { val: "Life Processes & Photosynthesis", label: "Biology: Photosynthesis & Respiration" }
    ],
    chemistry: [
      { val: "Chemical Reactions & Equations", label: "Balancing & Types of Reactions" },
      { val: "Acids, Bases and Salts", label: "Indicators, pH & Salt Reactions" },
      { val: "Metals and Non-metals", label: "Reactivity Series & Ionic Bonds" },
      { val: "Carbon and its Compounds", label: "Covalent Bonds & Functional Groups" }
    ],
    biology: [
      { val: "Life Processes (Nutrition & Respiration)", label: "Photosynthesis, Digestion & ATP" },
      { val: "Control and Coordination", label: "Nervous System & Phytohormones" },
      { val: "How do Organisms Reproduce", label: "Asexual & Sexual Reproduction" },
      { val: "Heredity & Mendel's Crosses", label: "Monohybrid & Dihybrid Ratios" }
    ]
  };

  function updateTopicSuggestions(subject) {
    if (!patternTopicSuggestions) return;
    const s = (subject || 'mathematics').toLowerCase();
    const list = subjectTopicsMap[s] || subjectTopicsMap.mathematics;
    patternTopicSuggestions.innerHTML = '';
    list.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.val;
      opt.textContent = item.label;
      patternTopicSuggestions.appendChild(opt);
    });
    if (patternTopicInput && list.length > 0) {
      patternTopicInput.value = list[0].val;
    }
  }

  if (patternGenSubjectSelect) {
    patternGenSubjectSelect.addEventListener('change', () => {
      updateTopicSuggestions(patternGenSubjectSelect.value);
    });
  }

  if (generatePatternPaperBtn) {
    generatePatternPaperBtn.addEventListener('click', async () => {
      generatePatternPaperBtn.disabled = true;
      generatedPatternPaperResult.innerHTML = '<div class="p-4 bg-emerald-950/30 border border-emerald-800/50 rounded-lg text-emerald-300 text-sm flex items-center gap-2"><div class="w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin"></div><span>Synthesizing mathematical questions conforming to school pattern & solutions...</span></div>';
      try {
        const selectedSchool = patternSchoolSelect ? patternSchoolSelect.value : 'navodaya';
        const genSubjectEl = document.getElementById('patternGenSubjectSelect');
        const genClassEl = document.getElementById('patternGenClassSelect');
        const genTypeEl = document.getElementById('patternTypeSelect');
        const subjectVal = (genSubjectEl ? genSubjectEl.value : document.getElementById('patternSubjectInput')?.value) || 'mathematics';
        const classVal = (genClassEl ? genClassEl.value : document.getElementById('patternClassInput')?.value) || '10';
        const qTypeVal = genTypeEl ? genTypeEl.value : 'all';
        const topicVal = document.getElementById('patternTopicInput')?.value.trim() || 'Quadratic Equations & Roots';
        const diffVal = document.getElementById('patternDifficultyInput')?.value.trim() || 'medium';
        const countVal = Number(document.getElementById('patternCountInput')?.value) || 5;

        const response = await fetch('/api/papers/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pattern_id: activePatternId || 'auto',
            school: selectedSchool,
            class_level: classVal,
            subject: subjectVal,
            topic: topicVal,
            difficulty: diffVal,
            question_type: qTypeVal,
            question_count: countVal
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Paper generation failed');
        
        const schoolTitle = data.school || (patternSchoolSelect ? patternSchoolSelect.options[patternSchoolSelect.selectedIndex]?.text.split(' (')[0] : 'School');

        generatedPatternPaperResult.innerHTML = `
          <div class="bg-slate-900 border border-emerald-800/60 rounded-xl p-5 mb-4 shadow-lg">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div>
                <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider bg-emerald-950/60 border border-emerald-700/60 px-2 py-0.5 rounded">
                  ${escapeHtml(schoolTitle)} Pattern Compliant
                </span>
                <h3 class="text-lg font-bold text-slate-100 mt-1">${escapeHtml(data.title)}</h3>
              </div>
              <span class="text-xs text-slate-400 font-mono">${data.paper.questions.length} Generated Questions</span>
            </div>

            <div class="flex flex-col gap-4">
              ${data.paper.questions.map(question => {
                const cleanQText = (question.question_text || '').replace(/^\\[[^\\]]+\\]\\s*/, '');
                return `
                <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-4 transition-all hover:border-slate-700">
                  <div class="flex items-center justify-between text-xs mb-2">
                    <span class="font-bold text-emerald-300">${escapeHtml(question.question_number)} · ${escapeHtml(question.question_type || 'Question')}</span>
                    ${question.correct_answer ? `<span class="text-[11px] text-slate-400 font-mono">Answer: ${escapeHtml(question.correct_answer)}</span>` : ''}
                  </div>
                  <div class="text-sm text-slate-100 leading-relaxed">${renderMarkdownToHtml(cleanQText)}</div>
                  ${question.options && question.options.length ? `
                    <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      ${question.options.map(opt => `
                        <div class="p-2 bg-slate-900 border border-slate-800 rounded flex items-start gap-2">
                          <span class="font-bold text-indigo-400">(${escapeHtml(opt.label || '')})</span>
                          <span class="text-slate-200">${renderMarkdownToHtml(opt.text || '')}</span>
                        </div>
                      `).join('')}
                    </div>
                  ` : ''}
                  <details class="mt-3 text-xs text-slate-300">
                    <summary class="cursor-pointer text-indigo-400 font-semibold hover:text-indigo-300 flex items-center gap-1">
                      <span class="material-symbols-outlined text-[14px]">help</span>
                      <span>View Step-by-Step Solution (${escapeHtml(schoolTitle)} Marking Scheme)</span>
                    </summary>
                    <div class="mt-2 p-3 bg-slate-900/90 rounded border border-slate-800 text-slate-300 leading-relaxed whitespace-pre-wrap">${renderMarkdownToHtml(question.solution)}</div>
                  </details>
                </div>
              `;
              }).join('')}
            </div>
          </div>
        `;
        await typesetMath(generatedPatternPaperResult);
      } catch (error) {
        generatedPatternPaperResult.innerHTML = `<div class="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-400 flex items-center gap-2"><span class="material-symbols-outlined text-base">error</span><span>${escapeHtml(error.message)}</span></div>`;
      } finally {
        generatePatternPaperBtn.disabled = false;
      }
    });
  }

  // File Upload Handlers
  if (pdfFileInput) {
    pdfFileInput.addEventListener('change', () => {
      if (pdfFileInput.files && pdfFileInput.files[0]) {
        pdfFileLabel.innerText = `Selected File: ${pdfFileInput.files[0].name}`;
      }
    });
  }

  if (processPdfBtn) {
    processPdfBtn.addEventListener('click', async () => {
      if (!pdfFileInput || !pdfFileInput.files || !pdfFileInput.files[0]) {
        alert('Please select a PDF file to upload.');
        return;
      }

      const file = pdfFileInput.files[0];
      const uploadClassSelect = document.getElementById('uploadClassSelect');
      const uploadSubjectSelect = document.getElementById('uploadSubjectSelect');
      const uploadTypeSelect = document.getElementById('uploadTypeSelect');
      const uploadYearSelect = document.getElementById('uploadYearSelect');
      const targetSchoolName = (uploadSchoolInput ? uploadSchoolInput.value.trim() : '') || 'Navodaya';

      const formData = new FormData();
      formData.append('file', file);
      formData.append('class_name', uploadClassSelect.value);
      formData.append('subject', uploadSubjectSelect.value);
      formData.append('pdf_type', uploadTypeSelect.value);
      formData.append('year', uploadYearSelect.value);
      formData.append('school', targetSchoolName);

      processPdfBtn.disabled = true;
      processPdfBtn.innerHTML = '<span>Processing PDF Pages...</span>';
      uploadStatusCard.style.display = 'block';
      uploadStatusText.innerText = `Parsing PDF text & routing questions into ${targetSchoolName} database (${slugifySchool(targetSchoolName)}.db)...`;

      try {
        const res = await fetch('/api/upload_pdf', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to process PDF paper');
        }

        const data = await res.json();
        currentUploadedPaperId = data.paper_id;

        uploadStatusText.innerText = `✓ Processed ${data.total_questions} questions into ${data.school} DB (${data.school_slug}.db)!`;
        reviewPaperTitle.innerText = `Paper #${data.paper_id} (${data.filename}) · ${data.school} DB - ${data.total_questions} Questions Extracted`;

        contextReviewPanel.style.display = 'flex';
        renderContextQuestionsPreview(data.questions_preview || []);
        await typesetMath(contextQuestionsList);

        // Refresh school listing to immediately reflect newly populated school DB
        await fetchSchoolsList(data.school_slug);

      } catch (err) {
        alert('Error processing PDF: ' + err.message);
        uploadStatusText.innerText = '✕ Processing failed. ' + err.message;
      } finally {
        processPdfBtn.disabled = false;
        processPdfBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">auto_fix_high</span><span>Process PDF Paper</span>';
      }
    });
  }

  // AI Context Refinement Handler
  if (aiRefineBtn) {
    aiRefineBtn.addEventListener('click', async () => {
      if (!currentUploadedPaperId) return;

      aiRefineBtn.disabled = true;
      aiRefineBtn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">refresh</span><span>✨ Improving Context with AI...</span>';

      try {
        const res = await fetch('/api/refine_context', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paper_id: currentUploadedPaperId })
        });

        if (!res.ok) throw new Error('Context refinement failed');

        const data = await res.json();
        aiRefineBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">check_circle</span><span>✓ AI Context Improved!</span>';
        renderContextQuestionsPreview(data.questions_preview || []);
        await typesetMath(contextQuestionsList);
      } catch (err) {
        alert('Error refining context: ' + err.message);
        aiRefineBtn.disabled = false;
        aiRefineBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">auto_awesome</span><span>✨ Improve Context (AI Refine)</span>';
      }
    });
  }

  // Vector DB Embedding Handler
  if (embedFinalBtn) {
    embedFinalBtn.addEventListener('click', async () => {
      if (!currentUploadedPaperId) return;

      embedFinalBtn.disabled = true;
      embedFinalBtn.innerHTML = '<span class="material-symbols-outlined text-[16px] animate-spin">database</span><span>⚡ Indexing into Vector DB...</span>';

      try {
        const res = await fetch('/api/embed_paper', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paper_id: currentUploadedPaperId })
        });

        if (!res.ok) throw new Error('Vector store embedding failed');

        const data = await res.json();
        embedFinalBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">check_circle</span><span>✓ Vector Indexing Complete!</span>';
        alert(`Successfully embedded ${data.embedded_count} questions into the Vector Store DB!`);
        fetchStats();
      } catch (err) {
        alert('Error embedding paper: ' + err.message);
        embedFinalBtn.disabled = false;
        embedFinalBtn.innerHTML = '<span class="material-symbols-outlined text-[16px]">database</span><span>⚡ Embed PDF into Vector Store</span>';
      }
    });
  }

  function renderContextQuestionsPreview(questions) {
    if (!contextQuestionsList) return;
    contextQuestionsList.innerHTML = '';

    if (questions.length === 0) {
      contextQuestionsList.innerHTML = '<div class="p-4 bg-slate-900 rounded-lg text-slate-400 text-xs">No extracted questions found.</div>';
      return;
    }

    questions.forEach((q, idx) => {
      const card = document.createElement('div');
      card.className = 'question-card';

      // Upload previews receive a chunk whose `content` may contain both the
      // original PDF option lines and a legacy `Options:` metadata block.
      // Render the stem separately and use structured options exactly once.
      let previewStem = String(q.stem_text || q.content || '');
      previewStem = previewStem.split(/\n\s*Options\s*:/i)[0];
      previewStem = previewStem
        .split(/\r?\n/)
        .filter(line => !/^\s*\(?[A-Da-d]\)\s+/.test(line))
        .join('\n');

      const previewOptions = (q.options || []).map((option, optionIndex) => {
        const raw = typeof option === 'object'
          ? `${option.label || ''}) ${option.text || option.latex_text || ''}`
          : String(option);
        const match = raw.match(/^\s*\(?([A-Da-d])\)?[\.:\)]?\s*(.*)$/);
        return {
          label: match ? match[1].toUpperCase() : String(optionIndex + 1),
          text: match ? match[2] : raw
        };
      });
      const previewOptionsHtml = previewOptions.length ? `
        <div class="options-container">
          <div class="options-title">MCQ Choice Options</div>
          <div class="options-grid">
            ${previewOptions.map(option => `
              <div class="option-card">
                <span class="option-label">${option.label}</span>
                <span class="option-text">${renderMarkdownToHtml(cleanOptionText(option.text, option.label))}</span>
              </div>
            `).join('')}
          </div>
        </div>` : '';

      const imgBadge = (q.linked_images && q.linked_images.length > 0)
        ? `<span class="badge badge-type">🖼️ ${q.linked_images.length} Diagram Linked</span>`
        : `<span class="badge badge-year">No Diagram</span>`;

      const refinedTag = q.context_refined ? '<span class="badge badge-type" style="background:rgba(99,102,241,0.2); color:#a5b4fc;">✨ AI Context Refined</span>' : '';

      // Render Diagram Figure Lightbox if diagrams exist
      let diagramHtml = "";
      const validUrls = (q.image_urls && q.image_urls.length > 0)
        ? q.image_urls
        : (q.linked_images || []).map(img => {
            const fn = typeof img === 'object' ? (img.filename || img.relative_path) : String(img);
            const cleanFn = fn ? fn.replace(/^.*[\\\/]/, '').replace(/['"} ]/g, '') : '';
            if (!cleanFn) return '';
            const pid = q.paper_id || currentUploadedPaperId;
            return `/static/parsed/${q.class}/${q.subject}/${q.year || '2024-2025'}/${pid}/images/${cleanFn}`;
          }).filter(Boolean);

      if (validUrls.length > 0) {
        const imgTags = validUrls.map(url => `
          <div class="diagram-img-wrapper" onclick="window.openImageLightbox('${url}')" style="margin-top:10px; max-width:100%; border-radius:6px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); background:#0f172a; padding:6px; cursor:pointer;">
            <img src="${url}" alt="Diagram Figure" class="diagram-img" loading="lazy" style="max-width:100%; height:auto; display:block; border-radius:4px;" onerror="window.handleImageError(this, '${url}')" />
            <div class="diagram-zoom-hint" style="font-size:11px; color:#94a3b8; margin-top:4px; text-align:center;">🔍 Click to Expand</div>
          </div>
        `).join("");

        diagramHtml = `
          <div class="diagram-container" style="margin-top:12px;">
            <div class="diagram-header" style="font-size:12px; font-weight:600; color:#38bdf8; display:flex; align-items:center; gap:6px;">
              <span class="material-symbols-outlined text-[16px]">image</span>
              <span>Linked Diagram Figures (${validUrls.length})</span>
            </div>
            <div class="diagram-images-grid">
              ${imgTags}
            </div>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="card-header">
          <div class="card-badges">
            <span class="badge badge-class">Class ${q.class} ${q.subject}</span>
            <span class="badge badge-qnum">${q.question_number}</span>
            ${imgBadge}
            ${refinedTag}
          </div>
        </div>
        <div class="question-stem">${renderMarkdownToHtml(cleanStemText(previewStem))}</div>
        ${previewOptionsHtml}
        ${diagramHtml}
      `;
      contextQuestionsList.appendChild(card);
    });
  }

  async function fetchDedupQueue() {
    try {
      const res = await fetch('/api/dedup');
      if (!res.ok) return;
      const data = await res.json();
      if (dedupBadge) {
        dedupBadge.textContent = data.total_duplicate_pairs || 0;
      }
      renderDedupQueue(data.duplicate_pairs || []);
    } catch (e) {
      console.error("Error fetching dedup queue:", e);
    }
  }

  function renderDedupQueue(pairs) {
    if (!dedupQueueGrid) return;
    if (pairs.length === 0) {
      dedupQueueGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🎉</div>
          <h3>Zero Duplicate Questions Detected!</h3>
          <p>All question chunks in the vector store are unique.</p>
        </div>`;
      return;
    }

    dedupQueueGrid.innerHTML = '';
    pairs.forEach(pair => {
      const card = document.createElement('div');
      card.className = 'question-card';
      const pct = (pair.similarity * 100).toFixed(1);
      const c1 = pair.chunk1;
      const c2 = pair.chunk2;

      card.innerHTML = `
        <div class="card-header">
          <div class="card-badges">
            <span class="badge badge-type">🔄 ${pct}% Cosine Match</span>
            <span class="badge badge-class">Class ${c1.class} ${c1.subject}</span>
          </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px;">
          <div style="padding:12px; background:rgba(0,0,0,0.3); border-radius:6px; border:1px solid rgba(255,255,255,0.1);">
            <div style="font-weight:700; color:var(--accent-cyan); margin-bottom:4px;">Original Question (${c1.year} - ${c1.question_id}):</div>
            <div style="font-size:13px; color:var(--text-secondary);">${escapeHtml(c1.document_snippet)}...</div>
          </div>
          <div style="padding:12px; background:rgba(0,0,0,0.3); border-radius:6px; border:1px solid rgba(239,68,68,0.3);">
            <div style="font-weight:700; color:#f87171; margin-bottom:4px;">Duplicate Match (${c2.year} - ${c2.question_id}):</div>
            <div style="font-size:13px; color:var(--text-secondary);">${escapeHtml(c2.document_snippet)}...</div>
            <button class="btn-remove-dedup" data-chunkid="${c2.chunk_id}" style="margin-top:10px; padding:6px 14px; background:rgba(239,68,68,0.2); border:1px solid #ef4444; color:#f87171; border-radius:4px; font-weight:700; cursor:pointer;">Remove Duplicate</button>
          </div>
        </div>
      `;
      dedupQueueGrid.appendChild(card);
    });

    document.querySelectorAll('.btn-remove-dedup').forEach(btn => {
      btn.addEventListener('click', async () => {
        const cid = btn.getAttribute('data-chunkid');
        btn.disabled = true;
        btn.textContent = 'Removing...';
        try {
          const res = await fetch('/api/dedup/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chunk_id: cid })
          });
          if (res.ok) {
            btn.textContent = '✓ Removed';
            setTimeout(() => fetchDedupQueue(), 800);
          }
        } catch (e) {
          btn.textContent = 'Failed';
          btn.disabled = false;
        }
      });
    });
  }

  async function fetchDraftsQueue() {
    try {
      const res = await fetch('/api/drafts');
      if (!res.ok) return;
      const data = await res.json();
      
      if (draftsBadge) {
        draftsBadge.textContent = data.total_flagged_questions || 0;
      }

      renderDraftsQueue(data.drafts || []);
    } catch (e) {
      console.error("Error fetching drafts queue:", e);
    }
  }

  function renderDraftsQueue(drafts) {
    if (!draftsQueueGrid) return;
    draftsQueueGrid.innerHTML = '';

    if (drafts.length === 0) {
      draftsQueueGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">✅</div>
          <h3>No Pending Drafts</h3>
          <p>All paper drafts have been audited and approved for vector indexing.</p>
        </div>
      `;
      return;
    }

    drafts.forEach(draft => {
      const card = document.createElement('div');
      card.className = 'draft-card';

      const flaggedItems = (draft.flagged_questions || []).map(q => `
        <div class="draft-flag-item">
          <div style="display:flex; justify-between; align-items:center; margin-bottom:4px;">
            <strong>${escapeHtml(q.question_number)}</strong>
            <span class="flag-chip ${q.confidence}">${q.confidence} confidence</span>
          </div>
          <div style="color:var(--text-muted); font-size:13px;">${escapeHtml(q.stem_text)}</div>
          <div style="color:var(--accent-amber); font-size:12px; margin-top:4px;">⚠️ ${escapeHtml(q.flag_reason)}</div>
        </div>
      `).join('');

      card.innerHTML = `
        <div class="draft-card-header">
          <div>
            <div class="draft-card-title">
              <span>📄 ${escapeHtml(draft.filename)}</span>
              <span class="badge badge-class">Class ${draft.class}</span>
              <span class="badge badge-subject">${draft.subject}</span>
              <span class="badge badge-year">${draft.year}</span>
            </div>
            <div style="font-size:13px; color:var(--text-muted); margin-top:6px;">
              Parse Status: <strong>${draft.parse_status}</strong> | Embed Status: <strong>${draft.embed_status}</strong> | Flagged Questions: <strong>${draft.flagged_questions_count}</strong>
            </div>
          </div>
          <button class="draft-approve-btn" data-pid="${draft.paper_id}">
            ✓ Approve Draft
          </button>
        </div>

        <div class="draft-flagged-list">
          <h4 style="font-size:14px; font-weight:700; color:var(--accent-cyan);">Flagged Review Items (${draft.flagged_questions_count})</h4>
          ${flaggedItems || '<div style="color:var(--text-muted); font-size:13px;">Zero structural flags found. Standard pass completed.</div>'}
        </div>
      `;

      draftsQueueGrid.appendChild(card);
    });

    // Add click listener for approve buttons
    document.querySelectorAll('.draft-approve-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const pid = e.target.getAttribute('data-pid');
        if (!pid) return;
        btn.textContent = 'Approving...';
        btn.disabled = true;

        try {
          const res = await fetch('/api/drafts/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: pid })
          });
          if (res.ok) {
            btn.textContent = '✓ Approved';
            setTimeout(() => fetchDraftsQueue(), 1000);
          }
        } catch (err) {
          console.error("Error approving draft:", err);
          btn.textContent = 'Failed';
          btn.disabled = false;
        }
      });
    });
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Lightbox Modal & Image Fallback Helpers
  window.openImageLightbox = function(url) {
    const modal = document.getElementById('imageLightboxModal');
    const img = document.getElementById('lightboxImage');
    const downloadBtn = document.getElementById('downloadImageBtn');
    if (modal && img) {
      img.src = url;
      if (downloadBtn) {
        downloadBtn.href = url;
      }
      modal.classList.add('open');
    }
  };

  window.closeImageLightbox = function() {
    const modal = document.getElementById('imageLightboxModal');
    if (modal) {
      modal.classList.remove('open');
    }
  };

  window.handleImageError = function(imgElement, originalUrl) {
    const wrapper = imgElement.parentElement;
    if (wrapper) {
      const filename = originalUrl ? originalUrl.split('/').pop() : 'diagram.png';
      wrapper.innerHTML = `
        <div class="diagram-fallback">
          <div style="font-weight:700; margin-bottom:4px; font-size:13px;">🖼️ Diagram Figure Attached</div>
          <div style="font-size:11px; color:var(--text-muted); word-break:break-all;">${escapeHtml(filename)}</div>
          <a href="${originalUrl}" target="_blank" style="display:inline-block; margin-top:6px; font-size:11px; color:var(--accent-cyan); font-weight:600;">Open Direct Image ↗</a>
        </div>
      `;
      wrapper.onclick = null;
    }
  };

  // Lightbox Event Listeners
  const closeLightboxBtn = document.getElementById('closeLightboxBtn');
  const imageLightboxModal = document.getElementById('imageLightboxModal');

  if (closeLightboxBtn) {
    closeLightboxBtn.addEventListener('click', window.closeImageLightbox);
  }

  if (imageLightboxModal) {
    imageLightboxModal.addEventListener('click', (e) => {
      if (e.target === imageLightboxModal) {
        window.closeImageLightbox();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.closeImageLightbox();
    }
  });
});
