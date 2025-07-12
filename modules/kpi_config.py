import os
import fnmatch
import pandas as pd
KPI_THRESHOLDS_5G = {
   
        "FT_NSA DRB Drop Rate(%)": {"threshold": 5, "mode": "greater"},
        "FT_AVERAGE NB OF NSA DC USERS(number)": {"threshold": 38, "mode": "greater"},
        "Radio Network Availability Rate (CU) (Cell level)(%)": {"threshold": 95, "mode": "less"},
        "5G Cell DL Throughput(Mbit/s)": {"threshold": 28, "mode": "less"}
}

KPI_THRESHOLDS = {
    "FT_4G/LTE DROP CALL RATE": {"threshold": 2, "mode": "greater"},
    "FT_AVE 4G/LTE DL USER THRPUT without Last TTI(ALL) (KBPS)(kbit/s)": {"threshold": 4000, "mode": "less"},
    "L.ChMeas.PRB.DL.Avail": {"threshold": 90, "mode": "greater"},
    "FT_AVERAGE NB OF CA UEs RRC CONNECTED(number)": {"threshold": 2, "mode": "greater"},
    "FT_PHYSICAL RESOURCE BLOCKS LOAD DL(%)": {"threshold": 70, "mode": "greater"},
    "FT_UL.Interference": {"threshold": -110, "mode": "greater"}
    }

suffix_mapping = {
    'l': '2100',
    'h': '1800',
    'f': '800',
    'j': '2nd1800'  # Ajoutez une valeur pour J si nécessaire
}

def extract_cell_suffix(cell_name):
    return cell_name.split('_')[-1].lower() #découpage en liste et prendre la dernière partie et la rendre en min
def extract_m_suffix(cell_name):
    parts=cell_name.split('_')
    if len(parts)>=2:
        m_part=parts[-2].upper()
        if m_part.startswith('M') and m_part[1:].isdigit():
            return m_part
    return None


def load_report_file(base_folder, period):
    reports_dir = os.path.join(base_folder,'Rapports_Analyse_4G')

    file_map = {
        'J-1': 'Rapport_KPI_4G_J-1_*.xlsx',
        'J-7': 'Rapport_KPI_4G_J-7_*.xlsx',
        'J-30': 'Rapport_KPI_4G_J-30_*.xlsx'
    }
    pattern = file_map.get(period)
    if not pattern:
        raise ValueError("Période invalide")
    
    folder = os.path.join(base_folder, reports_dir)
    for file in os.listdir(folder):
        if fnmatch.fnmatch(file, pattern):
            return pd.read_excel(os.path.join(folder, file))
    raise FileNotFoundError("Fichier de rapport introuvable")

def load_report5g_file(base_folder, period):
    reports_dir = os.path.join(base_folder,'Rapports_Analyse_5G')

    file_map = {
        'J-1': 'Rapport_KPI_5G_J-1_*.xlsx',
        'J-7': 'Rapport_KPI_5G_J-7_*.xlsx',
        'J-30': 'Rapport_KPI_5G_J-30_*.xlsx'
    }
    pattern = file_map.get(period)
    if not pattern:
        raise ValueError("Période invalide")
    
    folder = os.path.join(base_folder, reports_dir)
    for file in os.listdir(folder):
        if fnmatch.fnmatch(file, pattern):
            return pd.read_excel(os.path.join(folder, file))
    raise FileNotFoundError("Fichier de rapport introuvable")