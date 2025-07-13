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
            const totalCards = cards.reduce((sum, card) => {
                return sum + (card.quantity || 1);
            }, 0);
            cardCountDisplay.textContent = totalCards;
        }
        if (totalPriceDisplay) {
            const totalPrice = cards.reduce((sum, card) => {
                const cardPrice = card.price && !isNaN(card.price) ? parseFloat(card.price) : 0;
                const quantity = card.quantity || 1;
                return sum + (cardPrice * quantity);
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
                // Check if there are any filters applied
                const hasFilters = (colorFilterInput && colorFilterInput.value) || 
                                 (manaCostFilterInput && manaCostFilterInput.value) || 
                                 (maxPriceFilterInput && maxPriceFilterInput.value);
                
                if (hasFilters) {
                    showStatus('No cards found matching the current filters.', 'info');
                } else {
                    showStatus('No cards scanned yet. Start by scanning your first card!', 'info');
                }
            }

        } catch (error) {
            console.error('Error fetching cards:', error);
            cardListDiv.innerHTML = `
                <div style="text-align: center; padding: var(--spacing-12); color: var(--danger-color);">
                    <div style="font-size: 3rem; margin-bottom: var(--spacing-4);">⚠️</div>
                    <h3 style="margin-bottom: var(--spacing-4);">Error Loading Cards</h3>
                    <p style="margin-bottom: var(--spacing-6);">There was a problem loading your scanned cards. Please try refreshing the page.</p>
                    <button onclick="location.reload()" class="btn btn-primary">Refresh Page</button>
                </div>
            `;
            showStatus('Error loading cards.', 'error');
            updateStats([]);
        }
    };

    const renderCards = (cards) => {
        if (!cards || cards.length === 0) {
            cardListDiv.innerHTML = `
                <div style="text-align: center; padding: var(--spacing-12); color: var(--gray-600);">
                    <div style="font-size: 3rem; margin-bottom: var(--spacing-4);">📷</div>
                    <h3 style="margin-bottom: var(--spacing-4); color: var(--gray-700);">No Cards Scanned Yet</h3>
                    <p style="margin-bottom: var(--spacing-6);">Start by scanning your first Magic card using the camera button above.</p>
                    <div style="background: var(--gray-50); border: 2px dashed var(--gray-300); border-radius: var(--radius-lg); padding: var(--spacing-6); margin: 0 auto; max-width: 400px;">
                        <p style="margin: 0; font-size: var(--font-size-sm); color: var(--gray-500);">
                            <strong>Tip:</strong> Make sure your card is well-lit and clearly visible in the camera view.
                        </p>
                    </div>
                </div>
            `;
            return;
        }

        cardListDiv.innerHTML = '';
        cards.forEach(card => {
            const cardItem = document.createElement('div');
            cardItem.classList.add('card-item');

            const detailsDiv = document.createElement('div');
            detailsDiv.classList.add('card-details');

            // Card name as prominent header with quantity
            const cardName = document.createElement('div');
            cardName.classList.add('card-name');
            const quantity = card.quantity || 1;
            if (quantity > 1) {
                cardName.innerHTML = `${card.name || 'Unknown Card'} <span style="background: var(--primary-color); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 8px;">×${quantity}</span>`;
            } else {
                cardName.textContent = card.name || 'Unknown Card';
            }
            detailsDiv.appendChild(cardName);

            // Card metadata in grid layout
            const metaDiv = document.createElement('div');
            metaDiv.classList.add('card-meta');

            const metaItems = [
                { label: 'Price', value: card.price !== null ? `€${card.price}` : 'N/A' },
                { label: 'CMC', value: card.cmc !== null ? card.cmc : 'N/A' },
                { label: 'Colors', value: card.color_identity || 'N/A' },
                { label: 'Type', value: card.type_line || 'N/A' },
                { label: 'Quantity', value: card.quantity || 1 },
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
                        // Check if this was a duplicate (quantity > 1)
                        if (result.quantity && result.quantity > 1) {
                            statusMessage = `Card '${result.name}' quantity increased to ${result.quantity}!`;
                        } else {
                            statusMessage = `Card '${result.name}' scanned successfully!`;
                        }
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

    // Initial load of cards
    fetchAndDisplayCards();
});
