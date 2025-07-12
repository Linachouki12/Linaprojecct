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
function updateKpiList() {
    selectedSite = document.getElementById("siteSelect").value;
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
function loadKpiData() {
    selectedKpi = document.getElementById("kpiSelect").value;

    fetch("/api/kpi-data5g", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            period: selectedPeriod,
            site: selectedSite,
            kpi: selectedKpi
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert("Erreur : " + data.error);
            return;
        }
        const labels = data.cell_names && data.cell_names.length ? data.cell_names : data.dates;
        drawChart(data.dates, data.values);
        updateKpiInfo(data.current, data.moyenne, data.variation, data.seuil_depasse, data.seuil, data.seuil_mode);
    })
    .catch(err => {
        console.error("Erreur chargement des données KPI", err);
        alert("Erreur lors du chargement des données.");
    });
}

function drawChart(labels, values) {
    const ctx = document.getElementById("kpiChart").getContext("2d");

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: selectedKpi,
                data: values,
                fill: false,
                borderColor: "rgb(75, 192, 192)",
                tension: 0.1
            }]
        },
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

document.addEventListener("DOMContentLoaded", function() {
    var runBtn = document.getElementById("runAnalysisBtn");
    if (runBtn) {
        runBtn.addEventListener("click", function() {
            document.getElementById("analysis5gBtns").style.display = "";
        });
    }
});