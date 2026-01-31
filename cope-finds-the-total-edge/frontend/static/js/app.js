/**
 * Cope Finds the Total Edge - Dashboard JavaScript
 * NBA Totals Betting Calculator
 */

const API_BASE = '';

// State
let games = [];
let bets = [];
let injuries = [];
let teamStats = [];

// DOM Elements
const gamesList = document.getElementById('games-list');
const betsList = document.getElementById('bets-list');
const injuriesList = document.getElementById('injuries-list');
const teamsList = document.getElementById('teams-list');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initModals();
    initForms();
    loadAllData();
});

// Tab Navigation
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Add active to clicked
            tab.classList.add('active');
            document.getElementById(`${tab.dataset.tab}-tab`).classList.add('active');
        });
    });
}

// Modal Management
function initModals() {
    // Close buttons
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });

    // Click outside to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', refreshData);

    // Alert button
    document.getElementById('alert-btn').addEventListener('click', sendAlert);
}

// Form Handlers
function initForms() {
    // Bet form
    document.getElementById('bet-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await placeBet();
    });

    // Settle form
    document.getElementById('settle-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await settleBet();
    });
}

// API Functions
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { success: false, error: error.message };
    }
}

// Load All Data
async function loadAllData() {
    await Promise.all([
        loadGames(),
        loadBets(),
        loadInjuries(),
        loadTeamStats(),
        loadStats()
    ]);
}

// Load Games
async function loadGames() {
    gamesList.innerHTML = '<div class="loading">Loading games...</div>';

    const data = await fetchAPI('/api/games');

    if (data.success) {
        games = data.games;
        renderGames();
        document.getElementById('last-updated').textContent =
            `Last updated: ${new Date().toLocaleTimeString()}`;
    } else {
        gamesList.innerHTML = `<div class="loading">Error loading games: ${data.error}</div>`;
    }
}

// Render Games
function renderGames() {
    if (games.length === 0) {
        gamesList.innerHTML = '<div class="loading">No games found. Click Refresh to fetch today\'s games.</div>';
        return;
    }

    gamesList.innerHTML = games.map(game => {
        const hasEdge = Math.abs(game.edge || 0) >= 5;
        const edgeClass = game.edge_direction === 'OVER' ? 'over' : 'under';

        return `
            <div class="game-card ${hasEdge ? 'has-edge' : ''}">
                <div class="game-header">
                    <div>
                        <div class="game-teams">${game.away_team} @ ${game.home_team}</div>
                        <div class="game-time">${formatDateTime(game.game_date)}</div>
                    </div>
                    ${hasEdge ? `
                        <div class="edge-badge ${edgeClass}">
                            ${game.edge_direction} ${Math.abs(game.edge).toFixed(1)}pts
                        </div>
                    ` : ''}
                </div>

                <div class="game-details">
                    <div class="detail-item">
                        <div class="detail-label">FanDuel Total</div>
                        <div class="detail-value">${game.fanduel_total}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Our Projection</div>
                        <div class="detail-value">${game.projected_total?.toFixed(1) || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Edge</div>
                        <div class="detail-value ${game.edge > 0 ? 'positive' : 'negative'}">
                            ${game.edge > 0 ? '+' : ''}${game.edge?.toFixed(1) || 'N/A'}
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Inj. Adjustment</div>
                        <div class="detail-value">${game.injury_adjustment?.toFixed(1) || '0'}</div>
                    </div>
                </div>

                ${game.injured_players && game.injured_players.length > 0 ? `
                    <div class="game-injuries">
                        <h4>🚑 Injuries Affecting Total</h4>
                        <div class="injury-list">
                            ${game.injured_players.map(inj => `
                                <span class="injury-tag ${inj.is_star ? 'star' : ''}">${inj.name} (${inj.team})</span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <div class="game-actions">
                    <button class="btn btn-primary btn-small" onclick="openBetModal('${game.game_id}')">
                        Record Bet
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Load Bets
async function loadBets() {
    const data = await fetchAPI('/api/bets');

    if (data.success) {
        bets = data.bets;
        renderBets();
    }
}

// Render Bets
function renderBets() {
    if (bets.length === 0) {
        betsList.innerHTML = '<div class="loading">No bets recorded yet.</div>';
        return;
    }

    betsList.innerHTML = bets.map(bet => {
        const resultClass = bet.result?.toLowerCase() || 'pending';
        const profitClass = bet.profit > 0 ? 'positive' : bet.profit < 0 ? 'negative' : '';

        return `
            <div class="bet-card">
                <div class="bet-info">
                    <h3>${bet.away_team} @ ${bet.home_team}</h3>
                    <div class="bet-details">
                        ${bet.bet_type} ${bet.line} (${bet.odds > 0 ? '+' : ''}${bet.odds}) |
                        Stake: $${bet.stake} |
                        Edge: ${bet.edge?.toFixed(1) || 'N/A'}pts
                    </div>
                </div>
                <div class="bet-result">
                    <span class="result-badge ${resultClass}">
                        ${bet.result || 'PENDING'}
                    </span>
                    ${!bet.result ? `
                        <button class="btn btn-secondary btn-small" onclick="openSettleModal(${bet.id})" style="margin-top: 0.5rem;">
                            Settle
                        </button>
                    ` : ''}
                </div>
                <div class="bet-profit ${profitClass}">
                    ${bet.profit !== null ? (bet.profit >= 0 ? '+' : '') + '$' + bet.profit.toFixed(2) : '-'}
                </div>
            </div>
        `;
    }).join('');
}

// Load Injuries
async function loadInjuries() {
    const data = await fetchAPI('/api/injuries');

    if (data.success) {
        injuries = data.injuries;
        renderInjuries();
    }
}

// Render Injuries
function renderInjuries() {
    if (injuries.length === 0) {
        injuriesList.innerHTML = '<div class="loading">No injury data available. Click Refresh to fetch.</div>';
        return;
    }

    injuriesList.innerHTML = injuries.map(inj => {
        const statusClass = inj.status?.toLowerCase().includes('out') ? 'out' :
                           inj.status?.toLowerCase().includes('question') ? 'questionable' : 'probable';

        return `
            <div class="injury-row ${inj.is_star_player ? 'star-player' : ''}">
                <div class="injury-player">
                    ${inj.is_star_player ? '⭐ ' : ''}${inj.player_name}
                </div>
                <div class="injury-team">${inj.team_abbrev}</div>
                <div class="injury-type">${inj.injury}</div>
                <div class="injury-status ${statusClass}">${inj.status}</div>
            </div>
        `;
    }).join('');
}

// Load Team Stats
async function loadTeamStats() {
    const data = await fetchAPI('/api/team-stats');

    if (data.success) {
        teamStats = data.stats;
        renderTeamStats();
    }
}

// Render Team Stats
function renderTeamStats() {
    if (teamStats.length === 0) {
        teamsList.innerHTML = '<div class="loading">No team stats available. Click Refresh to fetch.</div>';
        return;
    }

    teamsList.innerHTML = `
        <table class="teams-table">
            <thead>
                <tr>
                    <th>Team</th>
                    <th>Off Efficiency</th>
                    <th>Def Efficiency</th>
                    <th>Pace</th>
                </tr>
            </thead>
            <tbody>
                ${teamStats.map(team => `
                    <tr>
                        <td><strong>${team.team}</strong></td>
                        <td>${team.off_eff?.toFixed(1) || 'N/A'}</td>
                        <td>${team.def_eff?.toFixed(1) || 'N/A'}</td>
                        <td>${team.pace?.toFixed(1) || 'N/A'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Load Stats
async function loadStats() {
    const data = await fetchAPI('/api/stats');

    if (data.success) {
        const stats = data.stats;
        document.getElementById('total-bets').textContent = stats.settled_bets;
        document.getElementById('win-rate').textContent = `${stats.win_rate.toFixed(1)}%`;

        const profitEl = document.getElementById('total-profit');
        profitEl.textContent = `$${stats.total_profit.toFixed(2)}`;
        profitEl.classList.toggle('negative', stats.total_profit < 0);

        document.getElementById('roi').textContent = `${stats.roi.toFixed(1)}%`;
    }
}

// Refresh Data
async function refreshData() {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Refreshing...';

    const data = await fetchAPI('/api/refresh', { method: 'POST' });

    if (data.success) {
        await loadAllData();
        alert(`Data refreshed! Found ${data.games_with_edges} games with 5+ point edges.`);
    } else {
        alert(`Error refreshing: ${data.error}`);
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔄</span> Refresh Data';
}

// Send Alert
async function sendAlert() {
    const btn = document.getElementById('alert-btn');
    btn.disabled = true;

    const data = await fetchAPI('/api/send-alert', { method: 'POST' });

    if (data.success) {
        alert(data.message);
    } else {
        alert(`Error: ${data.message || data.error}`);
    }

    btn.disabled = false;
}

// Open Bet Modal
function openBetModal(gameId) {
    const game = games.find(g => g.game_id === gameId);
    if (!game) return;

    document.getElementById('bet-game-id').value = game.game_id;
    document.getElementById('bet-game-date').value = game.game_date;
    document.getElementById('bet-home-team').value = game.home_team;
    document.getElementById('bet-away-team').value = game.away_team;
    document.getElementById('bet-projected').value = game.projected_total;
    document.getElementById('bet-edge-value').value = game.edge;

    document.getElementById('bet-game-display').textContent =
        `${game.away_team} @ ${game.home_team}`;
    document.getElementById('bet-line').value = game.fanduel_total;
    document.getElementById('bet-type').value = game.edge_direction || 'OVER';
    document.getElementById('bet-odds').value = game.edge_direction === 'OVER' ?
        game.over_odds : game.under_odds;

    document.getElementById('bet-modal').classList.add('active');
}

// Place Bet
async function placeBet() {
    const betData = {
        game_id: document.getElementById('bet-game-id').value,
        game_date: document.getElementById('bet-game-date').value,
        home_team: document.getElementById('bet-home-team').value,
        away_team: document.getElementById('bet-away-team').value,
        bet_type: document.getElementById('bet-type').value,
        line: parseFloat(document.getElementById('bet-line').value),
        odds: parseInt(document.getElementById('bet-odds').value),
        stake: parseFloat(document.getElementById('bet-stake').value),
        projected_total: parseFloat(document.getElementById('bet-projected').value),
        edge: parseFloat(document.getElementById('bet-edge-value').value)
    };

    const data = await fetchAPI('/api/bets', {
        method: 'POST',
        body: JSON.stringify(betData)
    });

    if (data.success) {
        document.getElementById('bet-modal').classList.remove('active');
        document.getElementById('bet-form').reset();
        await loadBets();
        await loadStats();
        alert('Bet recorded successfully!');
    } else {
        alert(`Error recording bet: ${data.error}`);
    }
}

// Open Settle Modal
function openSettleModal(betId) {
    document.getElementById('settle-bet-id').value = betId;
    document.getElementById('settle-modal').classList.add('active');
}

// Settle Bet
async function settleBet() {
    const betId = document.getElementById('settle-bet-id').value;
    const actualTotal = parseFloat(document.getElementById('actual-total').value);

    const data = await fetchAPI(`/api/bets/${betId}/settle`, {
        method: 'POST',
        body: JSON.stringify({ actual_total: actualTotal })
    });

    if (data.success) {
        document.getElementById('settle-modal').classList.remove('active');
        document.getElementById('settle-form').reset();
        await loadBets();
        await loadStats();
        alert(`Bet settled: ${data.result} (${data.profit >= 0 ? '+' : ''}$${data.profit.toFixed(2)})`);
    } else {
        alert(`Error settling bet: ${data.error}`);
    }
}

// Utility Functions
function formatDateTime(isoString) {
    if (!isoString) return 'TBD';
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}
