import os
import pandas as pd


def separate_site_id(base_folder):
    cellplan_path = os.path.join(base_folder, "LTE_cell_Plan_HU_MasterFile.xlsx")
    
    if cellplan_path.endswith('.csv'):
            df=pd.read_csv(cellplan_path, sep='\t')
    elif cellplan_path.endswith('.xlsx'):
        df=pd.read_excel(cellplan_path)
    else:
        print("Format de fichier non supporté")
        return False
    if 'CellName' not in df.columns and 'SiteID' not in df.columns:
        print("Les colonnes CellName et SiteID sont introuvables dans le fichier ")
        return False
    df['Site']=df['CellName'].str.extract(r'^([A-Za-z]{3}_\d{4})')[0]
    result_df = pd.DataFrame ({
            'Site': df['CellName'].astype(str).str[:8],
            'SiteID': df['SiteID']
        })
    result_df = result_df.drop_duplicates()
    output_file=os.path.join(base_folder, "ID_Sites.xlsx")
    result_df.to_excel(output_file, index=False)

    print ("Fichier généré avec succès")
    print(f"Nombre de sites disponibles: {len(result_df)}")
    