from celery import shared_task, task
from django.db import transaction
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from celery.exceptions import MaxRetriesExceededError
from selenium import webdriver
import time
from .models import Links, SDMX
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import requests
from xml.etree import ElementTree as ET
import io
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded


@task(bind=True, autoretry_for=(Exception,), soft_time_limit=600)
def parse_emiss(self):
    try:
        capabilities = {
            "screenResolution": "5000x1080x24",
            "browserName": "chrome",
            "browserVersion": "91.0",
            "selenoid:options": {
                "enableVNC": True,
                "enableVideo": False,
                "sessionTimeout": "4m",
            }
        }

        sdmx_parsed_data = SDMX.objects.values_list(
            'links_id').distinct()

        sdmx_parse_status = SDMX.objects.filter(
            parse_status=True)

        print(sdmx_parsed_data)
        links = Links.objects.filter(
            activity=True).exclude(
                id__in=sdmx_parsed_data).exclude(id__in=sdmx_parse_status)
        print(links)
        for link in links:
                if link:
                    try:
                        driver = webdriver.Remote(
                            command_executor='http://selenoid:4444/wd/hub', desired_capabilities=capabilities)
                        driver.maximize_window()
                        url = 'http://localhost:4444/download/' + \
                            driver.session_id+'/'+os.environ['EMISS_FILE_MANE']
                        driver.get(link.urls)
                        try:
                            elem = WebDriverWait(driver, 30).until(EC.presence_of_element_located(
                                (By.CLASS_NAME, 'k-grid')))

                        finally:
                            # проверка на прелоадер
                            preloader = driver.find_element(
                                By.CLASS_NAME, 'agrid-loader')
                            if preloader.is_displayed():
                                time.sleep(5)
                            else:
                                # Расширить таблицу
                                driver.find_element(
                                    By.CLASS_NAME, 'inst_tab').click()
                                time.sleep(2)
                                driver.find_element(
                                    By.CLASS_NAME, 'agrid-action-fullscreen').click()
                                time.sleep(2)
                                driver.find_element(
                                    By.CLASS_NAME, 'inst_tab').click()
                                time.sleep(2)

                                # Снять фильтры
                                sortable_block = driver.find_element(
                                    By.ID, 'sortable')
                                if sortable_block.is_displayed():
                                    delete_buttons = sortable_block.find_elements(
                                        By.CLASS_NAME, 'k-group-delete')
                                    for delete_button in range(len(delete_buttons)):
                                        sortable_block.find_element(
                                            By.CLASS_NAME, 'k-group-delete').click()
                                        time.sleep(2)

                                # Проскроллить вниз на 550 px
                                driver.execute_script("window.scrollTo(0, 550)")
                                time.sleep(2)

                                # Отобрать все фильтры за исключением скрытых колонок
                                print("first grid loaded")
                                links = driver.find_elements(
                                    By.CLASS_NAME, 'k-header:not(.hidden-col)')
                                print("Первичный поиск ссылок ", len(links))
                                i = 0

                                # Проход по ссылкам
                                while i <= len(links)-1:
                                    try:
                                        # Проверка появлекния новых фильтров если новые фильты есть то переопределяем изначальный состав ссылок
                                        time.sleep(2)
                                        links = driver.find_elements(
                                            By.CLASS_NAME, 'k-header:not(.hidden-col)')

                                        preloader = driver.find_element(
                                            By.CLASS_NAME, 'agrid-loader')
                                        if preloader.is_displayed():
                                            print("Ожидание 5 секунд")
                                            time.sleep(5)
                                        else:

                                            # Условие для сработки скрола
                                            Link_is_displayed = links[i].find_element(
                                                By.CLASS_NAME, 'k-filter')
                                            if Link_is_displayed.is_displayed():
                                                print("element is visible")
                                                pass
                                            else:
                                                print("element invisible - scroll")
                                                option = driver.find_element(
                                                    By.CLASS_NAME, 'mCSB_scrollTools_horizontal')
                                                # gragbar_size = option.size
                                                # gragbar_width = gragbar_size['width']

                                                scrollbar = option.find_element(
                                                    By.CLASS_NAME, 'mCSB_dragger')
                                                # scrollbar_size = scrollbar.size
                                                # scrollbar_width = scrollbar_size['width']

                                                action = ActionChains(driver)
                                                # Условие если елемент не виден то сдвинуть скролл на 50 px
                                                while Link_is_displayed.is_displayed() == False:
                                                    try:
                                                        action.drag_and_drop_by_offset(
                                                            scrollbar, 50, 1)
                                                        action.release()
                                                        action.perform()
                                                    except:
                                                        print("scroll drug is out")
                                                        break

                                            # Клик по фильтру
                                            links[i].find_element(
                                                By.CLASS_NAME, 'k-filter').click()
                                            try:
                                                # Дожидаемся грида
                                                elem = WebDriverWait(driver, 300).until(
                                                    EC.presence_of_element_located(
                                                        (By.CLASS_NAME, 'k-grid')))
                                            finally:
                                                print("grid loaded after filter",
                                                    i, 'из', len(links)-1)
                                                # Открываем фильрацию
                                                try:
                                                    elem = WebDriverWait(driver, 300).until(
                                                        EC.presence_of_element_located(
                                                            (By.CLASS_NAME, 'k-filter-menu'))
                                                    )
                                                finally:
                                                    # Проверка на установленные фильтры
                                                    chech_filter_open = elem.find_element(
                                                        By.CLASS_NAME, 'k-other-filters')
                                                    if chech_filter_open.is_displayed():
                                                        elem.find_element(
                                                            By.CLASS_NAME, 'sp_checkbox').click()
                                                    driver.find_element(
                                                        By.CLASS_NAME, 'k-filter-load').click()
                                                    time.sleep(2)

                                            new_links = driver.find_elements(
                                                By.CLASS_NAME, 'k-header:not(.hidden-col)')

                                            # Условие проверки появления новыз фильтров
                                            if len(links) == len(new_links):
                                                pass
                                            else:
                                                # Переприсваиваем состав фильтров на новый состав
                                                i = 0
                                                links = new_links

                                            i = i + 1
                                    except (TimeoutException, NoSuchElementException, WebDriverException, Exception, MaxRetriesExceededError) as e:
                                        print(e)
                                        check_SDMX_dublicate = SDMX.objects.filter(
                                            links_id=link)

                                        if check_SDMX_dublicate:
                                            print(link.name_index,
                                                link.description, "- Дубликат")
                                        else:
                                            with transaction.atomic():
                                                sdmx = SDMX(
                                                    index=link.name_index,
                                                    links_id=link,
                                                    description=link.description,
                                                    parse_status=False,
                                                )
                                                sdmx.save()
                                        driver.quit()
                                        print("exeption on while")
                                
                                # Загрузка файла
                                time.sleep(1)
                                menu = driver.find_element(
                                    By.CLASS_NAME, 'filt_btns')
                                menu.find_element(
                                    By.CLASS_NAME, 'blue_btn').click()
                                time.sleep(1)
                                driver.find_element(
                                    By.ID, 'download_sdmx_file').click()

                                time.sleep(5)
                                
                                # Получаем файл из Selenoid и проверяем на валидность
                                url = 'http://selenoid:4444/download/' + \
                                    driver.session_id+'/' + \
                                    os.environ['EMISS_FILE_MANE']
                                response = requests.get(url)
                                if response.status_code != 200:
                                    while response.status_code != 200:
                                        url = 'http://selenoid:4444/download/' + \
                                            driver.session_id+'/' + \
                                            os.environ['EMISS_FILE_MANE']
                                        response = requests.get(url)

                                sdmx_content = response.text
                                try:
                                    f = io.StringIO(str(sdmx_content))
                                    ET.parse(f)
                                    validate_status = True
                                except Exception as e:
                                    print("Показатель ", link.description,
                                        " - XML не соответвует формату XML, требутся привести в соответствие формату XML")
                                    validate_status = False

                                check_SDMX_dublicate = SDMX.objects.filter(
                                    links_id=link)

                                if check_SDMX_dublicate:
                                    print(link.name_index,
                                        link.description, "- Дубликат")
                                else:
                                    with transaction.atomic():
                                        sdmx = SDMX(
                                            sdmx_data=sdmx_content,
                                            index=link.name_index,
                                            links_id=link,
                                            description=link.description,
                                            parse_status=True,
                                            validate_status=validate_status,
                                        )
                                        sdmx.save()
                                        driver.quit()

                    except (TimeoutException, TimeLimitExceeded, SoftTimeLimitExceeded, NoSuchElementException, WebDriverException, Exception, MaxRetriesExceededError) as e:
                        print(e)
                        check_SDMX_dublicate = SDMX.objects.filter(
                            links_id=link)

                        if check_SDMX_dublicate:
                            print(link.name_index,
                                link.description, "- Дубликат")
                        else:
                            with transaction.atomic():
                                sdmx = SDMX(
                                    index=link.name_index,
                                    links_id=link,
                                    description=link.description,
                                    parse_status=False,
                                )
                                sdmx.save()
                        driver.quit()
                        print("exeption on for link")
                else:
                    print("Отсутствуют данные для парсинга, необходимо проверить наличие и активность показателей ЦУР в административном интерфейсе")
            
    except SoftTimeLimitExceeded as e:
        print("SoftTimeLimitExceeded")
        raise self.retry(exc=e)

            
       

@shared_task(name="sdmx", default_retry_delay=300, max_retries=5)
def sdmx():
    print("Задача обработки SDMX (вынесено в иетерфейс)")
