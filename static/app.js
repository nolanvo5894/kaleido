document.addEventListener('DOMContentLoaded', () => {
    const topicInput = document.getElementById('topic');
    const generateButton = document.getElementById('generate');
    const loadingDiv = document.getElementById('loading');
    const contentDiv = document.getElementById('content');
    const essayDiv = document.getElementById('essay');
    const questionsDiv = document.getElementById('questions');

    // Handle enter key
    topicInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            generateButton.click();
        }
    });

    async function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded relative mb-4';
        errorDiv.innerHTML = `<strong>Error:</strong> ${message}`;
        contentDiv.parentNode.insertBefore(errorDiv, contentDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    generateButton.addEventListener('click', async () => {
        const topic = topicInput.value.trim();
        if (!topic) {
            showError('Please enter a topic');
            return;
        }

        try {
            // Show loading state
            loadingDiv.classList.remove('hidden');
            contentDiv.classList.add('hidden');
            generateButton.disabled = true;

            // Make API request
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic }),
            });

            const data = await response.json();

            if (data.status === 'error' || !response.ok) {
                throw new Error(data.error || 'Failed to generate exercise');
            }

            // Update content
            await updateContent(data);
            
            // Format questions with better structure
            const questionsHtml = marked.parse(data.questions || '')
                .replace(/<p>([A-D])\. /g, '<div class="option"><input type="radio" name="q$1" value="$1"><div class="option-text">$1. ')
                .replace(/<\/p>/g, '</div></div>')
                .replace(/Question (\d+)/g, '<span class="question-number">Question $1</span>')
                // Format matching section
                .replace(
                    /<h3>Matching Headings<\/h3>/,
                    '<h3 class="text-xl font-semibold mb-4">Matching Headings</h3>' +
                    '<p class="text-gray-400 mb-4">Drag the headings to match them with the correct paragraphs</p>'
                );
            questionsDiv.innerHTML = questionsHtml;
            
            // Generate audio
            await generateAudio();
            
            // Show content
            contentDiv.classList.remove('hidden');
        } catch (error) {
            showError(error.message);
            contentDiv.classList.add('hidden');
        } finally {
            // Hide loading state
            loadingDiv.classList.add('hidden');
            generateButton.disabled = false;
        }
    });

    async function updateContent(data) {
        // Update essay content
        const essayContent = marked.parse(data.essay || '');
        
        // Add image if available
        const imageHtml = data.image_url ? 
            `<div class="illustration-container mb-8">
                <img src="${data.image_url}" alt="Topic illustration" class="w-full rounded-xl shadow-lg">
             </div>` : '';
        
        // Wrap content in reading-content div
        const contentHtml = `
            <div class="reading-content">
                ${imageHtml}
                ${essayContent}
            </div>
        `;
        
        document.getElementById('essay-only').innerHTML = contentHtml;
        document.getElementById('transcript').innerHTML = contentHtml;
    }

    function initializeQuestions() {
        const submitButton = document.getElementById('submit-answers');
        const answerKey = document.getElementById('answer-key');
        const scoreDisplay = document.getElementById('score-display');

        // Initialize drag and drop for matching
        initializeMatchingDragDrop();

        submitButton.addEventListener('click', () => {
            const score = calculateScore();
            displayResults(score);
        });
    }

    function initializeMatchingDragDrop() {
        const headings = document.querySelectorAll('.heading');
        const slots = document.querySelectorAll('.slot');

        headings.forEach(heading => {
            heading.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', heading.dataset.id);
                heading.classList.add('dragging');
            });

            heading.addEventListener('dragend', () => {
                heading.classList.remove('dragging');
            });
        });

        slots.forEach(slot => {
            slot.addEventListener('dragover', (e) => {
                e.preventDefault();
                slot.classList.add('active');
            });

            slot.addEventListener('dragleave', () => {
                slot.classList.remove('active');
            });

            slot.addEventListener('drop', (e) => {
                e.preventDefault();
                const headingId = e.dataTransfer.getData('text/plain');
                const heading = document.querySelector(`.heading[data-id="${headingId}"]`);
                slot.appendChild(heading);
                slot.classList.remove('active');
            });
        });
    }

    function calculateScore() {
        let score = {
            multipleChoice: 0,
            trueFalse: 0,
            matching: 0,
            total: 0,
            maxScore: 0
        };

        // Check multiple choice answers
        const mcQuestions = document.querySelectorAll('[data-type="multiple-choice"]');
        const mcAnswers = document.querySelectorAll('[data-answer-type="mc"]');
        
        mcQuestions.forEach((q, i) => {
            const selected = q.querySelector('input:checked');
            const correct = mcAnswers[i].textContent.split('. ')[1];
            if (selected && selected.value === correct) {
                score.multipleChoice++;
                q.classList.add('correct');
            } else {
                q.classList.add('incorrect');
            }
        });

        // Check true/false answers
        const tfQuestions = document.querySelectorAll('[data-type="true-false"]');
        const tfAnswers = document.querySelectorAll('[data-answer-type="tf"]');
        
        tfQuestions.forEach((q, i) => {
            const selected = q.querySelector('input:checked');
            const correct = tfAnswers[i].textContent.split('. ')[1];
            if (selected && selected.value === correct) {
                score.trueFalse++;
                q.classList.add('correct');
            } else {
                q.classList.add('incorrect');
            }
        });

        // Check matching answers
        const slots = document.querySelectorAll('.slot');
        slots.forEach((slot, i) => {
            const heading = slot.querySelector('.heading');
            if (heading && heading.dataset.id === (i + 1).toString()) {
                score.matching++;
                slot.classList.add('correct');
            } else {
                slot.classList.add('incorrect');
            }
        });

        score.total = score.multipleChoice + score.trueFalse + score.matching;
        score.maxScore = mcQuestions.length + tfQuestions.length + slots.length;

        return score;
    }

    function displayResults(score) {
        const scoreDisplay = document.getElementById('score-display');
        const answerKey = document.getElementById('answer-key');
        const submitButton = document.getElementById('submit-answers');
        const tryAgainButton = document.getElementById('try-again');
        
        // Move try again button to score display
        scoreDisplay.innerHTML = `
            <h3>✨ Your Results ✨</h3>
            <p>
                <span>Total Score</span>
                <span class="score-highlight">${score.total}/${score.maxScore} (${Math.round(score.total/score.maxScore*100)}%)</span>
            </p>
            <p>
                <span>Multiple Choice</span>
                <span class="score-highlight">${score.multipleChoice}/${document.querySelectorAll('[data-type="multiple-choice"]').length}</span>
            </p>
            <p>
                <span>True/False/Not Given</span>
                <span class="score-highlight">${score.trueFalse}/${document.querySelectorAll('[data-type="true-false"]').length}</span>
            </p>
            <p>
                <span>Matching</span>
                <span class="score-highlight">${score.matching}/${document.querySelectorAll('.slot').length}</span>
            </p>
        `;
        
        // Show results and answer key
        scoreDisplay.classList.remove('hidden');
        answerKey.classList.remove('hidden');
        
        // Move try again button into score display
        scoreDisplay.appendChild(tryAgainButton);
        tryAgainButton.classList.remove('hidden');
        submitButton.classList.add('hidden');
        
        // Disable all inputs
        document.querySelectorAll('input[type="radio"]').forEach(input => {
            input.disabled = true;
        });
        document.querySelectorAll('.heading').forEach(heading => {
            heading.setAttribute('draggable', 'false');
        });
    }

    // Add try again functionality
    document.getElementById('try-again')?.addEventListener('click', () => {
        const scoreDisplay = document.getElementById('score-display');
        const answerKey = document.getElementById('answer-key');
        const submitButton = document.getElementById('submit-answers');
        const tryAgainButton = document.getElementById('try-again');
        
        // Reset all answers
        document.querySelectorAll('input[type="radio"]').forEach(input => {
            input.checked = false;
            input.disabled = false;
        });
        
        // Reset matching section
        const headingsList = document.querySelector('.headings-list');
        document.querySelectorAll('.heading').forEach(heading => {
            heading.setAttribute('draggable', 'true');
            headingsList.appendChild(heading);
        });
        
        // Remove correct/incorrect indicators
        document.querySelectorAll('.correct, .incorrect').forEach(el => {
            el.classList.remove('correct', 'incorrect');
        });
        
        // Hide results and answer key
        scoreDisplay.classList.add('hidden');
        answerKey.classList.add('hidden');
        
        // Show submit button and hide try again button
        submitButton.classList.remove('hidden');
        tryAgainButton.classList.add('hidden');
    });

    // Initialize questions when content is loaded
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.target.id === 'questions' && mutation.addedNodes.length > 0) {
                initializeQuestions();
            }
        });
    });

    observer.observe(document.getElementById('questions'), { childList: true });

    // Add view toggle functionality
    const readingViewBtn = document.getElementById('reading-view');
    const exerciseViewBtn = document.getElementById('exercise-view');
    const historyViewBtn = document.getElementById('history-view');
    const listeningViewBtn = document.getElementById('listening-view');
    
    const readingOnlyView = document.getElementById('reading-only-view');
    const exerciseView = document.getElementById('exercise-view-content');
    const historyView = document.getElementById('history-view');
    const listeningView = document.getElementById('listening-only-view');

    // Function to switch views
    function switchView(activeBtn, activeView) {
        // Remove active class from all buttons
        [readingViewBtn, exerciseViewBtn, historyViewBtn, listeningViewBtn].forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Hide all views
        [readingOnlyView, exerciseView, historyView, listeningView].forEach(view => {
            view.classList.add('hidden');
        });
        
        // Activate selected button and view
        activeBtn.classList.add('active');
        activeView.classList.remove('hidden');
    }

    // Reading view toggle
    readingViewBtn.addEventListener('click', () => {
        switchView(readingViewBtn, readingOnlyView);
    });

    // Exercise view toggle
    exerciseViewBtn.addEventListener('click', () => {
        switchView(exerciseViewBtn, exerciseView);
    });

    // History view toggle
    historyViewBtn.addEventListener('click', () => {
        switchView(historyViewBtn, historyView);
        loadExerciseHistory();
    });

    // Listening view toggle
    listeningViewBtn.addEventListener('click', () => {
        switchView(listeningViewBtn, listeningView);
    });

    // Load exercise history
    async function loadExerciseHistory() {
        try {
            const response = await fetch('/api/exercises');
            const exercises = await response.json();
            
            const historyContainer = document.getElementById('exercise-history');
            historyContainer.innerHTML = exercises.map(exercise => `
                <div class="exercise-item bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl hover:bg-gray-700/50 transition-all duration-200 cursor-pointer transform hover:-translate-y-1"
                     onclick="loadExercise(${exercise.id})">
                    <h3 class="font-semibold text-xl text-gray-100 mb-2">${exercise.topic}</h3>
                    <p class="text-sm text-gray-400">Created ${new Date(exercise.created_at).toLocaleDateString()} at ${new Date(exercise.created_at).toLocaleTimeString()}</p>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading exercise history:', error);
            showError('Failed to load exercise history');
        }
    }

    // Make loadExercise function globally available first
    window.loadExercise = async function(id) {
        try {
            const response = await fetch(`/api/exercises/${id}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // Update content
                const essayContent = marked.parse(data.essay || '');
                const imageHtml = data.image_url ? 
                    `<div class="illustration-container mb-8">
                        <img src="${data.image_url}" alt="Topic illustration" class="w-full rounded-xl shadow-lg">
                     </div>` : '';
                
                document.getElementById('essay-only').innerHTML = imageHtml + essayContent;
                document.getElementById('transcript').innerHTML = imageHtml + essayContent;
                
                // Format questions with better structure
                const questionsHtml = marked.parse(data.questions || '')
                    .replace(/<p>([A-D])\. /g, '<div class="option"><input type="radio" name="q$1" value="$1"><div class="option-text">$1. ')
                    .replace(/<\/p>/g, '</div></div>')
                    .replace(/Question (\d+)/g, '<span class="question-number">Question $1</span>')
                    // Format matching section
                    .replace(
                        /<h3>Matching Headings<\/h3>/,
                        '<h3 class="text-xl font-semibold mb-4">Matching Headings</h3>' +
                        '<p class="text-gray-400 mb-4">Drag the headings to match them with the correct paragraphs</p>'
                    );
                questionsDiv.innerHTML = questionsHtml;
                
                // Show content first
                contentDiv.classList.remove('hidden');
                
                // Switch to reading view
                switchView(readingViewBtn, readingOnlyView);
            }
        } catch (error) {
            showError('Error loading exercise: ' + error.message);
        }
    };

    // Audio player functionality
    const audioPlayer = document.getElementById('essay-audio');
    const playPauseBtn = document.getElementById('play-pause');
    const restartBtn = document.getElementById('restart');
    const progressBar = document.getElementById('progress-bar');
    const progressBarContainer = document.querySelector('.progress-bar-container');
    const currentTimeDisplay = document.getElementById('current-time');
    const durationDisplay = document.getElementById('duration');
    const toggleTranscriptBtn = document.getElementById('toggle-transcript');
    const transcriptContainer = document.querySelector('.transcript-container');

    // Format time in minutes:seconds
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        seconds = Math.floor(seconds % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    // Update progress bar and time displays
    audioPlayer.addEventListener('timeupdate', () => {
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressBar.style.width = `${progress}%`;
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
    });

    audioPlayer.addEventListener('loadedmetadata', () => {
        durationDisplay.textContent = formatTime(audioPlayer.duration);
    });

    // Click on progress bar to seek
    progressBarContainer.addEventListener('click', (e) => {
        const rect = progressBarContainer.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        audioPlayer.currentTime = pos * audioPlayer.duration;
    });

    playPauseBtn.addEventListener('click', () => {
        if (audioPlayer.paused) {
            audioPlayer.play();
            playPauseBtn.querySelector('.play-icon').classList.add('hidden');
            playPauseBtn.querySelector('.pause-icon').classList.remove('hidden');
        } else {
            audioPlayer.pause();
            playPauseBtn.querySelector('.play-icon').classList.remove('hidden');
            playPauseBtn.querySelector('.pause-icon').classList.add('hidden');
        }
    });

    restartBtn.addEventListener('click', () => {
        audioPlayer.currentTime = 0;
        audioPlayer.play();
    });

    // Initialize audio player
    async function generateAudio() {
        try {
            const response = await fetch('/api/generate-audio', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic: topicInput.value.trim() }),
            });

            if (!response.ok) {
                throw new Error('Failed to generate audio');
            }

            // Update audio source
            audioPlayer.src = '/audio/essay_reading.mp3';
            await audioPlayer.load();
        } catch (error) {
            showError('Error generating audio: ' + error.message);
        }
    }

    // Transcript toggle
    toggleTranscriptBtn.addEventListener('click', () => {
        transcriptContainer.classList.toggle('hidden');
        toggleTranscriptBtn.textContent = transcriptContainer.classList.contains('hidden') 
            ? 'Show Passage' 
            : 'Hide Passage';
    });
}); 