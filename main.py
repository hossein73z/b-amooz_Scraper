import csv
import json
import sys

import pyperclip
import requests
from bs4 import BeautifulSoup, NavigableString, Tag, PageElement


def main(path: str, start: int) -> None:
    print(f'The file path is: {path}')

    # Opening the TSV file
    with open(path, 'r', newline="", encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')

        # Iterating through rows
        for index, row in enumerate(reader):
            if index >= start:
                word = row[0]

                find_word(word)

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

                        html_template = html_template.replace(f">present_{j}<" if i == 0 else f">past_{j}<",
                                                              f">{result}<")

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


def find_word(word):
    # Retrieve and parse data from b-amooz.com
    dic_url = f"https://dic.b-amooz.com/de/dictionary/w?word={word}"
    response = requests.get(dic_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    result_list: list[dict]

    # Find rows container
    container: list[Tag] = [child for child in soup.find(class_="container mt-2") if type(child) != NavigableString]

    # Divide list of rows by their type
    rows_list = []
    rows = []
    for div in container:
        if div.attrs['class'][0] == 'clearfix':
            rows_list.append(rows)
            rows = []
        else:
            rows.append(div)

    # Create List of data to be returned
    word_list = []
    for i, rows in enumerate(rows_list):
        word_data = {'role': None, 'deutsch': None, 'tags': None, 'meaning_data': []}
        for index, row in enumerate(rows):
            if index == 0:
                word_data['role'] = row.select_one("div > div > div > span").text.strip()[1:-1]
                word_data['deutsch'] = row.select_one("div > div > div > h1").text.strip()
                word_data['tags'] = [
                    item.text.strip() for item in row.select_one("div > div > div > div.my-3") if item.text.strip()
                ]
                word_data['extra'] = {key: val for key, val in tuple(
                    item.text.strip()[1:-1].split(": ") for item in row.select_one("div > div > div > div.text-muted")
                    if item.text.strip()[1:-1]
                )}

            else:

                word_data['meaning_data'].append({
                    "meaning": row.select_one("div > div > div.row > div > h2 > strong").text.strip(),
                    "examples": create_examples_from_html(row, word_data['role'])
                })
        word_list.append(word_data)

        pyperclip.copy(json.dumps(word_list))


def create_examples_from_html(row: Tag, word_role: str):
    if word_role == "اسم":
        temp_result = [tuple(text.text.strip()[2:].strip() for text in exp_box.select_one("div") if text.text.strip())
                       for exp_box in row.select_one("div > div > div.mdc-typography > ul") if
                       type(exp_box) != NavigableString and exp_box is not None]
        result = {key: val for key, val in temp_result}
        return result

    elif word_role == "فعل":
        temp_result = [tuple(text.text.strip()[2:].strip() for text in exp_box.select_one("div") if text.text.strip())
                       for exp_box in row.select_one("div > div > div.mdc-typography > div > ul") if
                       type(exp_box) != NavigableString and exp_box is not None]
        # result = {key: val for key, val in temp_result}
        return temp_result

    else:
        return None


if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv[1]) > 1 else input(
        'Please write the file name or its path: ')
start_row = int(sys.argv[2]) if len(sys.argv) > 2 else int(
    input('Please insert the starting row number: '))
# main(path=file_path, start=start_row - 1)
find_word('lesen')
