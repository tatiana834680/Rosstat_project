from django.db import models

# Create your models here.
class Links(models.Model):
    created = models.DateTimeField(
        verbose_name='Дата создания', auto_now_add=True)
    urls = models.CharField(max_length=1000, verbose_name='Ссылка показателя на ЕМИСC')
    name_index = models.CharField(max_length=1000, verbose_name='Наименование индекса')
    description = models.CharField(
        max_length=1000, verbose_name='Описание индекса',blank=True, null=True,)
    section  = models.CharField(
        max_length=1000, verbose_name='Раздел индекса', blank=True, null=True)
    activity = models.BooleanField(
        verbose_name='Активность', default=True)

    class Meta:
        verbose_name = 'Показатель'
        verbose_name_plural = 'Показатели ЦУР'


class SDMX(models.Model):
    created = models.DateTimeField(
        verbose_name='Дата создания', auto_now_add=True)
    links_id = models.ForeignKey(
        Links, on_delete=models.CASCADE, verbose_name='Ссылка на показатель')
    sdmx_data = models.TextField(verbose_name='SDMX данные',blank=True, null=True,)
    index = models.CharField(
        max_length=1000, verbose_name='Наименование индекса', blank=True, null=True,)
    description = models.CharField(
        max_length=1000, verbose_name='Описание индекса', blank=True, null=True,)
    parse_status = models.BooleanField(verbose_name='Статус получения SDMX',default=False)
    activity = models.BooleanField(
        verbose_name='Активность', default=True)
    validate_status = models.BooleanField(
        verbose_name='Соответствие структуре SDMX', default=False)

    class Meta:
        verbose_name = 'SDMX файл'
        verbose_name_plural = 'SDMX файлы'
        ordering = ['index']


class Data(models.Model):
    index_value = models.CharField(
        max_length=1000, verbose_name='Индекс', blank=True, null=True,)
    created = models.DateTimeField(
        verbose_name='Дата создания', auto_now_add=True)
    period = models.CharField(
        max_length=1000, verbose_name='Период')
    year = models.CharField(max_length=1000, blank=True,
                            null=True, verbose_name='Год')
    index = models.TextField(
        max_length=1000, verbose_name='Показатель', blank=True, null=True,)
    value = models.CharField(
        max_length=1000, verbose_name='Значение', blank=True, null=True,)
    ei = models.CharField(
        max_length=1000, verbose_name='Единица изменения', blank=True, null=True,)
    sdmx_id = models.ForeignKey(
        SDMX, on_delete=models.CASCADE, verbose_name='Ссылка на SDMX')
    series_key_data = models.JSONField(verbose_name='Массив вариативных категорий',blank=True, null=True,)
    last_update = models.DateTimeField(
        verbose_name='Дата обновления данных', blank=True, null=True)
    periodicity = models.CharField(
        max_length=1000, verbose_name='Частота предоставления данных', blank=True, null=True,)

    class Meta:
        verbose_name = 'Данные'
        verbose_name_plural = 'Данные из SDMX'


class Dictionary(models.Model):
    codelist_id = models.CharField(max_length=1000 )
    codelist_name = models.CharField(max_length=1000 )
    code_value = models.CharField(max_length = 1000)
    code_description = models.CharField(max_length=1000)
    short_name = models.CharField(max_length=1000, blank=True, null=True,)

    class Meta:
        verbose_name = 'Словарь вариативных категорий'
        verbose_name_plural = 'Словарь вариативных категорий'


class DictionaryPrimary(models.Model):
    concept_name = models.CharField(max_length=1000)
    value = models.CharField(max_length=1000)
    category_name = models.CharField(
        max_length=1000, blank=True, null=True,)
    short_name = models.CharField( max_length=1000,  blank=True, null=True,)

    class Meta:
        verbose_name = 'Словарь основных категорий'
        verbose_name_plural = 'Словарь основных категорий'
