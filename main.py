import os
from itertools import count

import requests
from dotenv import load_dotenv
from loguru import logger
from terminaltables import AsciiTable

HH_BASE_URL = "https://api.hh.ru/vacancies"
SJ_BASE_URL = "https://api.superjob.ru/2.0/vacancies/"
PROGRAMMING_CATEGORY_ID = 96
SEARCH_PERIOD = 30
HH_AREA_ID = 1
SJ_AREA_ID = 4
VACANCIES_PER_PAGE = 20
HH_MAX_PAGES = 99
PROGRAMMING_LANGUAGES = (
    "Python",
    "Java",
    "Perl",
    "JavaScript",
    "C++",
    "C#",
    "Go",
    "Ruby",
    "Php",
    "Rust",
    "1C",
)

TABLE_HEADERS = [
    [
        "Язык программирования",
        "Вакансий найдено",
        "Вакансий обработано",
        "Средняя зарплата",
    ],
]


def predict_salary(salary_from: int, salary_to: int) -> float or None:
    """Усредняем зарплаты в зависимости от того, указано ли "от" и/или "до\" """
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from and not salary_to:
        return salary_from * 1.2
    elif not salary_from and salary_to:
        return salary_to * 0.8


def predict_rub_salary_hh(vacancy):
    if vacancy["salary"] and vacancy["salary"]["currency"] == "RUR":
        salary_from = vacancy["salary"]["from"]
        salary_to = vacancy["salary"]["to"]
        return predict_salary(salary_from, salary_to)
    return False


def predict_rub_salary_sj(vacancy):
    salary_from = vacancy["payment_from"]
    salary_to = vacancy["payment_to"]
    if not (salary_from or salary_to):
        return False
    return predict_salary(salary_from, salary_to)


def get_api_response(url: str, payload: dict = None, headers: dict = None) -> str:
    """Отправляет Get запрос на указанный url"""
    response = requests.get(url, params=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def get_superjob_statistic(language: str, superjob_token: str):
    headers = {"X-Api-App-Id": superjob_token}
    average_salary, vacancies_processed, sum_salary = 0, 0, 0
    superjob_statistic = {}
    for page in count(0):
        payload = {
            "id": SJ_AREA_ID,
            "keywords": ["srws", 1, f"Программист {language}"],
            "page": f"{page}",
            "town": "Москва",
        }
        vacancies = get_api_response(SJ_BASE_URL, headers=headers, payload=payload)
        num_of_vacancies = vacancies["total"]
        if not num_of_vacancies % VACANCIES_PER_PAGE:
            num_of_pages = num_of_vacancies // VACANCIES_PER_PAGE
        else:
            num_of_pages = num_of_vacancies // VACANCIES_PER_PAGE + 1
        if page >= num_of_pages:
            break
        logger.info(f"Superjob, язык {language}, стр. {page+1} из {num_of_pages}..")
        superjob_statistic[language] = {"vacancies_found": num_of_vacancies}
        for vacancy in vacancies["objects"]:
            if predicted_rub_salary := predict_rub_salary_sj(vacancy):
                sum_salary += int(predicted_rub_salary)
                vacancies_processed += 1
    if sum_salary:
        average_salary = sum_salary / vacancies_processed
        superjob_statistic[language]["average_salary"] = int(average_salary)
    if vacancies_processed:
        superjob_statistic[language]["vacancies_processed"] = vacancies_processed
    return superjob_statistic


def get_headhunter_statistic(language: str) -> dict[dict]:
    """Парсит вакансии по переданному на вход языку программирования,
    возвращает объект с информацией по языку"""
    average_salary, vacancies_processed, sum_salary = 0, 0, 0
    headhunter_statistic = {}
    for page in count(0):
        payload = {
            "professional_role": PROGRAMMING_CATEGORY_ID,
            "period": SEARCH_PERIOD,
            "area": HH_AREA_ID,
            "text": language,
            "page": page,
        }
        language_page = get_api_response(HH_BASE_URL, payload=payload)
        if page >= language_page["pages"] or page >= HH_MAX_PAGES:
            break
        logger.info(
            f"HeadHunter, язык {language}, стр. {page+1} из {language_page['pages']}"
        )
        headhunter_statistic[language] = {"vacancies_found": language_page["found"]}
        for vacancy in language_page["items"]:
            if predicted_rub_salary := predict_rub_salary_hh(vacancy):
                sum_salary += int(predicted_rub_salary)
                vacancies_processed += 1
    if sum_salary:
        average_salary = sum_salary / vacancies_processed
        headhunter_statistic[language]["average_salary"] = int(average_salary)
    if vacancies_processed:
        headhunter_statistic[language]["vacancies_processed"] = vacancies_processed
    return headhunter_statistic


def get_statistic_as_table(title: str, all_vacancies: dict):
    """Возвращает вакансии в виде таблицы terminaltable"""
    table_body = [
        [
            language,
            all_vacancies[language]["vacancies_found"],
            all_vacancies[language]["vacancies_processed"],
            all_vacancies[language]["average_salary"],
        ]
        for language in all_vacancies
    ]
    full_table = TABLE_HEADERS + table_body
    table_instance = AsciiTable(full_table, title)
    table_instance.justify_columns[2] = "right"
    return table_instance.table


def main() -> None:
    """Формирует финальный результат и выводит на экран"""
    load_dotenv()
    superjob_token = os.environ.get("SUPERJOB_TOKEN")
    all_hh_statistic, all_sj_statistic = {}, {}
    for language in PROGRAMMING_LANGUAGES:
        sj_statistic = get_superjob_statistic(language, superjob_token)
        if sj_statistic:
            all_sj_statistic[language] = sj_statistic[language]
        all_hh_statistic[language] = get_headhunter_statistic(language)[language]
    print(get_statistic_as_table("SuperJob", all_sj_statistic))
    print(get_statistic_as_table("HeadHunter", all_hh_statistic))


if __name__ == "__main__":
    main()
