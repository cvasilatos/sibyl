// Sibyl Web App JavaScript

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const reviewBtn = document.getElementById('reviewBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressMessage = document.getElementById('progressMessage');
const results = document.getElementById('results');

// State
let selectedFile = null;
let sessionId = null;
let ws = null;

// Initialize event listeners
function init() {
    // File input handling
    uploadArea.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Review button
    reviewBtn.addEventListener('click', startReview);
}

// File selection handler
function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        updateUploadAreaWithFile(selectedFile);
    }
}

// Drag over handler
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

// Drag leave handler
function handleDragLeave() {
    uploadArea.classList.remove('dragover');
}

// Drop handler
function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    if (e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.type === 'application/pdf') {
            selectedFile = file;
            fileInput.files = e.dataTransfer.files;
            updateUploadAreaWithFile(file);
        } else {
            showError('Please upload a PDF file');
        }
    }
}

// Update upload area UI with file info
function updateUploadAreaWithFile(file) {
    const fileSize = formatFileSize(file.size);
    uploadArea.classList.add('file-selected');
    uploadArea.querySelector('.upload-text').textContent = `Selected: ${file.name}`;
    uploadArea.querySelector('.upload-hint').textContent = `Size: ${fileSize}`;
    reviewBtn.disabled = false;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Start review process
async function startReview() {
    if (!selectedFile) return;
    
    // Reset UI
    reviewBtn.disabled = true;
    results.style.display = 'none';
    results.innerHTML = '';
    progressContainer.style.display = 'block';
    updateProgress(0, 'Uploading file...');
    
    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
        // Upload file
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        sessionId = data.session_id;
        
        // Connect WebSocket for progress updates
        connectWebSocket(sessionId);
        
    } catch (error) {
        console.error('Error:', error);
        showError(`Failed to upload file: ${error.message}`);
        progressContainer.style.display = 'none';
        reviewBtn.disabled = false;
    }
}

// Connect WebSocket for real-time updates
function connectWebSocket(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('Connection error. Please try again.');
        progressContainer.style.display = 'none';
        reviewBtn.disabled = false;
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed');
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    if (data.status === 'progress') {
        updateProgress(data.progress, data.message);
    } else if (data.status === 'completed') {
        progressContainer.style.display = 'none';
        displayResults(data.results);
        reviewBtn.disabled = false;
        if (ws) {
            ws.close();
        }
    } else if (data.status === 'error') {
        progressContainer.style.display = 'none';
        showError(data.message || 'An error occurred during review');
        reviewBtn.disabled = false;
        if (ws) {
            ws.close();
        }
    }
}

// Update progress bar
function updateProgress(percent, message) {
    progressFill.style.width = percent + '%';
    progressFill.textContent = percent + '%';
    progressMessage.textContent = message;
}

// Display review results
function displayResults(data) {
    let html = '';
    
    // Paper title
    if (data.paper_title && data.paper_title !== 'Unknown Paper') {
        html += `<h2 style="margin-bottom: 20px; color: #333;">Review Results: ${escapeHtml(data.paper_title)}</h2>`;
    } else {
        html += '<h2 style="margin-bottom: 20px; color: #333;">Review Results</h2>';
    }
    
    // Comparison statistics
    if (data.comparison) {
        const stats = data.comparison.score_statistics;
        html += `
            <div class="comparison-stats">
                <h3>📊 Overall Statistics</h3>
                <div class="stat-row">
                    <strong>Mean Score:</strong>
                    <span>${stats.mean.toFixed(2)}/10</span>
                </div>
                <div class="stat-row">
                    <strong>Standard Deviation:</strong>
                    <span>${stats.std.toFixed(2)}</span>
                </div>
                <div class="stat-row">
                    <strong>Score Range:</strong>
                    <span>${stats.min} - ${stats.max}</span>
                </div>
                <div class="stat-row">
                    <strong>Consensus:</strong>
                    <span>${escapeHtml(data.comparison.consensus)}</span>
                </div>
            </div>
        `;
    }
    
    // Individual reviews
    if (data.reviews && data.reviews.length > 0) {
        data.reviews.forEach((review, index) => {
            const criteria = review.criteria;
            const recClass = getRecommendationClass(criteria.recommendation);
            
            html += `
                <div class="review-card">
                    <div class="review-header">
                        <h3>🤖 ${escapeHtml(review.reviewer_model)}</h3>
                        <div class="review-meta">
                            <span class="score">${criteria.overall_score}/10</span>
                            <span class="recommendation ${recClass}">${escapeHtml(criteria.recommendation)}</span>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">💡 Novelty</div>
                        <div class="section-content">${escapeHtml(criteria.novelty)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">🔬 Methodology</div>
                        <div class="section-content">${escapeHtml(criteria.methodology)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">📈 Results</div>
                        <div class="section-content">${escapeHtml(criteria.results)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">✍️ Clarity</div>
                        <div class="section-content">${escapeHtml(criteria.clarity)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">🎯 Impact</div>
                        <div class="section-content">${escapeHtml(criteria.impact)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">💪 Strengths</div>
                        <div class="section-content">${escapeHtml(criteria.strengths)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">⚠️ Limitations</div>
                        <div class="section-content">${escapeHtml(criteria.limitations)}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">📝 Detailed Feedback</div>
                        <div class="section-content">${escapeHtml(criteria.detailed_feedback)}</div>
                    </div>
                </div>
            `;
        });
    }
    
    results.innerHTML = html;
    results.style.display = 'block';
    
    // Scroll to results
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Get recommendation CSS class
function getRecommendationClass(recommendation) {
    const rec = recommendation.toLowerCase();
    if (rec.includes('accept')) return 'accept';
    if (rec.includes('reject')) return 'reject';
    return 'revise';
}

// Show error message
function showError(message) {
    results.innerHTML = `<div class="error">❌ Error: ${escapeHtml(message)}</div>`;
    results.style.display = 'block';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Tab switching
function switchTab(tab) {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(tc => tc.classList.remove('active'));
    
    if (tab === 'review') {
        tabs[0].classList.add('active');
        document.getElementById('reviewTab').classList.add('active');
    } else if (tab === 'search') {
        tabs[1].classList.add('active');
        document.getElementById('searchTab').classList.add('active');
        loadStatistics();
        loadRecentReviews();
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const stats = await response.json();
        
        document.getElementById('statTotal').textContent = stats.total_reviews;
        document.getElementById('statAvgScore').textContent = stats.avg_score.toFixed(1);
        document.getElementById('statPapers').textContent = stats.unique_papers;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load recent reviews
async function loadRecentReviews() {
    try {
        const response = await fetch('/api/reviews?limit=20');
        const data = await response.json();
        
        if (data.reviews && data.reviews.length > 0) {
            displayReviewList(data.reviews, '📚 Recent Reviews');
        } else {
            displayEmptyState();
        }
    } catch (error) {
        console.error('Error loading reviews:', error);
        displayEmptyState();
    }
}

// Search reviews
async function searchReviews() {
    const query = document.getElementById('searchInput').value;
    if (!query) {
        loadRecentReviews();
        return;
    }
    
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '<p style="text-align: center; color: #666;">🔍 Searching...</p>';
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query, limit: 20})
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayReviewList(data.results, `Search Results for "${query}"`, true);
        } else {
            searchResults.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No reviews found matching your query.</p></div>';
        }
    } catch (error) {
        console.error('Error searching:', error);
        searchResults.innerHTML = '<div class="error">Error searching reviews. Please try again.</div>';
    }
}

// Display review list
function displayReviewList(reviews, title, showSimilarity = false) {
    const container = document.getElementById('searchResults');
    
    let html = `<h3 style="margin-bottom: 20px; color: #333;">${title}</h3>`;
    
    reviews.forEach(review => {
        const recClass = getRecommendationClass(review.recommendation);
        const similarity = showSimilarity && review.similarity_score && typeof review.similarity_score === 'number' ? 
            `<span class="similarity-badge">${(review.similarity_score * 100).toFixed(0)}% match</span>` : '';
        
        html += `
            <div class="review-list-item" onclick="viewReview('${review.id}')">
                <div class="review-list-header">
                    <span class="review-list-title">${escapeHtml(review.paper_title)}</span>
                    ${similarity}
                </div>
                <div class="review-list-meta">
                    ${escapeHtml(review.pdf_filename)} • ${escapeHtml(review.reviewer_model)} • ${new Date(review.created_at).toLocaleDateString()}
                </div>
                <div style="display: flex; align-items: center; gap: 10px; margin-top: 10px;">
                    <span class="score">${review.overall_score}/10</span>
                    <span class="recommendation ${recClass}">${escapeHtml(review.recommendation)}</span>
                </div>
                <div class="review-list-summary">
                    ${escapeHtml(review.review_summary)}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Display empty state
function displayEmptyState() {
    const container = document.getElementById('searchResults');
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📚</div>
            <p>No reviews in your library yet.</p>
            <p style="font-size: 14px; color: #999;">Review some papers to build your searchable library!</p>
        </div>
    `;
}

// View full review
async function viewReview(reviewId) {
    try {
        const response = await fetch(`/api/reviews/${reviewId}`);
        const review = await response.json();
        
        // Switch to review tab and display full review
        switchTab('review');
        
        const criteria = review.criteria;
        const recClass = getRecommendationClass(criteria.recommendation);
        
        const html = `
            <h2 style="margin-bottom: 20px; color: #333;">${escapeHtml(review.paper_title)}</h2>
            <div class="review-card">
                <div class="review-header">
                    <h3>🤖 ${escapeHtml(review.reviewer_model)}</h3>
                    <div class="review-meta">
                        <span class="score">${criteria.overall_score}/10</span>
                        <span class="recommendation ${recClass}">${escapeHtml(criteria.recommendation)}</span>
                    </div>
                </div>
                <p style="color: #999; font-size: 14px; margin-bottom: 20px;">
                    📄 ${escapeHtml(review.pdf_filename)} • 📅 ${new Date(review.created_at).toLocaleDateString()}
                </p>
                
                <div class="section">
                    <div class="section-title">💡 Novelty</div>
                    <div class="section-content">${escapeHtml(criteria.novelty)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">🔬 Methodology</div>
                    <div class="section-content">${escapeHtml(criteria.methodology)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">📈 Results</div>
                    <div class="section-content">${escapeHtml(criteria.results)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">✍️ Clarity</div>
                    <div class="section-content">${escapeHtml(criteria.clarity)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">🎯 Impact</div>
                    <div class="section-content">${escapeHtml(criteria.impact)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">💪 Strengths</div>
                    <div class="section-content">${escapeHtml(criteria.strengths)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">⚠️ Limitations</div>
                    <div class="section-content">${escapeHtml(criteria.limitations)}</div>
                </div>
                
                <div class="section">
                    <div class="section-title">📝 Detailed Feedback</div>
                    <div class="section-content">${escapeHtml(criteria.detailed_feedback)}</div>
                </div>
            </div>
        `;
        
        results.innerHTML = html;
        results.style.display = 'block';
        window.scrollTo({top: 0, behavior: 'smooth'});
    } catch (error) {
        console.error('Error loading review:', error);
        showError('Failed to load review details');
    }
}

// Add Enter key support for search
document.addEventListener('keypress', (e) => {
    if (e.target.id === 'searchInput' && e.key === 'Enter') {
        searchReviews();
    }
});

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
