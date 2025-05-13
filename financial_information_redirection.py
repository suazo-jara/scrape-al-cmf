import time
import csv
import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from bs4 import BeautifulSoup
import urllib.parse
import re

class CMF_REDIRECTION_DETECTOR:
    def __init__(self):
        self.Dir = str(input('Ingrese directorio de salida para el registro de redirecciones: '))
        
        if not os.path.exists(self.Dir):
            os.mkdir(self.Dir)
            
        # Archivos para seguimiento
        self.redirections_file = os.path.join(self.Dir, 'redirections.csv')
        self.progress_file = os.path.join(self.Dir, 'redirection_progress.json')
        
        # Cargar progreso existente si está disponible
        self.progress = self.load_progress()
        
        # Configuración del navegador
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")
        
        self.main()
        
    def load_progress(self):
        """Cargar progreso de ejecución anterior si está disponible"""
        progress = {
            'processed_urls': set(),
            'remaining_urls': []
        }
        
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    saved_progress = json.load(f)
                    progress['remaining_urls'] = saved_progress.get('remaining_urls', [])
                    progress['processed_urls'] = set(saved_progress.get('processed_urls', []))
            except json.JSONDecodeError:
                pass
                
        return progress
    
    def save_progress(self):
        """Guardar progreso actual"""
        with open(self.progress_file, 'w') as f:
            json.dump({
                'remaining_urls': self.progress['remaining_urls'],
                'processed_urls': list(self.progress['processed_urls'])
            }, f)
    
    def setup_driver(self):
        # Add specific wait timeout and page load timeout
        driver = webdriver.Firefox(options=self.options)
        driver.set_page_load_timeout(30)
        return driver
    
    def get_com_urls(self):
        if self.progress['remaining_urls']:
            print("Reanudando con URLs pendientes de la ejecución anterior...")
            return self.progress['remaining_urls']
            
        all_links = []
        driver = self.setup_driver()
        
        # Obtener URLs tanto de empresas vigentes como no vigentes
        for estado in ['VI', 'NV']:  # VI = Vigentes, NV = No Vigentes
            estado_links = []
            try:
                driver.get('https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-18591.html')
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'Estado')))
                
                # Seleccionar el estado (Vigentes o No Vigentes)
                driver.execute_script(f"arguments[0].value = '{estado}'; arguments[0].dispatchEvent(new Event('change'))", 
                                       driver.find_element(By.ID, 'Estado'))
                
                # Esperar a que se carguen los resultados
                time.sleep(5)
                
                # Scroll para cargar todos los elementos
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                lh = driver.execute_script("return document.body.scrollHeight")
                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    nh = driver.execute_script("return document.body.scrollHeight")
                    if nh == lh:
                        break
                    lh = nh       
                
                time.sleep(5)
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                table = soup.findChildren('table')[0]
                rows = table.findChildren('tr')
                
                for r in rows:
                    td = r.findChildren('td')
                    try: 
                        link = td[1].find('a')['href']
                        if link and link not in self.progress['processed_urls']:
                            estado_links.append(link)
                    except:
                        continue
                
                # Añadir los enlaces encontrados para este estado al total
                all_links.extend(estado_links)
                print(f"Se encontraron {len(estado_links)} enlaces de empresas con estado {estado}")
                
            except TimeoutException:
                print("La carga tomó demasiado tiempo!")
            except Exception as e:
                print(f"Error al seleccionar la opción '{estado}': {e}")
        
        driver.quit()
        print(f"Total: Se analizarán {len(all_links)} empresas para detectar redirecciones")
        return all_links
    
    def get_company_info(self, link):
        """Obtener información básica de la empresa"""
        company_info = {'RUT': '', 'Nombre': ''}
        driver = self.setup_driver()
        
        try:
            driver.get('https://www.cmfchile.cl/' + link)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'contenido')))
            
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            table = soup.findChildren('table')[0]
            rows = table.findChildren('tr')
            
            # Extraer RUT y nombre de empresa
            company_info['RUT'] = rows[0].findChild('td').getText().strip() if rows and len(rows) > 0 else ''
            company_info['Nombre'] = rows[1].findChild('td').getText().strip() if rows and len(rows) > 1 else ''
            
        except Exception as e:
            print(f"Error al obtener información de la empresa: {e}")
        finally:
            driver.quit()
            
        return company_info
    
    def check_if_pdf_or_external(self, driver, url):
        """
        Verifica si un enlace lleva a un PDF o a un portal externo
        Returns: 
            - is_pdf (bool): True si es PDF
            - is_external (bool): True si redirecciona a portal externo
            - final_url (str): URL final después de redirecciones
        """
        original_url = driver.current_url
        original_domain = urllib.parse.urlparse(original_url).netloc
        
        # Completa la URL si es relativa
        if url.startswith('/'):
            base_url = f"https://{original_domain}"
            complete_url = base_url + url
        else:
            complete_url = url
            
        print(f"Comprobando enlace: {complete_url}")
        
        try:
            # Método 1: Verificar headers con requests para detectar tipo de contenido
            # Usamos head para no descargar el archivo completo
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.head(complete_url, headers=headers, allow_redirects=True, timeout=10)
                
                # Verificar el Content-Type
                content_type = response.headers.get('Content-Type', '').lower()
                content_disposition = response.headers.get('Content-Disposition', '').lower()
                
                if 'application/pdf' in content_type or '.pdf' in content_disposition:
                    return True, False, response.url
                
                # Si llega aquí y la URL final es diferente del dominio original
                final_domain = urllib.parse.urlparse(response.url).netloc
                if original_domain != final_domain and final_domain != '':
                    return False, True, response.url
                    
            except Exception as e:
                print(f"No se pudo verificar con requests: {e}")
            
            # Método 2: Navegar con Selenium como plan B
            # Guardamos la ventana original para volver después
            original_window = driver.current_window_handle
            
            # Abrimos el enlace en una nueva pestaña
            driver.execute_script(f"window.open('{complete_url}', '_blank');")
            time.sleep(2)
            
            # Cambiamos a la nueva pestaña
            windows = driver.window_handles
            driver.switch_to.window(windows[-1])
            
            # Esperar a que cargue la página (con timeout reducido)
            wait = WebDriverWait(driver, 10)
            try:
                wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
            except:
                pass
                
            final_url = driver.current_url
            final_domain = urllib.parse.urlparse(final_url).netloc
                
            # Verificar si es PDF por la URL o por el contenido de la página
            is_pdf = False
            is_external = False
            
            # Verificar si la URL termina en .pdf
            if final_url.lower().endswith('.pdf'):
                is_pdf = True
            
            # Verificar si estamos en un dominio externo
            if original_domain != final_domain and final_domain != '':
                is_external = True
                
            # Verificar si es un PDF por el contenido de la página
            if not is_pdf:
                try:
                    # Si la página tiene un objeto embed o iframe con PDF, es un visor de PDF
                    pdf_elements = driver.find_elements(By.CSS_SELECTOR, 'embed[type="application/pdf"], iframe[src$=".pdf"]')
                    if pdf_elements:
                        is_pdf = True
                        
                    # Verificar si hay elementos que indican un portal externo (más de 5 enlaces, menús, etc.)
                    links = driver.find_elements(By.TAG_NAME, 'a')
                    if len(links) > 5:
                        is_external = True
                        
                    # Verificar el título de la página para indicios de portal
                    page_title = driver.title.lower()
                    portal_keywords = ['portal', 'sitio', 'inicio', 'home', 'web', 'bienvenido']
                    if any(keyword in page_title for keyword in portal_keywords):
                        is_external = True
                        
                except Exception as e:
                    print(f"Error al analizar contenido: {e}")
            
            # Cerramos la pestaña y volvemos a la original
            driver.close()
            driver.switch_to.window(original_window)
            
            return is_pdf, is_external, final_url
            
        except Exception as e:
            print(f"Error al verificar enlace {complete_url}: {e}")
            # En caso de error, volvemos a la ventana original si es necesario
            try:
                current_handles = driver.window_handles
                if len(current_handles) > 1 and driver.current_window_handle != original_window:
                    driver.close()
                    driver.switch_to.window(original_window)
            except:
                pass
            return False, False, url
    
    def detect_external_download_links(self, link):
        """Detectar si los enlaces de descarga de memorias anuales redirigen a portales externos"""
        original_url = 'https://www.cmfchile.cl/' + link
        company_info = {'RUT': '', 'Nombre': ''}
        external_links = []
        
        driver = self.setup_driver()
        
        try:
            # Obtener información básica de la empresa
            driver.get(original_url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'contenido')))
            
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            table = soup.findChildren('table')[0]
            rows = table.findChildren('tr')
            
            company_info['RUT'] = rows[0].findChild('td').getText().strip() if rows and len(rows) > 0 else ''
            company_info['Nombre'] = rows[1].findChild('td').getText().strip() if rows and len(rows) > 1 else ''
            
            # Acceder a la sección de Memoria Anual
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'cmfBtnMenuValor')))
                
                # Usar JavaScript para hacer clic en el enlace, más confiable
                memoria_link = driver.find_element(By.LINK_TEXT, 'Memoria Anual')
                driver.execute_script("arguments[0].click();", memoria_link)
                
                time.sleep(5)  # Esperar a que cargue la página
                
                # Verificar si la página actual es externa a CMF
                current_url = driver.current_url
                parsed_original = urllib.parse.urlparse(original_url)
                parsed_current = urllib.parse.urlparse(current_url)
                
                if parsed_original.netloc != parsed_current.netloc:
                    print(f"¡Redirección de página completa detectada! {parsed_current.netloc}")
                    external_links.append({
                        'tipo': 'pagina_completa',
                        'año': 'todos',
                        'url': current_url
                    })
                else:
                    # Si estamos en el mismo dominio, buscar todos los años disponibles
                    try:
                        # Obtener todos los años disponibles del dropdown
                        try:
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'aa')))
                            years_select = Select(driver.find_element(By.ID, 'aa'))
                            available_years = [opt.text.strip() for opt in years_select.options if opt.text.strip()]
                            
                            print(f"Años disponibles: {available_years}")
                            
                            # Excluir la primera opción si es un texto como "Seleccione"
                            if available_years and not available_years[0].isdigit():
                                available_years = available_years[1:]
                            
                            # Para cada año, verificar los enlaces de descarga
                            for year in available_years:
                                try:
                                    # Usar JavaScript para seleccionar el año, evitando problemas de scrolling
                                    select_element = driver.find_element(By.ID, 'aa')
                                    driver.execute_script(
                                        f"var select = arguments[0]; "
                                        f"var option = select.querySelector('option[value=\"{year}\"]'); "
                                        f"if(option) {{ select.value = option.value; var event = new Event('change', {{ bubbles: true }}); "
                                        f"select.dispatchEvent(event); }}", 
                                        select_element
                                    )
                                    
                                    time.sleep(3)
                                    
                                    # Hacer clic en la flecha para mostrar archivos
                                    try:
                                        arrow_button = driver.find_element(By.CLASS_NAME, 'arriba')
                                        driver.execute_script("arguments[0].click();", arrow_button)
                                        time.sleep(1)
                                    except NoSuchElementException:
                                        print(f"No se encontró botón para mostrar archivos en el año {year}")
                                    except Exception as e:
                                        print(f"Error al hacer clic en botón de archivos del año {year}: {e}")
                                    
                                    # Buscar enlaces de descarga
                                    try:
                                        links = driver.find_elements(By.CSS_SELECTOR, 'table#Tabla>tbody>tr>td>a')
                                        for download_link in links:
                                            href = download_link.get_attribute('href')
                                            if href:
                                                # MEJORA: Verificar realmente si el enlace es PDF o portal externo
                                                is_pdf, is_external, final_url = self.check_if_pdf_or_external(driver, href)
                                                
                                                if is_external:
                                                    print(f"¡Portal externo detectado en año {year}!")
                                                    external_links.append({
                                                        'tipo': 'portal_externo',
                                                        'año': year,
                                                        'url': final_url
                                                    })
                                                elif not is_pdf:
                                                    # Si no es PDF ni portal externo reconocible, lo marcamos como potencial
                                                    print(f"¡Enlace no reconocido como PDF en año {year}!")
                                                    external_links.append({
                                                        'tipo': 'enlace_no_pdf',
                                                        'año': year,
                                                        'url': final_url
                                                    })
                                    except Exception as e:
                                        print(f"Error al buscar enlaces de descarga para el año {year}: {e}")
                                except ElementNotInteractableException:
                                    print(f"No se puede interactuar con la opción del año {year}")
                                    continue
                                except Exception as e:
                                    print(f"Error al procesar el año {year}: {e}")
                        except NoSuchElementException:
                            print("No se encontró selector de años (ID: aa)")
                        except Exception as e:
                            print(f"Error al obtener años disponibles: {e}")
                    except Exception as e:
                        print(f"Error general al verificar años: {e}")
                
                # Buscar también iframes que puedan contener portales externos
                try:
                    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
                    for iframe in iframes:
                        iframe_src = iframe.get_attribute('src')
                        if iframe_src:
                            parsed_iframe = urllib.parse.urlparse(iframe_src)
                            if parsed_iframe.netloc != '' and parsed_iframe.netloc != 'www.cmfchile.cl':
                                print(f"¡Iframe externo detectado! {parsed_iframe.netloc}")
                                external_links.append({
                                    'tipo': 'iframe',
                                    'año': 'desconocido',
                                    'url': iframe_src
                                })
                except Exception as e:
                    print(f"Error al buscar iframes: {e}")
            
            except NoSuchElementException:
                print("No se encontró enlace a Memoria Anual")
            except Exception as e:
                print(f"Error al verificar enlaces de Memoria Anual: {e}")
                
        except Exception as e:
            print(f"Error al acceder a URL {original_url}: {e}")
        finally:
            driver.quit()
            
        return company_info, external_links
    
    def register_external_links(self, company_info, original_url, external_links):
        """Registrar información de enlaces externos en el archivo CSV"""
        if not external_links:
            return
            
        with open(self.redirections_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for link_info in external_links:
                writer.writerow([
                    company_info['RUT'],
                    company_info['Nombre'],
                    original_url,
                    link_info['url'],
                    link_info['tipo'],
                    link_info['año'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
                
        print(f"Se registraron {len(external_links)} enlaces externos para {company_info['RUT']} - {company_info['Nombre']}")
        
    def main(self):
        # Crear/actualizar el archivo CSV con el formato correcto
        if not os.path.exists(self.redirections_file):
            with open(self.redirections_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['RUT', 'Nombre_Empresa', 'URL_Original', 'URL_Externa', 'Tipo_Redirección', 'Año', 'Fecha_Detección'])
        
        links = self.get_com_urls()
        print(f"Se analizarán {len(links)} empresas para detectar redirecciones")
        
        # Actualizar los enlaces pendientes
        self.progress['remaining_urls'] = links
        self.save_progress()
        
        contador = 0
        empresas_con_redirecciones = 0
        total_redirecciones = 0
        
        for link in links:
            contador += 1
            try:
                original_url = 'https://www.cmfchile.cl/' + link
                print(f"\n[{contador}/{len(links)}] Analizando: {original_url}")
                
                # Detectar enlaces externos en las memorias anuales
                company_info, external_links = self.detect_external_download_links(link)
                
                # Si se detectaron enlaces externos, registrarlos
                if external_links:
                    self.register_external_links(company_info, original_url, external_links)
                    empresas_con_redirecciones += 1
                    total_redirecciones += len(external_links)
                
                # Marcar como procesada y actualizar progreso
                self.progress['processed_urls'].add(link)
                self.progress['remaining_urls'] = links[links.index(link)+1:]
                self.save_progress()
                
                # Estadísticas
                print(f"Progreso: {contador}/{len(links)} empresas analizadas. Empresas con redirecciones: {empresas_con_redirecciones}, Total redirecciones: {total_redirecciones}")
                
            except Exception as e:
                print(f"Error al procesar enlace {link}: {e}")
                continue
        
        print(f"\nProceso completado. Se analizaron {contador} empresas.")
        print(f"Se encontraron {empresas_con_redirecciones} empresas con redirecciones y un total de {total_redirecciones} redirecciones.")
        print(f"Los resultados se guardaron en: {self.redirections_file}")

if __name__ == "__main__":
    CMF_REDIRECTION_DETECTOR()