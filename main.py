from pprint import pprint

import requests

ENDPOINT = "https://api.hh.ru/vacancies"


def get_json_data(url: str) -> str:
    """get page data

    Args:
        url (str): API endpoint

    Returns:
        str: JSON object
    """
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def main():
    vac = get_json_data(ENDPOINT)
    pprint(vac, indent=4)


if __name__ == "__main__":
    main()
