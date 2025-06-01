document.addEventListener('DOMContentLoaded', () => {
    const scanButton = document.getElementById('scanButton');
    const downloadCsvButton = document.getElementById('downloadCsvButton'); // Direct link, JS interaction optional
    const cardListDiv = document.getElementById('cardList');
    const scanStatusDiv = document.getElementById('scanStatus');
    const colorFilterInput = document.getElementById('colorFilter');
    const manaCostFilterInput = document.getElementById('manaCostFilter');
    const applyFilterButton = document.getElementById('applyFilterButton');
    const clearFilterButton = document.getElementById('clearFilterButton');
    const configureCropButton = document.getElementById('configureCropButton');

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

        if (color) {
            params.append('color', color);
        }
        if (manaCost) {
            params.append('mana_cost', manaCost);
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
            scanStatusDiv.textContent = cards.length > 0 ? '' : 'No cards found.';
        } catch (error) {
            console.error('Error fetching cards:', error);
            cardListDiv.innerHTML = '<p>Error loading cards. Please try again.</p>';
            scanStatusDiv.textContent = 'Error loading cards.';
        }
    };

    const renderCards = (cards) => {
        if (!cards || cards.length === 0) {
            cardListDiv.innerHTML = '<p>No cards scanned yet, or none match current filters.</p>';
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
                <p><strong>Timestamp:</strong> ${card.timestamp || 'N/A'}</p>
                ${card.image_path ? `<p><small>Image Path: ${card.image_path}</small></p>` : ''}
            `;

            const imagePlaceholderDiv = document.createElement('div');
            imagePlaceholderDiv.classList.add('card-image-placeholder');
            // In a real app, you might try to load an image if a URL/path is available
            // For local paths like `card.image_path`, direct display in browser is tricky
            // unless served. For now, just a placeholder.
            imagePlaceholderDiv.textContent = 'Card Image (placeholder)';
            // If card.image_path was a URL:
            // const img = document.createElement('img');
            // img.src = card.image_path;
            // img.alt = card.name;
            // img.style.maxWidth = '100px'; // Basic styling
            // img.style.maxHeight = '140px';
            // imagePlaceholderDiv.appendChild(img);


            cardItem.appendChild(detailsDiv);
            cardItem.appendChild(imagePlaceholderDiv);

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
                    scanStatusDiv.textContent = `Card '${result.name || 'Unknown'}' scanned successfully!`;
                    fetchAndDisplayCards(); // Refresh the list
                } else {
                    throw new Error(result.error || `Scan failed with status: ${response.status}`);
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
            colorFilterInput.value = '';
            manaCostFilterInput.value = '';
            fetchAndDisplayCards();
        });
    }

    // Initial load of cards
    fetchAndDisplayCards();
});
