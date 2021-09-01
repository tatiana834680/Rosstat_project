from django.core.management.base import BaseCommand
from emiss_parse.models import Links, Data, SDMX, Dictionary, DictionaryPrimary
from bs4 import BeautifulSoup
from django.db import transaction
from dateutil.parser import parse
import pytz


class Command(BaseCommand):
    help = 'Команда запуска парсинга SDMX'
    # Команда вызова обновления всех таблиц кодов из Россвязи

    def handle(self, *args, **options):
        # Константа отсутсвующих данных
        const_out_value = '_T'
        sdmx_datas = SDMX.objects.filter(
            validate_status=True).filter(activity=True).filter(parse_status=True)
        my_tz = pytz.timezone('Europe/Moscow')
        for sdmx_data in sdmx_datas:
            soup = BeautifulSoup(sdmx_data.sdmx_data, 'xml')
            data_set = soup.find_all("generic:Series")
            indicator_name = soup.find("Indicator")['name']
            last_update = soup.find("LastUpdate")['value']
            periodicity_value = soup.find("Periodicity")['value']
            print(indicator_name)

            try:
                check_value_in_dictionary_primary = DictionaryPrimary.objects.get(
                    concept_name='RERIODISITY',
                    value=periodicity_value
                )
            except DictionaryPrimary.DoesNotExist:

                with transaction.atomic():
                    dictionary_primary = DictionaryPrimary(
                        concept_name='RERIODISITY',
                        value=periodicity_value
                    )
                    dictionary_primary.save()

            # Структура с данными
            data_set = soup.find_all("generic:Series")
            for data_set_item in data_set:
                json_data = []
                year = data_set_item.find("generic:Time")
                if year:
                    year = data_set_item.find("generic:Time").get_text()
                else:
                    year = const_out_value

                value_data = data_set_item.find(
                    "generic:ObsValue")['value']
                generic_Value = data_set_item.find_all("generic:Value")
                generic_SeriesKeys = data_set_item.find(
                    "generic:SeriesKey")
                generic_SeriesKeys_values = generic_SeriesKeys.find_all(
                    'generic:Value')
                for generic_SeriesKey in generic_SeriesKeys_values:
                    concept = generic_SeriesKey['concept']
                    value = generic_SeriesKey['value']

                    json_data.append({'concept': concept, 'value': value})
                    codeLists = soup.find_all("structure:CodeList")
                    for codelist in codeLists:
                        structureCodeList = codelist['id']
                        structurename = codelist.find(
                            'structure:Name').get_text()
                        if concept == structureCodeList:
                            structureCodes = codelist.find_all(
                                'structure:Code')
                            for structureCode in structureCodes:
                                if structureCode['value'] == value:
                                    structureCodeValue = structureCode['value']
                                    structureDescription = structureCode.find(
                                        'structure:Description').get_text()

                                    try:
                                        check_value_in_dictionary = Dictionary.objects.get(
                                            codelist_id=structureCodeList,
                                            codelist_name=structurename,
                                            code_value=structureCodeValue,
                                            code_description=structureDescription)
                                    except Dictionary.DoesNotExist:

                                        with transaction.atomic():
                                            dictionary = Dictionary(
                                                codelist_id=structureCodeList,
                                                codelist_name=structurename,
                                                code_value=structureCodeValue,
                                                code_description=structureDescription,
                                            )
                                            dictionary.save()

                for value in generic_Value:
                    if value['concept'] == 'EI':
                        value_ei = value['value']

                    if value['concept'] == 'PERIOD':
                        value_period = value['value']

                    if (value['concept'] == 'EI') or (value['concept'] == 'PERIOD'):
                        try:
                            check_value_in_dictionary_primary = DictionaryPrimary.objects.get(
                                concept_name=value['concept'],

                                value=value['value']
                            )
                        except DictionaryPrimary.DoesNotExist:

                            with transaction.atomic():
                                dictionary_primary = DictionaryPrimary(
                                    concept_name=value['concept'],

                                    value=value['value']
                                )
                                dictionary_primary.save()

                check_value_in_data = Data.objects.filter(
                    index_value=sdmx_data.links_id.name_index,
                    period=value_period,
                    year=year,
                    index=indicator_name,
                    value=value_data,
                    ei=value_ei,
                    sdmx_id=sdmx_data,
                    series_key_data=json_data,
                    last_update=my_tz.localize(parse(
                        last_update)),
                    periodicity=periodicity_value,
                )

                if check_value_in_data:
                    print(indicator_name, "- Дубликат")
                else:
                    with transaction.atomic():
                        data = Data(
                            index_value=sdmx_data.links_id.name_index,
                            period=value_period,
                            year=year,
                            index=indicator_name,
                            value=value_data,
                            ei=value_ei,
                            sdmx_id=sdmx_data,
                            series_key_data=json_data,
                            last_update=my_tz.localize(parse(
                                last_update)),
                            periodicity=periodicity_value,

                        )
                        data.save()
