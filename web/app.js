// Frontend JavaScript Application Logic for PDF Question-Paper RAG Web UI with Step-by-Step Loader & MathJax

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  const classFilter = document.getElementById('classFilter');
  const subjectFilter = document.getElementById('subjectFilter');
  const topKSelect = document.getElementById('topKSelect');
  const searchBtn = document.getElementById('searchBtn');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const resultsGrid = document.getElementById('resultsGrid');
  const resultsCountHeader = document.getElementById('resultsCountHeader');
  const copyPromptBtn = document.getElementById('copyPromptBtn');
  const samplePills = document.querySelectorAll('.sample-pill');
  const pipelineLoaderCard = document.getElementById('pipelineLoaderCard');

  let currentRagPrompt = "";

  // Fetch Dataset Summary Stats
  fetchStats();

  // Event Listeners
  searchBtn.addEventListener('click', performSearch);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });

  searchInput.addEventListener('input', () => {
    clearSearchBtn.style.display = searchInput.value.length > 0 ? 'block' : 'none';
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
  });

  samplePills.forEach(pill => {
    pill.addEventListener('click', () => {
      searchInput.value = pill.getAttribute('data-query');
      clearSearchBtn.style.display = 'block';
      performSearch();
    });
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

  // Initial Search
  performSearch();

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        document.getElementById('statPapers').innerText = data.total_papers || 10;
        document.getElementById('statQuestions').innerText = data.total_questions || 361;
        document.getElementById('statImages').innerText = data.total_images || 101;
      }
    } catch (err) {
      console.warn("Could not fetch stats:", err);
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
    if (!query) return;

    searchBtn.disabled = true;
    searchBtn.innerHTML = "<span>Executing Pipeline...</span>";

    pipelineLoaderCard.style.display = "block";
    resetLoaderSteps();

    // Step 1: Vectorizing Query
    updateStep(1, "active", "In progress...");
    await delay(180);
    updateStep(1, "completed", "Done ✓");

    // Step 2: Querying VectorStore DB
    updateStep(2, "active", "Searching DB...");

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          top_k: parseInt(topKSelect.value, 10) || 5,
          class_filter: classFilter.value,
          subject_filter: subjectFilter.value
        })
      });

      if (!res.ok) throw new Error("Search request failed");

      const data = await res.json();
      updateStep(2, "completed", "Done ✓");

      // Step 3: Resolving Diagram PNGs
      updateStep(3, "active", "Resolving images...");
      await delay(150);
      updateStep(3, "completed", "Done ✓");

      // Step 4: Formatting LaTeX & Options Grid
      updateStep(4, "active", "Typesetting LaTeX...");
      
      currentRagPrompt = data.rag_prompt_context || "";
      renderResults(data);

      updateStep(4, "completed", "Done ✓");
      await delay(300);
      pipelineLoaderCard.style.display = "none";

      // Trigger MathJax LaTeX Typesetting
      if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise();
      }
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

  function renderResults(data) {
    const results = data.results || [];
    resultsCountHeader.innerText = `Search Results (${results.length})`;
    copyPromptBtn.style.display = results.length > 0 ? "inline-block" : "none";

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

      // Render Options Grid if options exist
      let optionsHtml = "";
      if (item.options && item.options.length > 0) {
        const optionCards = item.options.map(opt => `
          <div class="option-card">
            <span class="option-label">${opt.label}</span>
            <span class="option-text">${escapeHtml(opt.latex_text || opt.text)}</span>
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
        const subpartItems = item.subparts.map(sub => {
          const s = sub.trim();
          if (s === "OR" || s === "OR\n" || s === "[OR]" || s === "OR:") {
            return `
              <div class="or-divider">
                <span class="or-badge">OR</span>
              </div>
            `;
          }
          return `
            <div class="subpart-card">${escapeHtml(s)}</div>
          `;
        }).join("");

        subpartsHtml = `
          <div class="subparts-container">
            ${subpartItems}
          </div>
        `;
      }

      // Render Diagram Figure Lightbox if diagrams exist
      let diagramHtml = "";
      if (item.image_urls && item.image_urls.length > 0) {
        const imgTags = item.image_urls.map(url => `
          <img src="${url}" alt="Extracted Question Diagram" class="diagram-img" loading="lazy" />
        `).join("");

        diagramHtml = `
          <div class="diagram-container">
            <div class="diagram-header">🖼️ Linked Diagram Figure (${item.image_urls.length})</div>
            <div class="diagram-images-grid">
              ${imgTags}
            </div>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="card-header">
          <div class="card-badges">
            <span class="badge badge-class">Class ${item.class}</span>
            <span class="badge badge-subject">${item.subject}</span>
            <span class="badge badge-year">${item.year}</span>
            <span class="badge badge-qnum">${item.question_number}</span>
          </div>
          <span class="card-sim">${simPct}% Similarity</span>
        </div>

        <div class="question-stem">${escapeHtml(item.latex_stem || item.stem_text)}</div>

        ${optionsHtml}
        ${subpartsHtml}
        ${diagramHtml}
      `;

      resultsGrid.appendChild(card);
    });
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
});
