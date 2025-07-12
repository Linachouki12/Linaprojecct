
from datetime import datetime, timedelta
import pandas as pd
import os

def get_date_range(file_paths):
    """Détermine la plage de dates minimale et maximale parmi tous les fichiers"""
    min_date = datetime.max.date() #les extremes des dates 
    max_date = datetime.min.date()
    
    print("\nAnalyse des dates dans les fichiers...")
    
    for file_path in file_paths:
        try:
            df = pd.read_excel(file_path)
            
            if 'Date' in df.columns:
                # Conversion explicite avec dayfirst=True
                dates = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date #transformation en jj-mm-aaaa , suppression des valeurs NaT
                valid_dates = dates.dropna() #suppression des dates invalides
                
                if not valid_dates.empty:
                    print(f"Fichier {os.path.basename(file_path)}")
                    file_min = valid_dates.min() # calcul de date minimale dans le fichier
                    file_max = valid_dates.max()
                    min_date = min(min_date, file_min) #màj des dates disponibles globales
                    max_date = max(max_date, file_max)
        except Exception as e:
            print(f"Erreur avec {file_path}: {str(e)[:100]}...")
    
    print(f"\nPlage de dates détectée: {min_date} à {max_date}")
    return min_date, max_date


def define_period(end_date, days):
    """Définit une période de N jours avant la date de fin"""
    start_date = end_date - timedelta(days=days)
    return (start_date, end_date) # tuple*


def analyze_period(file_paths, date_range, is_5g=False):
    from .analysis_lte import analyze_kpis
    from .analysis_nr import analyze_5g_kpis
    """Analyse tous les fichiers pour une période donnée"""
    all_results = []
    data_found = False
    
    print(f"\nRecherche de données entre {date_range[0]} et {date_range[1]}")
    
    for file_path in file_paths:
        try:
            sheets = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in sheets.items():
                df.columns = df.columns.str.strip()
                
                if 'Date' not in df.columns:
                    continue
                
                try:
                    # Conversion robuste des dates
                    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
                    df = df.dropna(subset=['Date'])  # Supprime les lignes avec dates invalides
                    
                    # Filtrage par période
                    mask = (df['Date'] >= date_range[0]) & (df['Date'] <= date_range[1])
                    period_df = df[mask].copy()
                    
                    if not period_df.empty:
                        print(f"  ✓ Données trouvées dans {os.path.basename(file_path)} (feuille {sheet_name})")
                        data_found = True
                        
                        if 'Groupe' not in period_df.columns:
                            period_df['Groupe'] = sheet_name.split('_')[-1][0].upper()
                        
                        if is_5g:
                            results= analyze_5g_kpis(period_df)
                        else:
                            results = analyze_kpis(period_df)

                        if results is not None:
                            all_results.append(results)
                        
                except Exception as e:
                    print(f"  ✗ Erreur dans {os.path.basename(file_path)} (feuille {sheet_name}): {str(e)[:100]}...")
        
        except Exception as e:
            print(f"! Fichier {os.path.basename(file_path)} corrompu: {str(e)[:100]}...")
    
    if not data_found:
        print("Aucune donnée valide trouvée pour cette période")
    
    valid_results = [df for df in all_results if isinstance(df, pd.DataFrame) and not df.empty and not df.dropna(how='all', axis=1).empty]
    return pd.concat(valid_results, ignore_index=True) if valid_results else None

