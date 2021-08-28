## Инструкция
### Предварительные действия:
Установка Docker - официальное руководство: https://docs.docker.com/get-docker/

Корректность установки необходимо проверить командой в терминале:

 ```docker --version```  

**Вывод:**  
 ```
Docker version 20.10.7, build f0df350  
 ```
Установка Docker-compose - официальное руководство:  https://docs.docker.com/compose/

Корректность установки необходимо проверить командой в терминале:

 ```docker-compose --version ```  

**Вывод:**  
 ```
 Docker Compose version v2.0.0-beta.6   
 ```
Скачивание образа браузера Chrome (команда):

```docker pull selenoid/chrome:91.0```  



### Запуск проекта:

Расположение проекта на github: https://github.com/tatiana834680/emiss.git  

Необходимо перейти в директорию проекта и запустить сборку командой:

```docker-compose build```  

Запуск проекта (команда):

```docker-compose up -d```  

### Перечень команд управления приложением (последовательное выполнение):  
**Ручной запуск парсинга ссылок на показатели:**  

```docker-compose exec WEB python3 manage.py parse_link```  

**Ручной запуск выгрузки SDMX:**  

```docker-compose exec WEB python3 manage.py parse_emis```  

**Ручной запуск обработки (парсинга) SDMX:** 

```docker-compose exec WEB python3 manage.py parse_data```  

##### Интерфейсы приложения:  
Django http://localhost:8000/admin    
Selenoid http://localhost:8081    
PgAdmin4 http://localhost:8082    
Учетные данные к сервисам расположены в .env файле в директории проекта.   
