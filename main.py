from itertools import count
from pprint import pprint

import requests

HH_BASE_URL = 'https://api.hh.ru/vacancies'
PROGRAMMING_CATEGORY_ID = 96
SEARCH_PERIOD = 30
AREA_ID = 1
PROGRAMMING_LANGUAGES = ('Python', 'Java', 'Perl',
                         'JavaScript', 'C++', 'C#', 'Go', 'Ruby', 'Php', 'Rust')
ENDPOINT = "https://api.hh.ru/vacancies"


def predict_rub_salary(vacancy) -> float or None:
    """Усредняем зарплаты в зависимости от того, указано ли "от" и/или "до\""""
    if vacancy["salary"]:
        if vacancy["salary"]["currency"] != "RUR":
            return False
        vacancy_from, vacancy_to = vacancy["salary"]["from"], vacancy["salary"]["to"]
        if vacancy_from and vacancy_to:
            return (vacancy_from + vacancy_to) / 2
        elif vacancy_from and not vacancy_to:
            return vacancy_from * 1.2
        elif not vacancy_from and vacancy_to:
            return vacancy_to * 0.8


def get_json_data(url: str, payload: dict) -> str:
    """Отправляет Get запрос на указанный url, возвращает jSON"""
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response.json()


def get_salary_by_language(language: str) -> dict[dict]:
    """Парсит вакансии по переданному на вход языку программирования,
    возвращает объект с информацией по языку"""
    average_salary, vacancies_processed, sum_salary = 0, 0, 0
    vacancies_by_language = {}
    for page in count(0):
        payload_page = {'professional_role': PROGRAMMING_CATEGORY_ID,
                        'period': SEARCH_PERIOD, 'area': AREA_ID,
                        'text': language, 'page': page
                        }
        language_page = get_json_data(ENDPOINT, payload=payload_page)
        print(
            f"Парсинг вакансий языка {language}, страница {page} из {language_page['pages']} ...")
        if page >= language_page["pages"]:
            break
        vacancies_by_language[language] = {
            "vacancies_found": language_page["found"]}
        for vacancy in language_page["items"]:
            if predict_rub_salary(vacancy):
                sum_salary += int(predict_rub_salary(vacancy))
                vacancies_processed += 1
    average_salary = sum_salary/vacancies_processed
    vacancies_by_language[language].update(
        {'vacancies_processed': vacancies_processed})
    vacancies_by_language[language].update(
        {'average_salary': int(average_salary)})
    return vacancies_by_language


def main() -> None:
    """Формирует финальный результат и выводит на экран"""
    result = {}
    for language in PROGRAMMING_LANGUAGES:
        result.update(get_salary_by_language(language))
    pprint(result)


if __name__ == "__main__":
    main()
