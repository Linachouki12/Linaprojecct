import os
import pandas as pd

def merge_process(base_folder):
    distancefile=os.path.join(base_folder,"LTE_Distances")
    ''' if not os.path.exists(os.path.join(distancefile, distance_filename)):
        print(f"Le fichier {distance_filename} est introuvable dans {distancefile}.")
        print("Veuillez revenir à l'étape 11-Calcul de distance entre les sites avec la distance souhaitée")
        return
    '''
    for site_name in os.listdir(distancefile):
        site_path=os.path.join(distancefile,site_name)
        if not os.path.isdir(site_path):
            continue
        sitename=os.path.basename(site_path)
        for tech_type in ["FDD", "TDD"]:
            tech_path = os.path.join(site_path, tech_type)
            print(f"Dossier trouvé {tech_path}")
            if not os.path.isdir(tech_path):
                continue
            
            distance_files = []
            tech_file = None


            for file in os.listdir(tech_path):
                
                if "Distance" in file and file.endswith(".xlsx"):
                    distance_files.append(os.path.join(tech_path,file))

                elif file.startswith(f"{sitename}") and file.endswith(".xlsx"):
                    tech_file=os.path.join(tech_path, file )
                    
                if not distance_files or not tech_file:
                    print(f" Fichiers manquants pour {site_name} / {tech_type}")
                    continue
                try:
                    df_kpi = pd.read_excel(tech_file)
                    all_distance_dfs=[]
                    for dis_file in distance_files:
                        xls=pd.ExcelFile(dis_file)
                        for sheet_name in xls.sheet_names:
                            df_dist = pd.read_excel(dis_file, sheet_name=sheet_name)  
                            all_distance_dfs.append(df_dist)
                            
                    df_distance=pd.concat(all_distance_dfs, ignore_index=True)

                    required_dist_columns={"CellName_Src", "CellName_Neig", "Distance(km)"}
                    required_kpi_cols = {"Date", "Local cell name", "Target Cell Name", "L.HHO.NCell.ExecSuccOut"}

                    if not required_dist_columns.issubset(df_distance.columns) or not required_kpi_cols.issubset(df_kpi.columns):
                        print(f" Colonnes manquantes dans les fichiers de {tech_path}")
                        return
                    
                    df_kpi=df_kpi.rename(columns={
                        "Local cell name": "CellName_Src",
                        "Target Cell Name": "CellName_Neig"
                            })
                    
                    df_kpi["CellName_Src"] = df_kpi["CellName_Src"].astype(str).str.strip()
                    df_kpi["CellName_Neig"] = df_kpi["CellName_Neig"].astype(str).str.strip()
                    df_distance["CellName_Src"] = df_distance["CellName_Src"].astype(str).str.strip()
                    df_distance["CellName_Neig"] = df_distance["CellName_Neig"].astype(str).str.strip()
                    
                    merged=pd.merge(
                        df_kpi, df_distance[['CellName_Src', 'CellName_Neig', 'Distance(km)']], on=['CellName_Src','CellName_Neig'], how='inner'
                    )
                    print(merged.columns.tolist())


                    final_df = merged[["Date", "CellName_Src", "CellName_Neig", "Distance(km)", "L.HHO.NCell.ExecSuccOut"]]
                    final_df = final_df.sort_values(by="Distance(km)")
                    output_file=os.path.join(tech_path,f"{site_name}_{tech_type}_merged.xlsx")
                    final_df.to_excel(output_file, index=False)


                    print(f"Fusion réussie : {output_file}")

                except Exception as e:
                        print(f" Erreur lors de la lecture des fichiers dans {tech_path} : {e}")
                        continue
