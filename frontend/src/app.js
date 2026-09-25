import { scenarios, defaultInput } from './data/scenarios.js';
import { icon, foodArt, brandMark } from './icons.js';
import { apiGet, apiPost } from './api.js';

const $ = (selector, root = document) => root.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const state = { draft: defaultInput(), result: null, errors: {}, query: '', filter: 'all', selected: [], materials: [], modelCard: null, apiStatus: 'checking', apiMessage: 'Checking the API', mobileMenu: false, theme: 'light', submitting: false };
try { state.theme = localStorage.getItem('packwise-theme') === 'dark' ? 'dark' : 'light'; } catch {}
document.documentElement.dataset.theme = state.theme;
const routes = { home: 'Overview', analyze: 'New analysis', results: 'Recommendation', materials: 'Materials library', methodology: 'How it works' };
const getRoute = () => location.hash.slice(1).split('?')[0] || 'home';
const goto = route => { if (getRoute() === route) render(); else location.hash = route; };
const badge = (text, cls = '') => `<span class="badge ${cls}">${text}</span>`;
const btn = (text, action, cls = 'primary', ico = 'arrow') => `<button type="button" class="button ${cls}" data-action="${action}">${text}${ico ? icon(ico, 17) : ''}</button>`;
function notify(text) { const toast = $('#toast'); toast.textContent = text; toast.classList.add('show'); clearTimeout(notify.timer); notify.timer = setTimeout(() => toast.classList.remove('show'), 3500); }

function shell(route, body) {
  const nav = [['home', 'grid', 'Overview'], ['analyze', 'spark', 'New analysis'], ['materials', 'layers', 'Materials library'], ['methodology', 'book', 'How it works']];
  const dot = ['online', 'fallback'].includes(state.apiStatus) ? '' : 'offline';
  const apiLabel = state.apiStatus === 'online' ? 'ML API connected' : state.apiStatus === 'fallback' ? 'Compatibility engine ready' : state.apiStatus === 'checking' ? 'Checking API…' : 'API unavailable';
  return `<div class="layout"><aside class="sidebar ${state.mobileMenu ? 'open' : ''}" aria-label="Main navigation">
    <a href="#home" class="brand">${brandMark}<span>packwise<span class="brand-dot">.</span></span></a><p class="brand-caption">Food packaging intelligence</p><span class="nav-label">WORKSPACE</span>
    <nav>${nav.map(([id, ico, label]) => `<a href="#${id}" class="nav-item ${route === id || route === 'results' && id === 'analyze' ? 'active' : ''}" ${route === id ? 'aria-current="page"' : ''}>${icon(ico)}<span>${label}</span>${id === 'analyze' ? '<span class="nav-plus">+</span>' : ''}</a>`).join('')}</nav>
    <div class="sidebar-bottom"><div class="sidebar-note"><span class="note-icon">${icon('leaf', 22)}</span><strong>Small choices.<br>Lasting impact.</strong><p>Smarter materials start with clear evidence and honest limits.</p><a href="#methodology">Meet the method ${icon('arrow', 15)}</a></div><div class="prototype-mark"><span class="status-dot ${dot}"></span> RESEARCH PROTOTYPE <span>v1.0</span></div></div>
  </aside><div class="page-shell"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-toggle" data-action="menu" aria-label="Toggle navigation" aria-expanded="${state.mobileMenu}">${icon('menu')}</button><span>Workspace</span>${icon('chevron', 13)}<strong>${routes[route]}</strong></div><div class="topbar-right"><span class="engine-status" title="${esc(state.apiMessage)}"><span class="status-dot ${dot}"></span>${apiLabel}</span><span class="topbar-divider"></span><button class="icon-button" data-action="theme" aria-label="Switch to ${state.theme === 'light' ? 'dark' : 'light'} theme">${icon(state.theme === 'light' ? 'moon' : 'sun', 19)}</button><span class="avatar" title="Packwise workspace">PW</span></div></header>
  <main id="main-content" tabindex="-1" class="main-content page-${route}">${body}</main><footer class="footer"><span>${brandMark} Thoughtful packaging starts here.<small class="footer-credit">Built by 4Bit-Coders</small></span><span>Decision support, not certification. <a href="#methodology">Read our approach ${icon('arrow', 13)}</a></span></footer></div></div>`;
}

function heroIllustration() {
  return `<div class="hero-art" aria-label="Illustration of food and packaging research"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><span class="art-top-label">DESIGNED AROUND YOUR FOOD</span><div class="hero-art-food">${foodArt('tomato', 112)}</div><div class="art-float freshness">${icon('leaf', 18)}<span>Food properties</span></div><div class="art-float material-chip"><span class="chip-dot"></span> Research-linked materials</div><div class="art-float package-callout"><span class="callout-icon">${icon('layers', 19)}</span><div><strong>Inputs → model</strong><small>API → explanation</small></div></div></div>`;
}
function renderHome() {
  const cards = scenarios.map(s => `<button class="demo-card ${s.color}" data-action="demo-${s.id}"><div class="food-illustration">${foodArt(s.icon, 72)}<span class="demo-arrow">${icon('arrow', 15)}</span></div><strong>${esc(s.short)}</strong><span>${esc(s.tag)}</span></button>`).join('');
  return `<section class="welcome-row"><div><p class="eyebrow">FOOD SCIENCE, WITH ITS SOURCES</p><h1>Good food deserves a thoughtful fit.</h1><p class="muted">Food properties and journey conditions go to a trained model through the Packwise API.</p></div>${badge('DECISION SUPPORT', 'outline')}</section>
  <section class="hero"><div class="hero-copy"><div class="hero-tag"><span class="status-dot ${state.apiStatus === 'online' ? '' : 'offline'}"></span> ${state.apiStatus === 'online' ? 'MODEL SERVICE CONNECTED' : 'MODEL SERVICE STATUS'}</div><h2>Better packaging.<br><em>Less food waste.</em></h2><p>Explore a model-generated material class,<br class="desktop-break"> the information behind it, and the limits<br class="desktop-break"> that still need real-world testing.</p><div class="hero-actions">${btn('Get recommendation', 'new')}${btn('Choose a demo food', 'demo-tomato', 'text-button', 'bolt')}</div><div class="hero-trust"><span>${icon('check', 14)} Actual input values go to the backend</span><span>${icon('check', 14)} Suitability and model probability shown separately</span></div></div>${heroIllustration()}</section>
  <section class="overview-stats"><div>${icon('layers', 21)}<span><strong>${state.materials.length || 9}</strong> material profiles</span><small>Qualitative, source-linked data</small></div><div>${icon('chart', 21)}<span><strong>8</strong> property features</span><small>Plus validated pH input</small></div><div>${icon('leaf', 21)}<span><strong>${scenarios.length}</strong> supported commodities</span><small>Prototype scope is explicit</small></div></section>
  <section class="demo-section"><div class="section-heading"><div><p class="eyebrow">START WITH SOMETHING FAMILIAR</p><h2>What are we packing today?</h2></div><span class="section-aside">Seven demo foods. Different needs. <span>Explore the fit.</span></span></div><div class="demo-grid">${cards}</div></section>
  <section class="home-bottom"><div class="how-card"><div class="section-heading"><h2>From properties to possibilities.</h2><a href="#methodology">How it works ${icon('arrow', 15)}</a></div><div class="steps-inline">${[['01', 'Describe the food', 'Use measured properties where available.'], ['02', 'Send to the backend', 'The API validates and preprocesses your inputs.'], ['03', 'Review the model response', 'See the predicted class, evidence and caveats.']].map(([n, h, p]) => `<div><span class="step-number">${n}</span><strong>${h}</strong><p>${p}</p></div>`).join('')}</div></div><div class="preview-card"><div class="preview-header">${badge('HOW THE SERVICE WORKS')} ${icon('spark', 18)}</div><div class="preview-main"><span class="material-symbol mint">${icon('layers', 27)}</span><div><small>Browser → API → model</small><strong>One request. A traceable result.</strong><span>${state.apiStatus === 'online' ? 'The recommendation service is reachable.' : 'Connect the backend to run an analysis.'}</span></div></div><button class="link-button" data-action="new">Enter food properties ${icon('arrow', 16)}</button></div></section>`;
}

const tooltip = text => `<span class="help" tabindex="0" role="note" aria-label="${esc(text)}">${icon('info', 13)}<span role="tooltip">${esc(text)}</span></span>`;
function field(name, label, unit, min, max, step, help) {
  const error = state.errors[name] || '';
  return `<div class="field"><label for="${name}">${label} ${tooltip(help)}</label><div class="input-unit"><input id="${name}" name="${name}" type="number" inputmode="decimal" min="${min}" max="${max}" step="${step}" value="${esc(state.draft[name] ?? '')}" aria-invalid="${!!error}" ${error ? `aria-describedby="error-${name}"` : ''}><span>${unit}</span></div><span class="field-error" id="error-${name}">${esc(error)}</span></div>`;
}
function selectField(name, label, options, help = '') {
  const error = state.errors[name] || '';
  return `<div class="field"><label for="${name}">${label} ${help ? tooltip(help) : ''}</label><select id="${name}" name="${name}" aria-invalid="${!!error}" ${error ? `aria-describedby="error-${name}"` : ''}><option value="" ${!state.draft[name] ? 'selected' : ''}>Not provided</option>${Object.entries(options).map(([key, value]) => `<option value="${key}" ${state.draft[name] === key ? 'selected' : ''}>${value}</option>`).join('')}</select><span class="field-error" id="error-${name}">${esc(error)}</span></div>`;
}
function renderAnalyze() {
  const selected = scenarios.find(s => s.id === state.draft.id);
  const customFood = state.draft.id === 'custom';
  const customName = state.draft.customCommodityName || '';
  return `<div class="page-title"><div><p class="eyebrow">LET’S FIND THE RIGHT FIT</p><h1>A little about your food.</h1><p class="muted">Enter a recognized food and any properties you know. Blank measurements are omitted from the suitability score.</p></div>${badge('10 REQUEST FIELDS', 'outline')}</div>
  <div class="scenario-strip"><span>QUICK START</span>${scenarios.map(s => `<button class="scenario-pill ${state.draft.id === s.id ? 'selected' : ''}" data-action="demo-${s.id}">${foodArt(s.icon, 27)}${esc(s.short)}</button>`).join('')}</div>
  <div class="analysis-layout"><form id="analysis-form" novalidate><div class="form-card"><div class="card-heading"><span class="number-icon">01</span><div><h2>Food profile</h2><p>Enter what you know; blank measurements stay out of the score.</p></div>${icon('leaf', 22)}</div><div class="form-grid">
    <div class="field"><label for="commodity-select">Food commodity</label><select id="commodity-select" name="commoditySelect" required>${scenarios.map(s => `<option value="${s.id}" ${state.draft.id === s.id ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}<option value="custom" ${customFood ? 'selected' : ''}>Custom food…</option></select></div>
      ${customFood ? `<div class="field full custom-food-field"><label for="custom-food-name">Food name</label><input id="custom-food-name" name="customCommodityName" type="text" maxlength="73" required autocomplete="off" placeholder="For example, homemade pickle" value="${esc(customName)}"><span class="field-hint">Recognized foods can be assessed even when they are not named training profiles. Give any measured properties below.</span></div>` : ''}
      ${field('moisture', 'Moisture content', '%', 0, 100, '.01', 'Mass percentage of water. This is not water activity and does not establish microbial safety.')}
      ${field('fat', 'Fat / oil content', '%', 0, 100, '.01', 'Mass percentage of fat or oil in the food formulation being packed.')}
    ${field('ph', 'pH level', 'pH', 0, 14, '.1', 'pH is validated and shown in the report; this prototype does not use it as a model feature or as a food-safety assessment.')}
    ${field('respiration_rate', 'Respiration rate', 'mL CO₂/kg·h', 0, 500, '.1', 'Enter a measured rate at the intended condition for respiring produce. Zero means this prototype does not use a respiration measurement for the selected processed food.')}
  </div></div><div class="form-card"><div class="card-heading"><span class="number-icon">02</span><div><h2>Storage & journey</h2><p>Protect your food from the first mile to the last.</p></div>${icon('truck', 22)}</div><div class="form-grid">
    ${selectField('storage_condition', 'Storage condition', { ambient: 'Ambient', chilled: 'Chilled', frozen: 'Frozen' })}
    ${field('temperature', 'Storage temperature', '°C', -40, 60, '.1', 'Use maintained storage temperature. Chilled: −1 to 8 °C; frozen: −12 °C or below.')}
    ${field('humidity', 'Relative humidity', '% RH', 0, 100, '1', 'External storage humidity affects moisture transfer through the package.')}
    ${field('shelf_life', 'Desired shelf life', 'days', 1, 730, '1', 'A design target sent to the model, not a predicted or promised outcome.')}
    ${selectField('transport_condition', 'Transportation', { local: 'Local / gentle handling', long: 'Long-distance distribution', rough: 'Rough handling / bulk freight', cold: 'Temperature-controlled cold chain' })}
  </div></div><div class="form-submit"><div class="general-error" role="alert">${esc(state.errors.general || (Object.keys(state.errors).length ? 'Please review the highlighted fields.' : ''))}</div><div><button type="button" class="button secondary" data-action="reset">Reset values</button><button type="submit" class="button primary" id="analyze-button" ${state.submitting ? 'disabled aria-busy="true"' : ''}>${state.submitting ? '<span class="spinner"></span> Sending actual inputs…' : `${icon('spark', 18)} Get packaging recommendation ${icon('arrow', 17)}`}</button></div><small>${icon('shield', 13)} Values are sent to the configured Packwise API. No credentials are stored in the browser.</small></div></form>
  <aside class="analysis-side"><div class="profile-preview"><div class="profile-food ${selected?.color || 'mint'}">${foodArt(selected?.icon || 'grain', 110)}</div>${badge(customFood ? 'CUSTOM FOOD NAME' : 'SUPPORTED DEMO PROFILE', customFood ? 'amber' : '')}<h2>${esc(customFood ? customName || 'Custom food' : selected?.name || 'Select a commodity')}</h2><p>${esc(customFood ? 'The model prediction and property-based material ranking use the submitted properties. Unknown measurements lower data coverage.' : selected?.description || 'Choose a demo food or enter another recognized food commodity. The API validates the name before prediction.')}</p><div class="profile-divider"></div><h3>The response includes</h3><ul class="check-list">${['Estimated suitability and data coverage', 'Ranked material recommendation', 'Estimated sustainability index', 'Model probability shown separately', 'Source-linked properties and limitations'].map(text => `<li>${icon('check', 15)}${text}</li>`).join('')}</ul></div><div class="info-note">${icon('info', 20)}<div><strong>Prototype data, clearly labeled.</strong><p>Training labels are curated from documented packaging principles, not measured package outcomes.</p></div></div><div class="plain-note">${icon('flask', 19)}<p>A decision-support shortlist only. Validate the food, package, process, transport and shelf life with qualified testing.</p></div></aside></div>`;
}

function commodityName(value) {
  if (value?.startsWith('custom:')) return value.slice('custom:'.length);
  return scenarios.find(item => item.apiCommodity === value)?.name || value;
}

function propertyValue(value) { return value == null || value === '' ? 'Data unavailable' : typeof value === 'string' ? value : JSON.stringify(value); }
function thicknessValue(value) {
  if (value == null || value === '') return 'Data unavailable';
  if (Array.isArray(value) && value.length === 2) return `${value[0]}–${value[1]} µm`;
  return typeof value === 'number' ? `${value} µm` : propertyValue(value);
}
function materialCard(material, label) {
  return `<article class="alternative-card"><div class="alt-top">${material.image_asset ? `<img class="alternative-image" src="${esc(material.image_asset)}" alt="" loading="lazy">` : `<span class="material-symbol mint">${esc(material.abbreviation)}</span>`}${badge('RANKED OPTION', 'outline')}</div><p class="eyebrow">${label}${Number.isFinite(material.estimated_suitability) ? ` · ${Math.round(material.estimated_suitability)}% fit` : ''}</p><h3>${esc(material.name)}</h3><p>${esc(material.structure)}</p><div class="alt-footer"><span>${esc((material.typical_applications || []).join(', ') || 'Food fit estimated from properties')}</span><button class="link-button" data-action="detail-${esc(material.id)}">View evidence ${icon('arrow', 15)}</button></div></article>`;
}
function renderResults() {
  const result = state.result;
  if (!result) return `<div class="empty-state">${icon('spark', 40)}<h1>Your next great fit starts here.</h1><p>Send a recognized food and any known properties for a compatibility estimate.</p>${btn('Start an analysis', 'new')}</div>`;
  const material = result.recommended_material || {}, input = result.input_echo || {};
  const isUnseenFood = ['valid_unseen_commodity', 'out_of_training_scope'].includes(result.prediction_scope);
  const suitabilityScore = Number.isFinite(result.suitability?.score) ? Math.max(0, Math.min(100, Math.round(result.suitability.score))) : null;
  const confidencePercent = Number.isFinite(result.confidence) ? Math.round(result.confidence * 100) : null;
  const sustainabilityScore = Number.isFinite(result.sustainability?.score) ? Math.max(0, Math.min(100, Math.round(result.sustainability.score))) : null;
  const coverage = Number.isFinite(result.data_coverage_percent) ? Math.max(0, Math.min(100, Math.round(result.data_coverage_percent))) : Number.isFinite(result.suitability?.data_coverage_percent) ? Math.max(0, Math.min(100, Math.round(result.suitability.data_coverage_percent))) : 0;
  const sustainabilityCoverage = Number.isFinite(result.sustainability?.data_coverage_percent) ? Math.max(0, Math.min(100, Math.round(result.sustainability.data_coverage_percent))) : 0;
  const targetShelfLife = result.target_shelf_life_days ?? input.shelf_life;
  const suitabilityLabel = result.suitability?.level || (suitabilityScore === null ? 'Estimate unavailable' : suitabilityScore >= 80 ? 'Highly Suitable' : suitabilityScore >= 65 ? 'Suitable' : suitabilityScore >= 45 ? 'Moderate Fit' : 'Limited Fit');
  const foodName = commodityName(input.commodity || 'food');
  const storageDescription = [input.temperature != null ? `${input.temperature} °C` : '', input.storage_condition || 'storage not specified', input.transport_condition ? `${input.transport_condition} transport` : ''].filter(Boolean).join(' · ');
  const properties = [
    ['Structure', propertyValue(material.structure)], ['Film thickness', thicknessValue(material.thickness_range_um)],
    ['OTR', propertyValue(material.otr)], ['WVTR', propertyValue(material.wvtr)],
    ['Gas permeability', propertyValue(material.gas_permeability)], ['Sealability', propertyValue(material.sealability)],
    ['Mechanical strength', propertyValue(material.mechanical_strength)], ['MAP suitability', propertyValue(material.map_suitability)],
    ['Packaging type', propertyValue(result.packaging_type || material.family)]
  ];
  const influences = (result.important_features || []).map(feature => `<div class="factor"><div><span>${esc(feature.label)}<small class="muted">${esc(feature.value)} · global importance</small></span><strong>${Math.round(feature.global_importance * 100)}<small>%</small></strong></div><div class="progress-track" role="meter" aria-label="${esc(feature.label)} global model importance" aria-valuenow="${Math.round(feature.global_importance * 100)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${Math.max(0, Math.min(100, feature.global_importance * 100))}%"></span></div></div>`).join('');
  const refs = material.references || [];
  const suitabilityReasons = (result.suitability?.key_factors || []).slice(0, 5);
  const sustainabilityReasons = (result.sustainability?.factors || []).map(factor => factor.label);
  const modelMaterial = result.model_prediction?.material?.name || 'Unavailable';
  const reasonList = suitabilityReasons.map(reason => `<li>${icon('check', 16)}<span>${esc(reason)}</span></li>`).join('');
  return `<div class="page-title result-title"><div><p class="eyebrow">${isUnseenFood ? 'NEW FOOD' : 'PACKAGING RESULT'}</p><h1>Recommended packaging for ${esc(foodName)}</h1><p class="muted">${esc(storageDescription)}</p></div><div class="title-actions">${btn('Edit inputs', 'edit', 'secondary', 'edit')}<button class="icon-button bordered" data-action="export" aria-label="Download recommendation as JSON" title="Download recommendation as JSON">${icon('download')}</button><button class="icon-button bordered" data-action="print" aria-label="Print or save report as PDF" title="Print or save as PDF">${icon('print')}</button></div></div>
  <div class="result-top recommendation-top"><section class="recommendation-hero"><div class="material-visual">${material.image_asset ? `<img src="${esc(material.image_asset)}" alt="Illustration of ${esc(material.name)} packaging">` : `<div class="material-visual-fallback" role="img" aria-label="${esc(material.name)} packaging illustration">${icon('layers', 42)}</div>`}</div><div class="recommendation-copy">${badge(isUnseenFood ? 'CUSTOM FOOD' : 'COMPATIBILITY RANKING', isUnseenFood ? 'amber' : 'lime')}<p class="eyebrow">RECOMMENDED PACKAGING</p><h2>${esc(material.name || 'Material estimate')}</h2><p>${esc(material.structure || 'Review the packaging structure with a qualified specialist.')}</p><div class="recommendation-tags"><span>${esc(material.family || result.packaging_type || 'Packaging type estimated')}</span><span>${esc(material.abbreviation || 'Prototype')}</span></div></div></section><section class="assessment-panel"><div class="suitability-metric"><div class="suitability-ring" role="img" aria-label="${suitabilityScore === null ? 'Suitability estimate unavailable' : `Estimated suitability ${suitabilityScore} percent`}" style="--score:${suitabilityScore ?? 0}"><span>${suitabilityScore === null ? '—' : `${suitabilityScore}%`}</span></div><div class="suitability-copy"><p class="eyebrow">ESTIMATED SUITABILITY</p><strong>${esc(suitabilityLabel)}</strong><small>${esc(result.suitability?.summary || 'Calculated from the available food properties and material profile.')}</small></div></div><div class="confidence-metric"><div><p class="eyebrow">MODEL PREDICTION</p><strong>${esc(modelMaterial)}</strong></div><small>${confidencePercent === null ? 'No model probability was returned. Compatibility ranking used available properties.' : `${confidencePercent}% model probability. ${result.confidence_note || ''}`}</small></div><p class="metric-separation">Model probability and compatibility suitability are separate estimates.</p></section></div>
  <section class="estimate-strip"><article class="estimate-tile sustainability-tile"><div><p class="eyebrow">ESTIMATED SUSTAINABILITY</p><strong>${sustainabilityScore === null ? '—' : `${sustainabilityScore}%`}</strong><span>Prototype index</span></div><small>${esc(result.sustainability?.summary || 'Based on available packaging structure evidence.')}</small></article><article class="estimate-tile coverage-tile"><div><p class="eyebrow">SUITABILITY DATA COVERAGE</p><strong>${coverage}%</strong><span>${result.suitability?.coverage?.available_factors ?? '—'} of ${result.suitability?.coverage?.relevant_factors ?? '—'} factors scored</span></div><div class="coverage-track" role="meter" aria-label="Suitability data coverage" aria-valuenow="${coverage}" aria-valuemin="0" aria-valuemax="100"><span style="width:${coverage}%"></span></div><small>Missing inputs are left out of the suitability score. Lower coverage means less supporting evidence.</small></article></section>
  <div class="results-grid redesigned-results"><section class="panel specs-panel"><div class="section-heading"><div><p class="eyebrow">MATERIAL PROFILE</p><h2>Material properties</h2></div>${icon('layers', 22)}</div><div class="material-properties-grid">${properties.map(([label, value], index) => `<div class="property-card ${index === 0 ? 'property-card-wide' : ''}"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join('')}</div></section>
  <section class="panel shelf-panel"><div class="panel-icon sand">${icon('clock', 22)}</div><p class="eyebrow">TARGET SHELF LIFE</p><h2>${targetShelfLife == null ? 'Not specified' : `${esc(targetShelfLife)} days`}</h2><p>${targetShelfLife == null ? 'No duration was entered; it was left out of the suitability score.' : 'Your requested storage duration. This is a target, not a prediction.'}</p></section>
  <section class="panel map-panel"><div class="panel-icon mint">${icon('spark', 22)}</div><p class="eyebrow">WHY THIS MATERIAL?</p><h2>${esc(material.name || 'Recommended material')}</h2><p>${esc(result.explanation || result.suitability?.summary || 'Ranked from the available food and packaging characteristics.')}</p><ul class="compatibility-reasons">${reasonList || `<li>${icon('info', 16)}<span>Reasons use the available measured properties and qualitative material profile.</span></li>`}</ul></section>
  <section class="panel score-panel"><div class="section-heading"><div><p class="eyebrow">MODEL INPUTS</p><h2>What shaped the model</h2></div>${icon('chart', 22)}</div><p class="muted small-text">These are overall patterns across the training data.</p><div class="factor-list">${influences || '<p class="muted">Feature details are unavailable.</p>'}</div></section></div>
  <section class="panel sustainability-detail"><div class="section-heading"><div><p class="eyebrow">SUSTAINABILITY ESTIMATE</p><h2>${sustainabilityScore === null ? 'Limited prototype index' : `${sustainabilityScore}% estimated index`}</h2></div>${icon('leaf', 22)}</div><p>${esc(result.sustainability?.summary || 'The estimate uses only characteristics available for this material.')}</p><p class="muted small-text">Coverage: ${sustainabilityCoverage}% · this index is not a life-cycle assessment. It does not claim verified recyclability or measured food-waste reduction.</p><div class="sustainability-factor-list">${sustainabilityReasons.map(label => `<span>${icon('check', 14)}${esc(label)}</span>`).join('') || '<span>Material evidence is incomplete.</span>'}</div></section>
  <section class="alternatives-section"><div class="section-heading"><div><p class="eyebrow">OTHER OPTIONS</p><h2>Alternative materials</h2></div><a href="#materials">Explore materials ${icon('arrow', 15)}</a></div><div class="alternatives-grid">${(result.alternatives || []).map((alt, i) => materialCard(alt, `OPTION ${String(i + 1).padStart(2, '0')}`)).join('') || `<article class="sustainability-card"><h3>No alternatives available</h3><p>${esc(result.alternatives_note || 'No other packaging profiles were ranked.')}</p></article>`}</div></section>
  ${refs.length ? `<section class="panel"><div class="section-heading"><div><p class="eyebrow">SOURCES</p><h2>Research references</h2></div>${icon('book', 22)}</div><ul>${refs.map(ref => `<li><a href="${esc(ref.url)}" target="_blank" rel="noopener noreferrer">${esc(ref.name)} ${icon('arrow', 13)}</a></li>`).join('')}</ul></section>` : ''}
  ${(result.warnings || []).length ? `<section class="warnings-panel"><div>${icon('info', 22)}<div><h2>Before choosing a package</h2></div></div><ul>${result.warnings.map(warning => `<li>${esc(warning)}</li>`).join('')}</ul></section>` : ''}<div class="result-bottom">${btn('Analyze another food', 'new', 'secondary', 'plus')}${btn('Download report', 'export', 'primary', 'download')}</div>`;
}

function libraryCards() {
  const found = state.materials.filter(material => (state.filter === 'all' || material.family === state.filter) && `${material.name} ${material.family} ${material.structure} ${(material.typical_applications || []).join(' ')}`.toLowerCase().includes(state.query.toLowerCase()));
  return `<div class="library-count"><span><strong>${found.length}</strong> material${found.length === 1 ? '' : 's'} ${state.query ? `matching “${esc(state.query)}”` : 'to explore'}</span><small>Qualitative source-linked profiles · unsourced numeric values omitted</small></div><div class="library-grid">${found.length ? found.map(material => `<article class="library-card"><div class="library-card-top"><span class="material-symbol mint">${esc(material.abbreviation)}</span>${badge(esc(material.family))}</div><h2>${esc(material.name)}</h2><p>${esc(material.structure)}</p><div class="material-metrics"><div><span>Oxygen barrier</span>${esc(material.oxygen_barrier)}</div><div><span>Moisture barrier</span>${esc(material.moisture_barrier)}</div><div><span>Gas exchange</span>${esc(material.gas_permeability)}</div></div><div class="application-tags">${(material.typical_applications || []).map(app => `<span>${esc(app)}</span>`).join('')}</div><div class="library-card-bottom"><button class="link-button" data-action="detail-${esc(material.id)}">View evidence ${icon('arrow', 15)}</button><label class="compare-check"><input type="checkbox" data-compare="${esc(material.id)}" ${state.selected.includes(material.id) ? 'checked' : ''}> Compare</label></div></article>`).join('') : `<div class="empty-state">${icon('search', 34)}<h2>${state.materials.length ? 'No materials found.' : 'Connect the API to load the packaging database.'}</h2><p>${state.materials.length ? 'Try a different search or family.' : esc(state.apiMessage)}</p>${btn('Retry API connection', 'retry-api', 'secondary', 'refresh')}</div>`}</div>`;
}
function renderMaterials() {
  if (!state.materials.length) return `<div class="page-title"><div><p class="eyebrow">SOURCE-LINKED PROFILES</p><h1>Packaging materials.</h1><p class="muted">${esc(state.apiMessage)}</p></div>${badge('LIVE API DATA', 'outline')}</div>${libraryCards()}`;
  const families = [...new Set(state.materials.map(material => material.family))];
  return `<div class="page-title"><div><p class="eyebrow">KNOW WHAT’S ON THE OUTSIDE</p><h1>A world of material possibilities.</h1><p class="muted">Explore structure, applications, source notes and the information still missing.</p></div>${badge(`${state.materials.length} MATERIAL PROFILES`, 'outline')}</div><div class="library-toolbar"><div class="search-input">${icon('search', 19)}<input id="material-search" type="search" placeholder="Search materials or food applications…" aria-label="Search materials" value="${esc(state.query)}"></div><label class="filter-label" for="material-filter">Material family<select id="material-filter"><option value="all">All families</option>${families.map(family => `<option value="${esc(family)}" ${state.filter === family ? 'selected' : ''}>${esc(family)}</option>`).join('')}</select></label></div><div id="library-content">${libraryCards()}</div><div id="compare-bar" class="compare-bar ${state.selected.length ? 'visible' : ''}"><span><strong id="compare-count">${state.selected.length}</strong> of 3 materials selected</span><div>${btn('Clear', 'clear-compare', 'text-button', 'close')}<button class="button primary" data-action="compare" ${state.selected.length < 2 ? 'disabled' : ''}>Compare materials ${icon('arrow', 16)}</button></div></div><p class="library-disclaimer">${icon('flask', 18)} No thickness, OTR, WVTR or strength numbers are inferred without a verified structure and test condition.</p>`;
}

function renderMethodology() {
  const card = state.modelCard, cv = card?.cross_validation || {};
  const cvRows = Object.entries(cv).map(([name, metrics]) => `<tr><th scope="row">${esc(name.replaceAll('_', ' '))}</th>${['accuracy', 'precision_macro', 'recall_macro', 'f1_macro'].map(key => `<td>${(metrics[key].mean * 100).toFixed(1)}% ± ${(metrics[key].std * 100).toFixed(1)}</td>`).join('')}</tr>`).join('');
  return `<div class="page-title"><div><p class="eyebrow">SCIENCE YOU CAN FOLLOW</p><h1>Clear reasoning. Clear limits.</h1><p class="muted">A real supervised classifier inside a research-derived prototype workflow.</p></div>${badge('SYNTHETIC / CURATED DATA', 'outline')}</div>
  <section class="method-hero"><div><span class="hero-tag">THE PACKWISE APPROACH</span><h2>From food profile<br>to model output.</h2><p>The API runs the trained classifier when available, then ranks every material with a property-based compatibility estimate.</p>${btn('Try an analysis', 'new')}</div><div class="method-pipeline">${[['leaf', 'Browser inputs', 'Food properties, storage and route'], ['layers', 'Food requirements', 'Relevant factors and available evidence'], ['spark', 'Ranked compatibility', 'Material fit, sustainability proxy and limits']].map(([ico, title, desc], index) => `<div><span>${icon(ico, 24)}</span><section><small>0${index + 1}</small><strong>${title}</strong><p>${desc}</p></section></div>`).join('')}</div></section>
  <div class="method-grid"><section class="panel"><p class="eyebrow">01 / DATA</p><h2>What was available.</h2><p>No inspected public dataset contained experimental labels for the complete relationship food properties + storage/transport conditions → recommended packaging material. Public data cover material permeability, food composition, respiration or packaging studies; those are not the requested labels.</p><p>Packwise uses a reproducible deterministic synthetic/curated design grid. Labels follow documented rules and are not presented as measured decisions.</p><p><a href="https://fdc.nal.usda.gov/" target="_blank" rel="noopener noreferrer">USDA FoodData Central</a> supplies selected illustrative moisture/fat centers. <a href="https://postharvest.ucdavis.edu/produce-facts-sheets/tomato" target="_blank" rel="noopener noreferrer">UC Davis tomato facts</a> supports tomato respiration anchors.</p></section>
  <section class="panel"><p class="eyebrow">02 / ALGORITHMS</p><h2>Compare, then choose.</h2><p>Candidate models: Logistic Regression, Random Forest and Gradient Boosting. The final model is selected using cross-validation macro-F1, with accuracy as a tie-breaker.</p><p>Current selected model: <strong>${esc(card?.model_name || 'Connect the API to load the model card')}</strong>. Training grid: <strong>${card?.dataset_rows ?? '—'}</strong> rows. Eight measured/storage fields enter the fitted model. Commodity name and pH are validated and recorded but excluded from prediction.</p><p>Categorical variables use one-hot encoding; numeric variables use imputation and standard scaling inside the training pipeline.</p></section>
  <section class="panel"><p class="eyebrow">03 / EVALUATION</p><h2>Metrics from the trained model.</h2><p>These values describe reproduction of the synthetic rule grid. They are not accuracy on real foods or independent packaging trials.</p>${cvRows ? `<div class="table-scroll"><table class="compare-table"><thead><tr><th>Model</th><th>Accuracy</th><th>Macro precision</th><th>Macro recall</th><th>Macro F1</th></tr></thead><tbody>${cvRows}</tbody></table></div><p>Held-out synthetic-grid macro F1: <strong>${(card.holdout.f1_macro * 100).toFixed(1)}%</strong>; accuracy: <strong>${(card.holdout.accuracy * 100).toFixed(1)}%</strong>. Full report is in <code>docs/model_report.md</code>.</p>` : '<p>Metrics load from the backend model card.</p>'}</section>
  <section class="panel"><p class="eyebrow">04 / INTERPRETATION</p><h2>Prediction is not validation.</h2><p>The property-based compatibility engine ranks catalog materials from relevant food requirements and qualitative capability bands. The trained model probability is an optional input and appears separately; it is not calibrated against package trials. Data coverage reports how much evidence informed the estimate.</p><p>Suitability is an estimated decision-support score, not a validated package outcome. The sustainability index is a limited design proxy, not a life-cycle assessment. Thickness, OTR, WVTR, sealability and mechanical performance remain qualitative or unavailable where verified structure-specific measurements were not found.</p></section></div>
  <section class="panel rules-panel"><div class="section-heading"><h2>The actual request path.</h2>${icon('book', 22)}</div><div class="rules-grid">${[['wind', 'Food characteristics', 'Commodity, composition, pH and respiration measurements; blanks are omitted.'], ['truck', 'Storage + transport', 'Shelf-life target, temperature, humidity and route when provided.'], ['spark', 'Model support', 'The trained classifier contributes a separate class probability when available.'], ['layers', 'Compatibility + estimate', 'Ranked material fit, data coverage, sustainability proxy and limitations.']].map(([ico, title, desc]) => `<div><span class="panel-icon mint">${icon(ico, 21)}</span><h3>${title}</h3><p>${desc}</p></div>`).join('')}</div></section>
  <section class="warnings-panel"><div>${icon('flask', 24)}<div><h2>Prototype boundary.</h2><p>Not a food-safety, migration, package-engineering or shelf-life certification.</p></div></div><p>Future validation requires independent package trials, measured material properties at relevant conditions, supplier specifications, food-contact compliance review, microbial and quality studies, and broader food/region coverage.</p></section>`;
}

function render() {
  let route = getRoute();
  if (!routes[route]) { route = 'home'; history.replaceState(null, '', '#home'); }
  document.title = `${routes[route]} — Packwise`;
  const pages = { home: renderHome, analyze: renderAnalyze, results: renderResults, materials: renderMaterials, methodology: renderMethodology };
  $('#app').innerHTML = shell(route, pages[route]());
}
function setScenario(id) {
  const scenario = scenarios.find(item => item.id === id);
  if (!scenario) return;
  state.customFoodName = '';
  state.draft = { ...scenario, commodity: scenario.apiCommodity };
  state.errors = {};
}
function selectCommodity(id) {
  if (id !== 'custom') { setScenario(id); return; }
  const customCommodityName = state.draft.customCommodityName || '';
  state.draft = { id: 'custom', customCommodityName, commodity: `custom:${customCommodityName}`, moisture: null, fat: null, ph: null, respiration_rate: null, shelf_life: null, temperature: null, humidity: null, storage_condition: '', transport_condition: '' };
  state.errors = {};
}
function showDialog(title, content, wide = false) {
  const dialog = document.createElement('dialog');
  dialog.className = `material-dialog ${wide ? 'wide' : ''}`;
  dialog.setAttribute('aria-labelledby', 'dialog-title');
  dialog.innerHTML = `<div class="dialog-header"><h2 id="dialog-title">${esc(title)}</h2><button class="icon-button" data-action="close-dialog" aria-label="Close dialog">${icon('close')}</button></div><div class="dialog-content">${content}</div>`;
  dialog.addEventListener('close', () => dialog.remove());
  document.body.append(dialog); dialog.showModal();
}
function detail(id) {
  const material = state.materials.find(item => item.id === id);
  if (!material) return;
  const fields = [
    ['Structure', material.structure], ['Typical applications', (material.typical_applications || []).join(', ')],
    ['Oxygen barrier', material.oxygen_barrier], ['Moisture barrier', material.moisture_barrier],
    ['OTR', propertyValue(material.otr)], ['WVTR', propertyValue(material.wvtr)], ['Gas permeability', material.gas_permeability],
    ['Sealability', material.sealability], ['Mechanical strength', material.mechanical_strength], ['MAP suitability', material.map_suitability],
    ['Limitations', (material.limitations || []).join(' ')], ['Numeric thickness range', propertyValue(material.thickness_range_um)]
  ];
  showDialog(material.name, `<div class="dialog-material-intro"><span class="material-symbol mint">${esc(material.abbreviation)}</span><div>${badge(esc(material.family))}<p>${esc(material.structure)}</p></div></div><dl class="spec-list">${fields.map(([key, value]) => `<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><h3>Sources used for this profile</h3><ul>${(material.references || []).map(ref => `<li><a href="${esc(ref.url)}" target="_blank" rel="noopener noreferrer">${esc(ref.name)} ${icon('arrow', 13)}</a></li>`).join('')}</ul><p class="reference-note">Numeric properties stay unspecified unless the source identifies a complete structure and test conditions.</p>`);
}
function compare() {
  const selected = state.selected.map(id => state.materials.find(item => item.id === id)).filter(Boolean);
  if (selected.length < 2) return;
  const fields = [['Structure', 'structure'], ['Applications', 'typical_applications'], ['Oxygen barrier', 'oxygen_barrier'], ['Moisture barrier', 'moisture_barrier'], ['OTR', 'otr'], ['WVTR', 'wvtr'], ['Gas permeability', 'gas_permeability'], ['Sealability', 'sealability'], ['Mechanical strength', 'mechanical_strength'], ['MAP suitability', 'map_suitability']];
  showDialog('Material comparison', `<div class="table-scroll"><table class="compare-table"><thead><tr><th scope="col">Property</th>${selected.map(item => `<th scope="col">${esc(item.name)}</th>`).join('')}</tr></thead><tbody>${fields.map(([label, key]) => `<tr><th scope="row">${esc(label)}</th>${selected.map(item => `<td>${esc(propertyValue(key === 'typical_applications' ? item[key]?.join(', ') : item[key]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`, true);
}
function exportReport() {
  if (!state.result) return;
  const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), ...state.result }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob), anchor = document.createElement('a');
  anchor.href = url; anchor.download = `packwise-${state.result.input_echo.commodity}-recommendation.json`;
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify('The API response report has been downloaded.');
}
async function refreshApiState(shouldRender = true) {
  state.apiStatus = 'checking'; state.apiMessage = 'Checking health, model and packaging database';
  try {
    const health = await apiGet('/api/health').catch(error => ({ model_loaded: false, detail: error.message }));
    const [catalog, modelCard] = await Promise.all([apiGet('/api/materials'), apiGet('/api/model-card').catch(() => null)]);
    state.materials = catalog.materials || []; state.modelCard = modelCard;
    state.apiStatus = health.model_loaded ? 'online' : 'fallback';
    state.apiMessage = health.model_loaded ? `Loaded ${health.model_name} · ${health.training_rows} curated rows` : 'Property compatibility is ready; trained model is unavailable';
  } catch (error) { state.apiStatus = 'offline'; state.apiMessage = error.message; }
  if (shouldRender) render();
}

document.addEventListener('click', event => {
  const target = event.target.closest('[data-action]'); if (!target) return;
  const action = target.dataset.action;
  if (action.startsWith('demo-')) { setScenario(action.slice(5)); goto('analyze'); }
  else if (action.startsWith('detail-')) detail(action.slice(7));
  else if (action === 'new') { state.errors = {}; goto('analyze'); }
  else if (action === 'edit') {
    const input = state.result?.input_echo;
    if (input) {
      const customFoodName = input.commodity.startsWith('custom:') ? input.commodity.slice('custom:'.length) : '';
      const scenario = scenarios.find(item => item.apiCommodity === input.commodity) || defaultInput();
      state.customFoodName = customFoodName;
      state.draft = { ...scenario, id: customFoodName ? 'custom' : scenario.id, customCommodityName: customFoodName, commodity: input.commodity, moisture: input.moisture, fat: input.fat, ph: input.ph, respiration_rate: input.respiration_rate, shelf_life: input.shelf_life, temperature: input.temperature, humidity: input.humidity, storage_condition: input.storage_condition, transport_condition: input.transport_condition };
    }
    state.errors = {}; goto('analyze');
  }
  else if (action === 'reset') {
    if (state.draft.id === 'custom') {
      const customCommodityName = state.draft.customCommodityName || '';
      state.draft = { ...defaultInput(), id: 'custom', customCommodityName, commodity: `custom:${customCommodityName}` };
      state.errors = {};
    } else setScenario(state.draft.id);
    render(); notify('Food profile values restored.');
  }
  else if (action === 'theme') { state.theme = state.theme === 'light' ? 'dark' : 'light'; document.documentElement.dataset.theme = state.theme; try { localStorage.setItem('packwise-theme', state.theme); } catch {} render(); }
  else if (action === 'menu') { state.mobileMenu = !state.mobileMenu; $('.sidebar').classList.toggle('open', state.mobileMenu); target.setAttribute('aria-expanded', String(state.mobileMenu)); }
  else if (action === 'export') exportReport();
  else if (action === 'print') window.print();
  else if (action === 'close-dialog') target.closest('dialog').close();
  else if (action === 'compare') compare();
  else if (action === 'clear-compare') { state.selected = []; render(); }
  else if (action === 'clear-filters') { state.query = ''; state.filter = 'all'; render(); }
  else if (action === 'retry-api') refreshApiState();
});
document.addEventListener('input', event => {
  if (event.target.closest('#analysis-form') && event.target.name !== 'commoditySelect') state.draft[event.target.name] = event.target.value;
  if (event.target.name === 'customCommodityName') state.draft.commodity = `custom:${event.target.value.trim()}`;
  if (event.target.id === 'material-search') { state.query = event.target.value; $('#library-content').innerHTML = libraryCards(); }
});
document.addEventListener('change', event => {
  if (event.target.id === 'commodity-select') {
    selectCommodity(event.target.value); render();
    if (event.target.value === 'custom') $('#custom-food-name')?.focus();
  }
  if (event.target.id === 'material-filter') { state.filter = event.target.value; $('#library-content').innerHTML = libraryCards(); }
  if (event.target.dataset.compare) {
    const id = event.target.dataset.compare;
    if (event.target.checked && state.selected.length === 3) { event.target.checked = false; notify('Choose up to three materials to compare.'); return; }
    state.selected = event.target.checked ? [...state.selected, id] : state.selected.filter(item => item !== id);
    $('#compare-bar').classList.toggle('visible', !!state.selected.length); $('#compare-count').textContent = state.selected.length; $('[data-action="compare"]').disabled = state.selected.length < 2;
  }
});
document.addEventListener('submit', async event => {
  if (event.target.id !== 'analysis-form') return;
  event.preventDefault();
  const form = event.target;
  if (!form.checkValidity()) { form.reportValidity(); return; }
  const values = new FormData(form), numeric = name => {
    const raw = values.get(name);
    return raw == null || String(raw).trim() === '' ? null : Number(raw);
  };
  const optionalText = name => {
    const raw = String(values.get(name) || '').trim();
    return raw || null;
  };
  const selection = values.get('commoditySelect');
  const scenario = scenarios.find(item => item.id === selection);
  const customFoodName = String(values.get('customCommodityName') || '').trim();
  const payload = {
    commodity: selection === 'custom' ? `custom:${customFoodName}` : scenario.apiCommodity, moisture: numeric('moisture'), fat: numeric('fat'), ph: numeric('ph'),
    respiration_rate: numeric('respiration_rate'), shelf_life: numeric('shelf_life'), temperature: numeric('temperature'),
    humidity: numeric('humidity'), storage_condition: optionalText('storage_condition'), transport_condition: optionalText('transport_condition')
  };
  state.draft = { ...state.draft, ...payload, id: selection === 'custom' ? 'custom' : scenario.id, customCommodityName: customFoodName };
  state.errors = {}; state.submitting = true; render();
  try {
    state.result = await apiPost('/api/recommend', payload);
    state.submitting = false; state.errors = {}; goto('results');
  } catch (error) {
    state.submitting = false;
    const details = error.body?.detail;
    if (Array.isArray(details)) for (const item of details) {
      const name = item.loc?.at(-1);
      if (['moisture', 'fat', 'ph', 'respiration_rate', 'shelf_life', 'temperature', 'humidity', 'storage_condition', 'transport_condition'].includes(name)) state.errors[name] = item.msg;
    }
    state.errors.general = error.message; render();
  }
});
window.addEventListener('hashchange', () => { state.mobileMenu = false; render(); window.scrollTo({ top: 0, behavior: 'instant' }); $('#main-content').focus({ preventScroll: true }); });
render();
refreshApiState(true);
