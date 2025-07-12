console.log("Chargement du script map.js");
window.selectedSites = new Set();

document.addEventListener('DOMContentLoaded', function() {
    const distanceForm = document.getElementById("distance-form");
    console.log('distanceForm:', distanceForm);
    const hiddenInput = document.getElementById("selected-sites");
    const calculateBtn = document.getElementById("calculate-btn");
    if (calculateBtn) calculateBtn.disabled = true; // Désactiver au chargement
    

    if (distanceForm) {
        distanceForm.addEventListener("submit", function(e) {
            console.log(">>> Formulaire soumis (JS fetch)");
            e.preventDefault(); // Empêche le rechargement de la page

            const selected = Array.from(selectedSites);
            if (selected.length === 0) {
                alert("Veuillez d'abord sélectionner un cluster de sites sur la carte.");
                return;
            }

            // Appel AJAX pour lancer le calcul côté backend sur la route dédiée
            fetch('/calculate_distances', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ site_names: selected })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    highlightOvershootSectors(selected);
                } else {
                    alert('Erreur lors du calcul de distance : ' + (data.error || ''));
                }
            })
            .catch(err => {
                alert('Erreur lors du calcul de distance : ' + err);
            });
        });
    }

    const mapElement = document.getElementById('map');
    if (!mapElement) {
        console.log('Élément map non trouvé sur cette page');
        return;
    }


    mapElement.innerHTML = '<div class="map-loading"><i class="fas fa-spinner fa-spin"></i><span>Chargement de la carte...</span></div>';

    let map;
    let sitesLayer, sectorsLayer;
    let globalSitesData = null;
    let drawSource; // Source pour la couche de dessin
    let drawInteraction; // Variable pour garder une référence à l'interaction de dessin active

    // Styles pour les sites
    const defaultStyle = new ol.style.Style({
        text: new ol.style.Text({
            text: '📍', // Utilisation de l'emoji
            font: '16px sans-serif',
            offsetY: -12 // Ajuster pour que la pointe de l'emoji soit sur le point
        })
    });
    const selectedStyle = new ol.style.Style({                                                                                                                                                                                                                                      
        // Combinaison de l'emoji et d'un cercle en arrière-plan pour la sélection
        image: new ol.style.Circle({
            radius: 12,
            fill: new ol.style.Fill({
                color: 'rgba(0, 204, 0, 0.4)' // Halo vert semi-transparent
            })
        }),
        text: new ol.style.Text({
            text: '📍',
            font: '24px sans-serif',
            offsetY: -12
        })
    });

    function waitForOpenLayers(callback) {
        if (typeof ol !== 'undefined') callback();
        else setTimeout(() => waitForOpenLayers(callback), 100);
    }

    async function loadSitesData() {
        try {
            const response = await fetch('/get_sites_data');
            const data = await response.json();
            if (data.error) {
                console.error('Erreur chargement sites:', data.error);
                mapElement.innerHTML = `<div class="map-error"><i class="fas fa-exclamation-triangle"></i> Erreur: ${data.error}</div>`;
                return null;
            }
            return data;
        } catch (error) {
            console.error('Erreur requête:', error);
            return null;
        }
    }

    function createSiteMarkers(sitesData) {
        const features = sitesData.map(site => {
            const feature = new ol.Feature({
                geometry: new ol.geom.Point(ol.proj.fromLonLat([site.longitude, site.latitude])),
                name: site.site_id,
                type: 'site'
            });
            feature.setStyle(defaultStyle);
            return feature;
        });
        return features;
    }

    function createSectorPolygons(sitesData) {
        return sitesData.flatMap(site => 
            site.sectors.map(sector => {
                const feature = new ol.Feature({
                    geometry: new ol.geom.Polygon([sector.sector_points.map(p => ol.proj.fromLonLat(p))]),
                    cell_names: sector.cell_names,
                    azimuth: sector.azimuth,
                    type: 'sector'
                });
                return feature;
            })
        );
    }

    async function displaySitesOnMap() {
        const sitesData = await loadSitesData();
        if (!sitesData) {
            console.error('Impossible de charger les données des sites');
            return;
        }

        globalSitesData = sitesData;

        const siteFeatures = createSiteMarkers(sitesData);
        const sectorFeatures = createSectorPolygons(sitesData);

        sitesLayer = new ol.layer.Vector({
            source: new ol.source.Vector({ features: siteFeatures })
        });
        sectorsLayer = new ol.layer.Vector({
            source: new ol.source.Vector({ features: sectorFeatures }),
            style: new ol.style.Style({
                fill: new ol.style.Fill({ color: 'rgba(0, 102, 204, 0.3)' }),
                stroke: new ol.style.Stroke({ color: '#0066cc', width: 1 })
            })
        });

        map.addLayer(sectorsLayer);
        map.addLayer(sitesLayer);

        addPopupInteraction();
        setupMapControls();
        // SUPPRIME : plus de rappel lors du changement de résolution
        // map.getView().on('change:resolution', function() {
        //     if (globalSitesData) {
        //         const newSectorFeatures = createSectorPolygons(globalSitesData);
        //         sectorsLayer.getSource().clear();
        //         sectorsLayer.getSource().addFeatures(newSectorFeatures);
        //     }
        // });
        if (siteFeatures.length > 0) {
            const extent = sitesLayer.getSource().getExtent();
            map.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });
        }
        console.log(`${sitesData.length} sites affichés sur la carte`);
    }

    function addPopupInteraction() {
        const popupElement = document.createElement('div');
        popupElement.className = 'ol-popup';
        popupElement.innerHTML = '<div id="popup-content"></div><div id="popup-closer" class="ol-popup-closer"></div>';
        document.body.appendChild(popupElement);

        const popupOverlay = new ol.Overlay({
            element: popupElement,
            positioning: 'bottom-center',
            stopEvent: false,
            offset: [0, -10]
        });

        map.addOverlay(popupOverlay);

        setTimeout(() => {
            const popupCloser = document.getElementById('popup-closer');
            if (popupCloser) {
                popupCloser.onclick = function() {
                    popupOverlay.setPosition(undefined);
                    popupCloser.blur();
                    return false;
                };
            }
        }, 100);

        map.on('click', function(evt) {
            if (overshootPopupActive) {
                overshootPopupActive = false; // On reset le flag pour le prochain clic
                return; // On n'affiche pas la popup générique
            }
            const feature = map.forEachFeatureAtPixel(evt.pixel, f => f);
            if (feature) {
                const coordinates = evt.coordinate;
                const props = feature.getProperties();
                const popupContent = document.getElementById('popup-content');

                if (props.type === 'site') {
                    const content = `
                        <div style="padding: 10px;">
                            <h4 style="margin: 0 0 10px 0; color: #cc0000;">
                                <i class="fas fa-map-marker-alt"></i> Site: ${props.name}
                            </h4>
                            <p><strong>Coordonnées:</strong><br>Lat: ${ol.proj.toLonLat(coordinates)[1].toFixed(6)}<br>Lon: ${ol.proj.toLonLat(coordinates)[0].toFixed(6)}</p>
                        </div>
                    `;
                    popupContent.innerHTML = content;
                    popupOverlay.setPosition(coordinates);

                } else if (props.type === 'sector') {
                    // Correction : garantir une liste de noms
                    const cellNames = Array.isArray(props.cell_names) ? props.cell_names : [props.cell_names || ''];
                    const content = `
                        <div style="padding: 10px;">
                            <h4 style="margin: 0 0 10px 0; color: #0066cc;">
                                <i class="fas fa-route"></i> Cellules:
                            </h4>
                            <ul style="padding-left: 18px; margin: 0;">
                                ${cellNames.map(name => `<li>${name}</li>`).join('')}
                            </ul>
                            <p><strong>Azimuth:</strong> ${props.azimuth}°</p>
                        </div>
                    `;
                    popupContent.innerHTML = content;
                    popupOverlay.setPosition(coordinates);
                }
            } else {
                popupOverlay.setPosition(undefined);
            }
        });
    }

    function initMap() {
        console.log('Initialisation de la carte...');
        try {
            const loadingIndicator = mapElement.querySelector('.map-loading');
            if(loadingIndicator) loadingIndicator.remove();
            
            map = new ol.Map({
                target: 'map',
                layers: [ new ol.layer.Tile({ source: new ol.source.OSM() }) ],
                view: new ol.View({
                    center: ol.proj.fromLonLat([9, 34]),
                    zoom: 6, minZoom: 5, maxZoom: 18
                })
            });

            displaySitesOnMap();
            setupSelectionToolbar();
            setupMapControls();
            setupSearchControl(); // Activer la recherche

        } catch (error) {
            console.error('Erreur initMap:', error);
        }
    }
    
    function setupMapControls() {
        const showSitesBtn = document.getElementById('show-sites');
        const showSectorsBtn = document.getElementById('show-sectors');
        const resetViewBtn = document.getElementById('reset-view');

        // Robustesse : attendre que les couches existent
        if (!sitesLayer || !sectorsLayer) return;

        // Initialiser l'état des boutons selon la visibilité réelle
        if (showSitesBtn) {
            showSitesBtn.classList.toggle('active', sitesLayer.getVisible());
            showSitesBtn.onclick = function() {
                if (!sitesLayer) return;
                sitesLayer.setVisible(!sitesLayer.getVisible());
                this.classList.toggle('active', sitesLayer.getVisible());
            };
        }
        if (showSectorsBtn) {
            showSectorsBtn.classList.toggle('active', sectorsLayer.getVisible());
            showSectorsBtn.onclick = function() {
                if (!sectorsLayer) return;
                sectorsLayer.setVisible(!sectorsLayer.getVisible());
                this.classList.toggle('active', sectorsLayer.getVisible());
            };
        }
        if (resetViewBtn) {
            resetViewBtn.onclick = function() {
                if (sitesLayer && sitesLayer.getSource().getFeatures().length > 0) {
                    map.getView().fit(sitesLayer.getSource().getExtent(), {
                        padding: [50, 50, 50, 50],
                        duration: 1000
                    });
                }
            };
        }
    }

    function setupSelectionToolbar() {
        const buttons = {
            polygon: document.getElementById('select-polygon'),
            circle: document.getElementById('select-circle'),
            box: document.getElementById('select-box'),
            clear: document.getElementById('clear-selection-btn'),
        };

        // Initialiser la source et la couche de dessin une seule fois
        drawSource = new ol.source.Vector();
        const drawLayer = new ol.layer.Vector({
            source: drawSource,
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'rgba(0, 102, 255, 0.2)'
                }),
                stroke: new ol.style.Stroke({
                    color: '#0066ff',
                    width: 2
                }),
            }),
        });
        map.addLayer(drawLayer);

        function deactivateAllButtons() {
            Object.values(buttons).forEach(btn => {
                if (btn) btn.classList.remove('active');
            });
        }
        
        function addDrawInteraction(type, geometryFunction) {
            map.removeInteraction(drawInteraction);
            deactivateAllButtons();
            
            if (!type) return;

            const activeBtn = type === 'Box' ? buttons.box : buttons[type.toLowerCase()];
            if (activeBtn) activeBtn.classList.add('active');

            drawInteraction = new ol.interaction.Draw({
                source: drawSource, // Utiliser la source de dessin partagée
                type: type === 'Box' ? 'Circle' : type,
                geometryFunction: geometryFunction,
            });

            drawInteraction.on('drawstart', function() {
                drawSource.clear(); // Effacer la sélection précédente au début d'un nouveau dessin
            });

            drawInteraction.on('drawend', function(event) {
                const geometry = event.feature.getGeometry();
                selectFeaturesByGeometry(geometry);
                map.removeInteraction(drawInteraction);
                deactivateAllButtons();
            });

            map.addInteraction(drawInteraction);
        }
        
        function selectFeaturesByGeometry(geometry) {
            selectedSites.clear();
            sitesLayer.getSource().forEachFeature(feature => {
                if (geometry.intersectsExtent(feature.getGeometry().getExtent())) {
                    selectedSites.add(feature.get('name'));
                    feature.setStyle(selectedStyle);
                }
            });
            updateSelectionUI();
            console.log('Sites sélectionnés:', Array.from(selectedSites));
        }

        function updateSelectionUI() {
            const hiddenInput = document.getElementById("selected-sites");
            const counter = document.getElementById("selected-sites-count");
            const calculateBtn = document.getElementById("calculate-btn");
            if (hiddenInput) hiddenInput.value = Array.from(selectedSites).join(',');
            if (counter) counter.textContent = selectedSites.size;
            if (calculateBtn) calculateBtn.disabled = selectedSites.size === 0;
        }

        if(buttons.polygon) buttons.polygon.addEventListener('click', () => addDrawInteraction('Polygon'));
        if(buttons.circle) buttons.circle.addEventListener('click', () => addDrawInteraction('Circle'));
        if(buttons.box) buttons.box.addEventListener('click', () => addDrawInteraction('Box', ol.interaction.Draw.createBox()));

        if(buttons.clear) {
            buttons.clear.addEventListener('click', () => {
                map.removeInteraction(drawInteraction);
                deactivateAllButtons();
                drawSource.clear(); // Vider la couche de dessin
                selectedSites.clear();
                // Réinitialiser le style de tous les sites
                if (sitesLayer) {
                    sitesLayer.getSource().forEachFeature(feature => {
                        feature.setStyle(defaultStyle);
                    });
                }
                updateSelectionUI();
                console.log('Sélection effacée.');
            });
        }
    }

    function setupSearchControl() {
        const searchInput = document.getElementById('map-search-input');
        const searchButton = document.getElementById('map-search-button');

        const search = () => {
            const query = (searchInput.value || '').trim().toUpperCase();
            if (!query) return;
            // Log debug
            // Recherche sur les 8 premiers caractères, insensible à la casse et aux espaces
            const siteFeature = sitesLayer.getSource().getFeatures().find(
                feature => ((feature.get('name') || '').substring(0, 8).replace(/\s+/g, '').toUpperCase() === query.replace(/\s+/g, ''))
            );
            if (siteFeature) {
                const geometry = siteFeature.getGeometry();
                const coordinates = geometry.getCoordinates();
                map.getView().animate({
                    center: coordinates,
                    zoom: 16,
                    duration: 1000
                });
                // Effet de "flash" pour la mise en évidence
                const flashStyle = new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 15,
                        fill: new ol.style.Fill({ color: 'rgba(255, 0, 0, 0.7)' }),
                        stroke: new ol.style.Stroke({ color: '#fff', width: 2 })
                    }),
                    text: new ol.style.Text({
                        text: '📍',
                        font: '16px sans-serif',
                        offsetY: -12
                    })
                });
                const previousStyle = siteFeature.getStyle();
                siteFeature.setStyle(flashStyle);
                setTimeout(() => {
                    siteFeature.setStyle(previousStyle);
                }, 1500);
            } else {
                alert(`Le site "${query}" n'a pas été trouvé.\nSites disponibles: ${allNames.join(', ')}`);
            }
        };
        if (searchButton) searchButton.onclick = search;
        if (searchInput) searchInput.onkeydown = (e) => { if (e.key === 'Enter') search(); };
    }

    // Ajoute cette fonction utilitaire pour remettre tous les secteurs en bleu
    function resetSectorsToDefault() {
        if (sectorsLayer) {
            sectorsLayer.getSource().getFeatures().forEach(feature => {
                feature.setStyle(new ol.style.Style({
                    fill: new ol.style.Fill({ color: 'rgba(0, 102, 204, 0.3)' }),
                    stroke: new ol.style.Stroke({ color: '#0066cc', width: 1 })
                }));
            });
        }
    }

    // Modifie highlightOvershootSectors pour ne colorer en rouge que les secteurs overshooteux du cluster
    async function highlightOvershootSectors(selectedSites) {
        if (!Array.isArray(selectedSites) || selectedSites.length === 0) return;
        try {
            // 1. Remet tous les secteurs en bleu (par défaut)
            resetSectorsToDefault();

            const response = await fetch('/get_overshoot_sectors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ site_names: selectedSites })
            });
            const data = await response.json();
            if (data.error) {
                alert('Erreur overshoot: ' + data.error);
                return;
            }
            window.overshootResults = data;

            // Vérifie si tous les tableaux sont vides
            const hasAnyOvershoot = Object.values(data).some(arr => Array.isArray(arr) && arr.length > 0);

            if (!hasAnyOvershoot) {
                alert("Aucun overshoot détecté sur le cluster sélectionné.");
                // masquer tous les surlignages ici
                resetSectorsToDefault();
                return;
            }
            // Récupérer tous les noms de cellules overshooteuses (source et target)
            const overshootCells = new Set();
            Object.values(data).forEach(cellPairs => {
                cellPairs.forEach(pair => {
                    if (pair.source) overshootCells.add(pair.source);
                    if (pair.target) overshootCells.add(pair.target);
                });
            });
            // Surligner en rouge uniquement les secteurs overshooteux du cluster sélectionné
            if (sectorsLayer) {
                sectorsLayer.getSource().getFeatures().forEach(feature => {
                    const cellNames = feature.get('cell_names') || [];
                    // On ne colore en rouge que si le secteur appartient à un site sélectionné
                    const belongsToSelectedSite = selectedSites.some(siteId => {
                        return cellNames.some(cell => (cell || '').startsWith(siteId));
                    });
                    const match = cellNames.some(cell => overshootCells.has(cell));
                    if (belongsToSelectedSite && match) {
                        feature.setStyle(new ol.style.Style({
                            fill: new ol.style.Fill({ color: 'rgba(255,0,0,0.5)' }),
                            stroke: new ol.style.Stroke({ color: '#ff0000', width: 2 })
                        }));
                    }
                });
            }
            highlightAllOvershootSources();
        } catch (e) {
            alert('Erreur lors de la récupération des secteurs overshooteurs: ' + e);
        }
    }

    // Ajoute une gestion du clic sur les sites pour vérifier s'ils sont dans le cluster sélectionné
    function addSiteClickValidation() {
        map.on('click', function(evt) {
            const feature = map.forEachFeatureAtPixel(evt.pixel, f => f);
            if (feature && feature.get('type') === 'site') {
                const siteId = feature.get('name');
                if (!selectedSites.has(siteId)) {
                    alert('Ce site ne fait pas partie du cluster sélectionné. Veuillez sélectionner un nouveau cluster pour une nouvelle analyse.');
                }
            }
        });
    }

    let overshootSectorFocus = false;
    let overshootPopupActive = false;

    function addSectorClickOvershootHighlight() {
        map.on('click', function(evt) {
            const feature = map.forEachFeatureAtPixel(evt.pixel, f => f);
            if (feature && feature.get('type') === 'sector') {
                const cellNames = feature.get('cell_names') || [];
                // 1. Cherche la cellule source cliquée qui est overshooteuse
                let sourceCell = null;
                let foundPairs = [];
                // On cherche la première cellule du secteur qui est une source dans overshootResults
                for (const cell of cellNames) {
                    const pairs = Object.values(window.overshootResults || {}).flat().filter(
                        pair => (cell || '').trim().toUpperCase() === (pair.source || '').trim().toUpperCase()
                    );
                    if (pairs.length > 0) {
                        sourceCell = cell;
                        foundPairs = pairs;
                        console.log('Cellule source trouvée:', sourceCell, 'Couples:', foundPairs);
                        break;
                    }
                }
                if (sourceCell && foundPairs.length > 0) {
                    resetSectorsToDefault(); // Remet tout en bleu
                    // Surligne le secteur source en rouge
                    feature.setStyle(new ol.style.Style({
                        fill: new ol.style.Fill({ color: 'rgba(255,0,0,0.5)' }),
                        stroke: new ol.style.Stroke({ color: '#ff0000', width: 2 })
                    }));
                    // Surligne les secteurs target en violet
                    sectorsLayer.getSource().getFeatures().forEach(f => {
                        const targetNames = f.get('cell_names') || [];
                        foundPairs.forEach(pair => {
                            if (targetNames.some(cell => (cell || '').trim().toUpperCase() === (pair.target || '').trim().toUpperCase())) {
                                f.setStyle(new ol.style.Style({
                                    fill: new ol.style.Fill({ color: 'rgba(255, 0, 238, 0.36)' }),
                                    stroke: new ol.style.Stroke({ color: '#8000ff', width: 2 })
                                }));
                            }
                        });
                    });
                    // Affiche le popup...
                    let html = `<div style="font-size:14px;"><b>Overshoot détecté !</b><ul style="margin:0;padding-left:18px;">`;
                    foundPairs.forEach(pair => {
                        html += `<li>
                            <span style='color:gray'>Date: ${pair.Date}</span><br>
                            <span style='color:red'>Source: ${sourceCell}</span><br>
                            <span style='color:orange'>Target: ${pair.target}</span>
                        </li>`;
                    });
                    html += '</ul></div>';
                    console.log('Affichage popup overshoot', html);
                    showCustomPopup(feature.getGeometry().getInteriorPoint().getCoordinates(), html);
                    overshootPopupActive = true;
                    return; // IMPORTANT : ne pas faire de reset ou de highlightAllOvershootSources() après
                }
            }
            // Si on clique ailleurs, on remet l'affichage général
            highlightAllOvershootSources();
        });
    }

    // Fonction utilitaire pour afficher un popup custom (à adapter selon ton système de popup)
    function showCustomPopup(coordinates, html) {
        let popupElement = document.getElementById('custom-overshoot-popup');
        if (!popupElement) {
            popupElement = document.createElement('div');
            popupElement.id = 'custom-overshoot-popup';
            popupElement.className = 'ol-popup';
            popupElement.style.position = 'fixed';
            popupElement.style.zIndex = 9999;
            popupElement.style.background = 'white';
            popupElement.style.color = 'black';
            popupElement.style.padding = '8px 14px';
            popupElement.style.border = '2px solid #888';
            popupElement.style.borderRadius = '8px';
            popupElement.style.maxWidth = '220px';
            popupElement.style.fontSize = '13px';
            popupElement.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
            document.body.appendChild(popupElement);
        }
        popupElement.innerHTML = html;
        // Positionne le popup à gauche de la carte
        const mapRect = document.getElementById('map').getBoundingClientRect();
        popupElement.style.left = `${mapRect.left + 20}px`; // 20px à droite du bord gauche de la carte
        popupElement.style.top = `${mapRect.top + 20}px`;   // 20px sous le haut de la carte
        popupElement.style.display = 'block';
        popupElement.style.visibility = 'visible';
        popupElement.style.opacity = 1;
        console.log('Popup HTML:', popupElement.innerHTML);
        // Ferme le popup au prochain clic
        setTimeout(() => {
            document.addEventListener('click', function handler() {
                popupElement.style.display = 'none';
                document.removeEventListener('click', handler);
            });
        }, 100);
    }

    function highlightAllOvershootSources() {
        resetSectorsToDefault();
        if (!window.overshootResults) return;
        const allSources = new Set();
        Object.values(window.overshootResults).flat().forEach(pair => {
            allSources.add(pair.source);
        });
        sectorsLayer.getSource().getFeatures().forEach(f => {
            const cellNames = f.get('cell_names') || [];
            if (cellNames.some(cell => allSources.has(cell))) {
                f.setStyle(new ol.style.Style({
                    fill: new ol.style.Fill({ color: 'rgba(255,0,0,0.5)' }),
                    stroke: new ol.style.Stroke({ color: '#ff0000', width: 2 })
                }));
            }
        });
    }

    // Appelle cette fonction après l'initialisation de la carte
    waitForOpenLayers(function() {
        initMap();
        addSiteClickValidation();
        addSectorClickOvershootHighlight();
    });

    // --- LOGIQUE D'EXPORTATION ---
    const exportButton = document.getElementById('btn-export-cells');
    if (exportButton) {
        exportButton.addEventListener('click', function () {
            if (!drawSource || drawSource.getFeatures().length === 0) {
                alert("Veuillez d'abord dessiner une zone de sélection (cluster) sur la carte.");
                return;
            }

            if (!sectorsLayer) {
                alert("La couche des secteurs n'est pas disponible. Veuillez recharger la page.");
                return;
            }

            const selectionGeometry = drawSource.getFeatures()[0].getGeometry();

            const cellNames = sectorsLayer.getSource().getFeatures()
                .filter(sectorFeature => {
                    const sectorExtent = sectorFeature.getGeometry().getExtent();
                    return selectionGeometry.intersectsExtent(sectorExtent);
                })
                .flatMap(sectorFeature => sectorFeature.get('cell_names') || []);

            if (cellNames.length === 0) {
                alert("Aucune cellule trouvée dans le cluster sélectionné.");
                return;
            }

            // Créer un formulaire dynamique pour envoyer les données
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/export_and_download_cells';
            
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'cells';
            hiddenInput.value = JSON.stringify(cellNames);
            form.appendChild(hiddenInput);

            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        });
    }

    // Ajout du bouton de mesure
    const measureBtn = document.getElementById('measure-btn');
    const distanceValue = document.getElementById('distance-value');

    let drawMeasure = null;
    let measureFeature = null;
    let measureLayer = new ol.layer.Vector({
      source: new ol.source.Vector(),
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({
          color: '#db4a29',
          width: 3
        })
      })
    });
    map.addLayer(measureLayer);

    measureBtn.onclick = function() {
      if (drawMeasure) {
        map.removeInteraction(drawMeasure);
        drawMeasure = null;
        measureBtn.classList.remove('active');
        distanceValue.textContent = '';
        measureLayer.getSource().clear();
        return;
      }
      measureBtn.classList.add('active');
      measureLayer.getSource().clear();

      drawMeasure = new ol.interaction.Draw({
        source: measureLayer.getSource(),
        type: 'LineString',
        maxPoints: 2
      });
      map.addInteraction(drawMeasure);

      drawMeasure.on('drawstart', function(evt) {
        measureFeature = evt.feature;
        evt.feature.getGeometry().on('change', function(e) {
          const geom = e.target;
          const length = ol.sphere.getLength(geom);
          distanceValue.textContent = 'Distance : ' + (length / 1000).toFixed(3) + ' km';
        });
      });

      drawMeasure.on('drawend', function(evt) {
        map.removeInteraction(drawMeasure);
        drawMeasure = null;
        measureBtn.classList.remove('active');
        // La distance reste affichée
      });
    };

    // Optionnel : style pour le bouton actif
    const measureBtnStyle = document.createElement('style');
    measureBtnStyle.innerHTML = `
    #measure-btn.active {
      background: #db4a29;
      color: #fff;
      border-radius: 4px;
    }
    `;
    document.head.appendChild(measureBtnStyle);

    // Ajoute le CSS pour le tooltip si besoin
    const style = document.createElement('style');
    style.innerHTML = `
    .ol-tooltip {
      position: absolute;
      background: rgba(255,255,255,0.8);
      border-radius: 4px;
      padding: 4px 8px;
      border: 1px solid #333;
      color: #222;
      font-size: 14px;
      white-space: nowrap;
      pointer-events: none;
    }
    .ol-tooltip-measure {
      font-weight: bold;
      color: #db4a29;
    }
    `;
    document.head.appendChild(style);
});
