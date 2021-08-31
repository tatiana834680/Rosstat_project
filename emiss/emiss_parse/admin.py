from django.contrib import admin
from django.db.models.expressions import F

# Register your models here.
from .models import Links, Data, SDMX, Dictionary, DictionaryPrimary
from django.http import HttpResponse
from rangefilter.filters import DateRangeFilter
from django.contrib import admin
import pandas as pd
from io import BytesIO
from UliPlot.XLSX import auto_adjust_xlsx_column_width
from django.utils.html import format_html
from django.core.management.base import BaseCommand
from emiss_parse.models import Links, Data, SDMX, Dictionary, DictionaryPrimary
from bs4 import BeautifulSoup
from django.db import transaction
from dateutil.parser import parse
from xml.etree import ElementTree as ET
import pytz


@admin.action(description='Обработать SDMX')
def parse_data(modeladmin, request, queryset):
    
    # Константа отсутсвующих данных
    const_out_value = '_T'
    sdmx_datas = queryset.filter(
        validate_status=True).filter(activity=True).filter(parse_status=True)
    
    # Таймзона для установки для дат без таймзоны
    my_tz = pytz.timezone('Europe/Moscow')
    
    for sdmx_data in sdmx_datas:
        soup = BeautifulSoup(sdmx_data.sdmx_data, 'xml')
        data_set = soup.find_all("generic:Series")
        indicator_name = soup.find("Indicator")['name']
        last_update = soup.find("LastUpdate")['value']
        periodicity_value = soup.find("Periodicity")['value']
        print(indicator_name)

        # Запись уникальных значений в словарь основных категорий
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

        # Обход структуры XML с данными
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
                
                # Формирование структуры для записи вариативных категорий
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

                                # Запись значений в словарь вариативных категорий
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
            
            # Запись значений в словарь основных категорий
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
            # Проверка на дубликаты
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


@admin.action(description='Активировать обработку')
def activate_links(modeladmin, request, queryset):
    queryset.update(activity=True)


@admin.action(description='Деактивировать обработку')
def de_activate_links(modeladmin, request, queryset):
    queryset.update(activity=False)


@admin.action(description='Экспорт в XLSX')
def excel_export(modeladmin, request, queryset):

    response = HttpResponse(content_type='text/xlsx')
    response['Content-Disposition'] = 'attachment; filename=excel.xlsx'
    column_name_list = []
    
    # Выбираем из словаря вариативных категорий все уникальные значения
    column_names = Dictionary.objects.values('codelist_name').distinct()
    for column_name in column_names:
        column_name_list.append(column_name['codelist_name'])

    # Вставка в состав колонок, колонок обязательных категорий
    column_name_list.insert(0, 'Индекс показателя')
    column_name_list.insert(1, 'Расшифровка')
    column_name_list.insert(2, 'Обозреваемый период')
    column_name_list.insert(3, 'Единица измерения')
    column_name_list.insert(4, 'Значение')
    column_name_list.insert(5, 'Период показателя')
    column_name_list.insert(6, 'Дата обновления данных')
    column_name_list.insert(7, 'Частота предоставления данных')

    rows = []
    for item in queryset:
        # Формируем список, длина которого равна количеству вариативных колонок
        row = ['_T']*len(column_name_list)
        
        # Обрабатываем значения в json и получаем эти значение из словая вариативных категорий
        list_jsons = item.series_key_data
        for json_item in list_jsons:
            concept = json_item['concept']
            value = json_item['value']

            get_value_in_dictionary = Dictionary.objects.get(
                codelist_id=concept,
                code_value=value,
            )
            column_name = get_value_in_dictionary.codelist_name

            if get_value_in_dictionary.short_name:
                column_value = get_value_in_dictionary.short_name
            else:
                column_value = get_value_in_dictionary.code_description
            index_data = column_name_list.index(column_name)
            row[index_data] = column_value

        # EI
        get_value_in_dictionary_primary_ei = DictionaryPrimary.objects.get(
            value=item.ei
        )
        if get_value_in_dictionary_primary_ei.short_name:
            Data_ei = get_value_in_dictionary_primary_ei.short_name
        else:
            Data_ei = item.ei

        # periodicity
        get_value_in_dictionary_primary_periodicity = DictionaryPrimary.objects.get(
            value=item.periodicity
        )
        if get_value_in_dictionary_primary_periodicity.short_name:
            Data_periodicity = get_value_in_dictionary_primary_periodicity.short_name
        else:
            Data_periodicity = item.periodicity

        Data_index_digit = item.index_value
        Data_value = item.value
        Data_period = item.period
        Data_year = item.year
        Data_index = item.index
        Data_last_update = item.last_update

        # Обязательные колонки
        row[0] = Data_index_digit
        row[1] = Data_index
        row[2] = Data_year
        row[3] = Data_ei
        row[4] = Data_value
        row[5] = Data_period
        row[6] = Data_last_update
        row[7] = Data_periodicity
        rows.append(row)

    # Выгрузка в виде файла
    b = BytesIO()
    df = pd.DataFrame(rows, columns=column_name_list)
    df['Значение'] = df['Значение'].replace(
        ',', '.', regex=True).astype(float)
    df['Дата обновления данных'] = df['Дата обновления данных'].dt.strftime(
        '%d.%m.%Y').astype(str)

    writer = pd.ExcelWriter(b, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Показатели')
    worksheet = writer.sheets['Показатели']

    auto_adjust_xlsx_column_width(
        df, writer, sheet_name="Показатели", margin=1)
    workbook = writer.book
    worksheet.set_column('A:A', 5)
    worksheet.autofilter(0, 0, df.shape[0], df.shape[1])
    writer.save()
    filename = 'data.xlsx'
    response = HttpResponse(
        b.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response


class LinksAdmin(admin.ModelAdmin):
    list_display = ('name_index', 'description', 'section',
                    'urls_formatted', 'activity', 'sdmx_downloaded',  'created')
    list_display_links = ['name_index']
    list_filter = ['name_index', 'section', ]
    actions = [activate_links, de_activate_links]

    def urls_formatted(self, obj):
        return format_html('<a href ='+obj.urls+' target = "_blank" rel = "noopener noreferrer" > '+obj.urls + ' </a>')
    urls_formatted.short_description = 'Ссылка на показатель'

    def sdmx_downloaded(self, obj):
        sdmx_data = SDMX.objects.filter(
            links_id=obj).filter(
            parse_status=True)
        if sdmx_data:
            return True
        else:
            return False
    sdmx_downloaded.boolean = True
    sdmx_downloaded.short_description = 'Статус получения SDMX'


class SDMXAdmin(admin.ModelAdmin):
    list_display = ('index', 'description',
                    'activity', 'parse_status', 'validate_status', 'created')
    list_display_links = ['index']
    list_filter = ['index', 'created', 'parse_status']
    actions = [activate_links, de_activate_links, parse_data]


class DataAdmin(admin.ModelAdmin):
    list_display = ('index_value', 'index', 'year', 'value',
                    'ei', 'series_key_data', 'last_update', 'periodicity', 'created')
    list_filter = ['index_value', 'created']
    # list_filter = (
    #     ('created', DateRangeFilter), ('created'), ('index'),
    # )
    ordering = ('index',)
    actions = [excel_export]


class DictionaryAdmin(admin.ModelAdmin):
    list_display = ('codelist_id', 'codelist_name',
                    'code_value', 'code_description', 'short_name')
    list_filter = ['codelist_name', 'codelist_id']


class DictionaryPrimaryAdmin(admin.ModelAdmin):
    list_display = ('concept_name', 'value',
                    'short_name')
    list_filter = ['concept_name']


admin.site.register(DictionaryPrimary, DictionaryPrimaryAdmin)
admin.site.register(Dictionary, DictionaryAdmin)
admin.site.register(Links, LinksAdmin)
admin.site.register(SDMX, SDMXAdmin)
admin.site.register(Data, DataAdmin)
