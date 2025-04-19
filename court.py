from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os

OUTPUT_PATH = r"C:\my files\homework\judges_data.json"
EDGE_DRIVER_PATH = r"C:\Users\Mi\Downloads\edgedriver_win64\msedgedriver.exe"
BASE_URL = "https://vsrf.ru/about/structure/"

def setup_driver():
    """Настройка драйвера (Edge)"""
    service = Service(EDGE_DRIVER_PATH)
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Edge(service=service, options=options)

def get_judge_details(driver, url):
    """Получение детальной информации о судье"""
    if not url:
        return {}
    
    original_window = driver.current_window_handle
    driver.switch_to.new_window('tab')
    driver.get(url)
    time.sleep(2)
    
    details = {
        'career': [], 
        'education': "Не указано", 
        'awards': "Не указано",
        'class': "Не указано",
        'appointment': "Не указано"
    }
    
    try:
        details['name'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.vs-person-detail-name'))).text
        details['position'] = driver.find_element(
            By.CSS_SELECTOR, '.vs-person-detail-position').text
        
        try:
            details['class'] = driver.find_element(
                By.XPATH, '//p[contains(text(), "квалификационный класс")]').text
        except NoSuchElementException:
            pass
        
        try:
            details['appointment'] = driver.find_element(
                By.XPATH, '//p[contains(text(), "Постановление")]').text
        except NoSuchElementException:
            pass
        
        try:
            career_items = driver.find_elements(
                By.CSS_SELECTOR, '.vs-person-detail-career-item')
            for item in career_items:
                year = item.find_element(
                    By.CSS_SELECTOR, '.vs-person-detail-career-item-year').text
                text = item.find_element(
                    By.CSS_SELECTOR, '.vs-person-detail-career-item-text').text
                details['career'].append(f"{year}: {text}")
        except NoSuchElementException:
            pass
        
        try:
            details['education'] = driver.find_element(
                By.CSS_SELECTOR, '.vs-person-detail-education').text
        except NoSuchElementException:
            pass
            
        try:
            details['awards'] = driver.find_element(
                By.CSS_SELECTOR, '.vs-person-detail-awards').text
        except NoSuchElementException:
            pass
            
    except Exception as e:
        print(f"Ошибка при получении деталей: {str(e)}")
    finally:
        driver.close()
        driver.switch_to.window(original_window)
        return details

def process_subsection(driver, subsection_url):
    """Обработка подраздела"""
    print(f"Обработка подраздела: {subsection_url}")
    original_url = driver.current_url
    driver.get(subsection_url)
    time.sleep(3)
    
    judges = []
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.vs-structure-list-persons')))
        
        judge_elements = driver.find_elements(
            By.CSS_SELECTOR, '.vs-structure-list-persons > div.clearfix')
        
        for judge in judge_elements:
            try:
                name_element = judge.find_element(By.CSS_SELECTOR, 'h2 a')
                judge_info = {
                    'name': name_element.text,
                    'position': judge.find_element(
                        By.CSS_SELECTOR, '.vs-structure-list-persons-position').text,
                    'photo_url': judge.find_element(
                        By.CSS_SELECTOR, '.vs-structure-list-persons-photo img').get_attribute('src')
                }
                
                profile_url = name_element.get_attribute('href')
                if profile_url:
                    judge_info.update(get_judge_details(driver, profile_url))
                
                judges.append(judge_info)
            except Exception as e:
                print(f"Ошибка при обработке судьи: {str(e)}")
                continue
                
    except (NoSuchElementException, TimeoutException) as e:
        print(f"Судьи не найдены в этом подразделе: {str(e)}")
    finally:
        driver.get(original_url)
        time.sleep(2)
    
    return judges

def get_all_structure_sections(driver):
    """Получение всех разделов структуры"""
    driver.get(BASE_URL)
    time.sleep(3)
    
    sections = []
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//table[@class="vs-tabs"]')))
        section_tabs = driver.find_elements(
            By.XPATH, '//table[@class="vs-tabs"]//a[@data-code]')
        
        for tab in section_tabs:
            sections.append({
                'name': tab.text.replace('\n', ' ').strip(),
                'code': tab.get_attribute('data-code'),
                'url': tab.get_attribute('href')
            })
            
    except Exception as e:
        print(f"Ошибка при получении разделов: {str(e)}")
    
    return sections

def get_subsections_for_section(driver, section_url):
    """Получение подразделов для раздела"""
    driver.get(section_url)
    time.sleep(3)
    
    subsections = []
    try:
        subsection_menu = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.ID, 'vs-structure-menu-dynamic')))
        
        subsection_links = subsection_menu.find_elements(
            By.XPATH, './/a[contains(@href, "subsection=")]')
        
        for link in subsection_links:
            subsections.append({
                'name': link.text.strip(),
                'url': link.get_attribute('href'),
                'code': link.get_attribute('href').split('subsection=')[1]
            })
            
    except (NoSuchElementException, TimeoutException):
        print("Подразделы не найдены, будет обработан основной раздел")
        subsections.append({
            'name': 'Основной раздел',
            'url': section_url,
            'code': None
        })
    
    return subsections

def scrape_judicial_structure():
    """Основная функция сбора данных"""
    driver = setup_driver()
    court_data = []
    
    try:
        print("Начало сбора данных...")
    
        sections = get_all_structure_sections(driver)
        for section in sections:
            print(f"\nОбработка раздела: {section['name']}")
            
            subsections = get_subsections_for_section(driver, section['url'])
            subsections_data = []
            for subsection in subsections:
                print(f"  Обработка подраздела: {subsection['name']}")
                judges = process_subsection(driver, subsection['url'])
                subsections_data.append({
                    'subsection_name': subsection['name'],
                    'subsection_url': subsection['url'],
                    'subsection_code': subsection['code'],
                    'judges_count': len(judges),
                    'judges': judges
                })
            
            court_data.append({
                'section_name': section['name'],
                'section_code': section['code'],
                'subsections_count': len(subsections_data),
                'subsections': subsections_data
            })
        
        if court_data:
            os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)          
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(court_data, f, ensure_ascii=False, indent=2)          
            print(f"\nДанные успешно сохранены в {OUTPUT_PATH}")
            
            total_sections = len(court_data)
            total_subsections = sum(s['subsections_count'] for s in court_data)
            total_judges = sum(
                len(sub['judges']) 
                for section in court_data 
                for sub in section['subsections']
            )
            
            print("\nСтатистика:")
            print(f"Всего разделов: {total_sections}")
            print(f"Всего подразделов: {total_subsections}")
            print(f"Всего судей: {total_judges}")
            
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
    finally:
        driver.quit()
        print("\nРабота завершена")

if __name__ == "__main__":
    scrape_judicial_structure()