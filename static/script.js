document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const minMagInput = document.getElementById('minMagnitude');
    const magValSpan = document.getElementById('magVal');
    const runBtn = document.getElementById('runBtn');
    
    // Progress Steps
    const steps = {
        fetch: document.getElementById('step-fetch'),
        clean: document.getElementById('step-clean'),
        analyze: document.getElementById('step-analyze'),
        visualize: document.getElementById('step-visualize'),
        save: document.getElementById('step-save'),
        pdf: document.getElementById('step-pdf')
    };
    
    // Downloads and Display
    const downloadsPanel = document.getElementById('downloadsPanel');
    const targetRangeDisplay = document.getElementById('targetRangeDisplay');
    
    // Stats Cards
    const statTotalCount = document.getElementById('statTotalCount');
    const statMaxMag = document.getElementById('statMaxMag');
    const statAvgMag = document.getElementById('statAvgMag');
    const statTsunamiAlerts = document.getElementById('statTsunamiAlerts');
    
    // Chart elements
    const tabButtons = document.querySelectorAll('.tab-btn');
    const chartContainer = document.querySelector('.chart-container');
    const chartImage = document.getElementById('chartImage');
    const chartPlaceholder = document.getElementById('chartPlaceholder');
    const chartLoader = document.getElementById('chartLoader');
    
    // Tables
    const strongEventsTableBody = document.querySelector('#strongEventsTable tbody');
    const activeRegionsTableBody = document.querySelector('#activeRegionsTable tbody');
    
    // In-memory state
    let chartPaths = {};
    let activeChartTab = 'magnitude_distribution';
    
    // --- INITIALIZATION ---
    // Set default dates (30 days ago to today)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    endDateInput.value = formatDate(today);
    startDateInput.value = formatDate(thirtyDaysAgo);
    
    // Magnitude slider indicator update
    minMagInput.addEventListener('input', (e) => {
        magValSpan.textContent = parseFloat(e.target.value).toFixed(1);
    });
    
    // Chart tab switches
    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            tabButtons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            activeChartTab = e.target.dataset.chart;
            updateChartImage();
        });
    });
    
    // Run Pipeline Event
    runBtn.addEventListener('click', runPipeline);
    
    // Auto-check status and run initial pipeline on load
    checkCachedStatus();
    
    // --- HELPER FUNCTIONS ---
    
    function formatDate(date) {
        const d = new Date(date);
        let month = '' + (d.getMonth() + 1);
        let day = '' + d.getDate();
        const year = d.getFullYear();
        
        if (month.length < 2) month = '0' + month;
        if (day.length < 2) day = '0' + day;
        
        return [year, month, day].join('-');
    }
    
    function resetSteps() {
        Object.values(steps).forEach(step => {
            step.className = 'step pending';
            const icon = step.querySelector('i');
            icon.className = 'fa-regular fa-circle-dot';
        });
    }
    
    function setStepStatus(stepKey, status) {
        const step = steps[stepKey];
        if (!step) return;
        
        const icon = step.querySelector('i');
        step.className = `step ${status}`;
        
        if (status === 'running') {
            icon.className = 'fa-solid fa-circle-notch fa-spin';
        } else if (status === 'success') {
            icon.className = 'fa-solid'; // CSS before class handles checkmark
        } else if (status === 'error') {
            icon.className = 'fa-solid'; // CSS before class handles cross
        } else {
            icon.className = 'fa-regular fa-circle-dot';
        }
    }
    
    function getMagnitudeClass(mag) {
        if (mag < 3.0) return 'mag-minor';
        if (mag < 4.5) return 'mag-light';
        if (mag < 6.0) return 'mag-moderate';
        if (mag < 7.0) return 'mag-strong';
        return 'mag-major';
    }
    
    function updateChartImage() {
        if (!chartPaths || !chartPaths[activeChartTab]) {
            chartImage.style.display = 'none';
            chartPlaceholder.style.display = 'flex';
            chartContainer.classList.remove('loaded');
            return;
        }
        
        chartContainer.classList.remove('loaded');
        chartLoader.classList.remove('id-hidden');
        chartPlaceholder.style.display = 'none';
        
        // Add cache-buster to prevent old chart cached rendering
        const imgUrl = `${chartPaths[activeChartTab]}?t=${Date.now()}`;
        
        const tempImg = new Image();
        tempImg.onload = () => {
            chartImage.src = imgUrl;
            chartImage.style.display = 'block';
            chartLoader.classList.add('id-hidden');
            chartContainer.classList.add('loaded');
        };
        tempImg.onerror = () => {
            chartLoader.classList.add('id-hidden');
            chartPlaceholder.style.display = 'flex';
            const placeholderText = chartPlaceholder.querySelector('p');
            placeholderText.textContent = "Failed to load visualization image.";
        };
        tempImg.src = imgUrl;
    }
    
    // --- API CALLS ---
    
    async function checkCachedStatus() {
        try {
            const res = await fetch('/api/pipeline/status');
            const data = await res.json();
            
            if (data.files.cleaned_csv) {
                targetRangeDisplay.textContent = `Active Dataset Bounds: Cached data available (${data.metadata.total_records || 'unknown'} records)`;
                // Trigger an initial run with parameters to auto-populate
                runPipeline();
            } else {
                targetRangeDisplay.textContent = "Active Dataset Bounds: No active local data. Run the pipeline!";
            }
        } catch (e) {
            console.error("Status check failed", e);
        }
    }
    
    async function runPipeline() {
        // Prepare inputs
        const start_date = startDateInput.value;
        const end_date = endDateInput.value;
        const min_magnitude = parseFloat(minMagInput.value);
        
        // UI lock
        runBtn.disabled = true;
        runBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Executing...';
        downloadsPanel.classList.add('id-hidden');
        
        resetSteps();
        
        // Visual simulation of pipeline steps
        setStepStatus('fetch', 'running');
        
        try {
            const response = await fetch('/api/pipeline/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ start_date, end_date, min_magnitude })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Pipeline run failed.");
            }
            
            const result = await response.json();
            
            if (result.status === 'empty') {
                setStepStatus('fetch', 'success');
                setStepStatus('clean', 'error');
                targetRangeDisplay.textContent = `Active Dataset Bounds: ${result.message}`;
                alert(result.message);
                resetStats();
                runBtn.disabled = false;
                runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Data Pipeline';
                return;
            }
            
            // Progressive visual success flow for steps
            setTimeout(() => {
                setStepStatus('fetch', 'success');
                setStepStatus('clean', 'running');
                
                setTimeout(() => {
                    setStepStatus('clean', 'success');
                    setStepStatus('analyze', 'running');
                    
                    setTimeout(() => {
                        setStepStatus('analyze', 'success');
                        setStepStatus('visualize', 'running');
                        
                        setTimeout(() => {
                            setStepStatus('visualize', 'success');
                            setStepStatus('save', 'running');
                            
                            setTimeout(() => {
                                setStepStatus('save', 'success');
                                setStepStatus('pdf', 'running');
                                
                                setTimeout(() => {
                                    setStepStatus('pdf', 'success');
                                    
                                    // Populate Dashboard Content
                                    populateDashboard(result);
                                    
                                    // Enable buttons
                                    runBtn.disabled = false;
                                    runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Data Pipeline';
                                }, 400);
                            }, 400);
                        }, 400);
                    }, 400);
                }, 400);
            }, 400);
            
        } catch (err) {
            console.error("Pipeline run failed", err);
            // Highlight current step as error
            const currentRunning = Object.keys(steps).find(key => steps[key].classList.contains('running'));
            if (currentRunning) {
                setStepStatus(currentRunning, 'error');
            } else {
                setStepStatus('fetch', 'error');
            }
            
            alert(`Pipeline Error: ${err.message}`);
            runBtn.disabled = false;
            runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Data Pipeline';
        }
    }
    
    function resetStats() {
        statTotalCount.textContent = '-';
        statMaxMag.textContent = '-';
        statAvgMag.textContent = '-';
        statTsunamiAlerts.textContent = '-';
        chartPaths = {};
        updateChartImage();
        strongEventsTableBody.innerHTML = '<tr class="table-placeholder"><td colspan="5">No data matching requirements.</td></tr>';
        activeRegionsTableBody.innerHTML = '<tr class="table-placeholder"><td colspan="3">No data matching requirements.</td></tr>';
    }
    
    function populateDashboard(data) {
        // Metadata display
        targetRangeDisplay.textContent = `Active Dataset Bounds: ${data.date_range} (Min: ${data.min_magnitude} M)`;
        
        // Cards
        statTotalCount.textContent = data.total_count;
        statMaxMag.textContent = `${data.mag_stats.max.toFixed(1)} M`;
        statAvgMag.textContent = `${data.mag_stats.mean.toFixed(2)} M`;
        statTsunamiAlerts.textContent = data.tsunami_stats.count_yes;
        
        // Charts
        chartPaths = data.charts;
        updateChartImage();
        
        // Tables
        renderStrongEventsTable(data.strongest_events);
        renderActiveRegionsTable(data.top_regions);
        
        // Show download panel
        downloadsPanel.classList.remove('id-hidden');
    }
    
    function renderStrongEventsTable(events) {
        if (!events || events.length === 0) {
            strongEventsTableBody.innerHTML = '<tr class="table-placeholder"><td colspan="5">No data available.</td></tr>';
            return;
        }
        
        let html = '';
        events.forEach(ev => {
            const dateStr = ev.time_readable.split(' ')[0];
            const badgeClass = getMagnitudeClass(ev.mag);
            
            html += `
                <tr>
                    <td>${dateStr}</td>
                    <td><span class="mag-badge ${badgeClass}">${ev.mag.toFixed(1)}</span></td>
                    <td>${ev.place}</td>
                    <td>${ev.depth.toFixed(1)} km</td>
                    <td>${ev.felt}</td>
                </tr>
            `;
        });
        strongEventsTableBody.innerHTML = html;
    }
    
    function renderActiveRegionsTable(regions) {
        if (!regions || regions.length === 0) {
            activeRegionsTableBody.innerHTML = '<tr class="table-placeholder"><td colspan="3">No data available.</td></tr>';
            return;
        }
        
        let html = '';
        regions.forEach(reg => {
            html += `
                <tr>
                    <td><strong>${reg.region}</strong></td>
                    <td>${reg.count}</td>
                    <td>${reg.max_mag.toFixed(1)} M</td>
                </tr>
            `;
        });
        activeRegionsTableBody.innerHTML = html;
    }
});
