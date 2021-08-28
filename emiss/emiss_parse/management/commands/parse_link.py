from django.core.management.base import BaseCommand
from emiss_parse.models import Links 
from bs4 import BeautifulSoup
from django.db import transaction
import requests
class Command(BaseCommand):
    help = 'Команда запуска парсинга с https://rosstat.gov.ru/sdg/data  для получения ссылок на ЕМИСС'
    # Команда вызова обновления всех таблиц кодов из Россвязи

    def handle(self, *args, **options):
        url = 'https://rosstat.gov.ru/sdg/data'
        page = requests.get(url)
        if page.status_code == 200:

            soup_group = BeautifulSoup(
                page.text, 'html.parser')
            all_group_raw = soup_group.findAll('div', class_='cards-color__item')
            for link_raw in all_group_raw:
                group_link = link_raw.find('a', class_='card-color__wrap').get('href')
                page_inside_group = requests.get(group_link)
                soup_page = BeautifulSoup(
                    page_inside_group.text, 'html.parser')
                section_index = soup_page.find('div', class_='title-page').get_text(
                ).replace('\n', '').replace('\r', '').replace('\t', '')
                main_container_indicators = soup_page.find('div', class_='grid-cards')
                indicator_row = main_container_indicators.findAll(
                    'div', class_='col-md-6')
                for indicator in indicator_row:
                    indicator_number = indicator.find(
                        'div', class_='card-sdk__title').get_text()
                    indicator_description = indicator.find(
                        'div', class_='card-sdk__desc').get_text()
                    link_indicators = indicator.find(
                        'a', class_='btn-light').get('href')
                    if link_indicators != '#':
                        print(indicator_number, link_indicators)
                        print(indicator_description)
                        print(section_index)
                        
                        check_link_dublicate = Links.objects.filter(
                                urls=link_indicators)

                        if check_link_dublicate:
                            print(link_indicators, indicator_description, "- Дубликат")
                        else:
                            with transaction.atomic():
                                links=Links(
                                    urls = link_indicators,
                                    name_index = indicator_number,
                                    description = indicator_description,
                                    section=section_index,
                            )
                                links.save()

        else:
            print("Ошибка при подучении данных rosstat.gov.ru")
