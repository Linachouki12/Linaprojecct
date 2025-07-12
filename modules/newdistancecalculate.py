import os
from math import radians, sin, cos, acos
import pandas as pd
import math
import glob


def supprimer_fichiers_distance(base_folder, site_names):
    distance_folder = os.path.join(base_folder, "LTE_Distances")
    for site in site_names:
        pattern = os.path.join(distance_folder, site, "*Distance*.xlsx")
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"Fichier supprimé : {file_path}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {file_path} : {e}")
                
                                       
def bearing_from_to_deg(lat1, lon1, lat2, lon2):
    """Retourne l'azimut (angle) en degrés du point (lat1, lon1) vers (lat2, lon2)"""
    lat1 = math.radians(float(lat1))
    lat2 = math.radians(float(lat2))
    diff_long = math.radians(float(lon2) - float(lon1))
    x = math.sin(diff_long) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(diff_long)
    )
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360) % 360

def bearing_category(bearing_deg):
    if 0 <= bearing_deg < 90:
        return '0-90'
    elif 90 <= bearing_deg < 180:
        return '90-180'
    elif 180 <= bearing_deg < 270:
        return '180-270'
    elif 270 <= bearing_deg < 360:
        return '270-360'
    else:
        return 'invalide'

def custom_distance(lon1, lat1, lon2, lat2):
    """Calcule la distance en km entre deux points GPS"""
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    lon_diff_rad = radians(lon1 - lon2)
    
    distance = acos(
        sin(lat1_rad) * sin(lat2_rad) + 
        cos(lat1_rad) * cos(lat2_rad) * cos(lon_diff_rad)
    ) * 6371  # Rayon de la Terre en km
    return distance

def calculate_distance(base_folder, site_names):
    cell_plan_file = os.path.join(base_folder, "LTE_cell_Plan_HU_MasterFile.xlsx")
    ho_file=os.path.join(base_folder,'HO_BAR_3G3G.xlsx' )
    distance_folder = os.path.join(base_folder, "LTE_Distances")
    os.makedirs(distance_folder, exist_ok=True)
    
    try:
        df_ho = pd.read_excel(ho_file)
        df_cp = pd.read_excel(cell_plan_file)
        df_cp.columns = df_cp.columns.str.strip()
        df_ho.columns = df_ho.columns.str.strip()
        df_cp['Site_name'] = df_cp['CellName'].str[:8]
        df_cp['Azimuth'] = pd.to_numeric(
        df_cp['Azimuth'].astype(str).str.replace('°', '', regex=False).str.strip(), errors='coerce' ).fillna(0)
    
    
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel: {e}")
        return

    for site in site_names:
        df_ho['eNodeB_Short'] = df_ho['eNodeB Name'].str[:8]
        df_site_ho = df_ho[df_ho['eNodeB_Short'] == site]
        if df_site_ho.empty:
            print(f"Aucune ligne HO trouvée pour {site}")
            continue
        site_dir = os.path.join(distance_folder, site)
        os.makedirs(site_dir, exist_ok=True)
        ho_output = os.path.join(site_dir, f"{site}_HO.xlsx")
        df_site_ho.to_excel(ho_output, index=False)
        print(f"HO pour le site {site} sauvegardé dans {ho_output}")


        source_cells = df_cp[df_cp['CellName'].str[:8] == site]
        if source_cells.empty:
            print(f"Aucune cellule trouvée pour le site {site} dans le cell plan.")
            continue

        try:
            results = []
            for _, row in df_site_ho.iterrows():
                neighbor_name = str(row['Target Cell Name'])[:8]
                neighbor_cells = df_cp[df_cp['CellName'].str.startswith(neighbor_name)]
                ho_date = row['Date']
                hho_count = row['L.HHO.NCell.ExecAttOut']
                hho_count2 = row['L.HHO.NCell.ExecSuccOut']

                if neighbor_cells.empty:
                    continue

                for _, cell_row in neighbor_cells.iterrows():
                    for _, src_row in source_cells.iterrows():

                        try:
                            src_lon = float(str(src_row['Longitude_Sector']).replace(',', '.'))
                            src_lat = float(str(src_row['Latitude_Sector']).replace(',', '.'))
                            src_az = float(src_row['Azimuth'])
                            nb_lon = float(str(cell_row['Longitude_Sector']).replace(',', '.'))
                            nb_lat = float(str(cell_row['Latitude_Sector']).replace(',', '.'))
                            nb_az = float(cell_row['Azimuth'])
                            distance = custom_distance(src_lon, src_lat, nb_lon, nb_lat)
                            bearing = bearing_from_to_deg(nb_lat, nb_lon, src_lat, src_lon)
                            az_diff = (nb_az - bearing + 180) % 360 - 180
                            is_valid = abs(az_diff) <= 32
                            if site == neighbor_name:
                                continue
                            if is_valid:
                                
                                results.append({
                                    'Date': ho_date,
                                    'Site_Src': site,
                                    'CellName_Src': src_row['CellName'],
                                    'Longitude_Src': src_lon,
                                    'Latitude_Src': src_lat,
                                    'Azimuth_Src': src_az,
                                    'Site_Neig': neighbor_name,
                                    'CellName_Neig': cell_row['CellName'],
                                    'Longitude_Neig': nb_lon,
                                    'Latitude_Neig': nb_lat,
                                    'Azimuth_Neig': nb_az,
                                    'Distance_km': round(distance, 2),
                                    'Angle_diff': round(az_diff, 2),
                                    'L.HHO.NCell.ExecAttOut': hho_count,
                                   'L.HHO.NCell.ExecSuccOut' : hho_count2

                                })
                        except Exception as ex:
                            print(f"Erreur lors du calcul pour {neighbor_name}: {ex}")
                            continue
            if results:
                results.sort(key=lambda x: x['Distance_km'])
                df_results = pd.DataFrame(results)
                df_results['Success_Rate(%)'] = df_results.apply( lambda row: round((row['L.HHO.NCell.ExecSuccOut'] / row['L.HHO.NCell.ExecAttOut']) * 100, 2)
                            if row['L.HHO.NCell.ExecAttOut'] != 0 else 0.0,axis=1
                       )

                results_file = os.path.join(site_dir, f"{site}_Valid_Distance.xlsx")
                df_results.to_excel(results_file, index=False)
                print(f"{site} → {len(results)} lignes valides enregistrées dans {results_file}")
            else:
                print(f"{site} → Aucune ligne valide trouvée après filtrage.")

        except Exception as e:
            print(f"Erreur traitement {site} : {e}")                    

    return True