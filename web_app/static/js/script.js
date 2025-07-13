document.addEventListener('DOMContentLoaded', () => {
    const scanButton = document.getElementById('scanButton');
    const downloadCsvButton = document.getElementById('downloadCsvButton');
    const cardListDiv = document.getElementById('cardList');
    const scanStatusDiv = document.getElementById('scanStatus');
    const colorFilterInput = document.getElementById('colorFilter');
    const manaCostFilterInput = document.getElementById('manaCostFilter');
    const maxPriceFilterInput = document.getElementById('maxPriceFilter');
    const cardCountDisplay = document.getElementById('cardCountDisplay');
    const totalPriceDisplay = document.getElementById('totalPriceDisplay');
    const applyFilterButton = document.getElementById('applyFilterButton');
    const clearFilterButton = document.getElementById('clearFilterButton');
    const configureCropButton = document.getElementById('configureCropButton');
    
    // Sorting rules elements
    const addRuleButton = document.getElementById('addRuleButton');
    const ruleNameInput = document.getElementById('ruleName');
    const ruleAttributeSelect = document.getElementById('ruleAttribute');
    const ruleOperatorSelect = document.getElementById('ruleOperator');
    const ruleValueInput = document.getElementById('ruleValue');
    const ruleDirectionSelect = document.getElementById('ruleDirection');
    const rulesListDiv = document.getElementById('rulesList');

    // Utility function to show status messages
    const showStatus = (message, type = 'info') => {
        scanStatusDiv.textContent = message;
        scanStatusDiv.className = `status-message status-${type}`;
        scanStatusDiv.style.display = 'flex';
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                scanStatusDiv.style.display = 'none';
            }, 5000);
        }
    };

    // Utility function to update statistics
    const updateStats = (cards) => {
        if (cardCountDisplay) {
            cardCountDisplay.textContent = cards.length;
        }
        if (totalPriceDisplay) {
            const totalPrice = cards.reduce((sum, card) => {
                return sum + (card.price && !isNaN(card.price) ? parseFloat(card.price) : 0);
            }, 0);
            totalPriceDisplay.textContent = `€${totalPrice.toFixed(2)}`;
        }
    };

    if (configureCropButton) {
        configureCropButton.addEventListener('click', async () => {
            showStatus('Opening crop configuration tool...', 'info');
            configureCropButton.disabled = true;
            configureCropButton.classList.add('loading');
            
            try {
                const response = await fetch('/configure_crop', { method: 'POST' });
                const result = await response.json();
                if (response.ok) {
                    showStatus(result.message || 'Crop configuration initiated. Check server display.', 'success');
                } else {
                    throw new Error(result.error || 'Failed to start crop configuration.');
                }
            } catch (error) {
                console.error('Error during crop configuration:', error);
                showStatus('Error during crop configuration: ' + error.message, 'error');
            } finally {
                configureCropButton.disabled = false;
                configureCropButton.classList.remove('loading');
            }
        });
    }

    const fetchAndDisplayCards = async () => {
        showStatus('Loading cards...', 'info');
        let url = '/cards';
        const params = new URLSearchParams();
        const color = colorFilterInput.value.trim();
        const manaCost = manaCostFilterInput.value.trim();
        const maxPrice = maxPriceFilterInput.value.trim();

        if (color) {
            params.append('color', color);
        }
        if (manaCost) {
            params.append('mana_cost', manaCost);
        }
        if (maxPrice) {
            params.append('max_price', maxPrice);
        }

        if (params.toString()) {
            url += `?${params.toString()}`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const cards = await response.json();
            renderCards(cards);
            updateStats(cards);

            if (cards.length > 0) {
                showStatus(`Loaded ${cards.length} card(s) successfully.`, 'success');
            } else {
                showStatus('No cards found matching the current filters.', 'info');
            }

        } catch (error) {
            console.error('Error fetching cards:', error);
            cardListDiv.innerHTML = '<p style="color: var(--danger-color); text-align: center; padding: var(--spacing-8);">Error loading cards. Please try again.</p>';
            showStatus('Error loading cards.', 'error');
            updateStats([]);
        }
    };

    const renderCards = (cards) => {
        if (!cards || cards.length === 0) {
            cardListDiv.innerHTML = '<p style="color: var(--gray-500); text-align: center; padding: var(--spacing-8);">No cards scanned yet, or none match current filters.</p>';
            return;
        }

        cardListDiv.innerHTML = '';
        cards.forEach(card => {
            const cardItem = document.createElement('div');
            cardItem.classList.add('card-item');

            const detailsDiv = document.createElement('div');
            detailsDiv.classList.add('card-details');

            // Card name as prominent header
            const cardName = document.createElement('div');
            cardName.classList.add('card-name');
            cardName.textContent = card.name || 'Unknown Card';
            detailsDiv.appendChild(cardName);

            // Card metadata in grid layout
            const metaDiv = document.createElement('div');
            metaDiv.classList.add('card-meta');

            const metaItems = [
                { label: 'Price', value: card.price !== null ? `€${card.price}` : 'N/A' },
                { label: 'CMC', value: card.cmc !== null ? card.cmc : 'N/A' },
                { label: 'Colors', value: card.color_identity || 'N/A' },
                { label: 'Type', value: card.type_line || 'N/A' },
                { label: 'Scanned', value: card.timestamp || 'N/A' }
            ];

            metaItems.forEach(item => {
                const metaItem = document.createElement('div');
                metaItem.classList.add('card-meta-item');
                metaItem.innerHTML = `<strong>${item.label}:</strong> ${item.value}`;
                metaDiv.appendChild(metaItem);
            });

            detailsDiv.appendChild(metaDiv);

            // Add Scryfall link if available
            if (card.image_uri) {
                const scryfallLink = document.createElement('div');
                scryfallLink.classList.add('card-meta-item');
                scryfallLink.innerHTML = `<strong>Image:</strong> <a href="${card.image_uri}" target="_blank" style="color: var(--primary-color); text-decoration: none;">View on Scryfall</a>`;
                metaDiv.appendChild(scryfallLink);
            }

            cardItem.appendChild(detailsDiv);

            const deleteButton = document.createElement('button');
            deleteButton.classList.add('btn', 'btn-danger');
            deleteButton.innerHTML = '<span class="icon icon-delete"></span> Delete';
            deleteButton.setAttribute('data-id', card.id);

            deleteButton.addEventListener('click', async (event) => {
                const cardId = event.target.closest('button').getAttribute('data-id');
                if (!confirm(`Are you sure you want to delete "${card.name || 'this card'}"?`)) {
                    return;
                }

                showStatus(`Deleting card...`, 'info');
                deleteButton.disabled = true;
                deleteButton.classList.add('loading');
                
                try {
                    const response = await fetch(`/cards/delete/${cardId}`, {
                        method: 'DELETE',
                    });
                    const result = await response.json();

                    if (response.ok) {
                        showStatus(result.message || `Card deleted successfully.`, 'success');
                        fetchAndDisplayCards(); // Refresh the list
                    } else {
                        throw new Error(result.error || `Failed to delete card. Status: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Error deleting card:', error);
                    showStatus(`Error deleting card: ${error.message}`, 'error');
                } finally {
                    deleteButton.disabled = false;
                    deleteButton.classList.remove('loading');
                }
            });

            cardItem.appendChild(deleteButton);
            cardListDiv.appendChild(cardItem);
        });
    };

    if (scanButton) {
        scanButton.addEventListener('click', async () => {
            showStatus('Scanning card...', 'info');
            scanButton.disabled = true;
            scanButton.classList.add('loading');
            
            try {
                const response = await fetch('/scan', { method: 'POST' });
                const result = await response.json();

                if (response.ok) {
                    let statusMessage = `Card '${result.name || 'Unknown'}' processed.`;
                    if (result.id) {
                        statusMessage = `Card '${result.name}' scanned successfully!`;
                    } else if (result.message) {
                        statusMessage = result.message;
                    }
                    if (result.sorted) {
                        statusMessage += ` Sorted: ${result.sorted}.`;
                    }
                    showStatus(statusMessage, 'success');
                    fetchAndDisplayCards(); // Refresh the list
                } else {
                    let errorMessage = result.error || `Scan failed with status: ${response.status}`;
                    if (result.sorted) {
                        errorMessage += ` Sorting attempt: ${result.sorted}.`;
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                console.error('Error scanning card:', error);
                showStatus(`Error scanning card: ${error.message}`, 'error');
            } finally {
                scanButton.disabled = false;
                scanButton.classList.remove('loading');
            }
        });
    }

    if (applyFilterButton) {
        applyFilterButton.addEventListener('click', fetchAndDisplayCards);
    }

    if (clearFilterButton) {
        clearFilterButton.addEventListener('click', () => {
            if (colorFilterInput) colorFilterInput.value = '';
            if (manaCostFilterInput) manaCostFilterInput.value = '';
            if (maxPriceFilterInput) maxPriceFilterInput.value = '';
            fetchAndDisplayCards();
        });
    }

    // Sorting Rules Functions
    const fetchAndDisplayRules = async () => {
        try {
            const response = await fetch('/sorting-rules');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const rules = await response.json();
            renderRules(rules);
        } catch (error) {
            console.error('Error fetching sorting rules:', error);
            rulesListDiv.innerHTML = '<p style="color: var(--danger-color); text-align: center; padding: var(--spacing-8);">Error loading sorting rules. Please try again.</p>';
        }
    };

    const renderRules = (rules) => {
        if (!rules || rules.length === 0) {
            rulesListDiv.innerHTML = '<p style="color: var(--gray-500); text-align: center; padding: var(--spacing-8);">No sorting rules configured. Add a rule above to get started.</p>';
            return;
        }

        rulesListDiv.innerHTML = '';
        rules.forEach(rule => {
            const ruleItem = document.createElement('div');
            ruleItem.classList.add('rule-item');

            const ruleInfo = document.createElement('div');
            ruleInfo.classList.add('rule-info');

            const ruleName = document.createElement('div');
            ruleName.classList.add('rule-name');
            ruleName.textContent = rule.name;

            const ruleCondition = document.createElement('div');
            ruleCondition.classList.add('rule-condition');
            ruleCondition.textContent = `${rule.attribute} ${rule.operator} ${rule.value}`;

            const ruleDirection = document.createElement('span');
            ruleDirection.classList.add('rule-direction', rule.sort_direction);
            ruleDirection.textContent = rule.sort_direction === 'left' ? 'Left Pile' : 'Right Pile';

            ruleInfo.appendChild(ruleName);
            ruleInfo.appendChild(ruleCondition);
            ruleInfo.appendChild(ruleDirection);

            const deleteButton = document.createElement('button');
            deleteButton.classList.add('btn', 'btn-danger');
            deleteButton.innerHTML = '<span class="icon icon-delete"></span> Delete';
            deleteButton.setAttribute('data-id', rule.id);

            deleteButton.addEventListener('click', async (event) => {
                const ruleId = event.target.closest('button').getAttribute('data-id');
                if (!confirm(`Are you sure you want to delete rule "${rule.name}"?`)) {
                    return;
                }

                showStatus(`Deleting rule...`, 'info');
                deleteButton.disabled = true;
                deleteButton.classList.add('loading');

                try {
                    const response = await fetch(`/sorting-rules/${ruleId}`, {
                        method: 'DELETE',
                    });
                    const result = await response.json();

                    if (response.ok) {
                        showStatus(result.message || `Rule "${rule.name}" deleted successfully.`, 'success');
                        fetchAndDisplayRules(); // Refresh the list
                    } else {
                        throw new Error(result.error || `Failed to delete rule. Status: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Error deleting rule:', error);
                    showStatus(`Error deleting rule: ${error.message}`, 'error');
                } finally {
                    deleteButton.disabled = false;
                    deleteButton.classList.remove('loading');
                }
            });

            ruleItem.appendChild(ruleInfo);
            ruleItem.appendChild(deleteButton);
            rulesListDiv.appendChild(ruleItem);
        });
    };

    if (addRuleButton) {
        addRuleButton.addEventListener('click', async () => {
            const name = ruleNameInput.value.trim();
            const attribute = ruleAttributeSelect.value;
            const operator = ruleOperatorSelect.value;
            const value = ruleValueInput.value.trim();
            const sortDirection = ruleDirectionSelect.value;

            if (!name || !value) {
                showStatus('Please fill in all required fields.', 'error');
                return;
            }

            addRuleButton.disabled = true;
            addRuleButton.classList.add('loading');
            
            try {
                const response = await fetch('/sorting-rules', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        attribute: attribute,
                        operator: operator,
                        value: value,
                        sort_direction: sortDirection
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    showStatus(result.message || 'Sorting rule added successfully.', 'success');
                    // Clear form
                    ruleNameInput.value = '';
                    ruleValueInput.value = '';
                    ruleAttributeSelect.selectedIndex = 0;
                    ruleOperatorSelect.selectedIndex = 0;
                    ruleDirectionSelect.selectedIndex = 0;
                    // Refresh rules list
                    fetchAndDisplayRules();
                } else {
                    throw new Error(result.error || `Failed to add rule. Status: ${response.status}`);
                }
            } catch (error) {
                console.error('Error adding sorting rule:', error);
                showStatus(`Error adding sorting rule: ${error.message}`, 'error');
            } finally {
                addRuleButton.disabled = false;
                addRuleButton.classList.remove('loading');
            }
        });
    }

    // Initial load of cards and rules
    fetchAndDisplayCards();
    fetchAndDisplayRules();
});
