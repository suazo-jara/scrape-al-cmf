import time
import csv
from datetime import timedelta
from dateutil import parser
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import urllib
import shutil
import os
import re

class GET_FINANCIAL_DATA:
   def __init__(self):
      self.Dir   = str(input('Enter output directory path where data will store!'))
      self.start = parser.parse(input("Enter start date in yyyy, m, d: ").replace(",", "-"))
      self.end = parser.parse(input("Enter end date yyyy, m, d: ").replace(",", "-"))
      if not os.path.exists(self.Dir): 
         os.mkdir(self.Dir)
      self.options = Options()
      self.options.add_argument("--headless")
      self.log_file = os.path.join(self.Dir, 'download_log.txt')
      self.main()
        
   def return_date_list(self, start, end):
      date_lst = []
      delta = timedelta(days=1)
      while start <= end:
         lst = start.strftime("%d/%m/%Y")
         date_lst.append(lst)
         start += delta
      return date_lst
   
   def setup_driver(self):
      self.options.add_argument("--headless")
      self.options.add_argument("--disable-gpu")  # Requerido en algunos entornos
      self.options.add_argument("--window-size=1920,1080")
      return webdriver.Firefox(options=self.options)
    
   def get_com_urls(self):
      link_lst = []   
      driver = self.setup_driver()
      driver.get('https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-18591.html')
      try:
         WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'Estado')))
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         select = Select(driver.find_element(By.ID, 'Estado'))
         driver.execute_script("arguments[0].value='TO';", driver.find_element(By.ID, 'Estado'))
         driver.find_element(By.ID, 'Estado').send_keys(Keys.RETURN)  # Presionar Enter para confirmar
         time.sleep(5)
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
            except:
               link = ''
            link_lst.append(link)
      except TimeoutException:
         print ("Loading took too much time!")
      driver.quit()
      return link_lst
    
   def get_com_info(self, link):
      lst = []
      driver = self.setup_driver()
      driver.get(link)
      delay = 15 # seconds
      try:
         WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'contenido')))      
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         lh = driver.execute_script("return document.body.scrollHeight")
         while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)         
            nh = driver.execute_script("return document.body.scrollHeight")
            if nh == lh:
               break
            lh = nh       
         time.sleep(1)
         html = driver.page_source
         soup = BeautifulSoup(html, "html.parser")
         table = soup.findChildren('table')[0]
         rows = table.findChildren('tr')
         try: 
            RUT = rows[0].findChild('td').getText()
         except:
            RUT = ''
         try:
            Business_name = rows[1].findChild('td').getText()
         except:
            Business_name = '' 
         try:
            Fantasy_name = rows[2].findChild('td').getText()
         except:
            Fantasy_name = '' 
         try:
            Validity = rows[3].findChild('td').getText()
         except:
            Validity = '' 
         try:   
            Reg_Num = rows[4].findChild('td').getText()
         except:
            Reg_Num = ''
         try:   
            Enroll_Date = rows[5].findChild('td').getText()
         except:
            Enroll_Date = '' 
         try:   
            Cancel_date = rows[6].findChild('td').getText()
         except:
            Cancel_date = '' 
         try:   
            Enrollment = rows[7].findChild('td').getText()
         except:
            Enrollment = ''
         try:
            Telephone = rows[8].findChild('td').getText()
         except:
            Telephone = '' 
         try:
            Fax = rows[9].findChild('td').getText()
         except:
            Fax = '' 
         try:
            Address = rows[10].findChild('td').getText()
         except:
            Address = ''
         try:
            Region = rows[11].findChild('td').getText()
         except:
            Region = ''
         try:  
            Town = rows[12].findChild('td').getText()
         except:
            Town = '' 
         try:   
            Commune = rows[13].findChild('td').getText()
         except:
            Commune = ''
         try:   
            email = rows[14].findChild('td').getText()
         except:
            email = ''
         try:   
            Website = rows[16].findChild('td').getText()
         except:
            Website = '' 
         try:   
            Postal_Code = rows[17].findChild('td').getText()
         except:
            Postal_Code = '' 
         try:   
            Name_Stock_Exchange = rows[18].findChild('td').getText()
         except:  
            Name_Stock_Exchange = '' 
         lst1 = [RUT, Business_name, Fantasy_name, Validity , Reg_Num, Enroll_Date, Cancel_date, Enrollment, Telephone, Fax, Address, Region, Town, Commune, email, Website, Postal_Code, Name_Stock_Exchange]
         lst.append(lst1)
      except:
         pass
      driver.close()
      return lst
   
   def download_files(self, driver, path, com_id, date_list):
      try:
         # Seleccionar el año
         select = Select(driver.find_element(By.ID, 'aa'))
         selected_option = select.first_selected_option
         year = str(selected_option.text).strip()  # Eliminar espacios innecesarios

         # Crear carpeta si no existe
         year_path = os.path.join(path, year)
         if not os.path.exists(year_path):
            os.mkdir(year_path)

         # Desplegar elementos de la tabla
         driver.implicitly_wait(3)
         driver.find_element(By.CLASS_NAME, 'arriba').send_keys(Keys.RETURN)
         time.sleep(1)
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         time.sleep(1)

         # Obtener el HTML
         html = driver.page_source
         soup = BeautifulSoup(html, "html.parser")

         # Buscar tabla y filas
         table = soup.findChildren('table')[0]
         rows = table.findChildren('tr')

         # Extraer datos de la primera fila (después del encabezado)
         data = rows[1].findChildren('td')

         # Extraer y limpiar la fecha de carga
         try:
            Upload_date = data[1].getText().strip()
            up_date = re.sub(r'[/]', '-', Upload_date)
            up_date = re.sub(r'\s', '_', up_date)
            up_date = re.sub(r'[:]', 'h', up_date)
         except Exception as e:
            print(f"Error obteniendo fecha de carga: {e}")
            return

         upload_date = Upload_date.split(' ')
         file_date = upload_date[0].strip()  # Asegurar que no tenga espacios en blanco

         # Verificar si la fecha está en la lista
         if file_date in date_list:
            # Intentar obtener el enlace del archivo
            try:
               file_link = driver.find_element(By.CSS_SELECTOR, 'table#Tabla>tbody>tr>td>a')
               file_URL = file_link.get_attribute('href')
               
               if file_URL:
                  # Construir nombre del archivo
                  file_name = os.path.join(year_path, f"{com_id}_{up_date}.pdf")

                  # Verificar si el archivo ya ha sido descargado
                  if self.is_file_downloaded(file_name):
                     print(f"El archivo ya fue descargado previamente: {file_name}")
                  else:
                     try:
                        request = urllib.request.Request(file_URL, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(request) as response, open(file_name, 'wb') as out_file:
                           shutil.copyfileobj(response, out_file)
                        print(f"Archivo guardado: {file_name}")
                        self.log_download(file_name)
                     except Exception as e:
                        print(f"Error al descargar {file_URL}: {e}")
               else:
                  print("No se encontró enlace de descarga.")
            except Exception as e:
               print(f"Error obteniendo enlace del archivo: {e}")

      except Exception as e:
         print(f"Error en download_files(): {e}")

      return

   def is_file_downloaded(self, file_name):
      # Verificar si el archivo ya ha sido descargado
      if not os.path.exists(self.log_file): 
         return False
      with open(self.log_file, 'r') as log:
         downloaded_files = log.read().splitlines()
      return file_name in downloaded_files
   
   def log_download(self, file_name):
      # Registrar el archivo descargado en el log
      with open(self.log_file, 'a') as log:
         log.write(file_name + '\n')
    
   def search_files(self, link, path, com_id, date_list):
      driver = self.setup_driver()
      driver.get(link)
      delay = 5 # seconds
      try:
         WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'cmfBtnMenuValor')))
         time.sleep(1)
         driver.find_element(By.LINK_TEXT, 'Memoria Anual').send_keys(Keys.RETURN)
         time.sleep(2)  # Pequeño delay para permitir la carga
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
         lh = driver.execute_script("return document.body.scrollHeight")
         while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)         
            nh = driver.execute_script("return document.body.scrollHeight")
            if nh == lh:
               break
            lh = nh
            
         # Obtener todos los años del dropdown
         years = Select(driver.find_element(By.ID, 'aa'))
         available_years = [opt.text.strip() for opt in years.options[1:]]  # Omitimos "Año" del primer índice

         # Filtrar solo los años que están en date_list
         filtered_years = [year for year in available_years if any(year in date for date in date_list)]

         for year in filtered_years:

            # Seleccionar el año en el dropdown
            driver.execute_script("arguments[0].value = arguments[1];", years._el, year)
            driver.find_element(By.ID, 'aa').send_keys(Keys.RETURN)  # Simula Enter para confirmar la selección
            
            time.sleep(3)  # Esperar a que se cargue el contenido de ese año
            
            # Verificar que el año realmente se seleccionó
            selected_option = Select(driver.find_element(By.ID, 'aa')).first_selected_option.text.strip()
            if selected_option == year:
               self.download_files(driver, path, com_id, date_list)

            # Refrescar la referencia al dropdown
            years = Select(driver.find_element(By.ID, 'aa'))

      except:
         pass
      driver.close()
      return
   
   def main(self):
      keys = ['RUT', 'Business_Name', 'Fantasy_Name', 'Validity' , 'Registration_Num', 'Enrollment_Date', 'Cancel_Date', 'Enrollment', 'Telephone', 'Fax', 'Address', 'Region', 'Town', 'Commune', 'Email', 'Website', 'Postal_Code', 'Stock_Exchange_Name']
      with open(self.Dir + '/'+ 'Output.csv', 'w', newline = '') as output_csv:
         csv_writer = csv.writer(output_csv)
         csv_writer.writerow(keys)
         links = self.get_com_urls()
         date_list = self.return_date_list(self.start, self.end)
         for link in links:
            try:
               lst = self.get_com_info('https://www.cmfchile.cl/'+link)[0]
               if lst != []:
                  csv_writer.writerow(lst)
                  com_id = lst[0]
               else:
                  pass
               self.search_files('https://www.cmfchile.cl/'+link, self.Dir, com_id, date_list)

            except:
               pass
      return

GET_FINANCIAL_DATA()