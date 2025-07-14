let selectedPeriod = 'J-1';
let selectedSite = null;
let selectedKpi = null;
let chart = null;

function setPeriod(period) {
    selectedPeriod = period;
    selectedSite = null;
    selectedKpi = null;

    // Affiche le select site, cache le select kpi
    document.getElementById("siteSelect").style.display = "";
    document.getElementById("kpiSelect").style.display = "none";

    document.getElementById("siteSelect").innerHTML = '<option selected disabled>Chargement des sites...</option>';
    document.getElementById("kpiSelect").innerHTML = '<option selected disabled>Choisir un KPI</option>';
    resetChart();

    fetchSites();
}
function fetchSites() {
    fetch(`/api/5gsites?period=${encodeURIComponent(selectedPeriod)}`)
        .then(res => res.json())
        .then(sites => {
            const siteSelect = document.getElementById("siteSelect");
            siteSelect.innerHTML = '<option selected disabled>Choisir un site</option>';
            if (Array.isArray(sites)) {
                sites.forEach(site => {
                    const opt = document.createElement("option");
                    opt.value = site;
                    opt.textContent = site;
                    siteSelect.appendChild(opt);
                });
            } else if (sites && typeof sites === 'object' && sites.error) {
                console.error("Réponse inattendue du backend :", sites);
                alert("Erreur lors du chargement des sites : " + (sites.error || "format inattendu"));
            } else {
                // Réponse vide ou format non attendu mais pas une erreur explicite
                console.warn("Aucun site disponible ou format inattendu :", sites);
                // Optionnel : afficher un message dans le select
                siteSelect.innerHTML = '<option selected disabled>Aucun site disponible</option>';
            }
        })
        .catch(err => {
            console.error("Erreur chargement des sites", err);
            alert("Impossible de charger les sites");
        });
}
function updateSectorList() {
        const site = document.getElementById("siteSelect").value;
    fetch(`/api/5gsecteurs?site=${encodeURIComponent(site)}`)

.then(res => res.json())
        .then(secteurs => {
            const sectorSelect = document.getElementById("sectorSelect");
            sectorSelect.innerHTML = '<option selected disabled>Choisir un secteur</option>';
            secteurs.forEach(sector => {
                const opt = document.createElement("option");
                opt.value = sector;
                opt.textContent = "Secteur " + sector;
                sectorSelect.appendChild(opt);
            });
            sectorSelect.style.display = "";
        });
}
function updateKpiList() {
    selectedSite = document.getElementById("siteSelect").value;
    selectSector = document.getElementById("sectorSelect").value;

    // Affiche le select kpi
    document.getElementById("kpiSelect").style.display = "";

    const defaultKpis5G = {
    "FT_NSA DRB Drop Rate(%)_Valeur":
        "Taux de coupure des DRB en NSA (%)",

    "FT_AVERAGE NB OF NSA DC USERS(number)_Valeur":
        "Nombre moyen d'utilisateurs en double connectivité NSA",

    "Radio Network Availability Rate (CU) (Cell level)(%)_Valeur":
        "Taux de disponibilité du réseau radio (CU, cellule) (%)",

    "5G Cell DL Throughput(Mbit/s)_Valeur":
        "Débit descendant moyen par cellule 5G (Mbit/s)"
};
    const kpiSelect = document.getElementById("kpiSelect");
    kpiSelect.innerHTML = '<option selected disabled>Choisir un KPI</option>';
    Object.entries(defaultKpis5G).forEach(([kpi, label]) => {
        const opt = document.createElement("option");
        opt.value = kpi;
        opt.textContent = label;
        kpiSelect.appendChild(opt);
    });
}


function drawChart(labels, datasetsOrValues) {
   const ctx = document.getElementById("kpiChart").getContext("2d");
    if (chart) chart.destroy();
    let dataObj;
    if (Array.isArray(datasetsOrValues) && datasetsOrValues.length && datasetsOrValues[0].data) {
        // Multi-lignes
        dataObj = {
            labels: labels,
            datasets: datasetsOrValues
        };
    } else {
        // Mono-ligne
        dataObj = {
            labels: labels,
            datasets: [{
                label: selectedKpi,
                data: datasetsOrValues,
                fill: false,
                borderColor: "rgb(75, 192, 192)",
                tension: 0.1
            }]
        };
    }
    chart = new Chart(ctx, {
        type: "line",
        data: dataObj,
        options: {
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Date' } },
                y: { title: { display: true, text: 'Valeur' } }
            }
        }
    });
    // Affiche les infos KPI
    document.getElementById("kpiInfo").style.display = "";
}

function updateKpiInfo(current, moyenne, variation, seuilDepasse, seuil, seuilMode) {
 document.getElementById("currentVal").textContent = `${current}`;
    document.getElementById("meanVal").textContent = `${moyenne}`;

    const varEl = document.getElementById("variationVal");
    const seuilVariation = 20;
    let color = "green";
    let icon = "";
    let msg = "";
    if (seuilDepasse) {
        color = "red";
        icon = "<i class='fas fa-exclamation-triangle' title='Seuil KPI dépassé'></i> ";
        msg = `⚠️ Seuil du KPI dépassé : au moins une valeur a franchi le seuil fixé (${seuil} - mode ${seuilMode === 'greater' ? '>' : '<'}).`;
    } else if (Math.abs(variation) > seuilVariation) {
        color = "orange";
        icon = "<i class='fas fa-exclamation-circle' title='Variation importante'></i> ";
        msg = `ℹ️ Variation importante (> ${seuilVariation}% par rapport à la moyenne).`;
    } else {
        msg = `✅ Valeurs dans la normale.`;
    }
    varEl.innerHTML = `${icon}${variation > 0 ? '🔺' : '🔻'} ${Math.abs(variation).toFixed(2)}%`;
    varEl.style.color = color;
    const infoEl = document.getElementById("kpiInfoMsg");
    infoEl.textContent = msg;
}

function resetChart() {
    if (chart) {
        chart.destroy();
        chart = null;
    }
    document.getElementById("kpiInfo").style.display = "none";
    document.getElementById("currentVal").textContent = "";
    document.getElementById("meanVal").textContent = "";
    document.getElementById("variationVal").textContent = "";
    document.getElementById("kpiInfoMsg").textContent = "";
}

function onSiteChange() {
    // Affiche le select KPI, cache le secteur
    document.getElementById("kpiSelect").style.display = "";
    document.getElementById("sectorSelect").style.display = "none";
    // Remplis le select KPI comme avant
    updateKpiList();
}

function onKpiChange() {
    const site = document.getElementById("siteSelect").value;
    const period = selectedPeriod || 'J-1';
    fetch(`/api/5gsecteurs?site=${encodeURIComponent(site)}&period=${encodeURIComponent(period)}`)
        .then(res => res.json())
        .then(secteursDict => {
            const sectorSelect = document.getElementById("sectorSelect");
            sectorSelect.innerHTML = '<option selected disabled>Choisir un secteur</option>';
            Object.keys(secteursDict).forEach(sector => {
                const opt = document.createElement("option");
                opt.value = sector;
                opt.textContent = "Secteur " + sector;
                sectorSelect.appendChild(opt);
            });
            sectorSelect.style.display = "";
            // Stocke le mapping secteur->cellules pour la suite
            window.secteursCellules = secteursDict;
        });
}

function onSectorChange() {
    const site = document.getElementById("siteSelect").value;
    const kpi = document.getElementById("kpiSelect").value;
    const secteur = document.getElementById("sectorSelect").value;
    const period = selectedPeriod || 'J-1';
    fetch("/api/kpi-5gdata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site, kpi, period, secteur })
    })
    .then(res => res.json())
    .then(data => {
        console.log("DEBUG data:", data);
        if (data.error) {
            alert("Erreur : " + data.error);
            return;
        }
        if (data.cell_series && data.cell_stats) {
            console.log("DEBUG cell_series:", data.cell_series);
            console.log("DEBUG dates:", data.dates);
            Object.entries(data.cell_stats).forEach(([cell, stats]) => {
                console.log(`Cellule ${cell} : variation=${stats.variation}, seuil dépassé=${stats.seuil_depasse}`);
            });
            const colorPalette = [
                '#db4a29', '#0066cc', '#28a745', '#ffc107', '#6f42c1', '#20c997', '#fd7e14', '#6610f2', '#e83e8c', '#17a2b8'
            ];
            const datasets = Object.entries(data.cell_series).map(([cell, values], idx) => ({
                label: cell,
                data: values,
                fill: false,
                borderColor: colorPalette[idx % colorPalette.length],
                tension: 0.1
            }));
            console.log("DEBUG datasets:", datasets);
            
            drawChart(data.dates, datasets);
            // Moyenne et variation sur toutes les valeurs affichées (hors null)
            
            const allValues = [].concat(...Object.values(data.cell_series)).filter(v => v !== null && v !== undefined);
            let moyenne = null;
            if (allValues.length > 1) {
                moyenne = allValues.slice(0, -1).reduce((a, b) => a + b, 0) / (allValues.length - 1);
            } else if (allValues.length === 1) {
                moyenne = allValues[0];
            }
            const current = allValues.length ? allValues[allValues.length - 1] : null;
            let variation = 0;
            if (moyenne !== null && current !== null && moyenne !== 0) {
                variation = ((current - moyenne) / moyenne) * 100;
            }
            updateKpiInfo(
                current,
                moyenne !== null ? moyenne.toFixed(2) : null,
                variation,
                false, // seuil_depasse non calculé ici
                null,
                null
            );
        } else {
            // Cas mono-ligne (fallback)
            const labels = data.cell_names && data.cell_names.length ? data.cell_names : data.dates;
            drawChart(labels, data.values);
            updateKpiInfo(data.current, data.moyenne, data.variation, data.seuil_depasse, data.seuil, data.seuil_mode);
        }
    });
}

document.addEventListener("DOMContentLoaded", function() {
    var runBtn = document.getElementById("runAnalysis5gBtn");
    if (runBtn) {
        runBtn.addEventListener("click", function() {
            document.getElementById("analysisBtns").style.display = "";
        });
    }
});