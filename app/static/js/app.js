// Chinese-English Flashcards JavaScript utilities

class FlashcardApp {
    constructor() {
        this.sessionStartTime = Date.now();
        this.currentCard = 0;
        this.studyMode = 'flip';
        this.sessionTimer = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startSessionTimer();
        this.setupKeyboardShortcuts();
        this.setupHTMXEvents();
    }
    
    setupEventListeners() {
        // Card flip functionality
        document.addEventListener('click', (e) => {
            if (e.target.closest('.flashcard')) {
                this.flipCard(e.target.closest('.flashcard'));
            }
        });
        
        // Quiz answer selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.quiz-option')) {
                this.selectQuizAnswer(e.target.closest('.quiz-option'));
            }
        });
        
        // Study session controls
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="next-card"]')) {
                this.nextCard();
            } else if (e.target.matches('[data-action="prev-card"]')) {
                this.previousCard();
            } else if (e.target.matches('[data-action="mark-easy"]')) {
                this.markCard('easy');
            } else if (e.target.matches('[data-action="mark-hard"]')) {
                this.markCard('hard');
            } else if (e.target.matches('[data-action="end-session"]')) {
                this.endSession();
            }
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger shortcuts when typing in inputs
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch(e.key) {
                case ' ': // Spacebar to flip card
                    e.preventDefault();
                    const activeCard = document.querySelector('.flashcard.active');
                    if (activeCard) this.flipCard(activeCard);
                    break;
                    
                case 'ArrowLeft':
                case 'h': // Vim-style navigation
                    e.preventDefault();
                    this.previousCard();
                    break;
                    
                case 'ArrowRight':
                case 'l': // Vim-style navigation
                    e.preventDefault();
                    this.nextCard();
                    break;
                    
                case '1':
                case '2':
                case '3':
                case '4':
                    // Select quiz option by number
                    e.preventDefault();
                    this.selectQuizAnswerByNumber(parseInt(e.key));
                    break;
                    
                case 'e': // Mark as easy
                    e.preventDefault();
                    this.markCard('easy');
                    break;
                    
                case 'd': // Mark as difficult
                    e.preventDefault();
                    this.markCard('hard');
                    break;
                    
                case 'Escape': // End session
                    e.preventDefault();
                    if (confirm('Are you sure you want to end this study session?')) {
                        this.endSession();
                    }
                    break;
            }
        });
    }
    
    setupHTMXEvents() {
        // Show loading indicators
        document.addEventListener('htmx:beforeRequest', (e) => {
            this.showLoading();
        });
        
        document.addEventListener('htmx:afterRequest', (e) => {
            this.hideLoading();
            
            // Handle errors
            if (e.detail.xhr.status >= 400) {
                try {
                    const response = JSON.parse(e.detail.xhr.responseText);
                    this.showNotification(response.detail || 'An error occurred', 'error');
                } catch (err) {
                    this.showNotification('Network error occurred', 'error');
                }
            }
        });
        
        // Handle successful responses
        document.addEventListener('htmx:beforeSwap', (e) => {
            if (e.detail.xhr.status === 200) {
                // Add fade-in animation to new content
                e.detail.target.style.opacity = '0';
                setTimeout(() => {
                    e.detail.target.style.opacity = '1';
                }, 50);
            }
        });
    }
    
    // Card manipulation methods
    flipCard(cardElement) {
        if (!cardElement) return;
        
        cardElement.classList.toggle('flipped');
        
        // Record flip interaction
        this.recordCardInteraction('flip');
        
        // Add haptic feedback if supported
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    }
    
    nextCard() {
        const nextBtn = document.querySelector('[data-action="next-card"]');
        if (nextBtn && !nextBtn.disabled) {
            nextBtn.click();
        }
    }
    
    previousCard() {
        const prevBtn = document.querySelector('[data-action="prev-card"]');
        if (prevBtn && !prevBtn.disabled) {
            prevBtn.click();
        }
    }
    
    markCard(difficulty) {
        const isCorrect = difficulty === 'easy';
        this.recordCardInteraction(isCorrect ? 'quiz_correct' : 'quiz_incorrect', isCorrect);
        
        // Visual feedback
        this.showNotification(
            `Card marked as ${difficulty}`, 
            isCorrect ? 'success' : 'info'
        );
        
        // Auto-advance after marking
        setTimeout(() => this.nextCard(), 1000);
    }
    
    // Quiz methods
    selectQuizAnswer(optionElement) {
        if (!optionElement || optionElement.disabled) return;
        
        // Disable all options
        const allOptions = document.querySelectorAll('.quiz-option');
        allOptions.forEach(opt => {
            opt.disabled = true;
            opt.classList.add('opacity-50');
        });
        
        // Mark selected option
        optionElement.classList.add('selected');
        
        // Submit answer
        const answer = optionElement.textContent.trim();
        this.submitQuizAnswer(answer);
    }
    
    selectQuizAnswerByNumber(number) {
        const options = document.querySelectorAll('.quiz-option');
        if (options[number - 1]) {
            this.selectQuizAnswer(options[number - 1]);
        }
    }
    
    async submitQuizAnswer(answer) {
        const sessionId = this.getSessionId();
        const cardId = this.getCurrentCardId();
        
        if (!sessionId || !cardId) return;
        
        try {
            const response = await fetch(`/api/study/sessions/${sessionId}/quiz`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({
                    card_id: cardId,
                    selected_answer: answer,
                    response_time: this.getResponseTime()
                })
            });
            
            const result = await response.json();
            this.showQuizFeedback(result);
            
            // Auto-advance after feedback
            setTimeout(() => this.nextCard(), 2000);
            
        } catch (error) {
            console.error('Error submitting quiz answer:', error);
            this.showNotification('Error submitting answer', 'error');
        }
    }
    
    showQuizFeedback(result) {
        const feedback = document.getElementById('quiz-feedback');
        if (!feedback) return;
        
        const isCorrect = result.correct;
        const bgClass = isCorrect ? 'bg-green-100 border-green-400 text-green-700' : 'bg-red-100 border-red-400 text-red-700';
        
        feedback.className = `border px-4 py-3 rounded mb-4 ${bgClass}`;
        feedback.innerHTML = `
            <div class="font-semibold flex items-center">
                ${isCorrect ? '✓' : '✗'} ${isCorrect ? 'Correct!' : 'Incorrect'}
            </div>
            ${!isCorrect ? `<div class="mt-1">Correct answer: ${result.correct_answer}</div>` : ''}
            ${result.explanation ? `<div class="mt-1 text-sm">${result.explanation}</div>` : ''}
        `;
        feedback.classList.remove('hidden');
        
        // Update quiz options with correct/incorrect styling
        const allOptions = document.querySelectorAll('.quiz-option');
        allOptions.forEach(option => {
            const optionText = option.textContent.trim();
            if (optionText === result.correct_answer) {
                option.classList.add('correct');
            } else if (option.classList.contains('selected')) {
                option.classList.add('incorrect');
            }
        });
    }
    
    // Session management
    startSessionTimer() {
        this.sessionTimer = setInterval(() => {
            this.updateSessionTimer();
        }, 1000);
    }
    
    updateSessionTimer() {
        const timerElement = document.getElementById('session-timer');
        if (!timerElement) return;
        
        const elapsed = Math.floor((Date.now() - this.sessionStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    async endSession() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
        }
        
        const sessionId = this.getSessionId();
        if (!sessionId) return;
        
        const duration = Math.floor((Date.now() - this.sessionStartTime) / 60000);
        
        try {
            await fetch(`/api/study/sessions/${sessionId}/end`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({
                    duration_minutes: duration
                })
            });
            
            window.location.href = `/study/complete?session=${sessionId}`;
            
        } catch (error) {
            console.error('Error ending session:', error);
            this.showNotification('Error ending session', 'error');
        }
    }
    
    // Utility methods
    async recordCardInteraction(type, isCorrect = null) {
        const sessionId = this.getSessionId();
        const cardId = this.getCurrentCardId();
        
        if (!sessionId || !cardId) return;
        
        try {
            await fetch('/api/study/interactions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAccessToken()}`
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    card_id: cardId,
                    interaction_type: type,
                    direction: this.getStudyDirection(),
                    response_time: this.getResponseTime()
                })
            });
        } catch (error) {
            console.error('Error recording interaction:', error);
        }
    }
    
    showNotification(message, type = 'info') {
        const container = document.getElementById('flash-messages');
        if (!container) return;
        
        const alertClass = {
            'error': 'bg-red-100 border-red-400 text-red-700',
            'success': 'bg-green-100 border-green-400 text-green-700',
            'info': 'bg-blue-100 border-blue-400 text-blue-700',
            'warning': 'bg-yellow-100 border-yellow-400 text-yellow-700'
        }[type] || 'bg-blue-100 border-blue-400 text-blue-700';
        
        const alertHtml = `
            <div class="notification border px-4 py-3 rounded mb-4 ${alertClass}" role="alert">
                <span class="block sm:inline">${message}</span>
                <button class="float-right ml-2 font-bold text-lg" onclick="this.parentElement.remove()">
                    &times;
                </button>
            </div>
        `;
        
        container.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            container.firstElementChild?.remove();
        }, 5000);
    }
    
    showLoading() {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.classList.add('hidden');
        }
    }
    
    // Helper methods to extract data from DOM
    getSessionId() {
        return document.querySelector('[data-session-id]')?.dataset.sessionId;
    }
    
    getCurrentCardId() {
        return document.querySelector('[data-card-id]')?.dataset.cardId;
    }
    
    getStudyDirection() {
        return document.querySelector('[data-direction]')?.dataset.direction || 'chinese_to_english';
    }
    
    getResponseTime() {
        const questionStart = document.querySelector('[data-question-start]')?.dataset.questionStart;
        return questionStart ? Date.now() - parseInt(questionStart) : null;
    }
    
    getAccessToken() {
        return localStorage.getItem('access_token') || '';
    }
}

// Statistics and charts utilities
class StatisticsChart {
    constructor(canvasId, data, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.data = data;
        this.options = options;
        
        if (this.canvas && typeof Chart !== 'undefined') {
            this.init();
        }
    }
    
    init() {
        this.chart = new Chart(this.canvas.getContext('2d'), {
            type: this.options.type || 'line',
            data: this.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                ...this.options.chartOptions
            }
        });
    }
    
    updateData(newData) {
        if (this.chart) {
            this.chart.data = newData;
            this.chart.update();
        }
    }
    
    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// CSV import/export utilities
class CSVHandler {
    static async importFile(file, deckId, validateOnly = false) {
        const formData = new FormData();
        formData.append('file', file);
        
        const url = `/api/csv/${validateOnly ? 'validate' : 'import'}/${deckId}`;
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            return await response.json();
        } catch (error) {
            console.error('CSV import error:', error);
            throw error;
        }
    }
    
    static async exportDeck(deckId, includeStats = false) {
        const url = `/api/csv/export/${deckId}?include_stats=${includeStats}`;
        
        try {
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `deck_${deckId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('CSV export error:', error);
            throw error;
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.flashcardApp = new FlashcardApp();
    
    // Auto-focus search inputs
    const searchInput = document.querySelector('input[type="search"]');
    if (searchInput) {
        searchInput.focus();
    }
});

// Export utilities for use in other scripts
window.FlashcardApp = FlashcardApp;
window.StatisticsChart = StatisticsChart;
window.CSVHandler = CSVHandler;