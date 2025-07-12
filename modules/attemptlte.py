import os
import pandas as pd


def get_suffix(cell_name):
    if isinstance(cell_name, str):
        parts = cell_name.strip().split('_')
        if parts:
            return parts[-1][0].lower()  
        
    return ''

def classify_suffix(suffix):
    if suffix in {'l', 'h', 'j', 'f'} :
        return 'FDD'
    elif suffix in  {'g', 'k', 'p'} :
        return 'TDD'
    return None

def read_file(file_path):
    try:
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        else:
            return pd.read_excel(file_path)
    except Exception as e:
        print(f" Erreur lors de la lecture de {file_path} : {e}")
        return None


def process_all_files(base_folder, folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith(('.xlsx', '.xls', '.csv')):
            file_path = os.path.join(folder_path, filename)
            df = read_file(file_path)
            if df is None:
                continue

        required_columns = ['eNodeB Name', 'Local cell name']
        if not all(col in df.columns for col in required_columns):
            print(f"Fichier {filename} ignoré : colonnes manquantes.")
            #continue  
        
        df['Site_ID'] = df['eNodeB Name'].astype(str).str[:8]
        unique_sites = df['Site_ID'].unique()
        print(f"Sites détectés dans {filename}: {list(unique_sites)}")
        for site in unique_sites:
                site_df = df[df['Site_ID'] == site]
                site_folder = os.path.join(base_folder, "LTE_Distances", site)
                print(f"chemin de dossier site : {site_folder}")
                if not os.path.isdir(site_folder):
                        print(f" Dossier LTE_Distances/{site} non trouvé.")
                        continue
                
                fdd_path = os.path.join(site_folder, "FDD")
                tdd_path = os.path.join(site_folder, "TDD")
                os.makedirs(fdd_path, exist_ok=True)
                os.makedirs(tdd_path, exist_ok=True)
                site_df['Suffix'] = site_df['Local cell name'].apply(get_suffix)
                fdd_df=pd.DataFrame()
                tdd_df=pd.DataFrame()

                
                for suffix, group in site_df.groupby('Suffix'):
                    tech_type = classify_suffix(suffix)
                    if tech_type == 'FDD':
                        fdd_df = pd.concat([fdd_df, group])
                    elif tech_type == 'TDD':
                        tdd_df = pd.concat([tdd_df, group])
                    else:
                        print(f"Suffixe inconnu '{suffix}' pour site {site} dans fichier {filename}")

                if not fdd_df.empty:
                    output_path = os.path.join(fdd_path, f"{site}_FDD.xlsx")
                    fdd_df.drop(columns=['Site_ID', 'Suffix']).to_excel(output_path, index=False)
                    print(f"Fichier FDD sauvegardé : {output_path}")

                if not tdd_df.empty:
                    output_path = os.path.join(tdd_path, f"{site}_TDD.xlsx")
                    tdd_df.drop(columns=['Site_ID', 'Suffix']).to_excel(output_path, index=False)
                    print(f"Fichier TDD sauvegardé : {output_path}")
    return True