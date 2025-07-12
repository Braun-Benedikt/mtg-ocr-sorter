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
                    if (result.id) {
                        // Successful card recognition and save
                        scanStatusDiv.textContent = `Card '${result.name || 'Unknown'}' scanned successfully!`;
                        fetchAndDisplayCards(); // Refresh the list
                    } else if (result.ocr_results) {
                        // OCR performed but card recognition failed - show debugging info
                        const ocrInfo = result.ocr_results;
                        // Build debug info display
                        let debugInfoHtml = '';
                        if (ocrInfo.debug_info && ocrInfo.debug_info.length > 0) {
                            debugInfoHtml = `<strong>Debug Info:</strong><br>`;
                            ocrInfo.debug_info.forEach(info => {
                                debugInfoHtml += `• ${info}<br>`;
                            });
                        }
                        
                        scanStatusDiv.innerHTML = `
                            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 5px;">
                                <strong>Card Recognition Failed</strong><br>
                                <strong>Error:</strong> ${result.error}<br>
                                <strong>Raw OCR Text:</strong> "${ocrInfo.raw_text || 'No text detected'}"<br>
                                <strong>Corrected Name:</strong> "${ocrInfo.corrected_name || 'No correction possible'}"<br>
                                <strong>Price:</strong> ${ocrInfo.price || 'N/A'}<br>
                                <strong>Color Identity:</strong> ${ocrInfo.color_identity || 'N/A'}<br>
                                <strong>CMC:</strong> ${ocrInfo.cmc || 'N/A'}<br>
                                <strong>Type Line:</strong> ${ocrInfo.type_line || 'N/A'}<br>
                                ${debugInfoHtml}
                                <em>This information can help debug OCR issues. Try adjusting the crop area or improving lighting.</em>
                                <br><br>
                                <button id="saveUnrecognizedButton" style="background-color: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                                    Save as Unrecognized Card (Debug)
                                </button>
                            </div>
                        `;
                        
                        // Add event listener for the save unrecognized button
                        const saveUnrecognizedButton = document.getElementById('saveUnrecognizedButton');
                        if (saveUnrecognizedButton) {
                            saveUnrecognizedButton.addEventListener('click', async () => {
                                saveUnrecognizedButton.disabled = true;
                                saveUnrecognizedButton.textContent = 'Saving...';
                                
                                try {
                                    const saveResponse = await fetch('/save_unrecognized', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                        },
                                        body: JSON.stringify({
                                            ocr_raw: ocrInfo.raw_text,
                                            corrected_name: ocrInfo.corrected_name,
                                            price: ocrInfo.price,
                                            color_identity: ocrInfo.color_identity,
                                            cmc: ocrInfo.cmc,
                                            type_line: ocrInfo.type_line,
                                            image_uri: ocrInfo.image_uri
                                        })
                                    });
                                    
                                    const saveResult = await saveResponse.json();
                                    
                                    if (saveResponse.ok) {
                                        scanStatusDiv.innerHTML = `
                                            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; margin: 10px 0; border-radius: 5px;">
                                                <strong>Unrecognized Card Saved!</strong><br>
                                                Card ID: ${saveResult.id}<br>
                                                This will help with debugging OCR issues.
                                            </div>
                                        `;
                                        fetchAndDisplayCards(); // Refresh the list
                                    } else {
                                        throw new Error(saveResult.error || 'Failed to save unrecognized card');
                                    }
                                } catch (error) {
                                    console.error('Error saving unrecognized card:', error);
                                    scanStatusDiv.innerHTML = `
                                        <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; margin: 10px 0; border-radius: 5px;">
                                            <strong>Error saving unrecognized card:</strong> ${error.message}
                                        </div>
                                    `;
                                }
                            });
                        }
                    } else {
                        // Other successful response
                        scanStatusDiv.textContent = result.message || 'Scan completed with unexpected result.';
                    }
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
            if (colorFilterInput) colorFilterInput.value = '';
            if (manaCostFilterInput) manaCostFilterInput.value = '';
            if (maxPriceFilterInput) maxPriceFilterInput.value = ''; // Add this line
            fetchAndDisplayCards();
        });
    }

    // Initial load of cards
    fetchAndDisplayCards();
});
