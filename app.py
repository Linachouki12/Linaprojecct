'''Configuration de la base de l'application Web
Définition des routes (URLs) et les fonctions associés 
Point d'entrée pour lancer l'application '''





from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
import math
import os
import io
import json
from flask import send_file
import shutil
from werkzeug.utils import secure_filename
import pandas as pd
# Importez vos modules comme avant
from modules.download import process_4g_file
from modules.download import process_5g_file
from modules.kpi_config import load_report_file
from modules.kpi_config import load_report5g_file
from modules.analysis_lte import run_kpi_analysis
from modules.analysis_nr import run_unified_5g_analysis
from modules.comparecell_lte import compare_compare
from modules.id_site_file import separate_site_id
from modules.globdistance import calculate_distance #supprimer_fichiers_distance
from modules.attemptlte import process_all_files
from modules.merge import merge_process
from modules.overshoot_extract import extract_overshoot_cells
from modules.kpi_config import KPI_THRESHOLDS
from modules.kpi_config import KPI_THRESHOLDS_5G

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_key_123')
# Configuration
app.config['BASE_FOLDER'] = os.path.join(os.path.dirname(__file__), 'WORKSPACE') #dossier principal de travail
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['BASE_FOLDER'], 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls', 'csv'}

# Créer les dossiers nécessaires
os.makedirs(app.config['BASE_FOLDER'], exist_ok=True)
#os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

#Page d'accueil ( route principale )
@app.route('/')
def index():
    return render_template('index.html') #affichage de page index.html




@app.route('/download/<path:filename>')
def downloadfile(filename):
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/download/<path:filename>')
def download_file1(filename):
    # Look in the 5G reports directory
    directory = os.path.join(app.config['BASE_FOLDER'], 'Rapports_Analyse_5G')
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/download_comparison/<site>/<filename>')
def download_comparison(site, filename):
    dir_path = os.path.join(app.config['BASE_FOLDER'], '4G', site, 'CELL_FDD')
    return send_from_directory(dir_path, filename, as_attachment=True)

@app.route('/option1', methods=['GET', 'POST'])
def option1():
    
    if request.method == 'POST':
        # Traitement pour l'option 1
        folder_4g = os.path.join(app.config['BASE_FOLDER'], "4G")
        
        # Vérifier si les dossiers existent déjà
        if os.path.exists(folder_4g) :
            # Analyse directe
            run_kpi_analysis(app.config['BASE_FOLDER'])
            compare_compare(app.config['BASE_FOLDER'])
            flash("Analyses effectuées avec succès (fichiers existants)", "success")
        else:
            # Traitement des fichiers uploadés
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Organiser les fichiers
                    prefix_upper = filename[:2].upper()
                    try:
                        if 'LTE' in prefix_upper or '4G' in prefix_upper:
                            process_4g_file(app.config['BASE_FOLDER'], filepath, "4G")
                    except Exception as e:
                        flash(f"Erreur lors du traitement de {filename}: {str(e)}", "error")
            
            # Exécuter les analyses
            if os.path.exists(folder_4g):
                run_kpi_analysis(app.config['BASE_FOLDER'])
                compare_compare(app.config['BASE_FOLDER'])
            
            flash("Traitement et analyses terminés avec succès", "success")
        
        return redirect(url_for('option1'))
    
    reports_folder = os.path.join(app.config['BASE_FOLDER'], '4G')
    results_folder = os.path.join('WORKSPACE', 'Rapports_Analyse_4G')
    available_reports = []
    site_reports=[]

    if os.path.exists(results_folder):
        for root, dirs, files in os.walk(results_folder):
            for file in files:
                if file.endswith('.xlsx') or file.endswith('.csv'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, start='.')
                    available_reports.append({
                        'filename': relative_path.replace('\\', '/'),  # important pour Flask
                        'display_name': os.path.basename(file)
                    })

    if os.path.exists(reports_folder):
        # Utiliser un dict pour ne garder qu'un fichier par site
        site_file_map = {}
        for site_name in os.listdir(reports_folder):
            site_path = os.path.join(reports_folder, site_name)
            if not os.path.isdir(site_path):
                continue
            tech_path = os.path.join(site_path, 'CELL_FDD')
            if not os.path.isdir(tech_path):
                continue
            # Chercher tous les fichiers Equilibrage pour ce site
            eq_files = [f for f in os.listdir(tech_path) if f.startswith("Equilibrage de charge L800-L1800") and f.endswith(".xlsx")]
            if eq_files:
                # Prendre le dernier fichier (par ordre alphabétique, donc le plus récent si le nom contient la date)
                eq_files.sort()
                last_file = eq_files[-1]
                site_file_map[site_name] = {
                    'site_name': site_name,
                    'filename': last_file,
                    'display_name': last_file
                }
        site_reports = list(site_file_map.values())

    rapports_existants = os.path.exists(results_folder) and any(
        file.endswith('.xlsx') or file.endswith('.csv')
        for root, dirs, files in os.walk(results_folder)
        for file in files
    )
    return render_template('option1.html', available_reports=available_reports, comparison_reports=site_reports, rapports_existants=rapports_existants)

# Nouvelle route pour la liste des sites
@app.route('/api/sites', methods=['GET'])
def get_sites_list():
    period = request.args.get('period')
    try:
        df = load_report_file(app.config['BASE_FOLDER'], period)
        sites = df['eNodeB Name'].dropna().unique().tolist()
        return jsonify(sites)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    

@app.route('/api/5gsites', methods=['GET'])
def get_5gsites_list():
    period = request.args.get('period')
    try:
        df = load_report5g_file(app.config['BASE_FOLDER'], period)
        sites = df['gNodeB Name'].dropna().unique().tolist()
        return jsonify(sites)
    except Exception as e:
        return jsonify({'error': str(e)}), 400




@app.route('/api/secteurs',methods=['GET'])
def get_secteurs():
    site = request.args.get('site')
    period = request.args.get('period')
    print(f"DEBUG: site={site}, period={period}")
    df = load_report_file(app.config['BASE_FOLDER'], period) 
    print(f"DEBUG: Colonnes: {df.columns}")

    df['last_digit'] = df[df['eNodeB Name']== site]['Cell Name'].str.extract(r'(\d)$')

    secteurs = df.groupby('last_digit')['Cell Name'].apply(lambda group: list(set(group))).to_dict() 
    
    print(f"DEBUG: Secteurs trouvés: {secteurs}")

    return jsonify(secteurs)


@app.route('/api/kpi-data', methods=['GET', 'POST'])
def get_kpi_data():
    if request.method == 'POST':
        data = request.get_json()
        period = data.get('period')
        site = data.get('site')
        kpi = data.get('kpi')
        secteur = data.get('secteur')
    else:  # GET
        period = request.args.get('period')
        site = request.args.get('site')
        kpi = request.args.get('kpi')
        secteur = request.args.get('secteur')
    try:
        df = load_report_file(app.config['BASE_FOLDER'], period)
        df_site = df[df['eNodeB Name'] == site].copy() if site else df.copy()
        print("DEBUG: site  sélectionné:", df_site)
       
        if secteur:
    # Recalcule le mapping secteur -> cellules à partir de df_site
            secteur_dict = {}
            for cell in df_site['Cell Name'].dropna().unique():
                suffix = cell.strip().split('_')[-1]  # Extrait le "h1", "l1", etc.
                secteur_num = suffix[-1]              # Extrait le dernier chiffre (ex: "1")
                secteur_dict.setdefault(secteur_num, []).append(cell)

            # Récupère les cellules du secteur demandé
            cellules_du_secteur = secteur_dict.get(str(secteur), [])
            print("DEBUG: Cellules du secteur sélectionné:", cellules_du_secteur)

            # Filtrer le DataFrame pour ne garder que les lignes du secteur sélectionné
            df_secteur = df_site[df_site['Cell Name'].isin(cellules_du_secteur)].copy()
            print("DEBUG: DataFrame du secteur sélectionné:", df_secteur)
            print(df_secteur.head())  # affiche un aperçu
            if not df_secteur.empty:
                min_date = df_secteur['Date'].min()
                max_date = df_secteur['Date'].max()
                all_dates = pd.date_range(min_date, max_date, freq='D').strftime('%Y-%m-%d').tolist()
            else:
                all_dates = []
            dates = all_dates
            print("Dates sélectionnés:", all_dates)
        df_site.loc[:, 'Date'] = pd.to_datetime(df_site['Date'], dayfirst=True)
        df_site = df_site.sort_values('Date')

        if secteur:
            cell_series = {}
            cell_variations={}
            call_seuils={}
            kpi_key = kpi.replace('_Valeur', '') if kpi else None
            threshold_info = KPI_THRESHOLDS.get(kpi_key, None)

            for cell in df_secteur['Cell Name'].unique():
                cell_df = df_secteur[df_secteur['Cell Name'] == cell]
                # Aligne les valeurs sur toutes les dates (None si manquant)
                values = []
                for d in dates:
                    row = cell_df[cell_df['Date'].dt.strftime('%Y-%m-%d') == d]
                    if not row.empty:
                        try:
                            values.append(float(row.iloc[0][kpi]))
                        except Exception:
                            values.append(None)
                    else:
                        values.append(None)
                cell_series[cell] = values
            
                filtered_vals = [v for v in values if v is not None]
                if len(filtered_vals) > 1:
                    moyenne = sum(filtered_vals[:-1]) / (len(filtered_vals) - 1)
                    current = filtered_vals[-1]
                    variation = ((current - moyenne) / moyenne) * 100 if moyenne != 0 else 0
                elif len(filtered_vals) == 1:
                    moyenne = filtered_vals[0]
                    current = filtered_vals[0]
                    variation = 0
                else:
                    moyenne = None
                    current = None
                    variation = 0 

                seuil_depasse = False
                if threshold_info and filtered_vals:
                    seuil= threshold_info['threshold']
                    mode=threshold_info['mode']
                    if mode == 'greater':
                        seuil_depasse = any(v> seuil for v in filtered_vals)
                    elif mode =='less':
                        seuil_depasse = any ( v< seuil for v in filtered_vals)
                cell_variations[cell]= {
                    'variation': variation,
                    'moyenne' : moyenne,
                    'current' : current,
                    'seuil_depasse' : seuil_depasse
                }
            #values = df_site[kpi].astype(float).tolist() if kpi else []
            #dates = df_site['Date'].dt.strftime('%Y-%m-%d').tolist() if kpi else []
            #cell_names = df_secteur['Cell Name'].tolist() if 'Cell Name' in df_secteur.columns else []
            #current = values[-1] if values else None
            #moyenne = sum(values[:-1]) / (len(values)-1) if len(values) > 1 else current
            #variation = ((current - moyenne) / moyenne) * 100 if moyenne and moyenne != 0 else 0

            # Seuils
            
            
            

            return jsonify({
                'dates': dates,

                'cell_series': cell_series,
                #'values': values,
                'cell_stats': cell_variations,
                #'cell_names': cell_names,
                'seuil': threshold_info['threshold'] if threshold_info else None,
                'seuil_mode': threshold_info['mode'] if threshold_info else None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/5gsecteurs',methods=['GET'])
def get_5gsecteurs():
    site = request.args.get('site')
    period = request.args.get('period')
    print(f"DEBUG: site={site}, period={period}")
    df = load_report5g_file(app.config['BASE_FOLDER'], period) 
    print(f"DEBUG: Colonnes: {df.columns}")
    df['last_digit'] = df[df['gNodeB Name']== site]['Cell Name'].str.extract(r'(\d)$')

    secteurs = df.groupby('last_digit')['Cell Name'].apply(lambda group: list(set(group))).to_dict() 
    
    print(f"DEBUG: Secteurs trouvés: {secteurs}")

    return jsonify(secteurs)


@app.route('/api/kpi-5gdata', methods=['GET', 'POST'])
def get_kpi_5gdata():
    if request.method == 'POST':
        data = request.get_json()
        period = data.get('period')
        site = data.get('site')
        kpi = data.get('kpi')
        secteur = data.get('secteur')
    else:  # GET
        period = request.args.get('period')
        site = request.args.get('site')
        kpi = request.args.get('kpi')
        secteur = request.args.get('secteur')
    try:
        df = load_report5g_file(app.config['BASE_FOLDER'], period)
        df_site = df[df['gNodeB Name'] == site].copy() if site else df.copy()
        print("DEBUG: site  sélectionné:", df_site)
       
        if secteur:
    # Recalcule le mapping secteur -> cellules à partir de df_site
            secteur_dict = {}
            for cell in df_site['Cell Name'].dropna().unique():
                suffix = cell.strip().split('_')[-1]  # Extrait le "h1", "l1", etc.
                secteur_num = suffix[-1]              # Extrait le dernier chiffre (ex: "1")
                secteur_dict.setdefault(secteur_num, []).append(cell)

            # Récupère les cellules du secteur demandé
            cellules_du_secteur = secteur_dict.get(str(secteur), [])
            print("DEBUG: Cellules du secteur sélectionné:", cellules_du_secteur)

            # Filtrer le DataFrame pour ne garder que les lignes du secteur sélectionné
            df_secteur = df_site[df_site['Cell Name'].isin(cellules_du_secteur)].copy()
            print("DEBUG: DataFrame du secteur sélectionné:", df_secteur)
            print(df_secteur.head())  # affiche un aperçu
            if not df_secteur.empty:
                min_date = df_secteur['Date'].min()
                max_date = df_secteur['Date'].max()
                all_dates = pd.date_range(min_date, max_date, freq='D').strftime('%Y-%m-%d').tolist()
            else:
                all_dates = []
            dates = all_dates
            print("Dates sélectionnés:", all_dates)
        df_site.loc[:, 'Date'] = pd.to_datetime(df_site['Date'], dayfirst=True)
        df_site = df_site.sort_values('Date')

        if secteur:
            cell_series = {}
            cell_variations={}
            call_seuils={}
            kpi_key = kpi.replace('_Valeur', '') if kpi else None
            threshold_info = KPI_THRESHOLDS_5G.get(kpi_key, None)

            for cell in df_secteur['Cell Name'].unique():
                cell_df = df_secteur[df_secteur['Cell Name'] == cell]
                # Aligne les valeurs sur toutes les dates (None si manquant)
                values = []
                for d in dates:
                    row = cell_df[cell_df['Date'].dt.strftime('%Y-%m-%d') == d]
                    if not row.empty:
                        try:
                            values.append(float(row.iloc[0][kpi]))
                        except Exception:
                            values.append(None)
                    else:
                        values.append(None)
                cell_series[cell] = values
            
                filtered_vals = [v for v in values if v is not None]
                if len(filtered_vals) > 1:
                    moyenne = sum(filtered_vals[:-1]) / (len(filtered_vals) - 1)
                    current = filtered_vals[-1]
                    variation = ((current - moyenne) / moyenne) * 100 if moyenne != 0 else 0
                elif len(filtered_vals) == 1:
                    moyenne = filtered_vals[0]
                    current = filtered_vals[0]
                    variation = 0
                else:
                    moyenne = None
                    current = None
                    variation = 0 

                seuil_depasse = False
                if threshold_info and filtered_vals:
                    seuil= threshold_info['threshold']
                    mode=threshold_info['mode']
                    if mode == 'greater':
                        seuil_depasse = any(v> seuil for v in filtered_vals)
                    elif mode =='less':
                        seuil_depasse = any ( v< seuil for v in filtered_vals)
                cell_variations[cell]= {
                    'variation': variation,
                    'moyenne' : moyenne,
                    'current' : current,
                    'seuil_depasse' : seuil_depasse
                }
            #values = df_site[kpi].astype(float).tolist() if kpi else []
            #dates = df_site['Date'].dt.strftime('%Y-%m-%d').tolist() if kpi else []
            #cell_names = df_secteur['Cell Name'].tolist() if 'Cell Name' in df_secteur.columns else []
            #current = values[-1] if values else None
            #moyenne = sum(values[:-1]) / (len(values)-1) if len(values) > 1 else current
            #variation = ((current - moyenne) / moyenne) * 100 if moyenne and moyenne != 0 else 0

            # Seuils
            
            
            

            return jsonify({
                'dates': dates,

                'cell_series': cell_series,
                #'values': values,
                'cell_stats': cell_variations,
                #'cell_names': cell_names,
                'seuil': threshold_info['threshold'] if threshold_info else None,
                'seuil_mode': threshold_info['mode'] if threshold_info else None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/option2', methods=['GET', 'POST'])
def option2():
    if request.method == 'POST':
        folder_5g = os.path.join(app.config['BASE_FOLDER'], "5G")
        
        # Vérifier si les dossiers existent déjà
        if  os.path.exists(folder_5g):
            # Analyse directe
            run_unified_5g_analysis(app.config['BASE_FOLDER'])
            flash("Analyses effectuées avec succès (fichiers existants)", "success")
        else:
            # Traitement des fichiers uploadés
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Organiser les fichiers
                    prefix_upper = filename[:2].upper()
                    try:
                        if 'NR' in prefix_upper or '5G' in prefix_upper:
                            process_5g_file(app.config['BASE_FOLDER'], filepath, "5G")
                    except Exception as e:
                        flash(f"Erreur lors du traitement de {filename}: {str(e)}", "error")
            
            # Exécuter les analyses
            if os.path.exists(folder_5g):
                run_unified_5g_analysis(app.config['BASE_FOLDER'])
            
            flash("Traitement et analyses terminés avec succès", "success")
        
        return redirect(url_for('option2'))
    
    results_folder = os.path.join('WORKSPACE', 'Rapports_Analyse_5G')
    available_reports = []
    if os.path.exists(results_folder):
        for root, dirs, files in os.walk(results_folder):
            for file in files:
                if file.endswith('.xlsx') or file.endswith('.csv'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, start='.')
                    available_reports.append({
                        'filename': relative_path.replace('\\', '/'),  # important pour Flask
                        'display_name': os.path.basename(file)
                    })
    rapports5g_existants = os.path.exists(results_folder) and any(
        file.endswith('.xlsx') or file.endswith('.csv')
        for root, dirs, files in os.walk(results_folder)
        for file in files
    )

    return render_template('option2.html',available_reports=available_reports,  rapports5g_existants=rapports5g_existants )


@app.route('/option3', methods=['GET', 'POST'])
def option3():
    cellplan_exists = any(f.lower().startswith('LTE_cell') and 
                         f.lower().endswith(('.xlsx', '.xls')) 
                         for f in os.listdir(app.config['BASE_FOLDER']))
    hofile_exists = any(f.lower().startswith('HO BAR') and 
                         f.lower().endswith(('.xlsx', '.xls')) 
                         for f in os.listdir(app.config['BASE_FOLDER']))
    if request.method == 'POST':
        file = request.files.get('cellplan_file')
        file1= request.files.get('ho_file')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            dest_path = os.path.join(app.config['BASE_FOLDER'], filename)
            
            if os.path.exists(dest_path):
                os.remove(dest_path)  # Remplacer le fichier existant
            
            file.save(dest_path)
            flash("Fichier Cell Plan importé avec succès", "success")
            cellplan_exists = True
           
        if file1 and allowed_file(file1.filename):
            filename = secure_filename(file1.filename)
            dest_path = os.path.join(app.config['BASE_FOLDER'], filename)
            
            if os.path.exists(dest_path):
                os.remove(dest_path)  # Remplacer le fichier existant
            
            file1.save(dest_path)
            flash("Fichier HO importé avec succès", "success")
            hofile_exists = True
        
        
        if 'calculate_distances' in request.form:
            print(">>> Requête Flask reçue pour calculate_distance")
            selected_sites=request.form.get("selected_sites", [])
            #cellplan_file = os.path.join(app.config['BASE_FOLDER'], 'LTE_cell_Plan_HU_MasterFile.xlsx')
            if selected_sites:
                site_names = [name.strip()[:8] for name in selected_sites.split(',') if name.strip()]
                

            #site_input = request.form.get('site_names') or ''
            #distance_input = request.form.get('distance') or ''
            #folders_input = request.form.get('kpi_folders') or ''
                        
                if not site_names:
                    flash("Aucun site source valide n'a été saisi", "error")
                else:
                    try:
                        #supprimer_fichiers_distance(app.config['BASE_FOLDER'], site_names)
                        calculate_distance(app.config['BASE_FOLDER'], site_names)
                        flash("Calcul de distance terminé avec succès", "success")
                        return jsonify({"success": True})

                    except Exception as e:
                        return jsonify({"success": False, "error": str(e)}), 500
                        flash(f"Erreur lors du calcul de distance: {str(e)}", "error")
                        
           
            else:
                flash("Aucun site sélectionné dans la carte" ,"error")
            
       
        
    
            
        return redirect(url_for('option3'))
            

    return render_template('overshoot.html',
                               cellplan_exists=cellplan_exists,
                               hofile_exists=hofile_exists,
                               show_map=True,
                               base_folder=app.config['BASE_FOLDER'])
@app.route('/export_and_download_cells', methods=['POST'])
def export_and_download_cells():
    try:
        cell_names_json = request.form.get('cells')
        if not cell_names_json:
            flash("Aucune donnée de cellule n'a été reçue.", "error")
            return redirect(url_for('option3'))

        cell_names = json.loads(cell_names_json)
        if not cell_names:
            flash("La liste des cellules est vide.", "warning")
            return redirect(url_for('option3'))

        df = pd.DataFrame({'Cellules': cell_names})

        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Cellules')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='cellules_export.xlsx'
        )

    except Exception as e:
        flash(f"Une erreur est survenue lors de l'exportation : {str(e)}", "error")
        return redirect(url_for('option3'))



@app.route('/extract_and_download_ids', methods=['POST'])
def extract_and_download_ids():
    try:
        separate_site_id(app.config['BASE_FOLDER'])
        id_file = os.path.join(app.config['BASE_FOLDER'], 'ID_Sites.xlsx')
        if os.path.exists(id_file):
            return send_file(
                id_file,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='ID_Sites.xlsx'
            )
        else:
            flash("Le fichier ID_Sites.xlsx n'a pas été trouvé.", "error")
    except Exception as e:
        flash(f"Erreur lors de l'extraction: {str(e)}", "error")
    return redirect(url_for('option3'))



@app.route('/get_sites_data')
def get_sites_data():
    # Rechercher le fichier Cell Plan
    #cellplan_file = None
    base_folder = app.config['BASE_FOLDER']
    cellplan_file= os.path.join(base_folder, 'LTE_cell_Plan_HU_MasterFile.xlsx')
    # Vérifier d'abord dans le dossier de base
    
    try:
        #print(f"Lecture du fichier Cell Plan: {cellplan_file}")
        df = pd.read_excel(cellplan_file)
        
        #Afficher les colonnes disponibles pour le debug
        #print(f"Colonnes disponibles: {list(df.columns)}")
        
        # Vérifier que les colonnes nécessaires existent
        #required_columns = ['CellName', 'Latitude_Sector', 'Longitude_Sector', 'Azimuth', 'SiteID']
        #missing_columns = [col for col in required_columns if col not in df.columns]
        
        #if missing_columns:
            #return jsonify({"error": f"Colonnes manquantes: {missing_columns}. Colonnes disponibles: {list(df.columns)}"})
        
        # Nettoyer les données
        df = df.dropna(subset=['Latitude_Sector', 'Longitude_Sector'])
        df['Azimuth'] = df['Azimuth'].astype(str).str.replace('°', '').str.strip()
        df['Azimuth'] = pd.to_numeric(df['Azimuth'], errors='coerce').fillna(0)
        

        
        # Extraire l'ID du site (8 premiers caractères du nom de cellule)
        df['SectorID'] = df['CellName'].str.extract(r'(^[^_]+_[^_]+_[^_]+_\d+)')
        
        # Grouper par site
        result = []
        for sector_id, group in df.groupby('SectorID'):
            if len(group) > 0:
                first_row = group.iloc[0]
                grouped_sectors = group.groupby(['Latitude_Sector', 'Longitude_Sector', 'Azimuth'])

                sectors = []
                
                for (lat, lon, azimuth), sector_group in grouped_sectors:
                    azimuth_rad =  math.radians(azimuth)
                    sector_width = math.radians(64)  # Ouverture de 64 degrés
                    length = 0.002  # Longueur fixe pour les secteurs
                    
                    # Calculer les points du secteur (forme de camembert)
                    sector_points = []
                    num_points = 10  # Nombre de points pour dessiner l'arc
                    
                    # Point central (position du site)
                    center_lat =lat
                    center_lon =lon
                    
                    # Calculer les angles de début et fin du secteur
                    start_angle = azimuth_rad - sector_width / 2
                    end_angle = azimuth_rad + sector_width / 2
                    
                    # Ajouter le point central
                    sector_points.append([center_lon, center_lat])
                    
                    # Ajouter les points de l'arc
                    for i in range(num_points + 1):
                        angle = start_angle + (end_angle - start_angle) * i / num_points
                        end_lat = center_lat + length * math.cos(angle)
                        end_lon = center_lon + length * math.sin(angle)
                        sector_points.append([end_lon, end_lat])
                    
                    # Fermer le secteur en revenant au centre
                    sector_points.append([center_lon, center_lat])
                    cell_names = sector_group['CellName'].tolist()

                    sectors.append({
                        "cell_names": cell_names,
                        "azimuth": float(azimuth),
                        "center_lat": float(center_lat),
                        "center_lon": float(center_lon),
                        "sector_points": sector_points,
                        "length": float(length)
                    })
                
                result.append({
                    "site_id": sector_id,
                    "latitude": float(first_row["Latitude_Sector"]),
                    "longitude": float(first_row["Longitude_Sector"]),
                    "sectors": sectors
                })

        print(f"Nombre de sites trouvés: {len(result)}")
        return jsonify(result)
    except Exception as e:
        print(f"Erreur lors du traitement: {str(e)}")
        return jsonify({"error": str(e)})




@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['BASE_FOLDER'], filename, as_attachment=True)

@app.route('/get_overshoot_sectors', methods=['POST'])
def get_overshoot_sectors():
    try:
        data = request.get_json()
        site_names = data.get('site_names', [])
        site_names = [name[:8] for name in site_names]
        overshoot_cells = extract_overshoot_cells(app.config['BASE_FOLDER'], site_names)
        print("Overshoot cells envoyées au frontend :", overshoot_cells)
        return jsonify(overshoot_cells)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/calculate_distances', methods=['POST'])
def calculate_distances():
    try:
        data = request.get_json()
        site_names = data.get('site_names') or data.get('selectedSites') or []
        site_names = [name[:8] for name in site_names if isinstance(name, str)]

        print(">>> Requête AJAX reçue pour calculate_distance")
        print(f"Liste des sites reçus : {site_names}")
        if not site_names:
            return jsonify({"success": False, "error": "Aucun site sélectionné."}), 400
        try:
            calculate_distance(app.config['BASE_FOLDER'], site_names)
            return jsonify({"success": True})
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)