document.addEventListener('DOMContentLoaded', () => {
    const scanButton = document.getElementById('scanButton');
    const downloadCsvButton = document.getElementById('downloadCsvButton'); // Direct link, JS interaction optional
    const cardListDiv = document.getElementById('cardList');
    const scanStatusDiv = document.getElementById('scanStatus');
    const colorFilterInput = document.getElementById('colorFilter');
    const manaCostFilterInput = document.getElementById('manaCostFilter');
    const maxPriceFilterInput = document.getElementById('maxPriceFilter'); // New
    const cardCountDisplay = document.getElementById('cardCountDisplay'); // New
    const totalPriceDisplay = document.getElementById('totalPriceDisplay'); // New
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

    if (configureCropButton) {
        configureCropButton.addEventListener('click', async () => {
            scanStatusDiv.textContent = 'Attempting to open crop configuration tool on the server... Please check the server display.';
            configureCropButton.disabled = true;
            try {
                const response = await fetch('/configure_crop', { method: 'POST' });
                const result = await response.json();
                if (response.ok) {
                    scanStatusDiv.textContent = result.message || 'Crop configuration initiated. Check server display.';
                } else {
                    throw new Error(result.error || 'Failed to start crop configuration.');
                }
            } catch (error) {
                console.error('Error during crop configuration:', error);
                scanStatusDiv.textContent = 'Error during crop configuration: ' + error.message;
            } finally {
                configureCropButton.disabled = false;
            }
        });
    }

    const fetchAndDisplayCards = async () => {
        scanStatusDiv.textContent = 'Loading cards...';
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
            renderCards(cards); // This will also update count/total for empty results

            if (cards.length > 0) {
                if (cardCountDisplay) {
                    cardCountDisplay.textContent = `Displaying ${cards.length} card(s).`;
                }
                if (totalPriceDisplay) {
                    let totalPrice = 0;
                    cards.forEach(card => {
                        if (card.price !== null && typeof card.price === 'number') {
                            totalPrice += card.price;
                        }
                    });
                    totalPriceDisplay.textContent = `Total Price of Displayed Cards: ${totalPrice.toFixed(2)} EUR/USD`;
                }
            }
            // scanStatusDiv.textContent is handled by renderCards for empty, and here for success.
            scanStatusDiv.textContent = cards.length > 0 ? 'Cards loaded.' : 'No cards found matching criteria.';

        } catch (error) {
            console.error('Error fetching cards:', error);
            cardListDiv.innerHTML = '<p>Error loading cards. Please try again.</p>';
            scanStatusDiv.textContent = 'Error loading cards.';
            if (cardCountDisplay) cardCountDisplay.textContent = '';
            if (totalPriceDisplay) totalPriceDisplay.textContent = '';
        }
    };

    const renderCards = (cards) => {
        if (!cards || cards.length === 0) {
            cardListDiv.innerHTML = '<p>No cards scanned yet, or none match current filters.</p>';
            if (cardCountDisplay) cardCountDisplay.textContent = 'Displaying 0 cards.';
            if (totalPriceDisplay) totalPriceDisplay.textContent = 'Total Price: 0.00 EUR/USD';
            return;
        }

        cardListDiv.innerHTML = ''; // Clear existing list
        cards.forEach(card => {
            const cardItem = document.createElement('div');
            cardItem.classList.add('card-item');

            const detailsDiv = document.createElement('div');
            detailsDiv.classList.add('card-details');

            detailsDiv.innerHTML = `
                <p><strong>Name:</strong> ${card.name || 'N/A'}</p>
                <p><strong>OCR Raw:</strong> ${card.ocr_name_raw || 'N/A'}</p>
                <p><strong>Price:</strong> ${card.price !== null ? card.price : 'N/A'} EUR/USD</p>
                <p><strong>Color Identity:</strong> ${card.color_identity || 'N/A'}</p>
                <p><strong>CMC:</strong> ${card.cmc !== null ? card.cmc : 'N/A'}</p>
                <p><strong>Type:</strong> ${card.type_line || 'N/A'}</p>
                <p><strong>Timestamp:</strong> ${card.timestamp || 'N/A'}</p>
                ${card.image_uri ? `<p><strong>Image:</strong> <a href="${card.image_uri}" target="_blank">View on Scryfall</a></p>` : '<p><strong>Image:</strong> N/A</p>'}
            `;

            cardItem.appendChild(detailsDiv);

            const deleteButton = document.createElement('button');
            deleteButton.classList.add('delete-button'); // For styling if needed
            deleteButton.textContent = 'Delete';
            deleteButton.setAttribute('data-id', card.id);

            deleteButton.addEventListener('click', async (event) => {
                const cardId = event.target.getAttribute('data-id');
                if (!confirm(`Are you sure you want to delete card ID ${cardId}?`)) {
                    return;
                }

                scanStatusDiv.textContent = `Deleting card ID ${cardId}...`;
                try {
                    const response = await fetch(`/cards/delete/${cardId}`, {
                        method: 'DELETE',
                    });
                    const result = await response.json(); // Try to parse JSON regardless of status for error messages

                    if (response.ok) {
                        scanStatusDiv.textContent = result.message || `Card ID ${cardId} deleted successfully.`;
                        fetchAndDisplayCards(); // Refresh the list
                    } else {
                        // Use result.error if available, otherwise a generic message
                        throw new Error(result.error || `Failed to delete card. Status: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Error deleting card:', error);
                    scanStatusDiv.textContent = `Error deleting card: ${error.message}`;
                }
            });

            cardItem.appendChild(deleteButton); // Add button to card item
            cardListDiv.appendChild(cardItem);
        });
    };

    if (scanButton) {
        scanButton.addEventListener('click', async () => {
            scanStatusDiv.textContent = 'Scanning... Please wait.';
            scanButton.disabled = true;
            try {
                const response = await fetch('/scan', { method: 'POST' });
                const result = await response.json();

                if (response.ok) {
                    let statusMessage = `Card '${result.name || 'Unknown'}' processed.`;
                    if (result.id) { // Successfully identified and likely saved
                        statusMessage = `Card '${result.name}' scanned successfully!`;
                    } else if (result.message) { // Processed but not identified
                        statusMessage = result.message;
                    }
                    if (result.sorted) {
                        statusMessage += ` Sorted: ${result.sorted}.`;
                    }
                    scanStatusDiv.textContent = statusMessage;
                    fetchAndDisplayCards(); // Refresh the list
                } else {
                    // Try to get error and sorted status from result if available
                    let errorMessage = result.error || `Scan failed with status: ${response.status}`;
                    if (result.sorted) {
                        errorMessage += ` Sorting attempt: ${result.sorted}.`;
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                console.error('Error scanning card:', error);
                scanStatusDiv.textContent = `Error scanning card: ${error.message}`;
            } finally {
                scanButton.disabled = false;
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
            if (maxPriceFilterInput) maxPriceFilterInput.value = ''; // Add this line
            fetchAndDisplayCards();
        });
    }

    // Initial load of cards
    fetchAndDisplayCards();
    
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
            rulesListDiv.innerHTML = '<p>Error loading sorting rules. Please try again.</p>';
        }
    };

    const renderRules = (rules) => {
        if (!rules || rules.length === 0) {
            rulesListDiv.innerHTML = '<p>No sorting rules configured. Add a rule above to get started.</p>';
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
            deleteButton.classList.add('delete-rule-button');
            deleteButton.textContent = 'Delete';
            deleteButton.setAttribute('data-id', rule.id);

            deleteButton.addEventListener('click', async (event) => {
                const ruleId = event.target.getAttribute('data-id');
                if (!confirm(`Are you sure you want to delete rule "${rule.name}"?`)) {
                    return;
                }

                try {
                    const response = await fetch(`/sorting-rules/${ruleId}`, {
                        method: 'DELETE',
                    });
                    const result = await response.json();

                    if (response.ok) {
                        scanStatusDiv.textContent = result.message || `Rule "${rule.name}" deleted successfully.`;
                        fetchAndDisplayRules(); // Refresh the list
                    } else {
                        throw new Error(result.error || `Failed to delete rule. Status: ${response.status}`);
                    }
                } catch (error) {
                    console.error('Error deleting rule:', error);
                    scanStatusDiv.textContent = `Error deleting rule: ${error.message}`;
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
                scanStatusDiv.textContent = 'Please fill in all required fields.';
                return;
            }

            addRuleButton.disabled = true;
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
                    scanStatusDiv.textContent = result.message || 'Sorting rule added successfully.';
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
                scanStatusDiv.textContent = `Error adding sorting rule: ${error.message}`;
            } finally {
                addRuleButton.disabled = false;
            }
        });
    }

    // Initial load of sorting rules
    fetchAndDisplayRules();
});
