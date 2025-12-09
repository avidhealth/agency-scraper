// API base URL
const API_BASE = '';

// State
let currentListId = null;
let currentListName = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupAgencySearch();
    setupLists();
    loadInitialStats();
});

// Tab switching
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Update buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');

            // Load lists if switching to lists tab
            if (tabName === 'lists') {
                loadLists();
            }
        });
    });
}

// Agency search functionality
function setupAgencySearch() {
    const searchBtn = document.getElementById('search-btn');
    searchBtn.addEventListener('click', searchAgencies);

    // Allow Enter key to search
    ['filter-state', 'filter-location', 'filter-npi'].forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchAgencies();
            }
        });
    });
}

async function loadInitialStats() {
    try {
        const response = await fetch(`${API_BASE}/agencies/stats`);
        if (response.ok) {
            const stats = await response.json();
            const statsSection = document.getElementById('stats-section');
            const statsText = document.getElementById('stats-text');
            statsText.textContent = `Total agencies: ${stats.total_agencies || 0}`;
            statsSection.style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function searchAgencies() {
    const state = document.getElementById('filter-state').value.trim().toUpperCase();
    const location = document.getElementById('filter-location').value.trim();
    const npi = document.getElementById('filter-npi').value.trim();

    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const agenciesList = document.getElementById('agencies-list');

    // Show loading
    loading.style.display = 'block';
    error.style.display = 'none';
    agenciesList.innerHTML = '';

    try {
        const params = new URLSearchParams();
        if (state) params.append('state', state);
        if (location) params.append('location', location);
        if (npi) params.append('npi', npi);
        params.append('limit', '100');

        const response = await fetch(`${API_BASE}/agencies?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayAgencies(data.agencies || [], false);

        // Update stats
        const statsSection = document.getElementById('stats-section');
        const statsText = document.getElementById('stats-text');
        statsText.textContent = `Found ${data.count || 0} agencies`;
        statsSection.style.display = 'block';

    } catch (err) {
        error.textContent = `Error: ${err.message}`;
        error.style.display = 'block';
    } finally {
        loading.style.display = 'none';
    }
}

function displayAgencies(agencies, isListView = false) {
    const agenciesList = document.getElementById('agencies-list');
    
    if (agencies.length === 0) {
        agenciesList.innerHTML = '<div class="empty-state"><h3>No agencies found</h3><p>Try adjusting your search filters</p></div>';
        return;
    }

    agenciesList.innerHTML = agencies.map(agency => {
        const address = agency.agency_addresses?.[0] || {};
        const official = agency.agency_officials?.[0] || {};
        const fullAddress = [
            address.street,
            address.city,
            address.state,
            address.zip
        ].filter(Boolean).join(', ') || 'N/A';

        return `
            <div class="agency-card" data-agency-id="${agency.id}">
                <div class="agency-header">
                    <div>
                        <div class="agency-name">${escapeHtml(agency.provider_name || agency.agency_name || 'Unknown')}</div>
                        <div class="agency-npi">NPI: ${agency.npi || 'N/A'}</div>
                    </div>
                    <div class="agency-actions">
                        ${!isListView ? `<button class="btn btn-small btn-primary" onclick="addAgencyToCurrentList('${agency.id}')">Add to List</button>` : ''}
                        ${isListView ? `<button class="btn btn-small btn-danger" onclick="removeAgencyFromList('${currentListId}', '${agency.id}')">Remove</button>` : ''}
                    </div>
                </div>
                <div class="agency-details">
                    <div class="detail-item">
                        <span class="detail-label">Address</span>
                        <span class="detail-value">${escapeHtml(fullAddress)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Phone</span>
                        <span class="detail-value">${escapeHtml(agency.phone || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">State</span>
                        <span class="detail-value">${escapeHtml(agency.source_state || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Location</span>
                        <span class="detail-value">${escapeHtml(agency.source_location || 'N/A')}</span>
                    </div>
                    ${official.name ? `
                    <div class="detail-item">
                        <span class="detail-label">Authorized Official</span>
                        <span class="detail-value">${escapeHtml(official.name)}${official.title ? ` - ${escapeHtml(official.title)}` : ''}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// List management
function setupLists() {
    // Create list button
    document.getElementById('create-list-btn').addEventListener('click', () => {
        document.getElementById('create-list-modal').style.display = 'block';
    });

    // Close modal buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
            if (e.target.closest('#create-list-modal')) {
                document.getElementById('create-list-form').reset();
            }
        });
    });

    // Create list form
    document.getElementById('create-list-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('list-name').value.trim();
        const description = document.getElementById('list-description').value.trim();

        if (!name) {
            alert('Please enter a list name');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/lists`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    description: description || null
                })
            });

            if (!response.ok) {
                throw new Error('Failed to create list');
            }

            document.getElementById('create-list-modal').style.display = 'none';
            document.getElementById('create-list-form').reset();
            loadLists();
        } catch (err) {
            alert(`Error creating list: ${err.message}`);
        }
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

async function loadLists() {
    const listsContainer = document.getElementById('lists-container');
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.textContent = 'Loading lists...';
    listsContainer.innerHTML = '';
    listsContainer.appendChild(loading);

    try {
        const response = await fetch(`${API_BASE}/lists`);
        if (!response.ok) {
            throw new Error('Failed to load lists');
        }

        const data = await response.json();
        const lists = data.lists || [];

        if (lists.length === 0) {
            listsContainer.innerHTML = '<div class="empty-state"><h3>No lists yet</h3><p>Create your first list to get started</p></div>';
            return;
        }

        listsContainer.innerHTML = lists.map(list => {
            const createdDate = new Date(list.created_at).toLocaleDateString();
            return `
                <div class="list-card">
                    <div class="list-header">
                        <div>
                            <div class="list-name">${escapeHtml(list.name)}</div>
                            ${list.description ? `<div class="list-description">${escapeHtml(list.description)}</div>` : ''}
                        </div>
                        <button class="btn btn-small btn-primary" onclick="viewList('${list.id}', '${escapeHtml(list.name).replace(/'/g, "\\'")}')">View</button>
                    </div>
                    <div class="list-meta">
                        <span>Created: ${createdDate}</span>
                        <span>Updated: ${new Date(list.updated_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        listsContainer.innerHTML = `<div class="error">Error loading lists: ${err.message}</div>`;
    }
}

async function viewList(listId, listName) {
    currentListId = listId;
    currentListName = listName;

    const modal = document.getElementById('list-view-modal');
    const title = document.getElementById('list-view-title');
    const agenciesContainer = document.getElementById('list-agencies-container');

    title.textContent = listName;
    modal.style.display = 'block';
    agenciesContainer.innerHTML = '<div class="loading">Loading agencies...</div>';

    try {
        const response = await fetch(`${API_BASE}/lists/${listId}/agencies`);
        if (!response.ok) {
            throw new Error('Failed to load list agencies');
        }

        const data = await response.json();
        displayAgencies(data.agencies || [], true);

    } catch (err) {
        agenciesContainer.innerHTML = `<div class="error">Error loading agencies: ${err.message}</div>`;
    }

    // Setup download buttons
    document.getElementById('download-csv-btn').onclick = () => {
        window.location.href = `${API_BASE}/lists/${listId}/download/csv`;
    };

    document.getElementById('download-json-btn').onclick = () => {
        window.location.href = `${API_BASE}/lists/${listId}/download/json`;
    };

    // Setup delete button
    document.getElementById('delete-list-btn').onclick = async () => {
        if (confirm(`Are you sure you want to delete "${listName}"?`)) {
            try {
                const response = await fetch(`${API_BASE}/lists/${listId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error('Failed to delete list');
                }

                modal.style.display = 'none';
                loadLists();
            } catch (err) {
                alert(`Error deleting list: ${err.message}`);
            }
        }
    };
}

async function addAgencyToCurrentList(agencyId) {
    // Get all lists for user to choose
    try {
        const response = await fetch(`${API_BASE}/lists`);
        if (!response.ok) {
            throw new Error('Failed to load lists');
        }

        const data = await response.json();
        const lists = data.lists || [];

        if (lists.length === 0) {
            if (confirm('No lists found. Would you like to create one?')) {
                // Switch to lists tab
                document.querySelector('[data-tab="lists"]').click();
                document.getElementById('create-list-btn').click();
            }
            return;
        }

        // Show a simple selection dialog
        if (lists.length === 1) {
            const listId = lists[0].id;
            await addAgencyToList(listId, agencyId, lists[0].name);
        } else {
            // Create a simple selection modal
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.display = 'block';
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 400px;">
                    <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
                    <h3>Select a List</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 20px;">
                        ${lists.map(list => `
                            <button class="btn btn-primary" onclick="
                                window.addAgencyToList('${list.id}', '${agencyId}', '${escapeHtml(list.name).replace(/'/g, "\\'")}');
                                this.closest('.modal').remove();
                            " style="width: 100%;">${escapeHtml(list.name)}</button>
                        `).join('')}
                        <button class="btn btn-secondary" onclick="
                            this.closest('.modal').remove();
                            document.querySelector('[data-tab=\\"lists\\"]').click();
                            document.getElementById('create-list-btn').click();
                        " style="width: 100%;">Create New List</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

async function addAgencyToList(listId, agencyId, listName) {
    try {
        const response = await fetch(`${API_BASE}/lists/${listId}/agencies/${agencyId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add agency to list');
        }

        alert(`Agency added to "${listName}" successfully!`);
    } catch (err) {
        alert(`Error adding agency: ${err.message}`);
    }
}

async function removeAgencyFromList(listId, agencyId) {
    if (!confirm('Remove this agency from the list?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/lists/${listId}/agencies/${agencyId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to remove agency');
        }

        // Reload the list view
        viewList(listId, currentListName);
    } catch (err) {
        alert(`Error removing agency: ${err.message}`);
    }
}

// Make functions available globally
window.addAgencyToCurrentList = addAgencyToCurrentList;
window.addAgencyToList = addAgencyToList;
window.removeAgencyFromList = removeAgencyFromList;
window.viewList = viewList;

