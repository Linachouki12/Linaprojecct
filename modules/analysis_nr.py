from .date_separate import get_date_range, analyze_period
from .kpi_config import KPI_THRESHOLDS_5G
import pandas as pd 
from datetime import timedelta
from .kpi_config import extract_m_suffix
import os


def run_unified_5g_analysis(base_folder):

    all_files = collect_5g_files(base_folder)
    if not all_files:
        print("Aucun fichier 5G trouvé dans OSS Downloads/5G/")
        return
    
    min_date, max_date = get_date_range(all_files)
    print(f"\nPlage de dates disponible: {min_date} à {max_date}")
    
    # Définition des périodes basée sur la date max détectée
    analysis_periods = {
        'J-1': (max_date - timedelta(days=1), max_date),
        'J-7': (max_date - timedelta(days=7), max_date),
        'J-30': (max_date - timedelta(days=30), max_date)
        #'Personnalisé': (min_date, max_date)
    }
    
    for period_name, date_range in analysis_periods.items():
        print(f"\nAnalyse pour {period_name} ({date_range[0]} à {date_range[1]})")
        results_df = analyze_period(all_files, date_range, is_5g=True)
        
        if results_df is not None and not results_df.empty:
            print(f"   {len(results_df)} enregistrements trouvés - Génération du rapport...")
            generate_unified_5g_report(results_df, base_folder, period_name, date_range)
        else:
            print(" Aucune donnée 5G valide trouvée")

def collect_5g_files(base_folder):
    #collection de tous les fichiers 5G
    all_files=[]
    for root, dirs, files in os.walk(os.path.join(base_folder, "5G")):
        if 'TDD' in root or 'FDD' in root :
            for file in files:
                if file.endswith('.xlsx'):
                    full_path = os.path.join(root, file)
                    all_files.append(full_path)
    return all_files


def generate_unified_5g_report(results_df, base_folder, period_name, date_range):

    reports_dir = os.path.join(base_folder, 'Rapports_Analyse_5G')
    os.makedirs(reports_dir, exist_ok=True)
    start_str = date_range[0].strftime('%Y%m%d')
    end_str = date_range[1].strftime('%Y%m%d')
    

    report_name = f"Rapport_KPI_5G_{period_name}_{start_str}_{end_str}.xlsx"
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
    summary_sheet.merge_range('A1:D1', f"Synthèse des KPI 5G - Période: {period_name}", title_format)
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
            
            print(f"Rapport 5G enregistré à : {os.path.abspath(output_path)}")
    
    writer.close()
    print(f"Rapport 5G généré: {output_path}")
    
def analyze_5g_kpis(df):
    
    results=[]
    required_columns=['Date', 'gNodeB Name', 'Cell Name']
    
    for col in required_columns:
        if col not in df.columns:
            print(f"Colonne manquante: {col}")
            return pd.DataFrame()
    
    for index, row in df.iterrows():
        anomaly = False
        congestion = False
        kpi_results = {}

        technology = "C_BAND" if row['Cell_Suffix'].startswith('c') else "DSS"

        for kpi, config in KPI_THRESHOLDS_5G.items():
            matching_cols = [ col for col in df.columns if kpi in col]
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
        
        m_suffix= extract_m_suffix(row['Cell Name'])
        cell_name = row['Cell Name']
        cell_name_upper = cell_name.upper()
        
        
        if m_suffix:
            dl_throughput=kpi_results.get("5G Cell DL Throughput(Mbit/s)",(None,))[0]
            nsa_user=kpi_results.get("FT_AVERAGE NB OF NSA DC USERS(number)",(None,))[0]
            
            if (nsa_user is not None and nsa_user >38) or (dl_throughput is not None and dl_throughput< 28):
                congestion=True
        elif "8T8R" in cell_name_upper:
            if (dl_throughput is not None and dl_throughput < 28) or (nsa_user is not None and nsa_user >= 11):
                congestion = True
        '''required_for_congestion = [
            "5G Cell DL Throughput(Mbit/s)", 
            "FT_AVERAGE NB OF NSA DC USERS(number)"
        ]
         #à regler
        if all(kpi in kpi_results and kpi_results[kpi][1] == "Dépassement" for kpi in required_for_congestion):
            congestion = True'''
        
        # Construction du résultat
        result_row = {
            'Date': row['Date'],
            'gNodeB Name': row['gNodeB Name'],
            'Cell Name': row['Cell Name'],
            'Technology':technology,
            'Congestion': "Oui" if congestion else "Non",
            'Anomalie': "Oui" if anomaly else "Non"
        }
        
        # Ajout des valeurs et statuts des KPI
        for kpi in KPI_THRESHOLDS_5G:
            if kpi in kpi_results:
                result_row[f"{kpi}_Valeur"] = kpi_results[kpi][0]
                result_row[f"{kpi}_Statut"] = kpi_results[kpi][1]
            else:
                result_row[f"{kpi}_Valeur"] = None
                result_row[f"{kpi}_Statut"] = "Non Mesuré"
        
        results.append(result_row)
    
    return pd.DataFrame(results) 
