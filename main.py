import os
from itertools import count
from pprint import pprint

import requests
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

HH_BASE_URL = "https://api.hh.ru/vacancies"
SUPERJOB_BASE_URL = "https://api.superjob.ru/2.0/vacancies/"
PROGRAMMING_CATEGORY_ID = 96
SEARCH_PERIOD = 30
AREA_ID = 1
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
)

ENDPOINT = "https://api.hh.ru/vacancies"


def predict_rub_salary(salary_from, salary_to) -> float or None:
    """Усредняем зарплаты в зависимости от того, указано ли "от" и/или "до\" """
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from and not salary_to:
        return salary_from * 1.2
    elif not salary_from and salary_to:
        return salary_to * 0.8


def predict_rub_salary_hh(vacancy):
    # pprint(vacancy)
    if vacancy["salary"]:
        if vacancy["salary"]["currency"] != "RUR":
            return False
        salary_from = vacancy["salary"]["from"]
        salary_to = vacancy["salary"]["to"]
        return predict_rub_salary(salary_from, salary_to)


def predict_rub_salary_sj(vacancy):
    salary_from = vacancy["payment_from"]
    salary_to = vacancy["payment_to"]
    return (
        False
        if not (salary_from or salary_to)
        else predict_rub_salary(salary_from, salary_to)
    )


def get_json_data(url: str, payload: dict = None, headers: dict = None) -> str:
    """Отправляет Get запрос на указанный url, возвращает jSON"""
    response = requests.get(url, params=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def get_superjob_vacancy(language: str = None):
    headers = {"X-Api-App-Id": os.environ.get("SUPERJOB_KEY")}
    average_salary, vacancies_processed, sum_salary = 0, 0, 0
    vacancies_by_language = {}
    for page in count(0):
        payload = {
            "id": 4,
            "keywords": ["srws", 1, f"Программист {language}"],
            "page": f"{page}",
            "count": 20,
            "town": "Москва",
        }
        vacancies = get_json_data(SUPERJOB_BASE_URL, headers=headers, payload=payload)
        num_of_vacancies = vacancies["total"]
        num_of_pages = (
            num_of_vacancies // 20
            if num_of_vacancies % 20 == 0
            else num_of_vacancies // 20 + 1
        )
        if page >= num_of_pages:
            break
        vacancies_by_language[language] = {"vacancies_found": num_of_vacancies}
        print(f"Парсинг SJ языка {language}, страница {page} из {num_of_pages}..")
        for vacancy in vacancies["objects"]:
            if predict_rub_salary_sj(vacancy):
                sum_salary += int(predict_rub_salary_sj(vacancy))
                vacancies_processed += 1
    if sum_salary and vacancies_processed:
        average_salary = sum_salary / vacancies_processed
        vacancies_by_language[language].update(
            {"vacancies_processed": vacancies_processed}
        )
        vacancies_by_language[language].update({"average_salary": int(average_salary)})
        return vacancies_by_language


def get_salary_by_language(language: str) -> dict[dict]:
    """Парсит вакансии по переданному на вход языку программирования,
    возвращает объект с информацией по языку"""
    average_salary, vacancies_processed, sum_salary = 0, 0, 0
    vacancies_by_language = {}
    for page in count(0):
        payload = {
            "professional_role": PROGRAMMING_CATEGORY_ID,
            "period": SEARCH_PERIOD,
            "area": AREA_ID,
            "text": language,
            "page": page,
        }
        language_page = get_json_data(ENDPOINT, payload=payload)
        print(
            f"Парсинг HH языка {language}, страница {page} из {language_page['pages']} ..."
        )
        if page >= language_page["pages"] or page >= 99:
            break
        vacancies_by_language[language] = {"vacancies_found": language_page["found"]}
        for vacancy in language_page["items"]:
            if predict_rub_salary_hh(vacancy):
                sum_salary += int(predict_rub_salary_hh(vacancy))
                vacancies_processed += 1
    average_salary = sum_salary / vacancies_processed
    vacancies_by_language[language].update({"vacancies_processed": vacancies_processed})
    vacancies_by_language[language].update({"average_salary": int(average_salary)})
    return vacancies_by_language


def main() -> None:
    """Формирует финальный результат и выводит на экран"""
    hh_result, sj_result = {}, {}
    for language in PROGRAMMING_LANGUAGES:
        sj_data = get_superjob_vacancy(language)
        if sj_data:
            sj_result.update(get_superjob_vacancy(language))
        hh_result.update(get_salary_by_language(language))
    pprint(hh_result)
    pprint(sj_result)


if __name__ == "__main__":
    main()
