"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import datetime
import logging
import time

import dateutil.parser
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import NoSuchElementException

from src.spp.types import SPP_document


class RFC:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'rfc'
    _content_document: list[SPP_document]

    HOST = "https://www.rfc-editor.org/rfc/"

    def __init__(self, webdriver: WebDriver, max_count_documents: int = 100, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver
        self.max_count_documents = max_count_documents

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        self._parse()
        self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -

        self.driver.get(self.HOST)

        links_list = self.driver.find_elements(By.TAG_NAME, 'a')
        """Список всех ссылок, которые есть на странице"""

        self.logger.info('Поиск новых материалов... Может занять долгое время (>20 мин.)')

        for link in links_list:

            filename = link.text
            """22. Название файла с расширением"""

            web_link = link.get_attribute('href')
            """21. Веб-ссылка на материал"""

            # self.logger.debug(f'Текущая ссылка: {web_link}')

            if '.txt' in web_link:

                self.logger.debug(f'Загрузка и обработка документа: {web_link}')

                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(web_link)
                time.sleep(1)

                doc_page_content = self.driver.find_element(By.TAG_NAME, 'body').text
                """Содержимое страницы документа"""

                doc_name = filename.split('.')[0]
                """Название материала (название файла без расширения)"""

                info_link = f'https://www.rfc-editor.org/info/{doc_name}'
                """23. Веб-ссылка на информацию о материале"""

                # Открыть ссылку с информацией о материале в той же вкладке
                self.driver.get(info_link)
                time.sleep(1)

                self.logger.debug(f'Открыта ссылка с информацией: {info_link}')

                """Парсинг информации по ссылке info_link"""

                try:
                    full_title = self.driver.find_element(By.CLASS_NAME, 'entryheader').text

                    if ('STD' in full_title) or ('FYI' in full_title) or ('BCP' in full_title):
                        title = full_title.split('\n')[2]
                    else:
                        title = full_title.split('\n')[1]

                    date_text = ' '.join(title.split(' ')[-2:])

                    title = ' '.join(title.split(' ')[:-2])[:-1]
                    """4. Заголовок материала"""

                    date = datetime.datetime.strptime(date_text, '%B %Y')
                    """5. Дата публикации материала"""
                except:
                    self.logger.debug('Не удалось сохранить название или дату публикации материала')
                    title = ''
                    date = ''

                try:
                    abstract_title = self.driver.find_element(By.XPATH, '//*[text()=\'Abstract\']')
                    abstract = abstract_title.find_element(By.XPATH, './following::p').text
                    """6. Аннотация к материалу"""

                except:
                    self.logger.debug('Не удалось сохранить аннотацию материала')
                    abstract = ''

                try:
                    dl_el = self.driver.find_element(By.TAG_NAME, 'dl')
                    dt_els = dl_el.find_elements(By.TAG_NAME, 'dt')
                    category = ''
                    authors = ''
                    stream = ''
                    source = ''
                    updates = ''
                    obsoletes = ''
                    updated_by = ''
                    obsoleted_by = ''
                    for dt_el in dt_els:
                        sibling_dd = dt_el.find_elements(By.XPATH, './following-sibling::dd')[0]
                        if dt_el.text == 'Status:':
                            category = sibling_dd.text
                            """3. Категория документа в терминологии RFC"""

                        elif (dt_el.text == 'Authors:') or (dt_el.text == 'Author:'):
                            authors = sibling_dd.text
                            """26. Автор(ы) материала"""

                        elif dt_el.text == 'Stream:':
                            stream = sibling_dd.text
                            """27. Поток документа в терминологии RFC"""

                        elif dt_el.text == 'Source:':
                            source = sibling_dd.text
                            """28. Источник (рабочая группа) в терминологии RFC"""

                        elif dt_el.text == 'Updates:':
                            updates = sibling_dd.text
                            """29. Материал(ы), который обновляется текущим"""

                        elif dt_el.text == 'Obsoletes:':
                            obsoletes = sibling_dd.text
                            """30. Материал(ы), который устаревает вследствие публикации текущего"""

                        elif dt_el.text == 'Updated by:':
                            updated_by = sibling_dd.text
                            """32. Материал(ы), которые обновляют текущий"""

                        elif dt_el.text == 'Obsoleted by:':
                            obsoleted_by = sibling_dd.text
                            """32. Материал(ы), которые делают текущий устаревшим"""
                except:
                    self.logger.debug('Не удалось сохранить доп. информацию о материале')
                    category = ''
                    authors = ''
                    stream = ''
                    source = ''
                    updates = ''
                    obsoletes = ''
                    updated_by = ''
                    obsoleted_by = ''

                other_data = {'category': category,
                              'authors': authors,
                              'stream': stream,
                              'source': source,
                              'updates': updates,
                              'obsoletes': obsoletes,
                              'updated_by': updated_by,
                              'obsoleted_by': obsoleted_by}

                doc = SPP_document(None,
                                   title,
                                   abstract,
                                   doc_page_content,
                                   web_link,
                                   None,
                                   other_data,
                                   date,
                                   datetime.datetime.now())
                self._content_document.append(doc)
                self.logger.info(self._find_document_text_for_logger(doc))

                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"
