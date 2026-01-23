// Global state
let agents = [];
let currentAgent = null;

// Color mapping
const colorMap = {
    'blue': '#00d9ff',
    'green': '#00ff41',
    'gold': '#ffd700',
    'purple': '#a855f7',
    'pink': '#ec4899',
    'red': '#ef4444',
    'cyan': '#06b6d4'
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadAgents();
    setupChatForm();
    // Start polling for jobs
    setInterval(refreshJobs, 2000);
    refreshJobs();
});

// Load agents from backend
async function loadAgents() {
    try {
        const response = await fetch('/agents');
        agents = await response.json();
        renderAgentList();
        renderManagerList();

        // Select first agent by default
        if (agents.length > 0) {
            selectAgent(agents[0].id);
        }
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

// Render agent selection buttons
function renderAgentList() {
    const agentsList = document.getElementById('agents-list');
    agentsList.innerHTML = agents.map(agent => `
        <button class="agent-btn" data-agent-id="${agent.id}" data-color="${agent.color}" onclick="selectAgent('${agent.id}')">
            <span class="agent-icon">${agent.icon}</span>
            <div class="agent-info">
                <span class="agent-name">${agent.name}</span>
                <span class="agent-role">${agent.role}</span>
            </div>
        </button>
    `).join('');
}

// Render agent management list
function renderManagerList() {
    const managerList = document.getElementById('agents-manager-list');
    managerList.innerHTML = agents.map(agent => `
        <div class="agent-card">
            <div class="agent-card-header">
                <h3>${agent.icon} ${agent.name}</h3>
                <div class="agent-card-actions">
                    <button onclick="editAgent('${agent.id}')">✏️</button>
                    <button onclick="deleteAgent('${agent.id}')">🗑️</button>
                </div>
            </div>
            <p class="agent-card-role">${agent.role}</p>
            <div class="agent-card-meta">
                <span class="api-badge ${agent.api_provider}">${agent.api_provider === 'gemini' ? '🔵 Gemini' : '🟣 Claude'}</span>
                <span class="color-badge" style="background: ${colorMap[agent.color]}"></span>
            </div>
        </div>
    `).join('');
}

// Select an agent
function selectAgent(agentId) {
    const agent = agents.find(a => a.id === agentId);
    if (!agent) return;

    currentAgent = agent;

    // Update UI
    document.querySelectorAll('.agent-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-agent-id="${agentId}"]`)?.classList.add('active');

    document.getElementById('current-agent').textContent = agent.name;
    document.getElementById('current-role').textContent = agent.role;
    document.documentElement.style.setProperty('--accent-color', colorMap[agent.color]);
}

// Chat functionality
function setupChatForm() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (!message || !currentAgent) return;

        // Add user message
        addMessage(message, 'user');
        messageInput.value = '';

        // Show typing indicator
        const typingId = addTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    agent_id: currentAgent.id
                })
            });

            const data = await response.json();

            // Remove typing indicator
            removeTypingIndicator(typingId);

            if (data.error) {
                addMessage(data.error, 'error');
            } else {
                // Add agent response
                addMessage(data.message, 'agent', data.agent, data.api_provider);
            }

        } catch (error) {
            removeTypingIndicator(typingId);
            addMessage('ERROR: Neural connection disrupted. Please retry.', 'error');
        }
    });
}

function addMessage(text, type, agentName = '', apiProvider = '') {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${type}-message`);

    if (type === 'agent') {
        const apiIcon = apiProvider === 'gemini' ? '🔵' : '🟣';
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="agent-tag">${agentName} ${apiIcon}</span>
                <span class="timestamp">${getCurrentTime()}</span>
            </div>
            <p>${text}</p>
        `;
    } else if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="timestamp">${getCurrentTime()}</span>
            </div>
            <p>${text}</p>
        `;
    } else {
        messageDiv.innerHTML = `<p>${text}</p>`;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('message', 'agent-message', 'typing');
    typingDiv.id = 'typing-' + Date.now();
    typingDiv.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv.id;
}

function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// Modal management
function openManageModal() {
    document.getElementById('manage-modal').classList.add('active');
}

function closeManageModal() {
    document.getElementById('manage-modal').classList.remove('active');
    cancelAgentForm();
}

function showAgentForm(agentId = null) {
    document.getElementById('agent-form').classList.remove('hidden');

    if (agentId) {
        const agent = agents.find(a => a.id === agentId);
        if (agent) {
            document.getElementById('form-title').textContent = 'Edit Agent';
            document.getElementById('edit-agent-id').value = agent.id;
            document.getElementById('agent-name').value = agent.name;
            document.getElementById('agent-role').value = agent.role;
            document.getElementById('agent-icon').value = agent.icon;
            document.getElementById('agent-color').value = agent.color;
            document.getElementById('agent-api-provider').value = agent.api_provider;
            document.getElementById('agent-model').value = agent.model;
            document.getElementById('agent-system-prompt').value = agent.system_prompt;
        }
    } else {
        document.getElementById('form-title').textContent = 'Create New Agent';
        document.getElementById('agent-edit-form').reset();
        document.getElementById('edit-agent-id').value = '';
    }
}

function cancelAgentForm() {
    document.getElementById('agent-form').classList.add('hidden');
    document.getElementById('agent-edit-form').reset();
}

function editAgent(agentId) {
    showAgentForm(agentId);
}

async function deleteAgent(agentId) {
    if (!confirm('Are you sure you want to delete this agent?')) return;

    try {
        await fetch(`/agents/${agentId}`, {
            method: 'DELETE'
        });

        await loadAgents();
    } catch (error) {
        alert('Error deleting agent: ' + error.message);
    }
}

// --- Mission Control Logic ---

function switchView(viewName) {
    const chatView = document.querySelector('.chat-container');
    const missionView = document.getElementById('mission-control');
    const navChat = document.getElementById('nav-chat');
    const navMission = document.getElementById('nav-mission');

    if (viewName === 'chat') {
        chatView.classList.remove('hidden');
        missionView.classList.add('hidden');
        navChat.classList.add('active');
        navMission.classList.remove('active');
    } else {
        chatView.classList.add('hidden');
        missionView.classList.remove('hidden');
        navChat.classList.remove('active');
        navMission.classList.add('active');
    }
}

async function refreshJobs() {
    try {
        const response = await fetch('/jobs');
        const jobs = await response.json();
        renderJobs(jobs);

        // Update active count
        const activeCount = jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
        document.getElementById('active-jobs-count').textContent = activeCount;
    } catch (error) {
        console.error('Error fetching jobs:', error);
    }
}

function renderJobs(jobs) {
    const grid = document.getElementById('jobs-grid');
    if (!grid) return;

    // Sort by started_at desc
    jobs.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));

    grid.innerHTML = jobs.map(job => {
        let statusClass = 'job-queued';
        let statusIcon = '⏳';

        if (job.status === 'running') {
            statusClass = 'job-running';
            statusIcon = '🔄';
        } else if (job.status === 'completed') {
            statusClass = 'job-completed';
            statusIcon = '✅';
        } else if (job.status === 'failed') {
            statusClass = 'job-failed';
            statusIcon = '❌';
        }

        const logsPreview = job.logs.slice(-3).join('<br>');
        const resultPreview = job.result ? `<div class="job-result-preview">${formatJobResult(job.result)}</div>` : '';

        return `
            <div class="job-card ${statusClass}">
                <div class="job-header">
                    <span class="job-id">MISSION: ${job.id.substring(0, 8)}...</span>
                    <span class="job-status">${statusIcon} ${job.status.toUpperCase()}</span>
                </div>
                <div class="job-meta">
                    <div>Started: ${formatDate(job.started_at)}</div>
                    <div>Duration: ${calculateDuration(job.started_at, job.completed_at)}</div>
                </div>
                <div class="job-logs">
                    ${logsPreview}
                </div>
                ${resultPreview}
            </div>
        `;
    }).join('');
}

function formatJobResult(result) {
    if (typeof result === 'object' && result.result) {
        return result.result.substring(0, 150) + '...';
    }
    return JSON.stringify(result).substring(0, 150) + '...';
}

function formatDate(isoString) {
    if (!isoString) return '--:--:--';
    return new Date(isoString).toLocaleTimeString();
}

function calculateDuration(start, end) {
    if (!start) return '-';
    const s = new Date(start);
    const e = end ? new Date(end) : new Date();
    const diffMs = e - s;
    const seconds = Math.floor(diffMs / 1000);
    return seconds + 's';
}

function openLaunchModal() {
    document.getElementById('launch-modal').classList.add('active');

    // Populate agent select
    const container = document.getElementById('mission-agent-select');
    container.innerHTML = agents.map(agent => `
        <label class="agent-checkbox">
            <input type="checkbox" name="mission-agents" value="${agent.id}" checked>
            <span class="checkmark"></span>
            ${agent.icon} ${agent.name}
        </label>
    `).join('');
}

function closeLaunchModal() {
    document.getElementById('launch-modal').classList.remove('active');
    document.getElementById('launch-form').reset();
}

async function launchMission(event) {
    event.preventDefault();
    const task = document.getElementById('mission-objective').value;
    const checkboxes = document.querySelectorAll('input[name="mission-agents"]:checked');
    const selectedAgents = Array.from(checkboxes).map(cb => cb.value);

    try {
        const response = await fetch('/jobs/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task: task,
                agents: selectedAgents
            })
        });

        const data = await response.json();
        if (data.job_id) {
            closeLaunchModal();
            switchView('mission');
            refreshJobs();
        }
    } catch (e) {
        alert('Mission Launch Failed: ' + e);
    }
}

async function saveAgent(event) {
    event.preventDefault();

    const agentId = document.getElementById('edit-agent-id').value;
    const agentData = {
        name: document.getElementById('agent-name').value,
        role: document.getElementById('agent-role').value,
        icon: document.getElementById('agent-icon').value || '●',
        color: document.getElementById('agent-color').value,
        api_provider: document.getElementById('agent-api-provider').value,
        model: document.getElementById('agent-model').value,
        system_prompt: document.getElementById('agent-system-prompt').value
    };

    try {
        if (agentId) {
            // Update existing agent
            await fetch(`/agents/${agentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(agentData)
            });
        } else {
            // Create new agent
            await fetch('/agents', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(agentData)
            });
        }

        await loadAgents();
        cancelAgentForm();
    } catch (error) {
        alert('Error saving agent: ' + error.message);
    }
}
