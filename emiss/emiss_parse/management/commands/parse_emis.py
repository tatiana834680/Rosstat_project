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
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded


class Command(BaseCommand):
    help = 'Команда запуска парсинга с https://rosstat.gov.ru/sdg/data  для получения ссылок на ЕМИСС'
    # Команда вызова обновления всех таблиц кодов из Россвязи

    def handle(self, *args, **options):
        try:
            capabilities = {
                "screenResolution": "5000x1080x24",
                "browserName": "chrome",
                "browserVersion": "91.0",
                "selenoid:options": {
                    "enableVNC": True,
                    "enableVideo": False,
                    "sessionTimeout": "2m",
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
                        print(link.name_index)
                        driver = webdriver.Remote(
                            command_executor='http://selenoid:4444/wd/hub', desired_capabilities=capabilities)
                        driver.maximize_window()
                        session_id = driver.session_id
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
                                time_counter = 0

                                # Проход по фильтрам
                                while i <= len(links)-1:
                                    try:
                                        # Проверка появлекния новых фильтров если новые фильты есть то переопределяем изначальный состав ссылок
                                        time.sleep(2)
                                        links = driver.find_elements(
                                            By.CLASS_NAME, 'k-header:not(.hidden-col)')

                                        preloader = driver.find_element(
                                            By.CLASS_NAME, 'agrid-loader')

                                        if time_counter != 50:
                                            if preloader.is_displayed():
                                                print("Ожидание 5 секунд")
                                                time.sleep(5)
                                                time_counter = time_counter+5
                                                print('time_counter ',
                                                    time_counter)
                                            else:
                                                time_counter = 0
                                                # Условие для сработки скрола
                                                Link_is_displayed = links[i].find_element(
                                                    By.CLASS_NAME, 'k-filter')
                                                if Link_is_displayed.is_displayed():
                                                    print("element is visible")
                                                    pass
                                                else:
                                                    print(
                                                        "element invisible - scroll")
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
                                                            print(
                                                                "scroll drug is out")
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

                                                    # ТУТ ДОБАВИТЬ ПРОВЕРКУ НА PRELOADER
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
                                                        time.sleep(5)

                                                new_links = driver.find_elements(
                                                    By.CLASS_NAME, 'k-header:not(.hidden-col)')

                                                # Условие проверки появления новыз фильтров
                                                if len(links) == len(new_links):
                                                    pass
                                                else:
                                                    # Переприсваиваем состав фильтров на новый состав
                                                    i = 0
                                                    links = new_links
                                        else:
                                            print("quit counter 50")
                                            driver.quit()
                                            # continue

                                        i = i + 1
                                    except (NoSuchElementException, WebDriverException) as e:
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
                                                    validate_status=False,
                                                )
                                                sdmx.save()

                                        print("quit exeption")
                                        print("exeption on while")
                                        driver.quit()
                                        # continue

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
                                if session_id:
                                    url = 'http://selenoid:4444/download/' + \
                                        session_id+'/' + \
                                        os.environ['EMISS_FILE_MANE']
                                    response = requests.get(url)
                                    if response.status_code != 200:
                                        counter = 1
                                        while response.status_code != 200 and counter != 20:
                                            url = 'http://selenoid:4444/download/' + \
                                                session_id+'/' + \
                                                os.environ['EMISS_FILE_MANE']
                                            response = requests.get(url)
                                            counter = counter+1

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
                                            print("SDMX saved")
                                            driver.quit()

                    except (WebDriverException, NoSuchElementException, TimeoutException, TimeLimitExceeded, SoftTimeLimitExceeded, MaxRetriesExceededError) as e:
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
                                    validate_status=False,
                                )
                                sdmx.save()

                        print("quit exeption save")
                        print("exeption on for link")
                        driver.quit()
                        # continue
                else:
                    print("Отсутствуют данные для парсинга, необходимо проверить наличие и активность показателей ЦУР в административном интерфейсе")
                    driver.quit()

        except SoftTimeLimitExceeded as e:
            print("SoftTimeLimitExceeded")
            driver.quit()
            print("quit SoftTimeLimitExceeded")
