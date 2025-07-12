import os
import pandas as pd
import re
from datetime import datetime

def compare_compare(base_folder):
   
   base_4g_folder=os.path.join(base_folder,"4G")

   for site_name in os.listdir(base_4g_folder):
        site_path=os.path.join(base_4g_folder,site_name)
        if not os.path.isdir(site_path):
            continue
        h_files=[]
        f_files=[]
        for root,_, files in os.walk(site_path):

            for file in files:
                full_path=os.path.join(root,file)
                if "L1800.xlsx" in file:
                    h_files.append(full_path)
                    print(f"[{site_name}] Fichiers L1800 trouvés: {h_files}")
                elif "L800.xlsx" in file:
                    f_files.append(full_path)
                    # Debug
                    print(f"[{site_name}] Fichiers L800 trouvés: {f_files}")
            if not h_files or not f_files:
                print(f"[{site_name}] Aucun fichier L1800 ou L800 trouvé")
                continue
            #préparation de rapport final
            all_results=[]

            for h_file in h_files:
                try:
                    tech_id = os.path.basename(h_file).split('_')[0]
                    cell_type = "CELL_FDD" if "CELL_FDD" in h_file else "CELL_TDD" if "CELL_TDD" in h_file else None
                    if not cell_type:
                        print(f"Type inconnu pour le fichier : {h_file}")
                    site_folder = os.path.dirname(h_file)
                    # Trouver le fichier F correspondant (prendre le premier match)
                    matching_f_files = [f for f in f_files if tech_id in os.path.basename(f) and os.path.dirname(f) == site_folder]
                    
                    if not matching_f_files:
                        print(f"{site_name} Aucun fichier F correspondant trouvé pour le site {tech_id}")
                        continue

                    f_file = matching_f_files[0]

                    h_sheets = pd.read_excel(h_file, sheet_name=None)
                    f_sheets = pd.read_excel(f_file, sheet_name=None)

                    def extract_sheet_number(sheet_name):
                        match = re.search(r'(\d+)$', sheet_name)
                        return int(match.group(1)) if match else None
                    h_sheets_by_num = {extract_sheet_number(name): name for name in h_sheets}
                    f_sheets_by_num = {extract_sheet_number(name): name for name in f_sheets}
                    common_sheet_nums = set(h_sheets_by_num.keys()) & set(f_sheets_by_num.keys())

                    for num in sorted(common_sheet_nums):
                        h_sheet_name = h_sheets_by_num[num]
                        f_sheet_name = f_sheets_by_num[num]   
                            
                        h_df = h_sheets[h_sheet_name]
                        f_df = f_sheets[f_sheet_name]
                        if 'eNodeB Name' in h_df.columns:
                            enodeb_full= str(h_df['eNodeB Name'].dropna().iloc[0])
                            enodeb_short=enodeb_full[:8]
                        else:
                            enodeb_short='Inconnu'

                    
                        # Vérifier la présence du KPI
                        kpi_name = "L.Traffic.ActiveUser.DL.Avg"

                        if kpi_name not in h_df.columns or kpi_name not in f_df.columns:
                            continue
                        
                        #calcul de moyenne
                        h_mean = h_df[kpi_name].mean()
                        f_mean = f_df[kpi_name].mean()
                        delta = h_mean - f_mean

                        result = {
                            'Technologie': tech_id,
                            'eNodeB':enodeb_short,
                            'Avg_AU_DL_L1800_BAND': h_mean,
                            'Avg_AU_DL_L800_BAND': f_mean,
                            'Delta_H-F': delta,
                            'Statut': 'OK' if delta >= 1 else 'ALERTE',
                        }
                        all_results.append(result)

                except Exception as e:
                    print(f"[{site_name} Erreur lors du traitement du fichier {h_file}: {str(e)}")
                    continue
                
            if all_results:
                results_df=pd.DataFrame(all_results)
                output_file = os.path.join(site_folder, f"Equilibrage de charge L800-L1800_{datetime.now().strftime('%Y%m%d')}.xlsx")
                writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
                workbook = writer.book

                positive_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                negative_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

                results_df.to_excel(writer, sheet_name='Résultats', index=False)
                worksheet = writer.sheets['Résultats']
        
                statut_col = results_df.columns.get_loc('Statut')
                for row in range(1, len(results_df)+1):
                    Statut = results_df.iloc[row-1]['Statut']
                    

                    if Statut =='OK':
                        worksheet.write(row, statut_col, Statut, positive_format)
                    else:
                        worksheet.write(row, statut_col, Statut, negative_format)

                writer.close()

                print(f"Rapport généré:[{site_name}] {output_file}")
            if not all_results:
                print("Aucune donnée à comparer trouvée.") 
