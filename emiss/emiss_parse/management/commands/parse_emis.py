from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from celery.exceptions import MaxRetriesExceededError
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import requests
from emiss_parse.models import Links, SDMX
import os
from django.db import transaction
import requests
from xml.etree import ElementTree as ET
import io


class Command(BaseCommand):
    help = 'Команда запуска парсинга с https://rosstat.gov.ru/sdg/data  для получения ссылок на ЕМИСС'
    # Команда вызова обновления всех таблиц кодов из Россвязи

    def handle(self, *args, **options):
        capabilities = {
            "screenResolution": "3840x2160x24",
            "browserName": "chrome",
            "browserVersion": "91.0",
            "selenoid:options": {
                "enableVNC": True,
                "enableVideo": False,
                "sessionTimeout": "7m",
            }
        }

        driver = webdriver.Remote(
            command_executor='http://selenoid:4444/wd/hub', desired_capabilities=capabilities)
        driver.maximize_window()
        print("Сессия", driver.session_id)
        url = 'http://localhost:4444/download/' + \
            driver.session_id+'/'+os.environ['EMISS_FILE_MANE']
        print(url)
        sdmx_parsed_data = SDMX.objects.values_list(
            'links_id').distinct()

        print(sdmx_parsed_data)
        links = Links.objects.filter(
            activity=True).exclude(
            id__in=sdmx_parsed_data).exclude()
        print(links)
        for link in links:
            if link:
                try:
                    driver.get(link.urls)
                    try:
                        elem = WebDriverWait(driver, 300).until(EC.presence_of_element_located(
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

                                    # Показать елемент с которым производится действие
                                    # print(linkss[i].get_attribute('outerHTML'))

                                    preloader = driver.find_element(
                                        By.CLASS_NAME, 'agrid-loader')
                                    if preloader.is_displayed():
                                        print("Ожидание 5 секунд")
                                        time.sleep(5)
                                    else:

                                        # Условие для сработки скрола
                                        if links[i].find_element(By.CLASS_NAME, 'k-filter').is_displayed():
                                            print("element is visible")
                                            pass
                                        else:
                                            print("element invisible - scroll")
                                            option = driver.find_element(
                                                By.CLASS_NAME, 'mCSB_scrollTools_horizontal')
                                            gragbar_size = option.size
                                            gragbar_width = gragbar_size['width']

                                            scrollbar = option.find_element(
                                                By.CLASS_NAME, 'mCSB_dragger')
                                            scrollbar_size = scrollbar.size
                                            scrollbar_width = scrollbar_size['width']

                                            # Показать елемент с которым производится действие
                                            # print(scrollbar.get_attribute('outerHTML'))

                                            # Подвинуть скрона 1000px
                                            action = ActionChains(driver)
                                            action.drag_and_drop_by_offset(
                                                scrollbar, gragbar_width-scrollbar_width, 1)
                                            action.release()
                                            action.perform()

                                        # Клик по фильтру
                                        # print(new_links[i].find_element(By.CLASS_NAME, 'k-filter'))

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

                                        if len(links) == len(new_links):
                                            pass
                                        else:
                                            # Переприсваиваем состав фильтров на новый состав
                                            i = 0
                                            links = new_links

                                        i = i + 1
                                except (TimeoutException, NoSuchElementException, WebDriverException, Exception, MaxRetriesExceededError) as e:
                                    print("Произошла ошибка")
                                    driver.quit()
                                    # continue

                            time.sleep(5)
                            menu = driver.find_element(
                                By.CLASS_NAME, 'filt_btns')
                            menu.find_element(
                                By.CLASS_NAME, 'blue_btn').click()
                            time.sleep(1)
                            driver.find_element(
                                By.ID, 'download_sdmx_file').click()

                            time.sleep(5)
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
                                f = io.StringIO(sdmx_content)
                                ET.parse(f)
                                validate_status = True
                            except Exception as e:
                                print("Показатель ", link.description,
                                      " - XML не соответвует формату XML, требутся привести в соответствие формату XML")
                                validate_status = False

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

                except (TimeoutException, NoSuchElementException, WebDriverException, Exception, MaxRetriesExceededError) as e:
                    with transaction.atomic():
                        sdmx = SDMX(
                            index=link.name_index,
                            links_id=link,
                            description=link.description,
                            parse_status=False,
                        )
                        sdmx.save()
                    driver.quit()
                    return (link.name_index, "error parsing")
                    # continue

        else:
            print("Отсутствуют данные для парсинга, необходимо проверить наличие и активность показателей ЦУР в административном интерфейсе")
            driver.quit()
