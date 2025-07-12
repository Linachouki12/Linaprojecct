from .kpi_config import suffix_mapping
from .kpi_config import extract_cell_suffix
import pandas as pd
import os






def process_5g_file(base_folder, filepath, tech_type):
    tech_type="5G"
    try:
        # Lecture du fichier selon le format
        if filepath.endswith('.csv'): # vérification d'extension de fichier 
            df = pd.read_csv(filepath) #création d une DF pour que pandas puisse lire le fichier
        elif filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            print(f"Format non supporté : {filepath}") # dans le cas ou le fichier n'est pas .csv ou .xlsx
            return
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {filepath}: {e}")
        return

    
    if 'gNodeB Name' not in df.columns or 'Cell Name' not in df.columns:
        print(f"Colonnes requises manquantes dans : {filepath}")
        return
    #site_id = str(df['gNodeB Name'].dropna().iloc[0])[:8]
    df['Site_ID'] = df['gNodeB Name'].astype(str).str[:8]
    df['Cell_Suffix'] = df['Cell Name'].apply(extract_cell_suffix) # Création de colonne Cell_Suffix 
    for site_id in df['Site_ID'].dropna().unique():
        site_df=df[df['Site_ID']==site_id]
        site_folder = os.path.join(base_folder, tech_type, site_id)
        os.makedirs(site_folder, exist_ok=True)
        #df['Cell_Suffix'] = df['Cell Name'].apply(extract_cell_suffix) # Création de colonne Cell_Suffix 
        df_cband = site_df[site_df['Cell_Suffix'].str.startswith('c', na=False)] #filtrage selon le suffix demandé 'c' et ignore les valeurs manquantes 
        df_dss = site_df[site_df['Cell_Suffix'].str.startswith('e', na=False)]
        cband_folder = os.path.join(site_folder, 'TDD') 
        dss_folder = os.path.join(site_folder, 'FDD')
        os.makedirs(cband_folder, exist_ok=True)
        os.makedirs(dss_folder, exist_ok=True)
    
        def process_5G_technology(df_tech, folder, tech_name): #df contient les data de tech , chemin de dossier de destination , nom de technologie 
            if df_tech.empty: #vérification que df est vide 
                return
            df_tech['Cell_Number'] = df_tech['Cell Name'].str.extract(r'([c|e]\d+)$') #accéder à la colonne Cell, extraire une partie de texte, chercher que ce soit e ou c, les enregistrer dans une nouvelle colonne 
            base_name = os.path.basename(filepath).split('.')[0]#extraire le nom de fichier de chemin complet et prendre le premier éément apres le '.'
            short_name = base_name.split("KPI")[0] + "KPI" if "KPI" in base_name else base_name
            output_file = os.path.join(folder, f"{short_name}_{tech_name}.xlsx")
            
            with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer: # création d une Writer excel
                for cell_num in df_tech['Cell_Number'].unique():
                    if pd.notna(cell_num): # vérifier que c'est un nombre 
                        sheet_df = df_tech[df_tech['Cell_Number'] == cell_num] #filtrage selon le nombre de cellule 
                        sheet_name = f"Cell_{cell_num}"
                        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False) #écrire les données dans les feuilles 
            
            print(f"[{site_id} 5G] {tech_name} sauvegardé : {os.path.basename(output_file)}")
    
        process_5G_technology(df_cband, cband_folder, "C_BAND") # appel de la fonction 
        process_5G_technology(df_dss, dss_folder, "DSS")
            
    os.remove(filepath)

def process_4g_file(base_folder, filepath, tech_type):
    tech_type="4G"
    try:
        # Lecture du fichier selon le format
        if filepath.endswith('.csv'): # vérification d'extension de fichier 
            df = pd.read_csv(filepath) #création d une DF pour que pandas puisse lire le fichier
        elif filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            print(f"Format non supporté : {filepath}") # dans le cas ou le fichier n'est pas .csv ou .xlsx
            return
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {filepath}: {e}")
        return

    
    
    if 'Cell FDD TDD Indication' not in df.columns or 'Cell Name' not in df.columns:
        print(f"Colonnes requises manquantes dans : {filepath}")
        return
    df['Cell FDD TDD Indication'] = df['Cell FDD TDD Indication'].astype(str).str.strip().str.upper()
    df['Cell_Suffix'] = df['Cell Name'].apply(extract_cell_suffix)

    if 'eNodeB Name' not in df.columns:
        #site_id = str(df['eNodeB Name'].dropna().iloc[0])[:8]
        print(f"Colonne eNodeB manquante dans : {filepath}")
        return
    df['Site_ID']= df['eNodeB Name'].astype(str).str[:8]
    
    for site_id in df['Site_ID'].dropna().unique():
        site_df=df[df['Site_ID']==site_id]
        
        subfolder = os.path.join(base_folder, tech_type, site_id)
        os.makedirs(subfolder, exist_ok=True)

        group_fdd_folder = os.path.join(subfolder, 'CELL_FDD')
        group_tdd_folder = os.path.join(subfolder, 'CELL_TDD')
        os.makedirs(group_fdd_folder, exist_ok=True)
        os.makedirs(group_tdd_folder, exist_ok=True)

        df_fdd = site_df[site_df['Cell FDD TDD Indication'] == 'CELL_FDD']
        df_tdd = site_df[site_df['Cell FDD TDD Indication'] == 'CELL_TDD']

        def process_group_by_suffix(df_filtered, parent_folder, tech_type, site_id):
            df_filtered = df_filtered.copy()
            df_filtered['Suffix_Letter'] = df_filtered['Cell_Suffix'].str[0].str.upper()

            for letter in df_filtered['Suffix_Letter'].unique():
                group_df = df_filtered[df_filtered['Suffix_Letter'] == letter]
                base_name = os.path.basename(filepath).split('.')[0]
                short_name = base_name.split("KPI")[0] + "KPI"
                suffix_value = suffix_mapping.get(letter.lower(), letter)
                file_name = f"{short_name}_{tech_type}_L{suffix_value}.xlsx"
                output_file = os.path.join(parent_folder, file_name)
                
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    for cell_suffix in group_df['Cell_Suffix'].unique():
                        sheet_df = group_df[group_df['Cell_Suffix'] == cell_suffix]
                        sheet_name = f"Cell_{cell_suffix}"
                        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

                print(f"[{site_id} {tech_type}] L {suffix_value} sauvegardé : {file_name}")

        process_group_by_suffix(df_fdd, group_fdd_folder, "FDD", site_id)
        process_group_by_suffix(df_tdd, group_tdd_folder, "TDD", site_id)

# Supprimer le fichier téléchargé après traitement
    os.remove(filepath)
