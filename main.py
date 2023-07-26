import csv

import requests
from bs4 import BeautifulSoup


def main() -> None:
    word = input("Write the word here: ")

    url = 'https://dic.b-amooz.com/de/dictionary/conjugation/v?verb=' + word
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    present_table = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-body.px-0.pb-0 > div > div > div:nth-child(1) > div > div:nth-child(1) > table")
    past_table = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-body.px-0.pb-0 > div > div > div:nth-child(1) > div > div:nth-child(3) > table")

    with open("template.html", "r") as template:
        html_template = template.read()

    for i in (0, 2):
        for j in range(1, 7):
            table = present_table if i == 0 else past_table

            result = table.select_one(f"table > tr:nth-child({j}) > td:nth-child(2) > span")

            if result.attrs['class'][0] == 'normal':
                result = f"<span style=\"color: #000\">{result.text.strip()}</span>"
            elif result.attrs['class'][0] == 'irregular':
                result = f"<span style=\"color: red\">{result.text.strip()}</span>"
            else:
                result = f"<span style=\"color: blue\">{result.text.strip()}</span>"

            html_template = html_template.replace(f">present_{j}<" if i == 0 else f">past_{j}<", f">{result}<")

    infinitive = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(1) > span")
    third_state = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(3) > span")
    past = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(2) > span")
    html_template = html_template.replace(">infinitive<", f'>{infinitive.text.strip()}<')
    html_template = html_template.replace(">past<", f'>{past.text.strip()}<')
    html_template = html_template.replace(">third_state<", f'>{third_state.text.strip()}<')

    # Write the data to a CSV file
    with open('output.csv', 'a', newline="", encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([html_template])


if __name__ == '__main__':
    main()
