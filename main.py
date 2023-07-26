import csv

import requests
from bs4 import BeautifulSoup


def main() -> None:
    word = input("Write the word here: ")

    url = 'https://dic.b-amooz.com/de/dictionary/conjugation/v?verb=' + word
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    html_table = soup.select_one(
        "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-body.px-0.pb-0 > div > div > div:nth-child(1) > div > div:nth-child(1) > table")
    html_template = ('<table style="width: 100%; border: 1px solid black;border-radius: 10px;border-spacing: 5px;">\n'
                     '    <tbody>\n'
                     '        <tr><td>ich</td><td>string_1</td></tr>\n'
                     '        <tr style="background-color: #D6EEEE;"><td>du</td><td>string_2</td></tr>\n'
                     '        <tr><td>er/sie/es</td><td>string_3</td></tr>\n'
                     '        <tr style="background-color: #D6EEEE;"><td>wir</td><td>string_4</td></tr>\n'
                     '        <tr><td>ihr</td><td>string_5</td></tr>\n'
                     '        <tr style="background-color: #D6EEEE;"><td>sie/Sie</td><td>string_6</td></tr>\n'
                     '    </tbody>\n'
                     '</table>')
    for i in range(1, 7):
        result = html_table.select_one(f"table > tr:nth-child({i}) > td:nth-child(2) > span").text.strip()
        html_template = html_template.replace(f"string_{i}", result)

    print(html_template)

    # Write the data to a CSV file
    with open('output.csv', 'a', newline="", encoding='utf-8') as file:
        writer = csv.writer(file)

        infinitive = soup.select_one(
            "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(1) > span")
        third_state = soup.select_one(
            "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(3) > span")
        past = soup.select_one(
            "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(2) > span")

        writer.writerow([infinitive.text.strip(), third_state.text.strip(), past.text.strip(), html_template])


if __name__ == '__main__':
    main()
