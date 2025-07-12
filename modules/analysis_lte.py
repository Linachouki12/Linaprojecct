from .date_separate import get_date_range, analyze_period
import os
import pandas as pd
from datetime import timedelta
# Configuration des KPI 4G
from .kpi_config import KPI_THRESHOLDS


def run_kpi_analysis(base_folder):
    """Lance l'analyse des KPI 4G"""
    all_files = collect_4g_files(base_folder)
    
    if not all_files:
        print("Aucun fichier 4G trouvé dans OSS Downloads/4G/")
        return
    
    
    min_date, max_date = get_date_range(all_files)
    print(f"\nPlage de dates disponible: {min_date} à {max_date}")
    
    # Définition des périodes basée sur la date max détectée
    analysis_periods = {
        'J-1': (max_date - timedelta(days=1), max_date),
        'J-7': (max_date - timedelta(days=7), max_date),
        'J-30': (max_date - timedelta(days=30), max_date),
        'Personnalisé': (min_date, max_date)
    }
    
    for period_name, date_range in analysis_periods.items():
        print(f"\nAnalyse pour {period_name} ({date_range[0]} à {date_range[1]})")
        results_df = analyze_period(all_files, date_range, is_5g=False)
        results_df = results_df[(results_df['Date'] >= date_range[0]) & (results_df['Date'] <= date_range[1])]
        if results_df is not None and not results_df.empty:
            print(f"   {len(results_df)} enregistrements trouvés - Génération du rapport...")
            generate_report(results_df, base_folder, period_name, date_range)
        else:
            print(" Aucune donnée valide trouvée")


def collect_4g_files(base_folder):
    """Collecte tous les fichiers 4G organisés dans la structure de dossiers"""
    all_files = [] # liste vide pour stocker les chemins compelts des fichiers 4G
    for root, dirs, files in os.walk(os.path.join(base_folder, "4G")):
        for file in files:
            if file.endswith('.xlsx') and not file.startswith('~$'):
                full_path = os.path.join(root, file)
                all_files.append(full_path)
    return all_files

def generate_report(results_df, base_folder, period_name, date_range):
    """Génère un rapport Excel avec mise en forme et statistiques"""
    reports_dir = os.path.join(base_folder,'Rapports_Analyse_4G')
    os.makedirs(reports_dir, exist_ok=True)
    start_str = date_range[0].strftime('%Y%m%d')
    end_str = date_range[1].strftime('%Y%m%d')
    

    report_name = f"Rapport_KPI_4G_{period_name}_{start_str}_{end_str}.xlsx"
    output_path = os.path.join(reports_dir, report_name)

    if os.path.exists(output_path):
        print(f"Fichier {report_name} existe déjà. Mise à jour...")
        # Lire l'ancien contenu
        old_df = pd.read_excel(output_path)
        # Concaténer l'ancien contenu et les nouvelles données
        updated_df = pd.concat([old_df, results_df], ignore_index=True)
    else:
        print(f"Création d'un nouveau fichier {report_name}...")
        # Sinon, juste utiliser les nouvelles données
        updated_df = results_df
    
    
    
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    results_df.to_excel(writer, sheet_name='Données', index=False)
    
    # Création feuille de synthèse
    workbook = writer.book
    summary_sheet = workbook.add_worksheet('Synthèse')
    title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
    summary_sheet.merge_range('A1:D1', f"Synthèse des KPI 4G - Période: {period_name}", title_format)
    summary_sheet.write('A2', f"Du: {date_range[0].strftime('%d/%m/%Y')}")
    summary_sheet.write('A3', f"Au: {date_range[1].strftime('%d/%m/%Y')}")
    
    stats = {
        #'Nombre total de mesures': len(results_df),
        'Nombre d\'anomalies': results_df['Anomalie'].value_counts().get('Oui', 0),
        'Nombre de congestions': results_df['Congestion'].value_counts().get('Oui', 0)
    }
    
    summary_sheet.write_column('A5', list(stats.keys()))
    summary_sheet.write_column('B5', list(stats.values()))
    
    # Mise en forme conditionnelle
    data_sheet = writer.sheets['Données']
    red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    
    for col_num, col_name in enumerate(results_df.columns):
        if col_name.endswith('_Statut'):
            data_sheet.conditional_format(
                1, col_num, len(results_df), col_num,
                {'type': 'text', 'criteria': 'containing', 'value': 'Dépassement', 'format': red_format}
            )
            data_sheet.conditional_format(
                1, col_num, len(results_df), col_num,
                {'type': 'text', 'criteria': 'containing', 'value': 'OK', 'format': green_format}
            )
            
            print(f"Rapport 4G enregistré à : {os.path.abspath(output_path)}")
    
    writer.close()
    print(f"Rapport 4G généré: {output_path}")
    #Analyse pour la 4G  

def analyze_kpis(df): 
    """Analyse les KPI selon les seuils définis pour un DataFrame"""
    results = []
    
    # Vérification des colonnes requises
    required_columns = ['Date', 'eNodeB Name', 'Cell Name', 'Cell FDD TDD Indication']
    for col in required_columns:
        if col not in df.columns:
            print(f"Colonne manquante: {col}")
            return pd.DataFrame()  # Retourne un DataFrame vide

    for index, row in df.iterrows():
        anomaly = False
        congestion = False
        kpi_results = {}
        
        for kpi, config in KPI_THRESHOLDS.items():
            # Recherche des colonnes correspondant au KPI
            matching_cols = [col for col in df.columns if kpi in col]
            if not matching_cols:
                continue
                
            actual_kpi = matching_cols[0]
            value = row.get(actual_kpi)
            
            if pd.isna(value):
                continue
                
            threshold = config['threshold']
            mode = config['mode']
            
            # Vérification des seuils
            if (mode == "greater" and value > threshold) or (mode == "less" and value < threshold):
                kpi_results[kpi] = (value, "Dépassement")
                anomaly = True
            else:
                kpi_results[kpi] = (value, "OK")
        
        # Détection de congestion
        required_for_congestion = [
            "FT_AVE 4G/LTE DL USER THRPUT without Last TTI(ALL) (KBPS)(kbit/s)",
            "L.ChMeas.PRB.DL.Avail", 
            "FT_AVERAGE NB OF CA UEs RRC CONNECTED(number)"
        ]
        
        if all(kpi in kpi_results and kpi_results[kpi][1] == "Dépassement" for kpi in required_for_congestion):
            congestion = True
        
        # Construction du résultat
        result_row = {
            'Date': row['Date'],
            'eNodeB Name': row['eNodeB Name'],
            'Cell FDD TDD Indication': row['Cell FDD TDD Indication'],
            'Cell Name': row['Cell Name'],
            'Congestion': "Oui" if congestion else "Non",
            'Anomalie': "Oui" if anomaly else "Non"
        }
        
        # Ajout des valeurs et statuts des KPI
        for kpi in KPI_THRESHOLDS:
            if kpi in kpi_results:
                result_row[f"{kpi}_Valeur"] = kpi_results[kpi][0]
                result_row[f"{kpi}_Statut"] = kpi_results[kpi][1]
            else:
                result_row[f"{kpi}_Valeur"] = None
                result_row[f"{kpi}_Statut"] = "Non Mesuré"
        
        results.append(result_row)
    
    return pd.DataFrame(results)   